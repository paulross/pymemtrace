//
// Created by Paul Ross on 03/11/2020.
//

#define _POSIX_C_SOURCE 200112L  // For gmtime_r in <time.h>

#include <stdio.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>

#include "pymemtrace_util.h"

const char *create_filename(void) {
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
    if (snprintf(filename + len, PYMEMTRACE_FILE_NAME_MAX_LENGTH - len - 1, "_%d.log", pid) == 0) {
        fprintf(stderr, "create_filename(): failed to add PID.");
        return NULL;
    }
    return filename;
}

const char *current_working_directory(void) {
    static char cwd[PYMEMTRACE_PATH_NAME_MAX_LENGTH];
    if (getcwd(cwd, sizeof(cwd)) == NULL) {
        fprintf(stderr, "Can not get current working directory.\n");
        return NULL;
    }
    return cwd;
}
