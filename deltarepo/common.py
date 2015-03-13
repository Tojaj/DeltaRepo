import re
import logging

import six
import createrepo_c as cr


DEFAULT_CHECKSUM_NAME = "sha256"
DEFAULT_CHECKSUM_TYPE = cr.SHA256
DEFAULT_COMPRESSION_TYPE = cr.GZ

# Compression types
AUTO_DETECT_COMPRESSION = cr.AUTO_DETECT_COMPRESSION
UNKNOWN_COMPRESSION = cr.UNKNOWN_COMPRESSION
NO_COMPRESSION = cr.NO_COMPRESSION
GZ = cr.GZ
BZ2 = cr.BZ2
XZ = cr.XZ


class LoggingInterface(object):
    """Base class with logging support.
    Other classes inherit this class to obtain
    support of logging methods.
    """

    def __init__(self, logger=None):
        self.logger = None
        self._set_logger(logger)

    def _set_logger(self, logger=None):
        if logger is None:
            logger = logging.getLogger()
            logger.disabled = True
        self.logger = logger

    def _get_logger(self):
        return self.logger

    def _log(self, level, msg):
        self.logger.log(level, msg)

    def _debug(self, msg):
        self._log(logging.DEBUG, msg)

    def _info(self, msg):
        self._log(logging.INFO, msg)

    def _warning(self, msg):
        self._log(logging.WARNING, msg)

    def _error(self, msg):
        self._log(logging.ERROR, msg)

    def _critical(self, msg):
        self._log(logging.CRITICAL, msg)


class ValidationMixin(object):
    """Adds support for self validation.

    Adds validate() method that validates attributes
    by running all self._validate_*() methods.
    Also provides some convenient _assert_*() methods for validation.
    """

    def validate(self):
        """Validate attributes by runing all self._validate_*() methods.

        :raises TypeError: if and attribute has invalid type
        :raises ValueError: if and attribute contains invalid value
        """
        method_names = sorted([i for i in dir(self) if i.startswith("_validate") and callable(getattr(self, i))])
        for method_name in method_names:
            method = getattr(self, method_name)
            method()

    def _assert_val_type(self, val, description, expected_types, allow_none=False):
        if allow_none and val is None:
            return
        for atype in expected_types:
            if isinstance(val, atype):
                return
        raise TypeError("%s: %s has invalid type: %s" % (self.__class__.__name__, description, type(val)))

    def _assert_type(self, field, expected_types, allow_none=False):
        value = getattr(self, field)
        if allow_none and value is None:
            return
        for atype in expected_types:
            if isinstance(value, atype):
                return
        raise TypeError("%s: Attr '%s' has invalid type: %s" % (self.__class__.__name__, field, type(value)))

    def _assert_value(self, field, expected_values):
        value = getattr(self, field)
        if value not in expected_values:
            raise ValueError("%s: Attr '%s' has invalid value: %s" % (self.__class__.__name__, field, value))

    def _assert_not_blank(self, field):
        value = getattr(self, field)
        if not value:
            raise ValueError("%s: Attr '%s' must not be blank" % (self.__class__.__name__, field))

    def _assert_matches_re(self, field, expected_patterns):
        value = getattr(self, field)
        matches = False
        for pattern in expected_patterns:
            if re.match(pattern, value):
                matches = True
                break
        if not matches:
            raise ValueError("%s: Attr '%s' has invalid value: %s. It does not match any provided REs: %s"
                             % (self.__class__.__name__, field, value, expected_patterns))

    def _assert_nonnegative_integer(self, field):
        self._assert_type(field, six.integer_types)
        value = getattr(self, field)
        if value < 0:
            raise ValueError("%s: Attr '%s' must be nonnegative integer" % (self.__class__.__name__, field))