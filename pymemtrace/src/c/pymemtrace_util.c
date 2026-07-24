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
#include <pthread.h>
#include <time.h>
#include <unistd.h>

#include "pymemtrace_util.h"

/**
 * This is used to discriminate between log files that are created at the same second as struct tm does not have
 * fractions of a second.
 */
static int file_number = 0;

/**
 * Creates a log file name with the timestamp (to the second), the process ID and the Python version.
 * Not thread safe.
 *
 * @param trace_type 'T' for a trace function, 'P' for a profile function, 'O' for Reference Tracing of objects.
 * @param trace_stack_depth The length of the linked list of trace functions starting from 0.
 *  This discriminates log files when there is nested tracing.
 * @return The log file name or NULL on failure. For example "20241107_195847_17_62264_P_0_PY3.13.0b3.log".
 */
char *create_filename(char trace_type, size_t trace_stack_depth) {
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
    int byte_len = snprintf(
        filename + len,
        PYMEMTRACE_FILE_NAME_MAX_LENGTH - len - 1,
        "_%d_%d_%c_%zu_PY%s.log",
        file_number++, pid, trace_type, trace_stack_depth, PY_VERSION
    );

    if (byte_len == 0) {
        fprintf(stderr, "create_filename(): failed to add PID, stack depth and Python version.");
        return NULL;
    }
    return filename;
}

/**
 * Get the current working directory using \c getcwd().
 * Not thread safe.
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

/**
 * Creates a log file name with the timestamp (to the second), the process ID and the Python version.
 * For example "20241107_195847_17_62264_P_0_PY3.13.0b3.log".
 * Not thread safe.
 *
 * @param trace_type 'T' for a trace function, 'P' for a profile function, 'O' for Reference Tracing of objects.
 * @param trace_stack_depth The length of the linked list of trace functions starting from 0.
 *  This discriminates log files when there is nested tracing.
 * @return 0 on failure or number of bytes written to the buffer.
 */
static size_t
write_filename_to_buffer(char trace_type, size_t trace_stack_depth, char *buffer) {
    static struct tm now;
    time_t t = time(NULL);
    gmtime_r(&t, &now);
    size_t ret = strftime(buffer, PYMEMTRACE_FILE_NAME_MAX_LENGTH, "%Y%m%d_%H%M%S", &now);
    if (ret == 0) {
        fprintf(stderr, "create_filename(): strftime failed.");
        return ret;
    }
    pid_t pid = getpid();
    int suffix_len = snprintf(
        buffer + ret,
        PYMEMTRACE_FILE_NAME_MAX_LENGTH - ret - 1,
        "_%d_%d_%lu_%c_%zu_PY%s.log",
        file_number++, pid, get_current_thread_id(), trace_type, trace_stack_depth, PY_VERSION
    );
    if (suffix_len == 0) {
        fprintf(stderr, "create_filename(): failed to add PID, stack depth and Python version.");
        return 0;
    }
    ret += suffix_len;
    return ret;
}

/**
 * Get the current working directory using \c getcwd().
 * Not thread safe.
 *
 * See https://pubs.opengroup.org/onlinepubs/009696599/functions/getcwd.html
 *
 * @return The length written into the buffer.
 */
static size_t
write_cwd_to_buffer(char *buffer, size_t buffer_size) {
    char *result = getcwd(buffer, buffer_size);
    if (result == NULL) {
        fprintf(stderr, "Can not get current working directory.\n");
        return 0;
    }
    assert(result == buffer);
    return strlen(buffer);
}

/**
 * Create a file path within the current working directory.
 * The file name will be, for example, \c "20241107_195847_17_62264_P_0_PY3.13.0b3.log".
 * This is thread safe.
 *
 * @param trace_type 'T' for a trace function, 'P' for a profile function, 'O' for Reference Tracing of objects.
 * @param trace_stack_depth The length of the linked list of trace functions starting from 0.
 *  This discriminates log files when there is nested tracing.
 * @param buffer The buffer to write the path and filename to.
 * @param bufsz The size of the buffer.
 * @return The number of bytes written to the buffer. A negative number on failure.
 */
size_t
create_filename_within_cwd(char trace_type, size_t trace_stack_depth, char* restrict buffer, size_t buffer_size) {
    pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;
    if (pthread_mutex_lock(&mutex)) {
        return -1;
    }
    size_t ret = write_cwd_to_buffer(buffer, buffer_size);
#ifdef _WIN32
    buffer[ret++] = '\\';
#else
    buffer[ret++] = '/';
#endif
    ret += write_filename_to_buffer(trace_type, trace_stack_depth, buffer + ret);
    if (pthread_mutex_unlock(&mutex)) {
        return -2;
    }
    /* Free any dynamically allocated state during the use of the mutex,
     * for example when locking. */
    if (pthread_mutex_destroy(&mutex)) {
        return -3;
    }
    return ret;
}
