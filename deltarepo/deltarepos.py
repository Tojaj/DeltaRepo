"""
Object representation of deltarepos.xml
"""

__all__ = (
    "DeltaRepoRecord",
    "DeltaRepos",
)

import os
import six
import tempfile
import createrepo_c as cr
import xml.dom.minidom
from lxml import etree

import deltarepo
from .errors import DeltaRepoError, DeltaRepoParseError
from .common import ValidationMixin
from .xmlcommon import getNode, getRequiredNode
from .xmlcommon import getAttribute, getRequiredAttribute, getNumAttribute
from .xmlcommon import getValue
from .util import isnonnegativeint


class DeltaRepoRecord(ValidationMixin):
    def __init__(self):
        self.location_base = None       #: (str)
        self.location_href = None       #: (str)
        self.revision_src = None        #: (str)
        self.revision_dst = None        #: (str)
        self.contenthash_src = None     #: (str)
        self.contenthash_dst = None     #: (str)
        self.contenthash_type = None    #: (str)
        self.timestamp_src = None       #: (int)
        self.timestamp_dst = None       #: (int)
        self.data = {}                  #: ({str: dict}) { "primary": {"size": 123}, ... }
        self.repomd_timestamp = None    #: (int) Mtime of repomd file
        self.repomd_size = None         #: (int) Size of repomd file in bytes
        self.repomd_checksums = []      #: ([(str, str), ..]) [('type', 'value'), ...]

    def _validate_location_base(self):
        self._assert_type("location_base", six.string_types, allow_none=True)

    def _validate_location_href(self):
        self._assert_type("location_href", six.string_types)

    def _validate_revision_src(self):
        self._assert_type("revision_src", six.string_types)

    def _validate_revision_dst(self):
        self._assert_type("revision_dst", six.string_types)

    def _validate_contenthash_src(self):
        self._assert_type("contenthash_src", six.string_types)

    def _validate_contenthash_dst(self):
        self._assert_type("contenthash_dst", six.string_types)

    def _validate_contenthash_type(self):
        self._assert_type("contenthash_type", six.string_types)

    def _validate_timestamp_src(self):
        self._assert_nonnegative_integer("timestamp_src")

    def _validate_timestamp_dst(self):
        self._assert_nonnegative_integer("timestamp_dst")

    def _validate_data(self):
        if not self.data:
            return
        self._assert_type("data", [dict])
        for key, value in six.iteritems(self.data):
            self._assert_val_type(key, "Key in 'data' dict", six.string_types)
            self._assert_val_type(value, "Value in 'data' dict", [dict])
            self._assert_val_type(value.get("size"), "Size element of '%s' key in 'data' dict" % key, six.integer_types)

    def _validate_repomd_timestamp(self):
        self._assert_nonnegative_integer("repomd_timestamp")

    def _validate_repomd_size(self):
        self._assert_nonnegative_integer("repomd_size")

    def _validate_repomd_checksums(self):
        self._assert_type("repomd_checksums", [list])
        for item in self.repomd_checksums:
            self._assert_val_type(item, "Item in 'repomd_checksums' list", [tuple])
            ch_type, ch_value = item
            self._assert_val_type(ch_type, "Checksum type in 'repomd_checksums' list", six.string_types)
            self._assert_val_type(ch_value, "Checksum value in 'repomd_checksums' list", six.string_types)

    def __repr__(self):
        strrepr = "<DeltaRepoRecord:\n"
        for key, val in self.__dict__.iteritems():
            if key.startswith("_"):
                continue
            if key == "data":
                continue
            strrepr += "  {}: {}\n".format(key, val)
        strrepr += ">"
        return strrepr

    def _to_xml_element(self):
        """Dump yourself to xml Element

        :returns: Self representation as an xml element
        :rtype: lxml.etree.Element
        """
        deltarepo_el = etree.Element("deltarepo")

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
                      "size": unicode(self.get_data(mtype)["size"]) }
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

        return deltarepo_el

    def _from_xml_element(self, node):
        """Fill yourself from <deltarepo> xml element

        :param node: Element node <deltarepo>
        :type node: xml.dom.minidom.Element
        :returns: Filled DeltaRepoRecord object
        :rtype: DeltaRepoRecord
        """
        subnode = getRequiredNode(node, "location")
        self.location_base = getAttribute(subnode, "base")
        self.location_href = getRequiredAttribute(subnode, "href")

        subnode = getNode(node, "revision")
        if subnode:
            self.revision_src = getAttribute(subnode, "src")
            self.revision_dst = getAttribute(subnode, "dst")

        subnode = getNode(node, "contenthash")
        if subnode:
            self.contenthash_src = getAttribute(subnode, "src")
            self.contenthash_dst = getAttribute(subnode, "dst")
            self.contenthash_type = getAttribute(subnode, "type")

        subnode = getNode(node, "timestamp")
        if subnode:
            self.timestamp_src = getNumAttribute(subnode, "src")
            self.timestamp_dst = getNumAttribute(subnode, "dst")

        subnodes = node.getElementsByTagName("data") or []
        for subnode in subnodes:
            type = getAttribute(subnode, "type")
            size= getNumAttribute(subnode, "size")
            self.set_data(type, size)

        # <repomd>
        repomdnode = getNode(node, "repomd")
        if repomdnode:
            subnode = getNode(repomdnode, "timestamp")
            if subnode and getValue(subnode):
                self.repomd_timestamp = int(getValue(subnode))

            subnode = getNode(repomdnode, "size")
            if subnode and getValue(subnode):
                self.repomd_size = int(getValue(subnode))

            checksumnodes = repomdnode.getElementsByTagName("checksum")
            if checksumnodes:
                for subnode in checksumnodes:
                    type = getAttribute(subnode, "type")
                    val = getValue(subnode)
                    if type and val:
                        self.repomd_checksums.append((type, val))

        return self

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

    def get_data(self, type):
        return self.data.get(type, None)

    def set_data(self, type, size):
        self.data[type] = {"size": int(size)}


