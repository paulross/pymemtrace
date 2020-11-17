//
// Created by Paul Ross on 03/11/2020.
//
#include <stdio.h>
#include <time.h>
#include <unistd.h>

#include "pymemtrace_util.h"

#define PATH_MAX 4096

char *create_filename(void) {
    /* Not thread safe. */
    static char filename[256];
    static struct tm now;
    time_t t = time(NULL);
    gmtime_r(&t, &now);
    size_t len = strftime(filename, 256, "%Y%m%d_%H%M%S", &now);
    if (len == 0) {
        fprintf(stderr, "create_filename(): strftime failed.");
        return NULL;
    }
    pid_t pid = getpid();
    if (snprintf(filename + len, 256 - len - 1, "_%d.log", pid) == 0) {
        fprintf(stderr, "create_filename(): failed to add PID.");
        return NULL;
    }
    return filename;
}

char *current_working_directory(void) {
    static char cwd[PATH_MAX];
    if (getcwd(cwd, sizeof(cwd)) == NULL) {
        fprintf(stderr, "Can not get current working directory.\n");
        return NULL;
    }
    return cwd;
}
