
__all__ = ["DeltaRepoError", "DeltaRepoPluginError"]

class DeltaRepoError(Exception):
    """Exception raised by deltarepo library"""
    pass

class DeltaRepoPluginError(DeltaRepoError):
    """Exception raised by delta plugins of deltarepo library"""
    pass

class DeltaRepoParseError(DeltaRepoError):
    """Exception raised when a parse error occurs"""
    pass