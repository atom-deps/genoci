#!/usr/bin/python

import os

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
        cmd = 'umoci ls --layout %s | grep "^%s$"' % (self.name, tag)
        found = 0 == os.system(cmd)
        del odir
        return found

    def HasTag(self, tag):
        odir = Chdir(self.parentdir)
        cmd = 'umoci ls --layout %s | grep "^%s$"' % (self.name, tag)
        found = 0 == os.system(cmd)
        del odir
        return found

    def DelTag(self, tag):
        odir = Chdir(self.parentdir)
        cmd = 'umoci rm --image %s:%s' % (self.name, tag)
        assert(0 == os.system(cmd))
        cmd = 'umoci gc --layout ' + self.name
        assert(0 == os.system(cmd))
        del odir

    def Tag(self, tag):
        odir = Chdir(self.parentdir)
        cmd = 'umoci repack --image %s:%s %s' % (self.name, tag, self.unpackdir)
        assert(0 == os.system(cmd))
        del odir

    def Unpack(self, tag):
        cmd = 'rm -rf %s' % self.unpackdir
        os.popen(cmd).read()
        odir = Chdir(self.parentdir)
        cmd = 'umoci unpack --image %s:%s %s' % (self.name, tag, self.unpackdir)
        assert(0 == os.system(cmd))
        del odir
