/**
 * @file 
 *
 * Support for threading.
 *
 * There are three macros here.
 * \c PYMEMTRACE_LOCK_DECLARE_LOCK_IN_PYOBJECT is to allocate a lock within an object.
 * This must **not** be used with a trailing semi colon.
 * \c PYMEMTRACE_LOCK_ACQUIRE_LOCK to acquire the object lock
 * and \c PYMEMTRACE_LOCK_RELEASE_LOCK is to release the object lock.
 *
 * Example of macro usage:
 *
 * @code
 *  // Object declaration.
 *  typedef struct {
 *      PyObject_HEAD
 *      // Other stuff...
 *      // This adds a "_mutex_lock" field.
 *      PYMEMTRACE_LOCK_DECLARE_LOCK_IN_PYOBJECT
 *  } cpyObject;
 *
 *  // Blocking function
 *  void some_function(cpyObject *object) {
 *      PYMEMTRACE_LOCK_ACQUIRE_LOCK(object);
 *      // Blocking code here...
 *      PYMEMTRACE_LOCK_RELEASE_LOCK(object);
 *  }
 * @endcode
 *
 * Created by PaulRoss on 11/07/2026.
 */

#ifndef PYMEMTRACE_THREADING_H
#define PYMEMTRACE_THREADING_H

#define PY_SSIZE_T_CLEAN

#include <Python.h>

#if PY_MAJOR_VERSION != 3
    #error "Python major version must be 3"
#endif

#ifdef WITH_THREAD
    #if PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION < 13
        /* Old style lock. */
        #define PYMEMTRACE_LOCK_DECLARE_LOCK_IN_PYOBJECT PyThread_type_lock _mutex_lock;

        #define PYMEMTRACE_LOCK_ACQUIRE_LOCK(obj) do {              \
            if (!PyThread_acquire_lock((obj)->_mutex_lock, 0)) {    \
            Py_BEGIN_ALLOW_THREADS                                  \
            PyThread_acquire_lock((obj)->_mutex_lock, 1);           \
            Py_END_ALLOW_THREADS                                    \
            } } while (0)

        #define PYMEMTRACE_LOCK_RELEASE_LOCK(obj) PyThread_release_lock((obj)->_mutex_lock)
    #else
        /* New style mutex lock.
         * See: https://docs.python.org/3/c-api/synchronization.html
         */
        #define PYMEMTRACE_LOCK_DECLARE_LOCK_IN_PYOBJECT PyMutex _mutex_lock;
        #define PYMEMTRACE_LOCK_ACQUIRE_LOCK(obj) PyMutex_Lock(obj->_mutex_lock)
        #define PYMEMTRACE_LOCK_RELEASE_LOCK(obj) PyMutex_Unlock((obj)->_mutex_lock)
    #endif


#else
    /* Non-threaded Python. */
    #define PYMEMTRACE_LOCK_DECLARE_LOCK_IN_PYOBJECT
    #define PYMEMTRACE_LOCK_ACQUIRE_LOCK(obj)
    #define PYMEMTRACE_LOCK_RELEASE_LOCK(obj)
#endif

unsigned long get_current_thread_id(void);

#endif //PYMEMTRACE_THREADING_H
