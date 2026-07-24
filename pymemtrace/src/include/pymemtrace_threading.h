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
 *  // Object installation. Corresponding to __init__
 *  static int
 * SubList_init(SubListObject *self, PyObject *args, PyObject *kwds) {
    if (PyList_Type.tp_init((PyObject *) self, args, kwds) < 0) {
        return -1;
    }
#ifdef WITH_THREAD
    self->lock = PyThread_allocate_lock();
    if (self->lock == NULL) {
        PyErr_SetString(PyExc_MemoryError, "Unable to allocate thread lock.");
        return -2;
    }
#endif
    return 0;
}

 *
 *
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
        #define PYMEMTRACE_LOCK_DECLARE_LOCK PyThread_type_lock _mutex_lock = PyThread_allocate_lock();

        #define PYMEMTRACE_LOCK_ACQUIRE_LOCK do {       \
        if (!PyThread_acquire_lock(&_mutex_lock, 0)) {   \
            Py_BEGIN_ALLOW_THREADS                      \
            PyThread_acquire_lock(&_mutex_lock, 1);      \
            Py_END_ALLOW_THREADS                        \
        } } while (0)

        #define PYMEMTRACE_LOCK_RELEASE_LOCK PyThread_release_lock(_mutex_lock)

        #define PYMEMTRACE_LOCK_FREE_LOCK PyThread_free_lock(_mutex_lock); _mutex_lock = NULL

        #define PYMEMTRACE_LOCK_DECLARE_LOCK_IN_PYOBJECT PyThread_type_lock _mutex_lock;
        #define PYMEMTRACE_LOCK_ALLOCATE_LOCK_IN_PYOBJECT(obj) (obj)->_mutex_lock = PyThread_allocate_lock()

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
        #define PYMEMTRACE_LOCK_FREE_LOCK

        #define PYMEMTRACE_LOCK_DECLARE_LOCK_IN_PYOBJECT PyMutex _mutex_lock = {0};
        #define PYMEMTRACE_LOCK_ALLOCATE_LOCK_IN_PYOBJECT(obj)
        #define PYMEMTRACE_LOCK_ACQUIRE_LOCK_IN_PYOBJECT(obj) PyMutex_Lock(obj->_mutex_lock)
        #define PYMEMTRACE_LOCK_RELEASE_LOCK_IN_PYOBJECT(obj) PyMutex_Unlock((obj)->_mutex_lock)
        #define PYMEMTRACE_LOCK_FREE_LOCK_IN_PYOBJECT(obj)
    #endif


#else
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

unsigned long get_current_thread_id(void);

#endif //PYMEMTRACE_THREADING_H
