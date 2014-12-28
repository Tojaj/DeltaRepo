import os
import shutil
import logging
import unittest
import tempfile
import createrepo_c as cr

from deltarepo.util import pkg_id_str
from deltarepo.util import calculate_content_hash
from deltarepo.util import compute_file_checksum
from deltarepo.util import deltareposrecord_from_repopath
from deltarepo.util import gen_deltarepos_file
from deltarepo.errors import DeltaRepoError
from deltarepo.deltarepos import DeltaRepos

import fixtures
from fixtures import *


def cp(src, dst):
    """Copy helper for this unittest"""
    final_dst = os.path.join(dst, os.path.basename(src))
    shutil.copytree(src, final_dst)
    return final_dst


class TestCasePackageIdString(unittest.TestCase):
    """Tests for util.pkg_id_str function"""

    def test_pkg_id_str_01(self):
        pkg = cr.Package()
        idstr = pkg_id_str(pkg)
        self.assertEqual(idstr, "")

    def test_pkg_id_str_02(self):
        pkg = cr.package_from_rpm(fixtures.PACKAGE_RIMMER)
        idstr = pkg_id_str(pkg)
        self.assertEqual(idstr, "60dee92d523e8390eb7430fca8ffce461b5b2ad4eb19878cde5c16d72955ee49")

    def test_pkg_id_str_03(self):
        pkg = cr.package_from_rpm(fixtures.PACKAGE_ARCHER)
        idstr = pkg_id_str(pkg)
        self.assertEqual(idstr, "4e0b775220c67f0f2c1fd2177e626b9c863a098130224ff09778ede25cea9a9e")

        pkg.location_href = os.path.basename(fixtures.PACKAGE_ARCHER)
        idstr = pkg_id_str(pkg)
        self.assertEqual(idstr, "4e0b775220c67f0f2c1fd2177e626b9c863a098130224ff09778ede25cea9a9eArcher-3.4.5-6.x86_64.rpm")

        pkg.location_base = "https://foobar/"
        idstr = pkg_id_str(pkg)
        self.assertEqual(idstr, "4e0b775220c67f0f2c1fd2177e626b9c863a098130224ff09778ede25cea9a9eArcher-3.4.5-6.x86_64.rpmhttps://foobar/")

    def test_pkg_id_str_04(self):
        self.assertRaises(TypeError, pkg_id_str, None)
        self.assertRaises(TypeError, pkg_id_str, 123)
        self.assertRaises(TypeError, pkg_id_str, "xyz")
        self.assertRaises(TypeError, pkg_id_str, [])
        self.assertRaises(TypeError, pkg_id_str, {})
        self.assertRaises(TypeError, pkg_id_str, tuple([]))


