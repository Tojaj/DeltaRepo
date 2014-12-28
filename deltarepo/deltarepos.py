"""
Object representation of deltarepos.xml
"""

__all__ = (
    "DeltaRepoRecord",
    "DeltaRepos",
)

import os
import tempfile
import createrepo_c as cr
import xml.dom.minidom
from lxml import etree

import deltarepo
from .errors import DeltaRepoError, DeltaRepoParseError
from .xmlcommon import getNode, getRequiredNode
from .xmlcommon import getAttribute, getRequiredAttribute, getNumAttribute
from .xmlcommon import getValue
from .util import isnonnegativeint


class DeltaRepoRecord(object):
    def __init__(self):
        self.location_base = None
        self.location_href = None
        self.revision_src = None
        self.revision_dst = None
        self.contenthash_src = None
        self.contenthash_dst = None
        self.contenthash_type = None
        self.timestamp_src = None
        self.timestamp_dst = None

        self.data = {}  # { "primary": {"size": 123}, ... }

        self.repomd_timestamp = None
        self.repomd_size = None
        self.repomd_checksums = []  # [('type', 'value'), ...]

    def __repr__(self):
        str = "<DeltaRepoRecord:\n"
        for key, val in self.__dict__.iteritems():
            if key.startswith("_"):
                continue
            if key == "data":
                continue
            str += "  {}: {}\n".format(key, val)
        str += ">"
        return str

    def _subelement(self, parent):
        """Appends yourself as a <deltarepo> sub-element to a parent element.

        :param parent: Parent element
        :type parent: lxml.etree._Element
        """

        attrs = {}

        deltarepo_el = etree.SubElement(parent, "deltarepo", attrs)

        # <location>
        if self.location_href:
            attrs = { "href": self.location_href }
            if self.location_base:
                attrs["base"] = self.location_base
            etree.SubElement(deltarepo_el, "location", attrs)

        # <revision>
        if self.revision_src and self.revision_dst:
            attrs = { "src": self.revision_src, "dst": self.revision_dst }
            etree.SubElement(deltarepo_el, "revision", attrs)

        # <contenthash>
        if self.contenthash_src and self.contenthash_dst and self.contenthash_type:
            attrs = { "src": unicode(self.contenthash_src),
                      "dst": unicode(self.contenthash_dst),
                      "type": unicode(self.contenthash_type)}
            etree.SubElement(deltarepo_el, "contenthash", attrs)

        # <timestamp>
        if self.timestamp_src and self.timestamp_dst:
            attrs = { "src": unicode(self.timestamp_src),
                      "dst": unicode(self.timestamp_dst) }
            etree.SubElement(deltarepo_el, "timestamp", attrs)

        # <data>
        metadata_types = sorted(self.data.keys())
        for mtype in metadata_types:
            attrs = { "type": unicode(mtype),
                      "size": unicode(self.get_data(mtype).get("size", 0)) }
            etree.SubElement(deltarepo_el, "data", attrs)

        # <repomd>
        repomd_el = etree.SubElement(deltarepo_el, "repomd", {})

        # <repomd> <timestamp>
        if self.repomd_timestamp:
            time_el = etree.SubElement(repomd_el, "timestamp", {})
            time_el.text = str(self.repomd_timestamp)

        # <repomd> <size>
        if self.repomd_size:
            size_el = etree.SubElement(repomd_el, "size", {})
            size_el.text = str(self.repomd_size)

        # <repomd> <checksum>
        for type, value in self.repomd_checksums:
            checksum_el = etree.SubElement(repomd_el, "checksum", {"type": type})
            checksum_el.text = str(value)

    @classmethod
    def _from_element(cls, node):
        """Parses XML node for delta repo record from deltarepos.xml and returns DeltaRepoRecord object

        :param node: Element node <deltarepo>
        :type node: xml.dom.Node
        :returns: Filled DeltaRepoRecord object
        :rtype: DeltaRepoRecord
        """

        # <deltarepo> element
        rec = cls()

        subnode = getRequiredNode(node, "location")
        rec.location_base = getAttribute(subnode, "base")
        rec.location_href = getRequiredAttribute(subnode, "href")

        subnode = getNode(node, "revision")
        if subnode:
            rec.revision_src = getAttribute(subnode, "src")
            rec.revision_dst = getAttribute(subnode, "dst")

        subnode = getNode(node, "contenthash")
        if subnode:
            rec.contenthash_src = getAttribute(subnode, "src")
            rec.contenthash_dst = getAttribute(subnode, "dst")
            rec.contenthash_type = getAttribute(subnode, "type")

        subnode = getNode(node, "timestamp")
        if subnode:
            rec.timestamp_src = getNumAttribute(subnode, "src")
            rec.timestamp_dst = getNumAttribute(subnode, "dst")

        subnodes = node.getElementsByTagName("data") or []
        for subnode in subnodes:
            type = getAttribute(subnode, "type")
            size= getNumAttribute(subnode, "size")
            rec.set_data(type, size)

        # <repomd>
        repomdnode = getNode(node, "repomd")
        if repomdnode:
            subnode = getNode(repomdnode, "timestamp")
            if subnode and getValue(subnode):
                rec.repomd_timestamp = int(getValue(subnode))

            subnode = getNode(repomdnode, "size")
            if subnode and getValue(subnode):
                rec.repomd_size = int(getValue(subnode))

            checksumnodes = repomdnode.getElementsByTagName("checksum")
            if checksumnodes:
                for subnode in checksumnodes:
                    type = getAttribute(subnode, "type")
                    val = getValue(subnode)
                    if type and val:
                        rec.repomd_checksums.append((type, val))

        return rec

    @property
    def size_total(self):
        """Total size of repodata

        :returns: Size that is sum of sizes of all metadata files
        :return: Int
        """
        size = self.repomd_size or 0
        for data in self.data.itervalues():
            size += data.get("size", 0)
        return size

    def check(self):
        """Check if all mandatory attributes are filled with reasonable values.

        :returns: True if all mandatory attributes are filled, False otherwise
        :rtype: bool
        """
        if not self.location_href:
            return False
        if not self.revision_dst or not self.revision_dst:
            return False
        if not self.contenthash_src or not self.contenthash_dst:
            return False
        if not self.contenthash_type:
            return False
        if not isnonnegativeint(self.timestamp_src):
            return False
        if not isnonnegativeint(self.timestamp_dst):
            return False
        for data_dict in self.data.itervalues():
            if not isnonnegativeint(data_dict.get("size")):
                return False
        if not isnonnegativeint(self.repomd_size):
            return False
        return True

    def get_data(self, type):
        return self.data.get(type, None)

    def set_data(self, type, size):
        self.data[type] = {"size": int(size)}


