#!/bin/bash

set -e  # Fail on first error

MY_DIR=`dirname $0`
export PYTHONPATH="../../"
MANAGEDELTAREPOS="../../bin/managedeltarepos"
REPOSDIR="../repos"

pushd $MY_DIR
rm -rfv deltarepo-*-*
rm -rfv deltarepos.xml.xz
$MANAGEDELTAREPOS $REPOSDIR/repo1/ $REPOSDIR/repo2/
$MANAGEDELTAREPOS $REPOSDIR/repo2/ $REPOSDIR/repo3/
popd
