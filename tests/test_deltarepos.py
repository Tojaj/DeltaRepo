import shutil
import unittest
import tempfile

import deltarepo
from deltarepo import DeltaRepoError
from deltarepo.deltarepos import DeltaRepos, DeltaRepoRecord

from .fixtures import *

XML_EMPTY = """<?xml version="1.0" encoding="UTF-8"?>
<deltarepos>
</deltarepos>
"""

XML_01 = """<?xml version="1.0" encoding="UTF-8"?>
<deltarepos>
  <deltarepo>
    <!-- <plugin name="MainDeltaPlugin" contenthash_type="sha256" dst_contenthash="043fds4red" src_contenthash="ei7as764ly"/> -->
    <location href="deltarepos/ei7as764ly-043fds4red" />
    <revision src="1387077123" dst="1387087456" />
    <contenthash src="a" dst="b" type="md5" />
    <timestamp src="1387075111" dst="1387086222" />
    <data type="primary" size="7766" />
    <repomd>
      <timestamp>123456789</timestamp>
      <size>963</size>
      <checksum type="sha256">foobarchecksum</checksum>
    </repomd>
  </deltarepo>
</deltarepos>
"""


class TestCaseDeltaRepos(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="deltarepo-test-")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_dump_and_load_empty_deltarepos_01(self):
        # Try to dump and load an empty DeltaRepos object (only via memory)
        content = DeltaRepos().dumps()
        dr = DeltaRepos().loads(content)
        self.assertEqual(len(dr.records), 0)

    def test_dump_and_load_empty_deltarepos_02(self):
        # Try to dump and load an empty DeltaRepos object (via files)
        path_without_suffix = os.path.join(self.tmpdir, "dump_empty.xml")

        path = DeltaRepos().dump(path_without_suffix)
        self.assertEqual(path, path_without_suffix+".xz")

        dr = DeltaRepos()
        dr.load(path)

        self.assertEqual(len(dr.records), 0)

    def test_dump_deltarepos_01(self):
        # Ty to dump fully filled DeltaRepos object
        rec = DeltaRepoRecord()

        # An empty record shouldn't be valid
        self.assertRaises(TypeError, rec.validate)

        # Fill the record with valid data
        rec.location_href = "deltarepos/ei7as764ly-043fds4red"
        rec.revision_src = "1387077123"
        rec.revision_dst = "1387086456"
        rec.contenthash_src = "a"
        rec.contenthash_dst = "b"
        rec.contenthash_type = "md5"
        rec.timestamp_src = 1387075111
        rec.timestamp_dst = 1387086222

        rec.set_data("primary", size=7766)

        rec.repomd_timestamp = 123456789
        rec.repomd_size = 963
        rec.repomd_checksums = [("sha256", "foobarchecksum")]

        # All mandatory arguments should be filled and thus the record should be valid
        rec.validate()

        # Dump the content to a file
        dr = DeltaRepos()
        dr.append_record(rec)
        path = dr.dump(os.path.join(self.tmpdir, "dump_01.xml"))

        # Load the content
        dr = DeltaRepos()
        dr.load(path)

        # Check the content
        self.assertEqual(len(dr.records), 1)
        self.assertEqual(dr.records[0].__dict__, rec.__dict__)

    def test_dump_and_load_with_different_compressions(self):
        # Try to dump DeltaRepos with different compression types
        dr = DeltaRepos()
        path_without_suffix = os.path.join(self.tmpdir, "dump_with_different_suffixes.xml")

        # Default (XZ)
        path = dr.dump(path_without_suffix)
        self.assertTrue(os.path.isfile(path))
        self.assertEqual(path, path_without_suffix+".xz")
        DeltaRepos().load(path)  # Exception shouldn't be raised

        # No compression
        path = dr.dump(path_without_suffix, deltarepo.NO_COMPRESSION)
        self.assertTrue(os.path.isfile(path))
        self.assertEqual(path, path_without_suffix)
        DeltaRepos().load(path)  # Exception shouldn't be raised

        # GZ
        path = dr.dump(path_without_suffix, deltarepo.GZ)
        self.assertTrue(os.path.isfile(path))
        self.assertEqual(path, path_without_suffix+".gz")
        DeltaRepos().load(path)  # Exception shouldn't be raised

        # BZ2
        path = dr.dump(path_without_suffix, deltarepo.BZ2)
        self.assertTrue(os.path.isfile(path))
        self.assertEqual(path, path_without_suffix+".bz2")
        DeltaRepos().load(path)  # Exception shouldn't be raised

        # XZ
        path = dr.dump(path_without_suffix, deltarepo.XZ)
        self.assertTrue(os.path.isfile(path))
        self.assertEqual(path, path_without_suffix+".xz")
        DeltaRepos().load(path)  # Exception shouldn't be raised

        # Error cases

        # Auto-detect compression
        self.assertRaises(DeltaRepoError, dr.dump, path_without_suffix, deltarepo.AUTO_DETECT_COMPRESSION)

        # Unknown compression
        self.assertRaises(DeltaRepoError, dr.dump, path_without_suffix, deltarepo.UNKNOWN_COMPRESSION)

    def test_parse_empty_deltarepos(self):
        # Try to parse deltarepos.xml with no items (the deltarepos.xml is valid!)
        path = os.path.join(self.tmpdir, "empty.xml")
        open(path, "w").write(XML_EMPTY)

        dr = DeltaRepos()
        dr.load(path)

        self.assertEqual(len(dr.records), 0)

    def test_parse_deltarepos_01(self):
        # Try to parse deltarepos.xml with some content
        path = os.path.join(self.tmpdir, "01.xml")
        open(path, "w").write(XML_01)

        dr = DeltaRepos()
        dr.load(path)

        self.assertEqual(len(dr.records), 1)

        rec = dr.records[0]

        self.assertEqual(rec.location_base, None)
        self.assertEqual(rec.location_href, "deltarepos/ei7as764ly-043fds4red")
        self.assertEqual(rec.size_total, 8729)
        self.assertEqual(rec.revision_src, "1387077123")
        self.assertEqual(rec.revision_dst, "1387087456")
        self.assertEqual(rec.timestamp_src, 1387075111)
        self.assertEqual(rec.timestamp_dst, 1387086222)

        self.assertEqual(rec.get_data("primary").get("size"), 7766)

        #self.assertEqual(len(rec.plugins), 1)
        #self.assertTrue("MainDeltaPlugin" in rec.plugins)
        #plugin = rec.plugins["MainDeltaPlugin"]
        #self.assertEqual(plugin, {'name': 'MainDeltaPlugin',
        #                          'src_contenthash': 'ei7as764ly',
        #                          'dst_contenthash': '043fds4red',
        #                          'contenthash_type': 'sha256'})
