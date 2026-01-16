//
// Created by Paul Ross on 03/11/2020.
//
#define PY_SSIZE_T_CLEAN

#include <Python.h>

#ifndef _POSIX_C_SOURCE
#define _POSIX_C_SOURCE 200112L  // For gmtime_r in <time.h>
#endif

#include <stdio.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>

#include "pymemtrace_util.h"

/**
 * Creates a log file name with the timestamp (to the second), the process ID and the Python version.
 *
 * @param trace_type 'T' for a trace function, 'P' for a profile function.
 * @param trace_stack_depth The length of the linked list of trace functions starting from 0.
 *  This discriminates log files when there is nested tracing.
 * @return The log file name or NULL on failure. For example "20241107_195847_62264_P_0_PY3.13.0b3.log".
 */
const char *create_filename(char trace_type, int trace_stack_depth) {
    /* Not thread safe. */
    static char filename[PYMEMTRACE_FILE_NAME_MAX_LENGTH];
    static struct tm now;
    time_t t = time(NULL);
    gmtime_r(&t, &now);
    size_t len = strftime(filename, PYMEMTRACE_FILE_NAME_MAX_LENGTH, "%Y%m%d_%H%M%S", &now);
    if (len == 0) {
        fprintf(stderr, "create_filename(): strftime failed.");
        return NULL;
    }
    pid_t pid = getpid();
    if (snprintf(filename + len, PYMEMTRACE_FILE_NAME_MAX_LENGTH - len - 1, "_%d_%c_%d_PY%s.log", pid, trace_type, trace_stack_depth, PY_VERSION) == 0) {
        fprintf(stderr, "create_filename(): failed to add PID, stack depth and Python version.");
        return NULL;
    }
    return filename;
}

/**
 * Get the current working directory using \c getcwd().
 *
 * @return The current working directory or NULL on failure.
 */
const char *current_working_directory(void) {
    static char cwd[PYMEMTRACE_PATH_NAME_MAX_LENGTH];
    if (getcwd(cwd, sizeof(cwd)) == NULL) {
        fprintf(stderr, "Can not get current working directory.\n");
        return NULL;
    }
    return cwd;
}
