TARGET_DIR="./"

if [ "$#" -eq "0" ]; then
    GITREV=`git rev-parse --short HEAD`
else
    GITREV=$1
fi

echo "Generate tarball for revision: $GITREV"

git archive ${GITREV} --prefix=deltarepo/ | xz > $TARGET_DIR/deltarepo-${GITREV}.tar.xz
