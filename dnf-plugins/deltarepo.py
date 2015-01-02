# coding=utf-8
# generate_completion_cache.py - generate cache for dnf bash completion
# Copyright © 2013 Elad Alfassa <elad@fedoraproject.org>

# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# the GNU General Public License v.2, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the
# GNU General Public License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.

from __future__ import absolute_import
from __future__ import unicode_literals
from dnf.i18n import ucd
from dnfpluginscore import logger

import sys
import dnf
import os.path
import dnf.repo
import tempfile
import subprocess

PY3 = sys.version_info.major >= 3

if PY3:
    from shlex import quote
else:
    from pipes import quote


# Hardcoded mirrors - only for early devel phase - will be removed in future
DELTA_MIRRORS = {
    "rawhide": ["http://10.34.34.33/deltamirror/rawhide/$basearch/os/"],
    "fedora": ["http://10.34.34.33/deltamirror/$releasever/$basearch/os/"],
}


def run_cmd(cmd):
    proc = subprocess.Popen(cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            close_fds=True)
    ret = proc.wait()
    output = proc.stdout.read()
    return ret, output


class DeltaRepo(dnf.Plugin):

    name = 'deltarepo'

    def __init__(self, base, cli):
        self.base = base
        self.cache = '/var/cache/dnf/'

    def _info(self, msg):
        logger.info('{0} plugin: {1}'.format(self.__class__.__name__, msg))

    def _debug(self, msg):
        logger.debug('{0} plugin: {1}'.format(self.__class__.__name__, msg))

    def config(self):
        for repo in self.base.repos.iter_enabled():
            # XXX: Early devel phase hack - remove in future
            if repo.id in DELTA_MIRRORS:
                repo.deltarepobaseurl = DELTA_MIRRORS[repo.id]

            if not hasattr(repo, "deltarepobaseurl"):
                # DNF do not support deltarepobaseurl config option
                return

            if not repo.deltarepobaseurl:
                # No delta repos available
                continue

            if not os.path.isdir(repo.cachedir):
                # No cache for the repo exists yet
                continue

            if repo.metadata is not None and repo.metadata.fresh:
                # Don't try to update repodata yet
                #return
                pass  # XXX: Devel hack

            if repo.sync_strategy in (dnf.repo.SYNC_LAZY, dnf.repo.SYNC_ONLY_CACHE):
                # Current metadata are not needed
                continue

            # Start working
            self._info("Processing \"{0}\"".format(repo.name))

            # Expand variables in URLs
            deltarepobaseurls = []
            for url in repo.deltarepobaseurl:
                for var, sub in repo.substitutions.iteritems():
                    url = url.replace("$"+var, sub)
                deltarepobaseurls.append(url)

            # Create a temporary directory
            dir = tempfile.mkdtemp(prefix="dnf-deltarepo-plugin-", dir="/tmp")
            self._debug("Temporary dir: {0}".format(dir))

            # Prepare command
            # Todo properly escape arguments
            cmd = ["repoupdater"]
            for url in deltarepobaseurls:
                cmd.append("--drmirror")
                cmd.append(url)
            for url in repo.baseurl:
                cmd.append("--repo")
                cmd.append(url)
            if repo.metalink:
                cmd.append("--repometalink")
                cmd.append(repo.metalink)
            if repo.mirrorlist:
                cmd.append("--repomirrorlist")
                cmd.append(repo.mirrorlist)
            cmd.append("--delta-or-nothing")
            #cmd.append("--force-deltas") # XXX
            cmd.append("--outputdir")
            cmd.append(dir)
            cmd.append("--verbose")
            cmd.append("--debug")
            cmd.append("--update-only-available")
            cmd.append(repo.cachedir)

            cmd_str = " ".join([quote(component) for component in cmd])

            # Run the update
            self._debug("Command: {0}".format(cmd_str))
            self._debug("------------------------------------------------------")
            ret, output = run_cmd(cmd)
            self._debug(output)
            self._debug("------------------------------------------------------")

            # Check results
            if ret != 0:
                self._debug("Repo haven't been updated by deltas")
                return

            self._info("The \"{0}\" have been updated by deltas".format(repo.name))

            # Remove old .solv[x] files
            cached_files_to_remove = (
                "{0}.solv",
                "{0}-filenames.solvx",
                "{0}-presto.solvx",
                "{0}-updateinfo.solvx"
            )

            for template in cached_files_to_remove:
                fn = template.format(repo.id)
                path = os.path.join(self.base.conf.cachedir, fn)
                if os.path.isfile(path):
                    self._debug("Removing old cache file: {0}".format(path))
                    os.unlink(path)

        return