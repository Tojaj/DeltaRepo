#!/bin/bash

CURRENT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd)"
DELTAREPO_DIR="$( cd "$CURRENT_DIR/.." && pwd )"
export PATH="$DELTAREPO_DIR/bin:$PATH"
export PYTHONPATH="$DELTAREPO_DIR/"

echo "export PATH=$PATH"
echo "export PYTHONPATH=$PYTHONPATH"

rm -rf test/
mkdir test/
cp -r repos/repo1 test/
cp -r repos/repo3 test/

repoupdater --verbose test/repo1/ $@ --repo "file://$CURRENT_DIR/test/repo3/" --drmirror "file://$CURRENT_DIR/deltarepos/"

echo ""
echo ""

rm -rf test2/
mkdir test2/
cp -r repos/repo1 test2/
cp -r repos/repo3 test2/
rm -f test2/repo1/repodata/*sqlite*
rm -f test2/repo1/repodata/*other*
rm -f test2/repo1/repodata/*foobar*

repoupdater --verbose test2/repo1/ $@ --repo "file://$CURRENT_DIR/test/repo3/" --drmirror "file://$CURRENT_DIR/deltarepos/"
