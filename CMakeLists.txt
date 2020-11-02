cmake_minimum_required(VERSION 3.13)
project(cPyMemTrace)

#set(CMAKE_CXX_STANDARD 17)
set(CMAKE_C_FLAGS "-std=c99")

#add_compile_definitions(SVF_THREAD_SAFE)

IF(CMAKE_BUILD_TYPE MATCHES DEBUG)
    message("debug build")
    add_compile_definitions(DEBUG)
ELSE()
    message("release build")
ENDIF(CMAKE_BUILD_TYPE MATCHES DEBUG)

add_compile_options(
    "-Wall"
    "-Wextra"
    "-Wpedantic"
    "-Werror"
    "-Wfatal-errors"
    "-Wno-unused-variable" # Temporary
    "-Wno-unused-parameter" # Temporary
    "-fexceptions"
    "$<$<CONFIG:DEBUG>:-O0;-g3;-ggdb>"
)

link_directories(
    /Library/Frameworks/Python.framework/Versions/3.8/lib
)

add_executable(
    cPyMemTrace
    pymemtrace/src/main.c
    pymemtrace/src/include/get_rss.h
    pymemtrace/src/c/get_rss.c
    pymemtrace/src/cpy/cPyMemTrace.c
    pymemtrace/src/cpy/cCustom.c
)

include_directories(
    pymemtrace/src/include
)

FIND_PACKAGE(PythonLibs 3.8 REQUIRED)
IF(PYTHONLIBS_FOUND)
    message(status " Python: ${PYTHON_INCLUDE_DIRS}")
    INCLUDE_DIRECTORIES("${PYTHON_INCLUDE_DIRS}")
ELSE()
    MESSAGE(FATAL_ERROR "Unable to find Python libraries.")
ENDIF()

target_link_libraries(cPyMemTrace python3.8)

target_compile_options(cPyMemTrace PRIVATE -Wall -Wextra -Wno-c99-extensions -pedantic)# -Werror)
