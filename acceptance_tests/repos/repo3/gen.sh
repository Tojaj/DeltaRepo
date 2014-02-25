#!/bin/bash

MY_DIR=`dirname $0`

if [[ -z "$CREATEREPO" ]]
then
    CREATEREPO="createrepo_c"
fi

if [[ -z "$MODIFYREPO" ]]
then
    MODIFYREPO="modifyrepo_c"
fi

pushd "$MY_DIR"
$CREATEREPO $EXTRAARGS --pkglist pkglist --groupfile comps.xml --revision "3th repo" --content "Content tag 123456" .
$MODIFYREPO foobar repodata/
popd