class TestCaseContentHashCalculation(unittest.TestCase):
    """Tests for util.calculate_content_hash function"""

    def test_contenthashcalculation_for_empty_primary(self):
        # Default checksum (sha256)
        ch = calculate_content_hash(fixtures.REPO_00_PRIMARY)
        self.assertEqual(ch, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")

        # sha - Classical creterepo says sha, but means sha1 so expect the value for sha1
        ch = calculate_content_hash(fixtures.REPO_00_PRIMARY, checksum_type="sha")
        self.assertEqual(ch, "da39a3ee5e6b4b0d3255bfef95601890afd80709")

        # sha1
        ch = calculate_content_hash(fixtures.REPO_00_PRIMARY, checksum_type="sha1")
        self.assertEqual(ch, "da39a3ee5e6b4b0d3255bfef95601890afd80709")

        # sha224
        ch = calculate_content_hash(fixtures.REPO_00_PRIMARY, checksum_type="sha224")
        self.assertEqual(ch, "d14a028c2a3a2bc9476102bb288234c415a2b01f828ea62ac5b3e42f")

        # sha512
        ch = calculate_content_hash(fixtures.REPO_00_PRIMARY, checksum_type="sha512")
        self.assertEqual(ch, "cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e")

    def test_contenthashcalculation(self):
        # Default checksum (sha256)
        ch = calculate_content_hash(fixtures.REPO_01_PRIMARY)
        self.assertEqual(ch, "4d1c9f8b7c442adb5f90fda368ec7eb267fa42759a5d125001585bc8928b3967")

        # sha - Classical creterepo says sha, but means sha1 so expect the value for sha1
        ch = calculate_content_hash(fixtures.REPO_01_PRIMARY, checksum_type="sha")
        self.assertEqual(ch, "c35d59311257eff6890e79e48526f4cd2bf66113")

        # sha1
        ch = calculate_content_hash(fixtures.REPO_01_PRIMARY, checksum_type="sha1")
        self.assertEqual(ch, "c35d59311257eff6890e79e48526f4cd2bf66113")

        # sha224
        ch = calculate_content_hash(fixtures.REPO_01_PRIMARY, checksum_type="sha224")
        self.assertEqual(ch, "6bc0ac11a5e611ed5371c0a19a3ed18f3c965c7dba4c1911cb0f7e4e")

        # sha512
        ch = calculate_content_hash(fixtures.REPO_01_PRIMARY, checksum_type="sha512")
        self.assertEqual(ch, "882e705c2f95d222ae525295ff440b4da4d30a0a857062ece3c05cc2a45b32ecfadf5614613eecb222a01aea8e4cf91695eed54433afb0a27341ca061de18933")

    def test_contenthashcalculation_for_badfile(self):
        # Bad XML type (e.g. other.xml instead of primary.xml) should return the same hash as for empty file
        ch = calculate_content_hash(fixtures.DELTAREPOS_01)
        self.assertEqual(ch, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")


class TestCaseComputeFileChecksum(unittest.TestCase):
    """Tests for util.compute_file_checksum function"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="deltarepo-test-")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_computefilechecksum_for_empty_file(self):
        path = os.path.join(self.tmpdir, "empty_file")
        open(path, "w").close()

        # Default checksum (sha256)
        calculated = compute_file_checksum(path)
        self.assertEqual(calculated, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")

        # sha - Classical creterepo says sha, but means sha1 so expect the value for sha1
        calculated = compute_file_checksum(path, type="sha")
        self.assertEqual(calculated, "da39a3ee5e6b4b0d3255bfef95601890afd80709")

        # sha1
        calculated = compute_file_checksum(path, type="sha1")
        self.assertEqual(calculated, "da39a3ee5e6b4b0d3255bfef95601890afd80709")

        # sha224
        calculated = compute_file_checksum(path, type="sha224")
        self.assertEqual(calculated, "d14a028c2a3a2bc9476102bb288234c415a2b01f828ea62ac5b3e42f")

        # sha512
        calculated = compute_file_checksum(path, type="sha512")
        self.assertEqual(calculated, "cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e")


class TestCaseDeltaReposRecordFromRepoPath(unittest.TestCase):
    """Tests for util.deltareposrecord_from_repopath function"""

    def test_deltareposrecord_from_non_existing_path(self):
        self.assertRaises(IOError, deltareposrecord_from_repopath, "some/non/existing/path")

    def test_deltareposrecord_from_repo_that_is_not_deltarepo(self):
        self.assertRaises(DeltaRepoError, deltareposrecord_from_repopath, fixtures.REPO_00_PATH)

    def test_deltareposrecord_from_valid_deltarepo(self):
        rec = deltareposrecord_from_repopath(fixtures.DELTAREPO_01_02)

        # Check values parsed from repo's deltametadata.xml
        self.assertEqual(rec.location_base, None)
        self.assertEqual(rec.location_href, fixtures.DELTAREPO_01_02)
        self.assertEqual(rec.revision_src, "1378724582")
        self.assertEqual(rec.revision_dst, "1413550726")
        self.assertEqual(rec.contenthash_src, "4d1c9f8b7c442adb5f90fda368ec7eb267fa42759a5d125001585bc8928b3967")
        self.assertEqual(rec.contenthash_dst, "29ff875f99fe44a4b697ffe19bee5e874b5c61c5b0517f7f0772caae292b2bf7")
        self.assertEqual(rec.contenthash_type, "sha256")
        self.assertEqual(rec.timestamp_src, 1378724581)
        self.assertEqual(rec.timestamp_dst, 1413550726)

        # Check values calculated for repo's repomd.xml
        repomd_path = os.path.join(fixtures.DELTAREPO_01_02, "repodata", "repomd.xml")
        self.assertEqual(rec.repomd_timestamp, int(os.path.getmtime(repomd_path)))
        self.assertEqual(rec.repomd_size, os.path.getsize(repomd_path))
        checksumval = compute_file_checksum(repomd_path)
        self.assertEqual(rec.repomd_checksums, [("sha256", checksumval)])

    def test_deltareposrecord_from_valid_deltarepo_with_path_prefix(self):
        rec = deltareposrecord_from_repopath(fixtures.DELTAREPO_01_02, prefix_to_strip=os.path.dirname(fixtures.DELTAREPO_01_02))
        self.assertEqual(rec.location_base, None)
        self.assertEqual(rec.location_href, os.path.basename(fixtures.DELTAREPO_01_02))


class TestCaseDeltaReposGeneration(unittest.TestCase):
    """Tests for util.gen_deltarepos_file function"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="deltarepo-test-")
        self.logger = logging.getLogger("silent_loger")
        self.logger.addHandler(logging.NullHandler())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_no_repos(self):
        # Try to generate deltarepos.xml.xz for an empty dir
        dir = tempfile.mkdtemp(prefix="no_repos-", dir=self.tmpdir)
        path = os.path.join(dir, "deltarepos.xml.xz")
        ret = gen_deltarepos_file(dir, self.logger)
        self.assertEqual(ret, path)
        self.assertTrue(os.path.isfile(path))

    def test_bad_repos(self):
        # Try to generate deltarepos.xml.xz for a dir with a bad repo
        dir = tempfile.mkdtemp(prefix="zero_repos-", dir=self.tmpdir)
        path = os.path.join(dir, "deltarepos.xml.xz")
        os.makedirs(os.path.join(dir, "bad_repo", "repodata"))
        self.assertRaises(DeltaRepoError, gen_deltarepos_file, dir, self.logger)
        ret = gen_deltarepos_file(dir, self.logger, force=True)
        self.assertEqual(ret, path)
        self.assertTrue(os.path.isfile(path))

    def test_one_repo(self):
        # Try to generate deltarepos.xml.xz for a directory with one repo
        dir = tempfile.mkdtemp(prefix="one_repo-", dir=self.tmpdir)
        path = os.path.join(dir, "deltarepos.xml.xz")
        cp(DELTAREPO_01_01, dir)
        ret = gen_deltarepos_file(dir, self.logger)
        self.assertEqual(ret, path)
        self.assertTrue(os.path.isfile(path))

        dr = DeltaRepos()
        dr.load(path)
        self.assertEqual(len(dr.records), 1)
        rec = dr.records[0]
        self.assertEqual(rec.location_href, os.path.basename(DELTAREPO_01_01))

    def test_two_repos(self):
        # Try to generate deltarepos.xml.xz for a directory with two repos
        dir = tempfile.mkdtemp(prefix="two_repos-", dir=self.tmpdir)
        path = os.path.join(dir, "deltarepos.xml.xz")
        cp(DELTAREPO_01_01, dir)
        cp(DELTAREPO_01_02, dir)
        ret = gen_deltarepos_file(dir, self.logger)
        self.assertEqual(ret, path)
        self.assertTrue(os.path.isfile(path))

        dr = DeltaRepos()
        dr.load(path)
        self.assertEqual(len(dr.records), 2)
        rec = dr.records[0]
        self.assertEqual(rec.location_href, os.path.basename(DELTAREPO_01_01))
        rec = dr.records[1]
        self.assertEqual(rec.location_href, os.path.basename(DELTAREPO_01_02))

    def test_update_01(self):
        # Try to update deltarepos.xml.xz (adition of a repo)
        dir = tempfile.mkdtemp(prefix="update_01-", dir=self.tmpdir)
        path = os.path.join(dir, "deltarepos.xml.xz")

        cp(DELTAREPO_01_01, dir)
        ret = gen_deltarepos_file(dir, self.logger)
        self.assertEqual(ret, path)
        self.assertTrue(os.path.isfile(path))

        cp(DELTAREPO_01_02, dir)
        ret = gen_deltarepos_file(dir, self.logger, update=True)
        self.assertEqual(ret, path)
        self.assertTrue(os.path.isfile(path))

        dr = DeltaRepos()
        dr.load(path)
        self.assertEqual(len(dr.records), 2)
        rec = dr.records[0]
        self.assertEqual(rec.location_href, os.path.basename(DELTAREPO_01_01))
        rec = dr.records[1]
        self.assertEqual(rec.location_href, os.path.basename(DELTAREPO_01_02))

    def test_update_02(self):
        # Try to update deltarepos.xml.xz (deletion of a repo)
        dir = tempfile.mkdtemp(prefix="update_02-", dir=self.tmpdir)
        path = os.path.join(dir, "deltarepos.xml.xz")

        first = cp(DELTAREPO_01_01, dir)
        cp(DELTAREPO_01_02, dir)
        ret = gen_deltarepos_file(dir, self.logger)
        self.assertEqual(ret, path)
        self.assertTrue(os.path.isfile(path))

        dr = DeltaRepos()
        dr.load(path)
        self.assertEqual(len(dr.records), 2)
        rec = dr.records[0]
        self.assertEqual(rec.location_href, os.path.basename(DELTAREPO_01_01))
        rec = dr.records[1]
        self.assertEqual(rec.location_href, os.path.basename(DELTAREPO_01_02))

        shutil.rmtree(first)
        ret = gen_deltarepos_file(dir, self.logger, update=True)
        self.assertEqual(ret, path)
        self.assertTrue(os.path.isfile(path))

        dr = DeltaRepos()
        dr.load(path)
        self.assertEqual(len(dr.records), 1)
        rec = dr.records[0]
        self.assertEqual(rec.location_href, os.path.basename(DELTAREPO_01_02))