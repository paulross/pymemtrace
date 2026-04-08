//
// Created by Paul Ross on 03/11/2020.
//

#ifndef CPYMEMTRACE_PYMEMTRACE_UTIL_H
#define CPYMEMTRACE_PYMEMTRACE_UTIL_H

#define PYMEMTRACE_PATH_NAME_MAX_LENGTH 4096
#define PYMEMTRACE_FILE_NAME_MAX_LENGTH 1024
#define PYMEMTRACE_FUNCTION_NAME_MAX_LENGTH 1024

char *create_filename(char trace_type, size_t trace_stack_depth);
const char *current_working_directory(void);
int create_filename_within_cwd(char trace_type, size_t trace_stack_depth,
                               char* restrict buffer, size_t bufsz);

#endif //CPYMEMTRACE_PYMEMTRACE_UTIL_H
