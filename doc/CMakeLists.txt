ADD_CUSTOM_TARGET (doc
    PYTHONPATH=${CMAKE_SOURCE_DIR} sphinx-build -E -b html
                  ${CMAKE_CURRENT_SOURCE_DIR} ${CMAKE_CURRENT_BINARY_DIR}
                  COMMENT "Building Python API documentation with Sphinx")
