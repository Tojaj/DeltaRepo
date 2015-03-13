import shutil
import os
import pprint
import os.path
import time
import librepo
import tempfile
import createrepo_c as cr
from .applicator import DeltaRepoApplicator
from .deltarepos import DeltaRepos
from .common import LoggingInterface
from .util import calculate_content_hash
from .errors import DeltaRepoError

class _Repo(object):
    """Base class for LocalRepo and OriginRepo classes."""

    def __init__ (self):
        self.path = None                    # Path (only for local repo)
        self.repodata = None                # Path to repodata dir (only for local repo)
        self.basename = None                # Repo's basename derived from path (only for local repo)
        self.repomd_size = 0                # Size of repomd
        self.timestamp = None               # Highest timestamp in the repository
        self.revision = None                # Revision
        self.contenthash = None             # Calculated content hash
        self.contenthash_type = None        # Type of calculated content hash
        self.repomd_contenthash = None      # Content hash from repomd
        self.repomd_contenthash_type = None # Content hash from repomd
        self.listed_metadata = []   # ["primary", "filelists", ...]
        self.present_metadata = []  # Metadata files which really exist in repo
        self._repomd = None          # createrepo_c.Repomd() object

    def __cmp__(self, other):
        """Comparison based on timestamp"""
        cmp(self.timestamp, other.timestamp)

    def _fill_from_repomd_object(self, repomd):
        timestamp = -1          # Highest timestamp
        listed_metadata = []    # Metadata types listed in the repomd

        for rec in repomd.records:
            if rec.timestamp:
                timestamp = max(timestamp, rec.timestamp)
            listed_metadata.append(rec.type)

        self.revision = repomd.revision
        self.timestamp = timestamp
        self.listed_metadata = listed_metadata
        self._repomd = repomd

    def _fill_from_path(self, path, contenthash=True, contenthash_type="sha256"):
        """Fill attributes from a repository specified by path.

        :param path: Path to repository (a dir that contains repodata/ subdirectory)
        :type path: str
        :param contenthash: Do content hash calculation (primary metadata must be available in the repo)
        :type contenthash: bool
        :param contenthash_type: type of the calculated content hash
        :type contenthash_type: str
        """

        if not os.path.isdir(path) or \
           not os.path.isdir(os.path.join(path, "repodata/")) or \
           not os.path.isfile(os.path.join(path, "repodata/repomd.xml")):
            raise DeltaRepoError("Not a repository: {0}".format(path))

        repomd_path = os.path.join(path, "repodata/repomd.xml")
        repomd = cr.Repomd(repomd_path)

        self.repomd_contenthash = repomd.contenthash
        self.repomd_contenthash_type = repomd.contenthash_type

        self._fill_from_repomd_object(repomd)

        # Find a primary path
        primary_path = None
        for rec in repomd.records:
            md_path = os.path.join(path, rec.location_href)
            if os.path.isfile(md_path):
                self.present_metadata.append(rec.type)
            if rec.type == "primary":
                primary_path = md_path

        if contenthash:
            if not primary_path:
                raise DeltaRepoError("{0} - primary metadata are missing"
                                     "".format(primary_path))
            self.contenthash = calculate_content_hash(primary_path, contenthash_type)
            self.contenthash_type = contenthash_type

        self.path = path
        self.repodata = os.path.join(path, "repodata")
        self.basename = os.path.basename(path)
        self.repomd_size = os.path.getsize(repomd_path)

    def cost(self, whitelisted_metadata=None, include_repomd_size=True):
        # TODO: Some records sometimes don't have size specified
        #       (size is determined as 0) - print warning about such records
        cost = 0
        for rec in self._repomd.records:
            if whitelisted_metadata and rec.type not in whitelisted_metadata:
                continue
            cost += rec.size or 0
        if include_repomd_size:
            cost += self.repomd_size
        return cost


class LocalRepo(_Repo):
    def __init__ (self):
        _Repo.__init__(self)

    def __repr__(self):
        return "<LocalRepo {0} ({1})>".format(self.path, self.timestamp)

    @classmethod
    def from_path(cls, path, contenthash_type="sha256", calc_contenthash=True):
        """Create a LocalRepo object from a path to the repo."""
        lr = cls()
        lr._fill_from_path(path,
                           contenthash=calc_contenthash,
                           contenthash_type=contenthash_type)
        return lr


