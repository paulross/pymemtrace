/**
 * @file 
 *
 * Support for threading across multiple Python versions.
 * See: https://docs.python.org/3/c-api/synchronization.html#synchronization-primitives
 *
 * Prior to version Python 3.13 there was a "secret" (undocumented) locking mechanism
 * that is described here: https://pythonextensionpatterns.readthedocs.io/en/latest/thread_safety.html
 * This was only documented as a legacy API in the Python 3.13 documentation onwards.
 *
 * With Python 3.13 onwards the PyMutex was introduced: https://docs.python.org/3.13/c-api/init.html#c.PyMutex
 *
 * Local Locks
 * -----------
 *
 * There are these macros defined here.
 *
 * - \c PYMEMTRACE_LOCK_DECLARE_LOCK declares a local lock object. This is named \c _mutex_lock
 * - \c PYMEMTRACE_LOCK_ACQUIRE_LOCK acquires a local lock object.
 * - \c PYMEMTRACE_LOCK_RELEASE_LOCK releases a local lock object.
 * - \c PYMEMTRACE_LOCK_FREE_LOCK releases a local lock object.
 *
 * Typical usage in a function:
 *
 * @code
 *  void foo(void) {
 *      PYMEMTRACE_LOCK_DECLARE_LOCK; // Named _mutex_lock
 *      PYMEMTRACE_LOCK_ACQUIRE_LOCK; // Blocks until lock is acquired.
 *      ... // Critical section.
 *      PYMEMTRACE_LOCK_RELEASE_LOCK; // Release the lock.
 *      PYMEMTRACE_LOCK_FREE_LOCK; // Free the lock.
 *  }
 * @endcode
 *
 * Per-object locks
 * ----------------
 *
 * This is for a lock associated with a \c PyObject
 *
* There are these macros defined here.
 *
 * - \c PYMEMTRACE_LOCK_DECLARE_LOCK_IN_PYOBJECT declares a lock in an object.
 *   This field is named \c _mutex_lock
 *   NOTE: This must **not** be used with a trailing semicolon.
 * - \c PYMEMTRACE_LOCK_ALLOCATE_LOCK_IN_PYOBJECT(obj) this allocates a lock in the object.
 * - \c PYMEMTRACE_LOCK_ACQUIRE_LOCK_IN_PYOBJECT(obj) acquires the lock in the object.
 * - \c PYMEMTRACE_LOCK_RELEASE_LOCK_IN_PYOBJECT(obj) releases the lock in the object.
 * - \c PYMEMTRACE_LOCK_FREE_LOCK_IN_PYOBJECT(obj) frees the lock in the object.
 *
 * Typical usage for a \c Pyobject, first declaration of the lock in the \c PyObject:
 *
* @code
 *  // Object declaration.
 *  typedef struct {
 *      PyObject_HEAD
 *      // Other stuff...
 *      // This adds a "_mutex_lock" field. NOTE: No trailing semicolon.
 *      PYMEMTRACE_LOCK_DECLARE_LOCK_IN_PYOBJECT
 *  } cpyObject;
 * @endcode
 *
 * Initialising the lock in the object instantiation:
 *
 * @code
 *  // Object installation. Corresponding to __init__
 *  static int
 *  cpyObject_init(cpyObject *self, PyObject *args, PyObject *kwds) {
 *      if (PyList_Type.tp_init((PyObject *) self, args, kwds) < 0) {
 *          return -1;
 *      }
 *      // This will do an early return of -2 with an error set.
 *      // NOTE: No use of semicolon.
 *      PYMEMTRACE_LOCK_ALLOCATE_LOCK_IN_PYOBJECT(self)
 *      return 0;
 *  }
 * @endcode
 *
 * Using the lock in an object method:
 *
 * @code
 *  // Blocking function
 *  static PyObject *
 *  cpyObject_some_function(cpyObject *self, PyObject *args, PyObject *kwds) {
 *      PYMEMTRACE_LOCK_ACQUIRE_LOCK_IN_PYOBJECT(self);
 *      // Critical section...
 *      PYMEMTRACE_LOCK_RELEASE_LOCK_IN_PYOBJECT(self);
 *      Py_RETURN_NONE;
 *  }
 * @endcode
 *
 * And in the object finalisation:
 *
 * @code
 *  static void
 *  cpyObject_dealloc(cpyObject *self) {
 *      // Other stuff...
 *      PYMEMTRACE_LOCK_FREE_LOCK_IN_PYOBJECT(self);
 *      // Other stuff...
 *      PyObject_Del((PyObject *) self);
 *  }
 * @endcode
 *
 * Created by PaulRoss on 11/07/2026.
 */

#ifndef PYMEMTRACE_THREADING_H
#define PYMEMTRACE_THREADING_H

#define PY_SSIZE_T_CLEAN

#include <Python.h>

#ifdef WITH_THREAD
    #include <pythread.h>
#else
    #error "Python threading must be enabled."
#endif

