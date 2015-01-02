PROJECT (deltarepo)
CMAKE_MINIMUM_REQUIRED (VERSION 2.6)

INCLUDE (${CMAKE_SOURCE_DIR}/VERSION.cmake)
SET (VERSION "${LIBREPO_MAJOR}.${LIBREPO_MINOR}.${LIBREPO_PATCH}")

FIND_PACKAGE (PythonInterp REQUIRED)

EXECUTE_PROCESS(COMMAND
                ${PYTHON_EXECUTABLE} -c "from sys import stdout; from distutils import sysconfig; stdout.write(sysconfig.get_python_lib())"
                OUTPUT_VARIABLE PYTHON_INSTALL_DIR)
EXECUTE_PROCESS(COMMAND
                ${PYTHON_EXECUTABLE} -c "import sys; sys.stdout.write('%s.%s' % (sys.version_info.major, sys.version_info.minor))"
                OUTPUT_VARIABLE PYTHON_MAJOR_DOT_MINOR_VERSION)

MESSAGE(STATUS "Python install dir is ${PYTHON_INSTALL_DIR}")


CONFIGURE_FILE(${CMAKE_SOURCE_DIR}/deltarepo/const.py.in
               ${CMAKE_SOURCE_DIR}/deltarepo/const.py
               @ONLY)

#INSTALL(DIRECTORY deltarepo/
#        DESTINATION ${PYTHON_INSTALL_DIR}/deltarepo
#        FILES_MATCHING PATTERN "*.py")

ENABLE_TESTING()

ADD_SUBDIRECTORY(bin)
ADD_SUBDIRECTORY(deltarepo)
ADD_SUBDIRECTORY(dnf-plugins)
ADD_SUBDIRECTORY(doc)
ADD_SUBDIRECTORY(tests)
