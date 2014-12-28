import os.path

# testdata/
TEST_DATA_PATH = os.path.normpath(os.path.join(__file__, "../testdata"))

# testdata/deltarepos
DELTAREPO_PATH = os.path.join(TEST_DATA_PATH, "deltarepos")
DELTAREPO_01_01 = os.path.join(DELTAREPO_PATH, "01_01")
DELTAREPO_01_02 = os.path.join(DELTAREPO_PATH, "01_02")
DELTAREPO_02_01 = os.path.join(DELTAREPO_PATH, "02_01")

# testdata/files/
TEST_DATA_FILES_PATH = os.path.normpath(os.path.join(TEST_DATA_PATH, "files"))

# testdata/files/deltarepos_01
DELTAREPOS_01_PATH = os.path.join(TEST_DATA_FILES_PATH, "deltarepos_01")
DELTAREPOS_01 = os.path.join(DELTAREPOS_01_PATH, "deltarepos.xml.xz")

# testdata/files/packages
PACKAGES_PATH = os.path.join(TEST_DATA_FILES_PATH, "packages")
PACKAGE_ARCHER = os.path.join(PACKAGES_PATH, "Archer-3.4.5-6.x86_64.rpm")
PACKAGE_RIMMER = os.path.join(PACKAGES_PATH, "Rimmer-1.0.2-2.x86_64.rpm")

# testdata/repo_*
REPO_00_PATH = os.path.join(TEST_DATA_PATH, "repo_00")
REPO_00_PRIMARY = os.path.join(REPO_00_PATH, "repodata", "1cb61ea996355add02b1426ed4c1780ea75ce0c04c5d1107c025c3fbd7d8bcae-primary.xml.gz")
REPO_01_PATH = os.path.join(TEST_DATA_PATH, "repo_01")
REPO_01_PRIMARY = os.path.join(REPO_01_PATH, "repodata", "341297672077ef71a5f8db569932d20975e906f192986cdfa8ab535f0c224d4d-primary.xml.gz")
REPO_02_PATH = os.path.join(TEST_DATA_PATH, "repo_02")
REPO_02_PRIMARY = os.path.join(REPO_02_PATH, "repodata", "a7715505059733a63c49e66fffc7cf3aee6217ae05bede274a2b3e3e143de7c6-primary.xml.gz")