class OriginRepo(_Repo):
    # TODO: Keep the downloaded repomd.xml

    def __init__ (self):
        _Repo.__init__(self)

        self.urls = []
        self.mirrorlist = None
        self.metalink = None

    def __repr__(self):
        return "<OriginRepo ({0})>".format(self.timestamp)

    @classmethod
    def from_url(cls, urls=None, mirrorlist=None, metalink=None):
        if not urls and not mirrorlist and not metalink:
            raise AttributeError("At least one argument must be specified")

        tmpdir = tempfile.mkdtemp(prefix="deltarepo-updater-", dir="/tmp")

        h = librepo.Handle()
        h.repotype = librepo.YUMREPO
        h.urls = urls
        h.mirrorlisturl = mirrorlist
        h.metalinkurl = metalink
        h.yumdlist = []
        h.destdir = tmpdir

        try:
            r = h.perform()
        except librepo.LibrepoException as e:
            shutil.rmtree(tmpdir)
            raise DeltaRepoError("Cannot download ({0}, {1}, {2}): {3}".format(
                urls, mirrorlist, metalink, e))

        repo = cls()
        repo._fill_from_path(tmpdir, contenthash=False)

        repo.path = None
        repo.repodata = None
        repo.basename = None

        repo.urls = urls
        repo.mirrorlist = mirrorlist
        repo.metalink = metalink

        shutil.rmtree(tmpdir)
        return repo

    @classmethod
    def from_local_repomd(cls, repomd_path):
        """Create OriginRepo object from the local repomd.xml.
        @param path      path to the repomd.xml"""
        repomd = cr.Repomd(repomd_path)
        repo = cls()
        repo._fill_from_repomd_object(repomd)
        return repo

class DRMirror(object):
    def __init__(self):
        self.url = None
        self.records = []       # list of DeltaRepoRecord
        self.deltarepos = None  # DeltaRepos object

    @classmethod
    def from_url(cls, url, force=False):
        """

        :param url: URL
        :type url: str
        :param force: Silently ignore invalid records
        :type force: bool
        :return:
        """
        # TODO: support for metalink and mirrorlist
        fd, fn = tempfile.mkstemp(prefix="deltarepos.xml.xz-", dir="/tmp")

        # Download deltarepos.xml
        deltarepos_xml_url = os.path.join(url, "deltarepos.xml.xz")
        try:
            librepo.download_url(deltarepos_xml_url, fd)
        except librepo.LibrepoException as e:
            os.remove(fn)
            raise DeltaRepoError("Cannot download {0}: {1}".format(
                deltarepos_xml_url, e))

        # Parse deltarepos.xml
        dr = DeltaRepos()
        try:
            dr.load(fn, pedantic=(not force))
        except DeltaRepoError as e:
            raise DeltaRepoError("Error while parsing deltarepos.xml "
                                 "from {0}: {1}".format(deltarepos_xml_url, e))
        finally:
            os.remove(fn)

        # Fill and return DRMirror object
        drm = cls()
        drm.url = url               # Url of the mirror
        drm.deltarepos = dr         # DeltaRepos object

        for record in dr.records:
            try:
                record.validate()
            except (ValueError, TypeError):
                continue
            drm.records.append(record)

        return drm


class Link(object):
    """Graph's link (path) = a delta repository
    from one point of history (version) to another.
    """

    def __init__(self):
        self._deltareposrecord = None    # DeltaRepoRecord()
        self._drmirror = None            # DRMirror()

    #def __getattr__(self, item):
    #    if hasattr(self.deltareposrecord, item):
    #        return getattr(self.deltareposrecord, item, None)
    #    raise AttributeError("object has no attribute '{0}'".format(item))

    def __str__(self):
        return "<LinkMock \'{0}\'->\'{1}\' ({2})>".format(
            self.src, self.dst, self.cost())

    @property
    def src(self):
        """Source content hash"""
        return self._deltareposrecord.contenthash_src

    @property
    def dst(self):
        """Destination content hash."""
        return self._deltareposrecord.contenthash_dst

    @property
    def type(self):
        """Type of content hash (e.g., sha256, etc.) """
        return self._deltareposrecord.contenthash_type

    @property
    def contenthash_src(self):
        """Source content hash"""
        return self._deltareposrecord.contenthash_src

    @property
    def contenthash_dst(self):
        """Destination content hash."""
        return self._deltareposrecord.contenthash_dst

    @property
    def contenthash_type(self):
        """Type of content hash (e.g., sha256, etc.) """
        return self._deltareposrecord.contenthash_type
    @property
    def revision_src(self):
        """Source repo revision"""
        return self._deltareposrecord.revision_src

    @property
    def revision_dst(self):
        """Destination repo revision"""
        return self._deltareposrecord.revision_dst

    @property
    def timestamp_src(self):
        """Source repo timestamp"""
        return self._deltareposrecord.timestamp_src

    @property
    def timestamp_dst(self):
        """Destination repo timestamp"""
        return self._deltareposrecord.timestamp_dst

    @property
    def mirrorurl(self):
        """Mirror url"""
        return self._drmirror.url

    @property
    def deltarepourl(self):
        """Delta repo url"""
        if self._deltareposrecord.location_base:
            url = os.path.join(self._deltareposrecord.location_base,
                               self._deltareposrecord.location_href)
        else:
            url = os.path.join(self.mirrorurl,
                               self._deltareposrecord.location_href)
        return url

    def cost(self, whitelisted_metadata=None):
        """Cost (currently just a total size).
        In future maybe just sizes of needed delta metadata."""
        if whitelisted_metadata is None:
            return self._deltareposrecord.size_total

        cost = self._deltareposrecord.repomd_size
        for md_type in whitelisted_metadata:
            md = self._deltareposrecord.get_data(md_type)
            if md:
                cost += md.get("size", 0)
        return cost

    @classmethod
    def links_from_drmirror(cls, drmirror):
        links = []
        for rec in drmirror.records:
            link = cls()
            link._deltareposrecord = rec
            link._drmirror = drmirror
            links.append(link)
        return links