#if PY_MAJOR_VERSION != 3
    #error "Python major version must be 3"
#endif

#ifdef WITH_THREAD
    #if PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION < 13
        /* Old style lock. */
        /* Local lock such as in a function. */
        #define PYMEMTRACE_LOCK_DECLARE_LOCK PyThread_type_lock _mutex_lock = PyThread_allocate_lock();
        #define PYMEMTRACE_LOCK_ACQUIRE_LOCK do {       \
        if (!PyThread_acquire_lock(&_mutex_lock, 0)) {  \
            Py_BEGIN_ALLOW_THREADS                      \
            PyThread_acquire_lock(&_mutex_lock, 1);     \
            Py_END_ALLOW_THREADS                        \
        } } while (0)
        #define PYMEMTRACE_LOCK_RELEASE_LOCK PyThread_release_lock(_mutex_lock)
        #define PYMEMTRACE_LOCK_FREE_LOCK PyThread_free_lock(_mutex_lock); _mutex_lock = NULL

        /* A lock in an object. */
        #define PYMEMTRACE_LOCK_DECLARE_LOCK_IN_PYOBJECT PyThread_type_lock _mutex_lock;
        /* NOTE: Do not use this with a semicolon. */
        #define PYMEMTRACE_LOCK_ALLOCATE_LOCK_IN_PYOBJECT(obj) do {                     \
            (obj)->_mutex_lock = PyThread_allocate_lock()                               \
            if ((obj)->_mutex_lock == NULL) {                                           \
                PyErr_SetString(PyExc_MemoryError, "Unable to allocate thread lock.");  \
                return -2;                                                              \
            } } while (0)
        #define PYMEMTRACE_LOCK_ACQUIRE_LOCK_IN_PYOBJECT(obj) do {      \
            if (!PyThread_acquire_lock((obj)->_mutex_lock, 0)) {        \
                Py_BEGIN_ALLOW_THREADS                                  \
                PyThread_acquire_lock((obj)->_mutex_lock, 1);           \
                Py_END_ALLOW_THREADS                                    \
            } } while (0)
        #define PYMEMTRACE_LOCK_RELEASE_LOCK_IN_PYOBJECT(obj) PyThread_release_lock((obj)->_mutex_lock)
        #define PYMEMTRACE_LOCK_FREE_LOCK_IN_PYOBJECT(obj) do { \
            if (obj->_mutex_lock) {                             \
                PyThread_free_lock(self->_mutex_lock);          \
                self->_mutex_lock = NULL;                       \
            }

    #else
        /* New style mutex lock.
         * See: https://docs.python.org/3/c-api/synchronization.html
         */
        #define PYMEMTRACE_LOCK_DECLARE_LOCK PyMutex _mutex_lock = {0};
        #define PYMEMTRACE_LOCK_ACQUIRE_LOCK PyMutex_Lock(&_mutex_lock)
        #define PYMEMTRACE_LOCK_RELEASE_LOCK PyMutex_Unlock(&_mutex_lock)
        #define PYMEMTRACE_LOCK_FREE_LOCK do { } while (0)

        #define PYMEMTRACE_LOCK_DECLARE_LOCK_IN_PYOBJECT PyMutex _mutex_lock = {0};
        /* NOTE: Do not use this with a semicolon. */
        #define PYMEMTRACE_LOCK_ALLOCATE_LOCK_IN_PYOBJECT(obj) do { } while (0)
        #define PYMEMTRACE_LOCK_ACQUIRE_LOCK_IN_PYOBJECT(obj) PyMutex_Lock(obj->_mutex_lock)
        #define PYMEMTRACE_LOCK_RELEASE_LOCK_IN_PYOBJECT(obj) PyMutex_Unlock((obj)->_mutex_lock)
        #define PYMEMTRACE_LOCK_FREE_LOCK_IN_PYOBJECT(obj) do { } while (0)
    #endif

#else
#error "Not tested with single threaded Python."
    /* Non-threaded Python. */
    #define PYMEMTRACE_LOCK_DECLARE_LOCK
    #define PYMEMTRACE_LOCK_ACQUIRE_LOCK
    #define PYMEMTRACE_LOCK_RELEASE_LOCK
    #define PYMEMTRACE_LOCK_FREE_LOCK

    #define PYMEMTRACE_LOCK_DECLARE_LOCK_IN_PYOBJECT
    #define PYMEMTRACE_LOCK_ALLOCATE_LOCK_IN_PYOBJECT(obj)
    #define PYMEMTRACE_LOCK_ACQUIRE_LOCK_IN_PYOBJECT(obj)
    #define PYMEMTRACE_LOCK_RELEASE_LOCK_IN_PYOBJECT(obj)
    #define PYMEMTRACE_LOCK_FREE_LOCK_IN_PYOBJECT(obj)
#endif

typedef unsigned long tThreadID;

tThreadID get_current_thread_id(void);

#endif //PYMEMTRACE_THREADING_H
