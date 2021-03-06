"""
DeltaRepo package for Python.
This is the library for generation, application and handling of
DeltaRepositories.
The library is builded on the Createrepo_c library and its a part of it.

Copyright (C) 2013   Tomas Mlcoch

"""

import createrepo_c as cr

from .common import LoggingInterface
from .common import NO_COMPRESSION, GZ, BZ2, XZ
from .common import UNKNOWN_COMPRESSION, AUTO_DETECT_COMPRESSION
from .const import VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH
from .util import calculate_content_hash
from .plugins_common import Metadata
from .deltarepos import DeltaRepos, DeltaRepoRecord
from .deltametadata import DeltaMetadata, PluginBundle
from .applicator import DeltaRepoApplicator
from .generator import DeltaRepoGenerator
from .plugins import PLUGINS
from .plugins import needed_delta_metadata
from .errors import DeltaRepoError, DeltaRepoPluginError

__all__ = ['VERSION_MAJOR', 'VERSION_MINOR', 'VERSION_PATCH',
           'VERSION', 'VERBOSE_VERSION',
           'NO_COMPRESSION', 'GZ', 'BZ2', 'XZ',
           'UNKNOWN_COMPRESSION', 'AUTO_DETECT_COMPRESSION',
           'LoggingInterface', 'calculate_content_hash',
           'Metadata',
           'DeltaRepos', 'DeltaRepoRecord',
           'DeltaMetadata', 'PluginBundle',
           'DeltaRepoApplicator',
           'DeltaRepoGenerator',
           'needed_delta_metadata',
           'DeltaRepoError', 'DeltaRepoPluginError']

VERSION = "{0}.{1}.{2}".format(VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH)
VERBOSE_VERSION = "%s (createrepo_c: %s)" % (VERSION, cr.VERSION)

# Compression types
AUTO_DETECT_COMPRESSION = cr.AUTO_DETECT_COMPRESSION    # Compression auto-detection
UNKNOWN_COMPRESSION = cr.UNKNOWN_COMPRESSION            # Unknown compression type
NO_COMPRESSION = cr.NO_COMPRESSION                      # No compression
GZ_COMPRESSION = cr.GZ_COMPRESSION                      # Gzip compression
BZ2_COMPRESSION = cr.BZ2                                # Bzip2 compression type
XZ_COMPRESSION = cr.XZ                                  # Xz compression type

# Compression types - shortcuts
GZ = GZ_COMPRESSION                                     # Gzip compression type (shortcut)
BZ2 = BZ2_COMPRESSION                                   # Bzip2 compression type (shortcut)
XZ = XZ_COMPRESSION                                     # Xz compression type (shortcut)