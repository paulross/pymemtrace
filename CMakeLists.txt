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
#    "-Wno-unused-variable" # Temporary
#    "-Wno-unused-parameter" # Temporary
    "-fexceptions"
    "$<$<CONFIG:DEBUG>:-O0;-g3;-ggdb>"
)

#link_directories(
#    /Library/Frameworks/Python.framework/Versions/3.8/lib
#)

add_executable(
    cPyMemTrace
    pymemtrace/src/main.c
    pymemtrace/src/include/get_rss.h
    pymemtrace/src/c/get_rss.c
    pymemtrace/src/cpy/cPyMemTrace.c
    pymemtrace/src/cpy/cCustom.c
    pymemtrace/src/cpy/cMemLeak.c
    pymemtrace/src/include/pymemtrace_util.h
    pymemtrace/src/c/pymemtrace_util.c
)

include_directories(
    pymemtrace/src/include
)

FIND_PACKAGE (Python3 3.11 EXACT REQUIRED COMPONENTS Interpreter Development)
#FIND_PACKAGE(PythonLibs 3.11 EXACT REQUIRED)
#SET(PythonLibs_DIR "/Library/Frameworks/Python.framework/Versions/3.8")
#FIND_PACKAGE(PythonLibs 3.8 REQUIRED PATHS ("/Library/Frameworks/Python.framework/Versions/3.8"))
#FindPythonLibs()
IF (Python3_FOUND)
    INCLUDE_DIRECTORIES("${Python3_INCLUDE_DIRS}")
    get_filename_component(PYTHON_LINK_DIRECTORY ${PYTHON_LIBRARY} DIRECTORY)
    # See: https://cmake.org/cmake/help/latest/module/FindPython3.html#module:FindPython3
    message("Python3_VERSION:           ${Python3_VERSION}")
    message("Python3_EXECUTABLE:        ${Python3_EXECUTABLE}")
    message("Python3_INTERPRETER_ID:    ${Python3_INTERPRETER_ID}")
    message("Python3_INCLUDE_DIRS:      ${Python3_INCLUDE_DIRS}")
    message("Python3_STDLIB:            ${Python3_STDLIB}")
    message("Python3_STDARCH:           ${Python3_STDARCH}")
    message("Python3_LINK_OPTIONS:      ${Python3_LINK_OPTIONS}")
    message("Python3_LIBRARIES:         ${Python3_LIBRARIES}")
ELSE ()
    MESSAGE(FATAL_ERROR "Unable to find Python libraries.")
ENDIF ()

#FIND_PACKAGE(PythonLibs 3.8 REQUIRED)
#IF(PYTHONLIBS_FOUND)
#    message(status " Python: ${PYTHON_INCLUDE_DIRS}")
#    INCLUDE_DIRECTORIES("${PYTHON_INCLUDE_DIRS}")
#ELSE()
#    MESSAGE(FATAL_ERROR "Unable to find Python libraries.")
#ENDIF()

link_directories(${PYTHON_LINK_LIBRARY})

target_link_libraries(${PROJECT_NAME} ${PYTHON_LIBRARY})

#target_link_libraries(cPyMemTrace python3.8)

target_compile_options(cPyMemTrace PRIVATE -Wall -Wextra -Wno-c99-extensions -pedantic)# -Werror)
