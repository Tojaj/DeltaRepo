import os
import tempfile
import xml.dom.minidom
import createrepo_c as cr
from lxml import etree

import deltarepo
from deltarepo.util import isnonnegativeint
from .errors import DeltaRepoError, DeltaRepoParseError
from .xmlcommon import getNode, getAttribute, getNumAttribute


class AdditionalXmlData(object):
    """Interface to store/load additional data to/from xml.
    """

    ADDITIONAL_XML_DATA = True

    def __init__(self):
        self._data = {}
        self._lists = {}

    def set(self, key, value):
        """Store a single key-value pair to the XML.
        Both key and value have to be a string.
        Each key could have only single string value.
        No multiple keys with same name are allowed."""
        if not isinstance(key, basestring):
            raise TypeError("expected string as key")
        if not isinstance(value, basestring):
            raise TypeError("expected string as value")
        self._data[key] = value

    def update(self, dictionary):
        """Store multiple key-value pairs to the XML.
        All keys and values have to be a strings.
        Each key could have only single string value.
        No multiple keys with same name are allowed."""
        if not isinstance(dictionary, dict):
            raise TypeError("expected dictionary")

        for key, val in dictionary.items():
            self.set(key, val)

    def append(self, listname, dictionary):
        """Append a multiple key-value pairs to the XML.
        One list/key could have multiple dictionaries."""
        if not isinstance(listname, basestring):
            raise TypeError("expected string")
        if not isinstance(dictionary, dict):
            raise TypeError("expected dict")

        if not listname in self._lists:
            self._lists[listname] = []

        # Validate items first
        for key, val in dictionary.items():
            if not isinstance(key, basestring) or not isinstance(val, basestring):
                raise TypeError("Dict's keys and values must be string")

        self._lists[listname].append(dictionary)

    def get(self, key, default=None):
        """Return a single valued key from the XML"""
        return self._data.get(key, default)

    def get_list(self, key, default=None):
        """Return list (a key with multiple values) of dictionaries"""
        return self._lists.get(key, default)

    def _subelement(self, parent, name, in_attrs=None):
        """Generate an XML element from the content of the object.

        :param parent: Parent xml.dom.Node object
        :param name: Name of the XML element
        :param in_attrs: Dictionary with element attributes.
                         Both keys and values have to be strings."""
        attrs = {}
        attrs.update(self._data)
        if in_attrs:
            attrs.update(in_attrs)
        elem = etree.SubElement(parent, name, attrs)

        for listname, listvalues in self._lists.items():
            for val in listvalues:
                etree.SubElement(elem, listname, val)

        return elem

class PluginBundle(AdditionalXmlData):
    """
    Object that persistently stores plugin configuration
    in deltametadata.xml XML file.
    To access data use the public methods from AdditionalXmlData object.
    """
    def __init__(self, name, version):
        AdditionalXmlData.__init__(self)

        if not isinstance(name, basestring):
            raise TypeError("string expected")
        if not isinstance(version, int):
            raise TypeError("integer expected")

        self.name = name        # Plugin name (string)
        self.version = version  # Plugin version (integer)

    @classmethod
    def _from_element(cls, node):
        """
        Parse

        :param node: Element node <plugin>
        :type node: xml.dom.Node
        :return:
        """
        name = None
        version = None
        other = {}

        # Parse attributes
        for x in xrange(node.attributes.length):
            attr = node.attributes.item(x)
            if attr.name == "name":
                name = attr.value
            elif attr.name == "version":
                version = attr.value
            else:
                other[attr.name] = attr.value

        if not name or not version:
            raise DeltaRepoError("Bad XML: name or version attribute "
                                 "of plugin element is missing")

        try:
            version_int = int(version)
        except ValueError:
            raise DeltaRepoError("Version {0} cannot be converted to "
                                 "integer number".format(version))

        bp = cls(name, version_int)
        bp.update(other)

        # Parse subelements
        for list_item_node in node.childNodes:
            if list_item_node.nodeType != list_item_node.ELEMENT_NODE:
                continue

            dictionary = {}
            listname = list_item_node.nodeName
            for x in xrange(list_item_node.attributes.length):
                attr = list_item_node.attributes.item(x)
                dictionary[attr.name] = attr.value

            bp.append(listname, dictionary)

        return bp

    def check(self):
        """
        Check if all mandatory attributes are filled with reasonable values.

        :rtype: bool
        """
        if not self.name:
            return False
        if not self.version:
            return False
        return True

#
# deltametadata.xml
#

