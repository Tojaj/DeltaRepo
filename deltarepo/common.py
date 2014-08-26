import logging
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
