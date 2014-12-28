import os.path
import hashlib
import logging
import datetime
import createrepo_c as cr

import deltarepo
from .errors import DeltaRepoError


def log(logger, level, msg):
    if not logger:
        return
    logger.log(level, msg)


def pkg_id_str(pkg, logger=None):
    """Return string identifying a package in repodata.
    This strings are used for the RepoId calculation."""
    if not isinstance(pkg, cr.Package):
        raise TypeError("A Package object expected")

    if not pkg.pkgId:
        log(logger, logging.WARNING, "Missing pkgId in a package!")

    if not pkg.location_href:
        log(logger, logging.WARNING, "Missing location_href at "
                                     "package %s %s" % (pkg.name, pkg.pkgId))

    idstr = "%s%s%s" % (pkg.pkgId or '',
                        pkg.location_href or '',
                        pkg.location_base or '')
    return idstr


def calculate_content_hash(path_to_primary_xml, checksum_type="sha256", logger=None):
    pkg_id_strs = []

    if checksum_type == "sha":
        # Classical createrepo says sha but means sha1 - so let's keep things around packaging stack compatible
        checksum_type = "sha1"

    def pkgcb(pkg):
        pkg_id_strs.append(pkg_id_str(pkg, logger))

    cr.xml_parse_primary(path_to_primary_xml, pkgcb=pkgcb, do_files=False)

    h = hashlib.new(checksum_type)
    for i in sorted(pkg_id_strs):
        h.update(i)
    return h.hexdigest()


def size_to_human_readable_str(size_in_bytes):
    if size_in_bytes < 0:
        return "{0}".format(size_in_bytes)

    for x in ['b','KB','MB','GB']:
        if size_in_bytes < 1024.0:
            return "{0:1.3f} {1}".format(size_in_bytes, x)
        size_in_bytes /= 1024.0
    return "{0:1.3f} {1}".format(size_in_bytes, 'TB')


def compute_file_checksum(path, type="sha256"):
    """Calculate file checksum"""
    if type == "sha":
        # Classical createrepo says sha but means sha1 - so let's keep things around packaging stack compatible
        type = "sha1"

    h = hashlib.new(type)
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024**2)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def isint(num):
    try:
        int(num)
    except ValueError:
        return False
    return True


def isnonnegativeint(num):
    try:
        int(num)
    except ValueError:
        return False
    return True


def isfloat(num):
    try:
        float(num)
    except ValueError:
        return False
    return True


def ts_to_str(ts):
    """Convert timestamp to string"""
    return datetime.datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")


def deltareposrecord_from_repopath(path, prefix_to_strip=None, logger=None):
    """Create DeltaRepoRecord object from a delta repository

    :param path: Path to a directory were a deltarepo lives
    :type path: str
    :param prefix_to_strip: Path prefix to strip from a path in the record
    :type prefix_to_strip: str or None
    :param logger: A logger
    :type logger: logging.Logger or None
    """

    # Prepare paths
    path = os.path.abspath(path)
    stripped_path = path
    if prefix_to_strip:
        abs_prefix_to_strip = os.path.abspath(prefix_to_strip)
        if path.startswith(abs_prefix_to_strip):
            stripped_path = os.path.relpath(path, abs_prefix_to_strip)

    # Parse repomd.xml of the delta repo
    repomd_path = os.path.join(path, "repodata/repomd.xml")
    repomd = cr.Repomd(repomd_path)

    deltametadata_path = None
    for repomd_rec in repomd.records:
        if repomd_rec.type == "deltametadata" and repomd_rec.location_href:
            deltametadata_path = os.path.join(path, repomd_rec.location_href)

    if not deltametadata_path:
        raise DeltaRepoError("Not a delta repository: {}".format(path))

    # Parse deltametadata.xml of the delta repo
    dm = deltarepo.DeltaMetadata()
    dm.load(deltametadata_path)

    # Prepare DeltaRepoRecord aka <deltarepo>
    rec = deltarepo.DeltaRepoRecord()
    rec.location_base = None
    rec.location_href = stripped_path
    rec.revision_src = dm.revision_src
    rec.revision_dst = dm.revision_dst
    rec.contenthash_src = dm.contenthash_src
    rec.contenthash_dst = dm.contenthash_dst
    rec.contenthash_type = dm.contenthash_type
    rec.timestamp_src = dm.timestamp_src
    rec.timestamp_dst = dm.timestamp_dst

    # Parepare <data> elements with info about files in the repo
    for repomd_rec in repomd.records:
        if not repomd_rec.type:
            continue
        if isnonnegativeint(repomd_rec.size):
            rec.set_data(repomd_rec.type, repomd_rec.size)
        elif isnonnegativeint(repomd_rec.open_size):
            rec.set_data(repomd_rec.type, repomd_rec.open_size)

    # Collect info about repomd.xml file of the delta repo
    rec.repomd_timestamp = int(os.path.getmtime(repomd_path))
    rec.repomd_size = os.path.getsize(repomd_path)
    checksumval = compute_file_checksum(repomd_path)
    rec.repomd_checksums = [("sha256", checksumval)]

    return rec