class ResolvedPath():
    """Path resolved by solver"""
    def __init__(self, resolved_path):
        self._path = resolved_path  # List of Link objects

    def __str__(self):
        return "<ResolvedPath {0}>".format(self._path)

    def __len__(self):
        return len(self._path)

    def __iter__(self):
        return self._path.__iter__()

    def __getitem__(self, item):
        return self._path.__getitem__(item)

    def path(self):
        return self._path

    def cost(self, whitelisted_metadata=None):
        cost = 0
        for link in self._path:
            cost += link.cost(whitelisted_metadata)
        return cost

class Solver(LoggingInterface):

    class Node(object):
        """Single graph node"""
        def __init__(self, value):
            self.value = value   # Content hash
            self.links = []      # List of all links that belong to the node
                                 # All of them must have self.value as a src value
            self.targets = {}    # { Node: Link }
            self.sources = set() # set(Nodes)

        def __repr__(self):
            targets = [x.value for x in self.targets]
            return "<Node {0} \'{1}\' points to: {2}>".format(
                id(self), self.value, targets)

    class Graph(LoggingInterface):
        def __init__(self, contenthash_type="sha256", logger=None):
            LoggingInterface.__init__(self, logger)

            self.nodes = {}  # { 'content_hash': Node }
            self.contenthash_type = contenthash_type

        def get_node(self, contenthash):
            return self.nodes.get(contenthash)

        def graph_from_links(self, links):
            already_processed_links = set() # Set of tuples (src, dst)
            nodes = {}  # { 'content_hash': Node }

            for link in links:
                if self.contenthash_type != link.type.lower():
                    self._warning("Content hash type mishmash {0} vs {1}"
                                   "".format(self.contenthash_type, link.type))
                    continue

                if (link.src, link.dst) in already_processed_links:
                    self._warning("Duplicated path {0}->{1} from {2} skipped"
                                   "".format(link.src, link.dst, link.mirrorurl))
                    continue

                node = nodes.setdefault(link.src, Solver.Node(link.src))

                if link.dst in node.targets:
                    # Should not happen (the already_processed_links
                    # list should avoid this)
                    self._warning("Duplicated path {0}->{1} from {2} skipped"
                                   "".format(link.src, link.dst, link.mirrorurl))
                    continue

                dst_node = nodes.setdefault(link.dst, Solver.Node(link.dst))
                dst_node.sources.add(node)
                node.targets[dst_node] = link

            self.links = links
            self.nodes = nodes

    def __init__(self, links, source, target, contenthash_type="sha256",
                 whitelisted_metadata=None, logger=None):
        LoggingInterface.__init__(self, logger)

        self.links = links      # Links
        self.source_ch = source # Source content hash (str)
        self.target_ch = target # Target content hash (str)
        self.contenthash_type = contenthash_type
        self.whitelisted_metadata = whitelisted_metadata

    def solve(self):
        # Build the graph
        graph = self.Graph(self.contenthash_type, logger=self.logger)
        graph.graph_from_links(self.links)

        if self.source_ch == self.target_ch:
            raise DeltaRepoError("Source and target content hashes are same {0}"
                                 "".format(self.source_ch))

        # Find start and end node in the graph
        source_node = graph.get_node(self.source_ch)
        if not source_node:
            raise DeltaRepoError("Source repo ({0}) not available".format(self.source_ch))
        target_node = graph.get_node(self.target_ch)
        if not target_node:
            raise DeltaRepoError("Target repo ({0}) not available".format(self.target_ch))

        # Dijkstra's algorithm
        # http://en.wikipedia.org/wiki/Dijkstra%27s_algorithm
        dist = {}       # Distance
        previous = {}   # Predecessor
        Q = []

        for _, node in graph.nodes.items():
            dist[node] = -1 # -1 Stands for infinity here
            previous[node] = None
            Q.append(node)

        dist[source_node] = 0

        while Q:
            u = None
            val = -1
            # Select node from Q with the smallest distance in dist
            for node in Q:
                if dist[node] == -1:
                    continue
                if val == -1 or dist[node] < val:
                    val = dist[node]
                    u = node

            if u:
                # Remove the u from the queue
                Q.remove(u)
            else:
                # All remaining nodes are inaccessible from source
                break

            if u == target_node:
                # Cool!
                break

            # Iterate over the u neighbors
            for v, link in u.targets.items():
                alt = dist[u] + link.cost(self.whitelisted_metadata)
                if alt < dist[v] or dist[v] == -1:
                    dist[v] = alt
                    previous[v] = u

        # At this point we have previous and dist lists filled
        self._debug("Solver: List of previous nodes:\n{0}"
                          "".format(pprint.pformat(previous)))
        self._debug("Solver: Distances:\n{0}"
                          "".format(pprint.pformat(dist)))

        resolved_path = []
        u = target_node
        while previous[u] is not None:
            resolved_path.append(previous[u].targets[u])
            u = previous[u]
        resolved_path.reverse()
        self._debug("Resolved path {0}".format(resolved_path))

        if resolved_path:
            return ResolvedPath(resolved_path)
        return None

