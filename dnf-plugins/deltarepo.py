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

import dnf
import os.path
import subprocess
import tempfile


def run_cmd(cmd):
    proc = subprocess.Popen(cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            shell=True,
                            close_fds=True)
    ret = proc.wait()
    output = proc.stdout.read()
    return ret, output


class DeltaRepo(dnf.Plugin):

    name = 'deltarepo'

    def __init__(self, base, cli):
        self.base = base
        self.cache = '/var/cache/dnf/'

    def _out(self, msg):
        logger.debug('DeltaRepo plugin: %s', msg)

    def config(self):
        for repo in self.base.repos.iter_enabled():
            if not hasattr(repo, "deltarepobaseurl"):
                return  # DNF do not support deltarepobaseurl config option

            if not repo.deltarepobaseurl:
                continue  # No delta repos available

            if not os.path.isdir(repo.cachedir):
                continue  # No cache for the repo exists

            if repo.metadata is not None and repo.metadata.fresh:
                pass

            self._out("Processing repo \"{0}\"".format(repo.name))

            dir = tempfile.mkdtemp(prefix="dnf-deltarepo-plugin-", dir="/tmp")
            self._out("Temporary dir: {0}".format(dir))

            # Prepare command
            # Todo properly escape arguments
            cmd = ["repoupdater"]
            for url in repo.deltarepobaseurl:
                cmd.append("--drmirror '{0}'".format(url))
            for url in repo.baseurl:
                cmd.append("--repo '{0}'".format(url))
            if repo.metalink:
                cmd.append("--repomatalink '{0}'".format(repo.metalink))
            if repo.mirrorlist:
                cmd.append("--repomirrorlist '{0}'".format(repo.mirrorlist))
            cmd.append("--delta-or-nothing")
            cmd.append("--outputdir '{0}'".format(dir))
            cmd.append("--verbose")
            cmd.append("--update-only-available")
            cmd.append(repo.cachedir)
            cmd = " ".join(cmd)

            # Run the update
            self._out("Command: {0}".format(cmd))
            self._out("------------------------------------------------------")
            ret, output = run_cmd(cmd)
            self._out(output)
            self._out("------------------------------------------------------")

            # Check results
            if not ret:
                self._out("FAILED")
                return

            self._out("SUCCESS")

            # Move results to dnf cache (repo.cachedir)
            # Remove old .solv[x] files
        return