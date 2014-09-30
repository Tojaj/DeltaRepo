import os.path
import hashlib
import logging
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
    if not pkg.pkgId:
        log(logger, logging.WARNING, "Missing pkgId in a package!")
    if not pkg.location_href:
        log(logger, logging.WARNING, "Missing location_href at "
                                     "package %s %s" % (pkg.name, pkg.pkgId))

    idstr = "%s%s%s" % (pkg.pkgId or '',
                        pkg.location_href or '',
                        pkg.location_base or '')
    return idstr


def calculate_content_hash(path_to_primary_xml, type="sha256", logger=None):
    pkg_id_strs = []

    def pkgcb(pkg):
        pkg_id_strs.append(pkg_id_str(pkg, logger))

    cr.xml_parse_primary(path_to_primary_xml, pkgcb=pkgcb, do_files=False)

    h = hashlib.new(type)
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


def deltareposrecord_from_repopath(path, prefix_to_strip=None):
    """Create DeltaRepoRecord object from a delta repository"""

    # Prepare paths
    path = os.path.abspath(path)
    prefix_to_strip = os.path.abspath(prefix_to_strip)
    stripped_path = path
    if prefix_to_strip and path.startswith(prefix_to_strip):
        stripped_path = os.path.relpath(path, prefix_to_strip)

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
    deltareposxml_path = os.path.join(path, "deltarepos.xml.xz")
    drs = deltarepo.DeltaRepos()
    if os.path.isfile(deltareposxml_path) and append:
        drs.load(deltareposxml_path)
    for rec in records:
        drs.append_record(rec)
    drs.dump(deltareposxml_path)


def log_warning(logger, msg):
    if logger:
        logger.warning(msg)


def gen_deltarepos_file(workdir, logger, force=False):

    deltareposrecords = []

    # Recursivelly walk the directories and search for repositories
    for root, dirs, files in os.walk(workdir):
        dirs.sort()
        if "repodata" in dirs:
            try:
                rec = deltareposrecord_from_repopath(root, logger, workdir)
            except DeltaRepoError as e:
                msg = "Bad repository {}: {}".format(root, e)
                logger.warning(msg)
                if not force:
                    raise DeltaRepoError(msg)

            if rec.check():
                deltareposrecords.append(rec)
            else:
                msg = "Record for {} is not valid".format(rec.location_href)
                logger.warning(msg)
                if not force:
                    raise DeltaRepoError(msg)

    write_deltarepos_file(workdir, deltareposrecords, append=False)