class UpdateSolver(LoggingInterface):

    def __init__(self, drmirrors, whitelisted_metadata=None, logger=None):
        LoggingInterface.__init__(self, logger)

        if not isinstance(drmirrors, list):
            raise AttributeError("List of drmirrors expected")

        self.whitelisted_metadata = whitelisted_metadata

        self._drmirrors = drmirrors or []   # [DeltaRepos, ...]
        self._links = []            # Link objects from the DeltaRepos objects
        self._cached_resolved_path = {} # { (src_ch, dst_ch, ch_type): ResolvedPath }

        self._fill_links()

    def _fill_links(self):
        for drmirror in self._drmirrors:
            links = Link.links_from_drmirror((drmirror))
            self._links.extend(links)

    def find_repo_contenthash(self, repo, contenthash_type="sha256"):
        """Find (guess) Link for the OriginRepo.
        Note: Currently, none of origin repos has contenthash in repomd.xml,
        so we need to combine multiple metrics (revision, timestamp, ..)

        @param repo     OriginRepo
        @param links    list of Link objects
        @return         (contenthash_type, contenthash) or None"""

        if repo.contenthash and repo.contenthash_type \
                and repo.contenthash_type == contenthash_type:
            return (repo.contenthash_type, repo.contenthash)

        self._debug('Finding content hash for repository with revision "%s" and timestamp: "%s"' % \
                    (repo.revision, repo.timestamp))

        for link in self._links:
            if repo.revision and link.revision_src and repo.timestamp and link.timestamp_src:
                if repo.revision == link.revision_src and repo.timestamp == link.timestamp_src:
                    if link.contenthash_type == contenthash_type:
                        self._debug("Content hash found: (%s) %s" % (contenthash_type, link.contenthash_src))
                        return (contenthash_type, link.contenthash_src)

            if repo.revision and link.revision_dst and repo.timestamp and link.timestamp_dst:
                if repo.revision == link.revision_dst and repo.timestamp == link.timestamp_dst:
                    if link.contenthash_type == contenthash_type:
                        self._debug("Content hash found: (%s) %s" % (contenthash_type, link.contenthash_dst))
                        return (contenthash_type, link.contenthash_dst)

        self._debug("Content hash not found")
        # TODO: List all available links (?)
        return (contenthash_type, None)

    def resolve_path(self, source_contenthash, target_contenthash, contenthash_type="sha256"):
        # Try cache first
        key = (source_contenthash, target_contenthash, contenthash_type)
        if key in self._cached_resolved_path:
            return self._cached_resolved_path[key]

        # Resolve the path
        solver = Solver(self._links, source_contenthash,
                        target_contenthash,
                        contenthash_type=contenthash_type,
                        whitelisted_metadata=self.whitelisted_metadata,
                        logger=self.logger)
        resolved_path = solver.solve()

        # Cache result
        self._cached_resolved_path[key] = resolved_path

        return resolved_path

