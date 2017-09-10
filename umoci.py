#!/usr/bin/python

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

class Chdir:
      def __init__( self, newPath ):  
        self.savedPath = os.getcwd()
        os.chdir(newPath)

      def __del__( self ):
        os.chdir( self.savedPath )

class Umoci:
    def __init__(self, dir, name, chroot):
        self.parentdir = dir
        self.name = name
        self.chrootdir = chroot
        self.unpackdir = os.path.dirname(chroot)
        odir = Chdir(dir)
        cmd = 'umoci init --layout=%s' % name
        if 0 != os.system(cmd):
            # This already existed;  TODO - check if user wanted it cleaned
            pass

        if not self.HasTag("empty"):
            cmd = 'umoci new --image %s:empty' % name
            assert(0 == os.system(cmd))
            cmd = 'umoci unpack --image %s:empty %s' % (name, self.unpackdir)
            print "Executing: " + cmd
            assert(0 == os.system(cmd))
        del odir

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
        for t in self.ListTags().split('\n'):
            print "t %s len(t) %d l %d" % (t, len(t), l)
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
        odir = Chdir(self.parentdir)
        cmd = 'umoci repack --image %s:%s %s' % (self.name, tag, self.unpackdir)
        assert(0 == os.system(cmd))
        del odir

    def AddTag(self, tag, newtag):
        odir = Chdir(self.parentdir)
        cmd = 'umoci tag --image %s:%s %s' % (self.name, tag, newtag)
        assert(0 == os.system(cmd))
        del odir

    def Unpack(self, tag):
        odir = Chdir(self.parentdir)
        cmd = 'rm -rf %s' % self.unpackdir
        os.popen(cmd).read()
        cmd = 'umoci unpack --image %s:%s %s' % (self.name, tag, self.unpackdir)
        assert(0 == os.system(cmd))
        del odir

    def ExpandTarball(self, path):
        self.Unpack("empty")
        cmd = 'tar -C %s -xvf %s' % (self.chrootdir, path)
        os.system(cmd)

    # TODO - handle arguments
    def RunInChroot(self, filename):
        runname = self.chrootdir + "/ocirun"
        try:
            os.remove(runname)
        except:
            pass
        shutil.copy(filename, runname)
        cmd = "chmod ugo+x " + runname
        os.system(cmd)
        cmd = 'chroot %s /ocirun' % self.chrootdir
        ret = os.system(cmd)
        os.remove(runname)
        return ret == 0

    def ShellInChroot(self, data):
        # We need a shell of some sort
        if not os.path.exists(self.chrootdir + "/bin/sh"):
            os.makedirs(self.chrootdir + "/bin")
            shutil.copy("/bin/busybox", self.chrootdir + "/bin/sh")

        fullname = self.chrootdir + "/ocirun"
        with open(fullname, "w") as outfile:
            outfile.write("#/bin/sh\n")
            outfile.write(data)
        cmd = "chmod ugo+x " + fullname
        os.system(cmd)
        cmd = 'chroot %s /ocirun' % self.chrootdir
        ret = os.system(cmd)
        os.remove(self.chrootdir + "/ocirun")
        return ret == 0

    def CopyFile(self, src, dest):
        shutil.copy(src, self.chrootdir + "/" + dest)
