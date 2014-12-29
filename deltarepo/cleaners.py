import time
import types
import shutil
import os.path
import numbers

from deltarepo.util import log_debug, log_info, log_error
from deltarepo.updater_common import LocalRepo


def clear_repos(workdir, max_num=None, max_age=None, logger=None):
    """Clear a workdir that contains bunch of different versions
    of repo metadata. Keep only max_num of latest metadata
    and/or metadata that aren't older than max_age

    :param workdir: A path to a directory with cached metadata
    :type workdir: str
    :param max_num: Maximum number of preserved latest metadata versions
    :type max_num: int or None
    :param max_age: Repodata older than this value will be removed
    :type max_age: int or None
    :raises: IOError, DeltaRepoError
    """
    cur_time = time.time()

    # Checking input arguments
    if not isinstance(max_num, (types.NoneType, numbers.Number)):
        raise TypeError("Number or None expected got '{0}'".format(type(max_num)))

    if not isinstance(max_age, (types.NoneType, numbers.Number)):
        raise TypeError("Number or None expected got '{0}'".format(type(max_age)))

    if (max_num is None or max_num < 0) and (max_age is None or max_age < 0):
        return

    if not os.path.isdir:
        raise IOError("Not a directory '{0}'".format(workdir))

    # Listing of all available repositories in the workdir
    available_repos = []
    
    for repodir in os.listdir(workdir):
        path = os.path.join(workdir, repodir)
        if not os.path.isdir(path):
            continue
        if not os.path.isdir(os.path.join(path, "repodata")):
            continue
        repo = LocalRepo.from_path(path, calc_contenthash=False)
        available_repos.append(repo)

    available_repos = sorted(available_repos,
                             key=lambda x: x.timestamp,
                             reverse=True)

    # Enumerating which repositories will be removed
    to_be_removed = set()

    if max_num is not None and max_num >= 0:
        to_be_removed.update(available_repos[max_num:])

    if max_age is not None and max_age >= 0:
        to_be_removed.update([x for x in available_repos if (cur_time - x.timestamp) > max_age])

    # Removing the repositories
    if to_be_removed:
        log_info(logger, "Clearing of {0}".format(workdir))

    for repo in sorted(to_be_removed, key=lambda x: x.timestamp, reverse=True):
        log_info(logger, "Removing: {0}".format(repo.path))
        shutil.rmtree(repo.path)
