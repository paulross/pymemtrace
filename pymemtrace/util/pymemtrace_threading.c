//
// Created by PaulRoss on 13/07/2026.
//
#include "pymemtrace_threading.h"

#ifdef WITH_THREAD
/**
 * See https://docs.python.org/3/c-api/threads.html#c.PY_HAVE_THREAD_NATIVE_ID
 *
 * And: https://docs.python.org/3/c-api/threads.html#c.PyThread_get_thread_native_id
 *
 * Python 3.8+
 *
 * @return The current thread ID as an unsigned long.
 */
unsigned long get_current_thread_id(void) {
#ifndef PY_HAVE_THREAD_NATIVE_ID
#error "PY_HAVE_THREAD_NATIVE_ID is not defined"
#endif
    return PyThread_get_thread_native_id();
}

#else
unsigned long get_current_thread_id(void) {
    return 0;
}
#endif