class DeltaRepos(ValidationMixin):
    """Object representation of deltarepos.xml"""

    def __init__(self):
        self.records = []
        """:type: list of :class:`DeltaRepoRecord`"""

    def _to_xml_element(self):
        """Dump yourself to xml Element

        :returns: Self representation as an xml element
        :rtype: lxml.etree.Element
        """
        deltarepos_el = etree.Element("deltarepos")
        for rec in self.records:
            deltarepos_el.append(rec._to_xml_element())
        return deltarepos_el

    def _from_xml_element(self, deltarepos_element, pedantic=True):
        """Parse <deltarepos> XML element

        :param deltarepos_element: <deltarepos> xml element
        :type deltarepos_element: xml.dom.minidom.Element
        :param pedantic: Fail if a record is not valid (enabled by default)
        :type pedantic: bool
        :returns: Self to enable chaining
        :rtype: DeltaRepos
        """
        for elem in deltarepos_element.getElementsByTagName("deltarepo"):
            rec = DeltaRepoRecord()._from_xml_element(elem)
            if pedantic:
                try:
                    rec.validate()
                except (TypeError, ValueError) as err:
                    raise DeltaRepoParseError("A record for {0} is not valid: {1}".format(rec.location_href, err))
            self.records.append(rec)
        return self

    def _from_xml_document(self, dom, pedantic=True):
        """Parse document object model of deltarepos.xml.

        :param dom: DOM of deltarepos.xml
        :type dom: xml.dom.minidom.Document
        :param pedantic: Fail if a record is not valid (enabled by default)
        :type pedantic: bool
        :returns: Self to enable chaining
        :rtype: DeltaRepos
        """
        deltarepos = dom.getElementsByTagName("deltarepos")
        if not deltarepos:
            raise DeltaRepoParseError("No <deltarepos> element in xml")
        return self._from_xml_element(deltarepos[0], pedantic=pedantic)

    def clear(self):
        """Clear/Reset object

        :returns: Self to enable chaining
        :rtype: DeltaRepos
        """
        self.records = []
        return self

    def _validate_records(self):
        for rec in self.records:
            rec.validate()

    def append_record(self, rec, force=False):
        """Append a DeltaRepoRecord.

        :param rec: Record
        :type rec: DeltaRepoRecord
        :param force: Ignore that record is not valid
                      (all mandatory attributes are not filled)
        :type force: bool
        :returns: Self to enable chaining
        :rtype: DeltaRepos
        """
        if not isinstance(rec, DeltaRepoRecord):
            raise TypeError("DeltaRepoRecord object expected")

        try:
            rec.validate()
        except (TypeError, ValueError) as err:
            if not force:
                raise DeltaRepoError("DeltaRepoRecord is not valid: %s" % err)

        self.records.append(rec)
        return self

    def loads(self, string, pedantic=True):
        """Load metadata from a string.

        :param xml: Input data
        :type xml: str
        :param pedantic: Raise exception if there is an invalid record
                         (a record that doesn't contain all mandatory info)
                         (enabled by default)
        :type pedantic: bool
        :returns: Self to enable chaining (dr = DeltaRepos().loads())
        :rtype: DeltaRepos
        """
        document = xml.dom.minidom.parseString(string)
        try:
            self._from_xml_document(document, pedantic=pedantic)
        except DeltaRepoError as err:
            raise DeltaRepoParseError("Cannot parse: {0}".format(err))
        return self

    def load(self, fn, pedantic=True):
        """Load metadata from a file.

        :param fn: Path to a file
        :type fn: str
        :param pedantic: Raise exception if there is an invalid record
                         (a record that doesn't contain all mandatory info)
                         (enabled by default)
        :type pedantic: bool
        :returns: Self to enable chaining (dr = DeltaRepos().load())
        :rtype: DeltaRepos
        """
        _, tmp_path = tempfile.mkstemp(prefix="tmp-deltarepos-xml-file-")
        cr.decompress_file(fn, tmp_path, cr.AUTO_DETECT_COMPRESSION)
        document = xml.dom.minidom.parse(tmp_path)
        os.remove(tmp_path)
        try:
            self._from_xml_document(document, pedantic=pedantic)
        except DeltaRepoError as err:
            raise DeltaRepoParseError("Cannot parse {0}: {1}".format(fn, err))
        return self

    def dumps(self):
        """Dump data to a string.

        :returns: String with XML representation
        :rtype: str
        """
        xmltree = self._to_xml_element()
        return etree.tostring(xmltree,
                              pretty_print=True,
                              encoding="UTF-8",
                              xml_declaration=True)

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
                                 "{0}".format(compression_type))

        suffix = cr.compression_suffix(compression_type)
        if suffix and not fn.endswith(suffix):
            fn += suffix

        content = self.dumps()
        f = cr.CrFile(fn, cr.MODE_WRITE, compression_type)
        f.write(content)
        f.close()
        return fn