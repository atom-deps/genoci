#!/usr/bin/python3

# umoci.py: a python class wrapping the umoci binary, for use by genoci.
#
# Copyright (C) 2017 Cisco Inc
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import os
import shutil
import subprocess
import sys

class Chdir:
      def __init__( self, newPath ):  
        self.savedPath = os.getcwd()
        os.chdir(newPath)

      def __del__( self ):
        os.chdir( self.savedPath )

class Umoci:
    # basedir is the directory under which the oci layout is found
    # name is the name of the oci layout
    # lpack_config is a dict with optional parameters to pass to lpack
    def __init__(self, basedir, name, lpack_config):
        self.parentdir = basedir
        self.name = name
        self.unpackdir = basedir + "/unpacked"
        self.chrootdir = self.unpackdir + "/rootfs"
        self.lpack_config = lpack_config
        odir = Chdir(basedir)
        cmd = 'umoci init --layout=%s' % name
        if 0 != os.system(cmd):
            # This already existed
            pass

        self.clearconfig()

        needempty = False
        if not self.HasTag("empty"):
            cmd = 'umoci new --image %s:empty' % name
            assert(0 == os.system(cmd))
            needempty = True

        # If lpack was requested, set it up.
        # Trust lpack to use the same config we are.
        if lpack_config["driver"] == "btrfs":
            self.chrootdir = lpack_config["btrfsmount"] + "/mounted"
            if needempty:
                os.system("umoci unpack --image %s:empty %s" % (name, self.unpackdir))
                os.system("umoci repack --image %s:empty %s" % (name, self.unpackdir))
                os.system("rm -rf -- " + self.unpackdir)
                os.system("btrfs subvolume create %s/empty" % lpack_config["btrfsmount"])
            del odir
            os.system("lpack unpack")
            return
        elif lpack_config["driver"] == "lvm":
            self.chrootdir = lpack_config["lvbasedir"] + "/mounted"
            if needempty:
                os.system("umoci unpack --image %s:empty %s" % (name, self.unpackdir))
                os.system("umoci repack --image %s:empty %s" % (name, self.unpackdir))
                os.system("rm -rf -- " + self.unpackdir)
            del odir
            os.system("lpack unpack")
            return
        if needempty:
            os.system("umoci unpack --image %s:empty %s" % (name, self.unpackdir))
            os.system("umoci repack --image %s:empty %s" % (name, self.unpackdir))
            os.system("rm -rf -- " + self.unpackdir)
        del odir

    def clearconfig(self):
        self.configs = { "entrypoint": [], "environment": [] }

    def ListTags(self):
        odir = Chdir(self.parentdir)
        p = subprocess.Popen(["umoci", "ls", "--layout", self.name],
                                stdout = subprocess.PIPE,
                                stderr = subprocess.PIPE)
        out, err = p.communicate()
        del odir
        if len(err) != 0:
            return []
        return out

    def NextVersionTag(self, tag):
        version = 1
        today = str(datetime.date.today())
        datetag = tag + "-" + today + "_"
        l = len(datetag)
        for t in self.ListTags().decode('utf8').split('\n'):
            if len(t) <= l:
                continue
            if t[0:l] != datetag:
                continue
            try:
                newv = int(t[l:])
                if newv >= version:
                    version = newv + 1
            except:
                pass
        return datetag + str(version)

    def HasTag(self, tag):
        odir = Chdir(self.parentdir)
        cmd = 'umoci ls --layout %s | grep "^%s$"' % (self.name, tag)
        found = 0 == os.system(cmd)
        del odir
        return found

    def DelTag(self, tag, force = True):
        odir = Chdir(self.parentdir)
        cmd = 'umoci rm --image %s:%s' % (self.name, tag)
        ret = os.system(cmd)
        if force:
            assert(0 == ret)
        cmd = 'umoci gc --layout ' + self.name
        ret = os.system(cmd)
        if force:
            assert(0 == ret)
        del odir

    def Tag(self, tag):
        if self.lpack_config["driver"] != "vfs":
            cmd = "lpack checkin " + tag
            ret = os.system(cmd)
            if ret != 0:
                print("Error checking in tag: %s" % tag)
                sys.exit(1)
        else:
            odir = Chdir(self.parentdir)
            cmd = 'umoci repack --image %s:%s %s' % (self.name, tag, self.unpackdir)
            assert(0 == os.system(cmd))
            del odir

        cfgcmd = 'umoci config --image %s/%s:%s' % (self.parentdir, self.name, tag)
        # set the entrypoint if specified
        if len(self.configs["entrypoint"]) != 0:
            epargs = ''
            for arg in self.configs["entrypoint"]:
                epargs = epargs + ' --config.cmd="' + arg + '"'
            ret = os.system(cfgcmd + epargs)
            assert(0 == ret)

        # set environment if in config
        if len(self.configs["environment"]) != 0:
            for arg in self.configs["environment"]:
                envargs = envargs + ' --config.env="' + arg + '"'
            ret = os.system(cfgcmd + envargs)
            assert(0 == ret)

    def AddTag(self, tag, newtag):
        odir = Chdir(self.parentdir)
        cmd = 'umoci tag --image %s:%s %s' % (self.name, tag, newtag)
        assert(0 == os.system(cmd))
        del odir

    def Unpack(self, tag):
        if self.lpack_config["driver"] != "vfs":
            ret = os.system("lpack checkout " + tag)
            if ret != 0:
                print("Error checking out base tag: %s" % tag)
                sys.exit(1)
            return
        odir = Chdir(self.parentdir)
        cmd = 'rm -rf -- %s' % self.unpackdir
        os.popen(cmd).read()
        cmd = 'umoci unpack --image %s:%s %s' % (self.name, tag, self.unpackdir)
        assert(0 == os.system(cmd))
        del odir

    # TODO - handle arguments
    def RunInChroot(self, filename, in_host_ns):
        runname = self.chrootdir + "/ocirun"
        try:
            os.remove(runname)
        except:
            pass
        shutil.copy(filename, runname)
        cmd = "chmod ugo+x " + runname
        os.system(cmd)
        if in_host_ns:
            cmd = '%s/ocirun' % self.chrootdir
        else:
            cmd = 'chroot %s /ocirun' % self.chrootdir
        ret = os.system(cmd)
        os.remove(runname)
        return ret == 0

    def ShellInChrootAsFile(self, data, in_host_ns):
        # We need a shell of some sort
        if not os.path.exists(self.chrootdir + "/bin/sh"):
            try:
                os.makedirs(self.chrootdir + "/bin")
            except:  # ignore already existing
                pass
            shutil.copy("/bin/busybox", self.chrootdir + "/bin/sh")

        fullname = self.chrootdir + "/ocirun"
        with open(fullname, "w") as outfile:
            outfile.write("#/bin/sh\n")
            outfile.write(data)
        cmd = "chmod ugo+x " + fullname
        os.system(cmd)
        if in_host_ns:
            cmd = '%s/ocirun' % self.chrootdir
        else:
            cmd = 'chroot %s /ocirun' % self.chrootdir
        ret = os.system(cmd)
        os.remove(self.chrootdir + "/ocirun")
        return ret == 0

    def ShellInChroot(self, data, in_host_ns):
        return self.ShellInChrootAsFile(data, in_host_ns)

    def CopyFile(self, src, dest):
        shutil.copy(src, self.chrootdir + "/" + dest)
        return True
