//
// Created by PaulRoss on 17/08/2026.
//

#ifndef PYMEMTRACE_MACROS_H
#define PYMEMTRACE_MACROS_H

#include <stdio.h>
#include <stdlib.h>

#ifdef DEBUG
#define PYMEMTRACE_DASSERT(expr)                                                \
    do {                                                                        \
        if (expr) {} else {                                                     \
            fprintf(                                                            \
                stderr,                                                         \
                "ASSERT: %s(): File %s Line %ld Assertion failed: \"%s\"\n",    \
                __func__, __FILE__, (long)__LINE__, #expr                       \
            );                                                                  \
            exit(EXIT_FAILURE);                                                 \
        }                                                                       \
    } while (0)
#else
#define PYMEMTRACE_DASSERT(expr) do {} while (0)
#endif

#endif //PYMEMTRACE_MACROS_H