class DeltaMetadata(object):
    """Object that represents deltametadata.xml file in deltarepository.
    The deltametadata.xml persistently stores plugin configuration.
    """

    def __init__(self):
        self.revision_src = None        #: (str)
        self.revision_dst = None        #: (str)
        self.contenthash_src = None     #: (str)
        self.contenthash_dst = None     #: (str)
        self.contenthash_type = None    #: (str)
        self.timestamp_src = None       #: (int)
        self.timestamp_dst = None       #: (int)
        self.usedplugins = {}
        """:type: dict of [str, PluginBundle]"""


    def _parse_dom(self, dom):
        """
        Parse document object model of deltametadata.xml.

        :param dom: DOM of deltarepos.xml
        :type dom: xml.dom.minidom.Document
        """

        # Get the root <deltametadata> element
        deltametadata = getNode(dom, "deltametadata")
        if not deltametadata:
            raise DeltaRepoParseError("No <deltametadata> element in deltametadata xml")

        # Parse metadata
        node = getNode(deltametadata, "revision")
        if node:
            self.revision_src = getAttribute(node, "src", None)
            self.revision_dst = getAttribute(node, "dst", None)

        node = getNode(deltametadata, "contenthash")
        if node:
            self.contenthash_src = getAttribute(node, "src", None)
            self.contenthash_dst = getAttribute(node, "dst", None)
            self.contenthash_type = getAttribute(node, "type", None)

        node = getNode(deltametadata, "timestamp")
        if node:
            self.timestamp_src = getNumAttribute(node, "src", 0)
            self.timestamp_dst = getNumAttribute(node, "dst", 0)

        # Parse plugins
        usedplugins = deltametadata.getElementsByTagName("plugin")
        for plugin_node in usedplugins:
            pluginbundle = PluginBundle._from_element(plugin_node)
            self.usedplugins[pluginbundle.name] = pluginbundle

    def clear(self):
        """Clear/Reset object"""
        self.revision_src = None        #: (str)
        self.revision_dst = None        #: (str)
        self.contenthash_src = None     #: (str)
        self.contenthash_dst = None     #: (str)
        self.contenthash_type = None    #: (str)
        self.timestamp_src = None       #: (int)
        self.timestamp_dst = None       #: (int)
        self.usedplugins = {}

    def check(self):
        """
        Check if content of deltametadata seem to be valid

        :rtype: bool
        """
        if not self.revision_src or not self.revision_dst:
            return False
        if not self.contenthash_dst or not self.contenthash_dst:
            return False
        if not self.contenthash_type:
            return False
        if cr.checksum_type(self.contenthash_type) == cr.UNKNOWN_CHECKSUM:
            return False
        if not isnonnegativeint(self.timestamp_src):
            return False
        if not isnonnegativeint(self.timestamp_dst):
            return False
        for pluginbundle in self.usedplugins:
            if not pluginbundle.check():
                return False
        return True

    def add_pluginbundle(self, pluginbundle):
        """
        Add new pluginbundle to the object

        :param pluginbundle: Plugin data in PluginBundle object
        :type pluginbundle: PluginBundle
        """
        if not isinstance(pluginbundle, PluginBundle):
            raise TypeError("PluginBundle object expected")
        self.usedplugins[pluginbundle.name] = pluginbundle

    def get_pluginbundle(self, name):
        """
        Get associate PluginBundle object

        :param name: Name of a plugin
        :type name: str
        :returns: PluginBundle specified by name
        :rtype: PluginBundle or None
        """
        return self.usedplugins.get(name, None)

    def loads(self, xml):
        """
        Load metadata from a string.

        :param xml: Input data
        :type xml: str
        """
        dom = xml.dom.minidom.parseString(xml)
        try:
            self._parse_dom(dom)
        except DeltaRepoParseError as err:
            raise DeltaRepoParseError("Cannot parse: {}".format(err))

    def load(self, fn):
        """
        Load metadata from a xml file.

        :param fn: Path to a file
        :type fn: str
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

    def dumps(self):
        """
        Dump data to a string.

        :rtype: str
        """
        xmltree = etree.Element("deltametadata")

        # Dump metadata
        if self.revision_src or self.revision_dst:
            attrs = {}
            if self.revision_src:
                attrs["src"] = str(self.revision_src)
            if self.revision_dst:
                attrs["dst"] = str(self.revision_dst)
            etree.SubElement(xmltree, "revision", attrs)

        if (self.contenthash_src or self.contenthash_dst) and self.contenthash_type:
            attrs = {"type": self.contenthash_type}
            if self.contenthash_src:
                attrs["src"] = self.contenthash_src
            if self.contenthash_dst:
                attrs["dst"] = self.contenthash_dst
            etree.SubElement(xmltree, "contenthash", attrs)

        if self.timestamp_src or self.timestamp_dst:
            attrs = {}
            if self.timestamp_src:
                attrs["src"] = str(self.timestamp_src)
            if self.timestamp_dst:
                attrs["dst"] = str(self.timestamp_dst)
            etree.SubElement(xmltree, "timestamp", attrs)

        # Dump plugins
        usedplugins = etree.SubElement(xmltree, "usedplugins")
        for plugin in self.usedplugins.values():
            attrs = {"name": plugin.name, "version": str(plugin.version)}
            plugin._subelement(usedplugins, "plugin", attrs)

        return etree.tostring(xmltree,
                              pretty_print=True,
                              encoding="UTF-8",
                              xml_declaration=True)

    def dump(self, fn, compression_type=deltarepo.XZ, stat=None):
        """
        Dump data to a file.

        :param fn: path to a file
        :type fn: str
        :param compression_type: Type of compression
        :type compression_type: int
        :param stat: Stat object
        :type stat: cr.ContentStat or None
        :returns: Real used path (basename with compression suffix)
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
        f = cr.CrFile(fn, cr.MODE_WRITE, compression_type, stat)
        f.write(content)
        f.close()
        return fn