class Updater(LoggingInterface):

    class DownloadedRepo(object):
        def __init__(self, urls=[], mirrorlist=None, metalink=None):
            # TODO: Downloading only selected metadatas
            self.urls = urls
            self.mirrorlist = mirrorlist
            self.metalink = metalink
            self.destdir = None
            self.h = None   # Librepo Handle()
            self.r = None   # Librepo Result()

        def download(self, destdir, wanted_metadata=None):
            self.destdir = destdir

            h = librepo.Handle()
            h.urls = self.urls
            h.mirrorlisturl = self.mirrorlist
            h.metalinkurl = self.metalink
            h.repotype = librepo.YUMREPO
            h.interruptible = True
            h.destdir = destdir
            h.yumdlist = wanted_metadata
            r = librepo.Result()
            # TODO: Catch exceptions
            h.perform(r)

            self.h = h
            self.r = r

    def __init__(self, localrepo, logger=None, outputdir=None):
        LoggingInterface.__init__(self, logger)
        self.localrepo = localrepo
        self.outputdir = outputdir  # In case that result should be
                                    # writen to different location and
                                    # localrepo should not be overwritten

    def _get_tmpdir(self):
        tmpdir = tempfile.mkdtemp(prefix="deltarepos-", dir="/tmp")
        self._debug("Using temporary directory: {0}".format(tmpdir))
        return tmpdir

    def _get_dst(self):
        if self.outputdir:
            return os.path.join(self.outputdir, "repodata")
        return os.path.join(self.localrepo.path, "repodata")

    def _final_move(self, src, dst, name="repodata"):
        # TODO: Try - except and restore original data on error (?)
        # TODO: Skip copy if both src and dst are on the same device
        dst_dirname = os.path.dirname(dst)
        tmp_dst_basename = ".deltarepo-{0}-{1}-{2}".format(name, time.time(), os.getpid())
        tmp_dst = os.path.join(dst_dirname, tmp_dst_basename)
        tmp_dst_backup = tmp_dst+"-backup"

        self._debug("Final move - STARTED")
        self._debug("Source:      {0}".format(src))
        self._debug("Destination: {0}".format(dst))
        self._debug(" + Copying:  {0} -> {1}".format(src, tmp_dst))
        shutil.copytree(src, tmp_dst)
        self._debug(" + Moving:   {0} -> {1}".format(dst, tmp_dst_backup))
        shutil.move(dst, tmp_dst_backup)
        self._debug(" + Moving:   {0} -> {1}".format(tmp_dst, dst))
        shutil.move(tmp_dst, dst)
        self._debug(" + Removing: {0}".format(tmp_dst_backup))
        shutil.rmtree(tmp_dst_backup)
        self._debug("Final move - COMPLETE".format(src, dst))

    def apply_resolved_path(self, resolved_path, whitelisted_metadata=None):
        # TODO: Make it look better (progressbar, etc.)
        counter = 1
        tmpdir = self._get_tmpdir()
        tmprepo = tempfile.mkdtemp(prefix="targetrepo", dir=tmpdir)
        prevrepo = self.localrepo.path

        for link in resolved_path:

            # Download repo
            self._info("{0:2}/{1:<2} Downloading delta repo {2}".format(
                counter, len(resolved_path), link.deltarepourl))
            dirname = "deltarepo_{0:02}".format(counter)
            destdir = os.path.join(tmpdir, dirname)
            os.mkdir(destdir)
            repo = Updater.DownloadedRepo(urls=[link.deltarepourl])
            repo.download(destdir, wanted_metadata=whitelisted_metadata)

            # Apply repo
            self._info("{0:2}/{1:<2} Applying delta repo".format(
                counter, len(resolved_path)))
            da = DeltaRepoApplicator(prevrepo,
                                     destdir,
                                     out_path=tmprepo,
                                     logger=self.logger,
                                     ignore_missing=True)
            da.apply()

            counter += 1
            prevrepo = tmprepo

        # Move updated repo to the final destination
        src = os.path.join(tmprepo, "repodata")
        dst = self._get_dst()
        self._final_move(src, dst)
        shutil.rmtree(tmpdir)

    def update_from_origin(self, origin_repo, wanted_metadata=None):
        tmpdir = self._get_tmpdir()
        downloaded_repo = Updater.DownloadedRepo(urls=origin_repo.urls,
                                                 mirrorlist=origin_repo.mirrorlist,
                                                 metalink=origin_repo.metalink)
        downloaded_repo.download(tmpdir, wanted_metadata=wanted_metadata)

        # Move downloaded repo to the final destination
        src = os.path.join(tmpdir, "repodata")
        dst = self._get_dst()
        self._final_move(src, dst)
        shutil.rmtree(tmpdir)
