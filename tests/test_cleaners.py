import os
import time
import shutil
import logging
import unittest
import tempfile

from deltarepo.cleaners import clear_repos

from fixtures import *


class TestCaseClearRepos(unittest.TestCase):
    """Tests for util.clear_repos function"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="deltarepo-test-")
        self.logger = logging.getLogger("silent_loger")
        self.logger.addHandler(logging.NullHandler())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_clearrepos_emptydir(self):
        clear_repos(self.tmpdir)
        self.assertEqual(len(os.listdir(self.tmpdir)), 0)

    def test_clearrepos_one_repo_max_num(self):
        cp(REPO_00_PATH, self.tmpdir)

        clear_repos(self.tmpdir, max_num=-1)
        self.assertEqual(len(os.listdir(self.tmpdir)), 1)

        clear_repos(self.tmpdir, max_num=1)
        self.assertEqual(len(os.listdir(self.tmpdir)), 1)

        clear_repos(self.tmpdir, max_num=0)
        self.assertEqual(len(os.listdir(self.tmpdir)), 0)

    def test_clearrepos_two_repos_max_num(self):
        cp(REPO_00_PATH, self.tmpdir)
        cp(REPO_01_PATH, self.tmpdir)

        self.assertEqual(len(os.listdir(self.tmpdir)), 2)

        clear_repos(self.tmpdir, max_num=-1)
        self.assertEqual(len(os.listdir(self.tmpdir)), 2)

        clear_repos(self.tmpdir, max_num=3)
        self.assertEqual(len(os.listdir(self.tmpdir)), 2)

        clear_repos(self.tmpdir, max_num=2)
        self.assertEqual(len(os.listdir(self.tmpdir)), 2)

        clear_repos(self.tmpdir, max_num=1)
        self.assertEqual(len(os.listdir(self.tmpdir)), 1)

        clear_repos(self.tmpdir, max_num=0)
        self.assertEqual(len(os.listdir(self.tmpdir)), 0)

    def test_clearrepos_three_repos_max_age(self):
        cp(REPO_00_PATH, self.tmpdir)
        cp(REPO_01_PATH, self.tmpdir)
        cp(REPO_02_PATH, self.tmpdir)

        self.assertEqual(len(os.listdir(self.tmpdir)), 3)

        clear_repos(self.tmpdir, max_age=time.time())
        self.assertEqual(len(os.listdir(self.tmpdir)), 3)

        clear_repos(self.tmpdir, max_age=-1)
        self.assertEqual(len(os.listdir(self.tmpdir)), 3)

        clear_repos(self.tmpdir, max_age=1)
        self.assertEqual(len(os.listdir(self.tmpdir)), 0)
