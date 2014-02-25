FILE(GLOB deltarepo_SRCS *.py)
INSTALL (FILES ${deltarepo_SRCS} DESTINATION ${PYTHON_INSTALL_DIR}/deltarepo)
# const.py is generated so the glob alone won't see it:
INSTALL (FILES const.py DESTINATION ${PYTHON_INSTALL_DIR}/deltarepo)