def write_deltarepos_file(path, records, append=False):
    # Add the record to the deltarepos.xml
    """Create/Overwrite/Update deltarepos.xml file.

    If the file doesn't exist, it will be created and records will be writen (regardless if append is True or False).
    If the file exists and append is True, the records will be appended.
    If the file exists and append is False, its content will be overwritten.

    :param: path: Path to deltarepos.xml.xz file
    """
    deltareposxml_path = os.path.join(path, "deltarepos.xml.xz")
    drs = deltarepo.DeltaRepos()
    if os.path.isfile(deltareposxml_path) and append:
        drs.load(deltareposxml_path)
    for rec in sorted(records, key=lambda x: x.location_href):
        drs.append_record(rec)
    drs.dump(deltareposxml_path)
    return deltareposxml_path


def log_warning(logger, msg):
    if logger:
        logger.warning(msg)


def gen_deltarepos_file(workdir, logger, force=False, update=False):
    """Generate deltarepos.xml.xz file in the repository

    :param workdir: Working directory
    :param logger: Logger
    :param force: Ignore bad repository
    :param update: Only add new repositories, that are not listed
                   and remove missing ones. (Do not regenerate whole
                   file from scratch)
    :return:
    """
    deltareposxml_path = os.path.join(workdir, "deltarepos.xml.xz")
    listed_locations = {}
    records = []

    logger.debug("Generating {}...".format(deltareposxml_path))

    if update and os.path.exists(deltareposxml_path):
        logger.debug("Loading previous version of deltarepos.xml.xz...")
        drs = deltarepo.DeltaRepos()
        drs.load(deltareposxml_path)
        for rec in drs.records:
            if rec.location_base:
                records.append(rec)
                continue
            listed_locations[os.path.normpath(rec.location_href)] = rec

    dir_prefix_len = len(os.path.normpath(workdir)) + 1
    for root, dirs, files in os.walk(workdir):
        # Recursivelly walk the directories and search for repositories
        root = os.path.normpath(root)
        if "repodata" in dirs:
            relative = root[dir_prefix_len:]

            if update and relative in listed_locations:
                logger.debug("Already listed - skipping: {}".format(root))
                records.append(listed_locations[relative])
                continue

            try:
                rec = deltareposrecord_from_repopath(root, prefix_to_strip=workdir, logger=logger)
            except (DeltaRepoError, IOError) as e:
                msg = "Bad delta repository {}: {}".format(root, e)
                logger.warning(msg)
                if not force:
                    raise DeltaRepoError(msg)
                continue

            logger.debug("Processing {}".format(root))

            if rec.check():
                records.append(rec)
            else:
                msg = "Record for {} is not valid".format(rec.location_href)
                logger.warning(msg)
                if not force:
                    raise DeltaRepoError(msg)

    sorted(records, key=lambda x: x.location_href)

    return write_deltarepos_file(workdir, records)