class DeltaRepos(object):
    """Object representation of deltarepos.xml"""

    def __init__(self):
        self.records = []
        """:type: list of :class:`DeltaRepoRecord`"""

    def _parse_dom(self, dom):
        """Parse document object model of deltarepos.xml.

        :param dom: DOM of deltarepos.xml
        :type dom: xml.dom.minidom.Document
        """

        # <deltarepos> element
        elist_deltarepos = dom.getElementsByTagName("deltarepos")
        if not elist_deltarepos or not elist_deltarepos[0]:
            raise DeltaRepoParseError("No <deltarepos> element in deltarepos xml")

        # <deltarepo> elements
        for node in elist_deltarepos[0].childNodes:
            if node.nodeType != node.ELEMENT_NODE or node.nodeName != "deltarepo":
                continue
            rec = DeltaRepoRecord._from_element(node)
            self.records.append(rec)

    def clear(self):
        """Clear/Reset object

        :returns: Self to enable chaining
        :rtype DeltaRepos
        """
        self.records = []
        return self

    def check(self):
        """Check if all records are valid

        :returns: True if all records are valid, False otherwise
        :rtype: bool
        """
        for rec in self.records:
            if not rec.check():
                return False
        return True

    def append_record(self, rec):
        """Append a DeltaRepoRecord.

        :param rec: Record
        :type rec: DeltaRepoRecord
        :returns: Self to enable chaining (dr = DeltaRepos().append_record(..).append_record(..))
        :rtype DeltaRepos
        """
        if not isinstance(rec, DeltaRepoRecord):
            raise TypeError("DeltaRepoRecord object expected")
        self.records.append(rec)
        return self

    def loads(self, string):
        """Load metadata from a string.

        :param xml: Input data
        :type xml: str
        :returns: Self to enable chaining (dr = DeltaRepos().loads())
        :rtype DeltaRepos
        """
        dom = xml.dom.minidom.parseString(string)
        try:
            self._parse_dom(dom)
        except DeltaRepoParseError as err:
            raise DeltaRepoParseError("Cannot parse: {}".format(err))
        return self

    def load(self, fn):
        """Load metadata from a file.

        :param fn: Path to a file
        :type fn: str
        :returns: Self to enable chaining (dr = DeltaRepos().load())
        :rtype DeltaRepos
        """
        _, tmp_path = tempfile.mkstemp()
        cr.decompress_file(fn, tmp_path, cr.AUTO_DETECT_COMPRESSION)
        dom = xml.dom.minidom.parse(tmp_path)
        os.remove(tmp_path)
        try:
            self._parse_dom(dom)
        except DeltaRepoParseError as err:
            msg = "Cannot parse {}: {}".format(fn, err)
            raise DeltaRepoParseError(msg)
        return self

    def dumps(self):
        """Dump data to a string.

        :returns: String with XML representation
        :rtype: str
        """
        xmltree = etree.Element("deltarepos")
        for rec in self.records:
            rec._subelement(xmltree)
        return etree.tostring(xmltree, pretty_print=True,
                              encoding="UTF-8", xml_declaration=True)

    def dump(self, fn, compression_type=deltarepo.XZ, stat=None):
        """Dump data to a file.

        :param fn: path to a file
        :type fn: str
        :param compression_type: Type of compression
        :type compression_type: int
        :param stat: Stat object
        :type stat: cr.ContentStat or None
        :returns: Final path (the used basename with compression suffix)
        :rtype: str
        """
        if (compression_type is None or
                compression_type == cr.UNKNOWN_COMPRESSION or
                compression_type == cr.AUTO_DETECT_COMPRESSION):
            raise DeltaRepoError("Bad compression type: "
                                 "{}".format(compression_type))

        suffix = cr.compression_suffix(compression_type)
        if suffix and not fn.endswith(suffix):
            fn += suffix

        content = self.dumps()
        f = cr.CrFile(fn, cr.MODE_WRITE, compression_type)
        f.write(content)
        f.close()
        return fn