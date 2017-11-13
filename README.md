# genoci

genoci is a tool for generating OCI images from yaml specifications.

The goal is to produce builds in layers, i.e.

```yaml
cirros:
  base: empty
  expand: ./cirros.tar.gz
modified:
  base: cirros
  run: |
    echo "Hello, world" > /hw
  entrypoint: /bin/echo "hello world"
```

or

```yaml
centos:
  base: empty
  expand: /var/cache/atom/centos.tar.gz
updated:
  base: centos
  run: |
    yum -y update
withskopeo:
  base: centos
  install: /var/cache/atom/skopeo-0.1.23-1.git1bbd87f.el7.x86_64.rpm 
filled:
  copy:
    - /etc/hosts etc_hosts
    - /etc/hostname etc_hostname
```

To test with the included cirros.yaml, first

```bash
wget https://download.cirros-cloud.net/0.3.5/cirros-0.3.5-i386-lxc.tar.gz
ln -s cirros-0.3.5-i386-lxc.tar.gz cirros.tar.gz
genoci centos.yaml
```

After running that, you will have an OCI layout with (at least) two layers and
four tags (existing layouts are not deleted, so you may have more, older
layers).  So you can

```bash
# umoci ls --layout oci
cirros-2017-09-26_1
cirros
modified-2017-09-26_1
modified
```

Each "tag-(date)" tag is from a unique genoci build.  Each "tag" without a date
will point to the latest build.  If you run genoci again with the same file,
you'll get:

```bash
# umoci ls --layout oci
cirros-2017-09-26_1
cirros-2017-09-26_2
cirros
modified-2017-09-26_1
modified-2017-09-26_2
modified
```

Notes:

1. each layer target must have a base and an action.
1. 'base' is either 'empty' or an existing tag.  The existing tag
can be either already existing in the OCI layout, or produced earlier
in the build.
1. genoci currently won't try to stop you from having circular deps.
1. 'expand' means expand a tarball
1. 'run' means run a script from the host (with no arguments), or
run shell in the container (with arguments).  This works for now but
is not clean/robust and will be cleaned up.
1. 'copy' means copy a file from the host into the container.  It
should be a single pair of filenames separated by a space, the
source path on the host and the relative dest path in the container,
or a yaml list of such pairs.
1. 'install' means install a .rpm or .deb package.
1. 'pre' and 'post' are hooks which run before an after the actions.
I've used this for instance to mount an /etc/resolv.conf.

## Dependencies:

This requires umoci and will likely require skopeo, depending on
where we cut off the workflow.

## Use with lpack

This tool can be used with [lpack](http://github.com/atom-deps/lpack)
for transparent exploitation of copy-on-write btrfs subvolumes for
quick iterations.  Currently this is quite inflexible, as we are still
figuring out ideal workflows.  (Feedback very much appreciated.)  To
start using lpack, fetch the lpack git tree, copy all ".sh" files into
/usr/share/lpack, and copy the lpack script to /usr/bin.  Next, you need
to setup a btrfs to use.  Currently only a loopback filesystem is supported.
You can set this up using:

```bash
lpack setup
```

This will setup btrfs in your local directory.  If you prefer to keep it
elsewhere, then create ~/.config/atom/config.yaml specifying the
location for loopback file and mounted btrfs:

```bash
mkdir -p ~/.config/atom
cat > ~/.config/atom/config.yaml << EOF
driver: btrfs
lofile: /tmp/lofile
btrfsmount: /tmp/btrfs.mount
EOF
lpack setup
```

You can also specify an alternate location for your OCI layout, using
the variable 'layoutdir' in the same configuration file.

Once this is done, genoci should take care to unpack the OCI layout into
your btrfs filesystem on each run (skipping the work for any already-expanded
images).  For each layer it creates, it will ask lpack to 'checkout' the
base tag, make the changes there, then ask lpack to 'checkin' the new updated
tree with the specified new tag.

When done, use 'lpack unsetup' to unmount and destroy the btrfs.  Note that
you really want to do this before updating your ~/.config/atom/config.yaml,
else you'll end up with stray btrfs filesystems.

## Todo

Next todos are:

1. run in a user namespace by default.  This will require a newer
umoci build which won't fail on things like expanding tarballs with
devices.

1. be more flexible with respect to CoW filesystem setups.  I.e. support
existing btrfs filesystems and maybe LVM.

In the meantime, depending on the install steps required, many
builds should be doable in a user namespace by using:

```bash
lxc-usernsexec ./genoci data.yaml
```

Then again, time is probably better spent on making sure these work
correctly in the replacement tool, stacker.

## Warning

A bug in this tool can easily wipe your system or kick your kitten.
