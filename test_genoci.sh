#!/bin/bash -xeu

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

if [ $(id -u) != 0 ]; then
	echo "be root"
	exit 1
fi

## Tests to be written:
## 1. basic recipe building:
##    a. expand
##    b. run
##       i. run: cmd1
##       i. run: followed by list
##       i. run: |
##    c. install (deb) (if ubuntu.tar.xz available)
##    d. install (rpm) (if centos.tar.xz available)
##    e. copy
##    f. entyrpoint
## 2. Test config file parsing

testdir=$(mktemp -d -p .)

if [ ! -f busybox.tar.gz ]; then
    mkdir busybox-dir
    wget https://busybox.net/downloads/binaries/1.27.1-i686/busybox
    chmod ugo+x busybox
    for dir in dev proc bin usr lib; do
        mkdir -p "busybox-dir/${dir}"
    done
    mv busybox "busybox-dir/bin/"
    for bin in sh ln ls ps echo; do
        ln -s busybox "busybox-dir/bin/${bin}"
    done
    tar zcf busybox.tar.gz -C busybox-dir .
fi

cp busybox.tar.gz "${testdir}/"

cat > "${testdir}/r1.yaml" << EOF
bb:
  base: empty
  expand: busybox.tar.gz
run1:
  base: bb
  run: |
    echo ab > ab
run2:
  base: bb
  run:
    - echo ab > ab
    - echo cd > cd
run3:
  base: bb
  run: echo ab > ab
expand1:
  base: bb
  expand:
    - tar1.tgz
    - tar2.tar.xz
copy1:
  base: run3
  copy: file1 file1
copy2:
  base: copy1
  copy:
    - file1 file1
    - file2 file2
  entrypoint: /bin/sh
prepost:
  base: bb
  pre: touch %ROOT%/ab
  post: rm %ROOT%/ab
  run: test -f /ab
EOF

mkdir "${testdir}/tar1"
touch "${testdir}/tar1/ab"
mkdir "${testdir}/tar2"
touch "${testdir}/tar2/cd"
tar -zcf "${testdir}/tar1.tgz" -C "${testdir}/tar1" .
tar -Jcf "${testdir}/tar2.tar.xz" -C "${testdir}/tar2" .

echo file1 > "${testdir}/file1"
echo file2 > "${testdir}/file2"

cd "${testdir}"
../genoci ./r1.yaml

# Verify
umoci unpack --image oci:run1 run1
grep ab run1/rootfs/ab

umoci unpack --image oci:run2 run2
grep ab run2/rootfs/ab
grep cd run2/rootfs/cd

umoci unpack --image oci:run3 run3
grep ab run3/rootfs/ab

umoci unpack --image oci:expand1 expand1
test -f expand1/rootfs/ab
test -f expand1/rootfs/cd

umoci unpack --image oci:copy1 copy1
diff file1 copy1/rootfs/file1

umoci unpack --image oci:copy2 copy2
diff file2 copy2/rootfs/file2

umoci unpack --image oci:prepost prepost
! test -f prepost/rootfs/ab
