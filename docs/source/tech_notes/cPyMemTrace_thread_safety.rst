
.. _tech_notes-cpymemtrace_thread_safetey:

.. raw:: latex

    [Continued on the next page]

    \pagebreak

Technical Note on ``cPyMemTrace`` Thread Safety
===============================================

:py:mod:`pymemtrace.cPyMemTrace` up to and including version 0.6.1
was not thread safe.

The Problem
-------------------------------

The CPython runtime can only have one Profile/Trace/Reference Trace
callback function at any time.
:py:mod:`pymemtrace.cPyMemTrace` gets over this limitation where multiple
tracers are required by maintaining a linked list of callbacks.
When a new one is created it is pushed onto the head of the list and
takes precedence.
When it goes out of scope it is popped from the list and the older one
is re-registered.

For example:

.. code-block:: python

    from pymemtrace import cPyMemTrace

    with cPyMemTrace.ReferenceTracing(filepath='A.log'):
        # Now writing to "A.log"
        with cPyMemTrace.ReferenceTracing(filepath='B.log'):
            # Writing to "A.log" is suspended.
            # Now writing to "B.log"
            pass
        # The log file "B.log" is closed.
        # Writing to "A.log" is resumed.
        pass
    # The log file "A.log" is closed.

This works fine for a single threaded process.
However with multiple threads this fails.

Introducing Threading
^^^^^^^^^^^^^^^^^^^^^

Supposing that we have this code:

.. code-block:: python

    import threading

    from pymemtrace import cPyMemTrace

    def do_work(some_argument):
        with cPyMemTrace.ReferenceTracing() as profiler:
            profiler.write_message_to_log(f'Starting: {some_argument}')
            # Do some work...

    threads = [
        threading.Thread(target=do_work, args=('Thread-A',),),
        threading.Thread(target=do_work, args=('Thread-B',),),
    ]
    # Start each thread
    for t in threads:
        t.start()
    # Wait for all threads to finish
    for t in threads:
        t.join()

Thread A will create a log file, say "A.log" [#file_name_note]_.
The linked list of Reference Tracers will look like this:


.. code-block:: text

    Head Node
        |
    File "A.log" ---> NULL

Then thread B creates a log file, say "B.log"
The linked list of Reference Tracers now looks like this:

.. code-block:: text

    Head Node
        |
    File "B.log" ---> File "A.log" ---> NULL

Now both threads are writing events to "B.log".
Suppose thread A completes first it will pop off the head node
closing the file "B.log".
Then the linked list will look like this:

.. code-block:: text

    Head Node
        |
    File "A.log" ---> NULL

And, as thread B is still running, it is writing events to the file
meant for thread A.

So both log files are corrupt, "B.log" has events from thread A
and thread B and "A.log" contains events from thread A and
trailing events from thread B.

Compelling a Common Log File
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

One solution might be that all treads write to a common, named, log file
like this:

.. code-block:: python

    import threading

    from pymemtrace import cPyMemTrace

    def do_work(some_argument):
        with cPyMemTrace.ReferenceTracing(filepath='do_work.log') as profiler:
            profiler.write_message_to_log(f'Starting: {some_argument}')
            # Do some work...

    threads = [
        threading.Thread(target=do_work, args=('Thread-A',),),
        threading.Thread(target=do_work, args=('Thread-B',),),
    ]
    # Start each thread
    for t in threads:
        t.start()
    # Wait for all threads to finish
    for t in threads:
        t.join()

Now both threads will have a separate ``FILE *`` to the same output stream
but those ``FILE *`` handles can be in a different state.
In particular the write pointer (found by ``tell()``) can be different.
Both ``FILE *`` handles will have a write pointer less than or equal
to the file length so there is no chance of writing beyond that.
However each thread can overwrite the others output.

The Proposed Solution
---------------------------

Macros
^^^^^^^^^^^^^^^

Include threading:

.. code-block:: c

    #ifdef WITH_THREAD
    #include "pythread.h"
    #endif

Conditional compilation:

.. code-block:: c

    /* Allow setup.py to override this with extra_compile_args */
    #ifndef PYMEMTRACE_THREAD_SUPPORT_PROFILE_TRACE
    /* Default in this code. */
    #define PYMEMTRACE_THREAD_SUPPORT_PROFILE_TRACE 1

    /* And... */
    #ifndef PYMEMTRACE_THREAD_SUPPORT_REFERENCE_TRACE
    #define PYMEMTRACE_THREAD_SUPPORT_REFERENCE_TRACE 1

    /* Verbose output as the data structures change etc. */
    #ifndef PYMEMTRACE_THREAD_SUPPORT_DEBUG
    #define PYMEMTRACE_THREAD_SUPPORT_DEBUG 1


Locks
^^^^^

Prior to Python 3.13 we had this, assuming that the obj had a ``lock``:

.. code-block:: c

    typedef struct {
        PyObject_HEAD
    #ifdef WITH_THREAD
        PyThread_type_lock lock;
    #endif
    } SomeObject;

These were the macros used in acquiring and releasing the lock:

.. code-block:: c

    #define ACQUIRE_LOCK(obj) do {                      \
        if (!PyThread_acquire_lock((obj)->lock, 0)) {   \
            Py_BEGIN_ALLOW_THREADS                      \
            PyThread_acquire_lock((obj)->lock, 1);      \
            Py_END_ALLOW_THREADS                        \
        } } while (0)

    #define RELEASE_LOCK(obj) PyThread_release_lock((obj)->lock)


From Python 3.13 we have ``PyMutex``:
https://docs.python.org/3/c-api/synchronization.html#synchronization-primitives
That is used like this:

.. code-block:: c

    typedef struct {
        PyObject_HEAD
    #ifdef WITH_THREAD
        PyMutex mutex;
    #endif
    } SomeObject;

.. code-block:: c

    PyMutex_Lock(obj->mutex);
    /* Do stuff. */
    PyMutex_Unlock(obj->mutex);

Perhaps choose between the field name "lock" or "mutex".

So a Python version dependent code might look like this:

.. code-block:: c

    #if PY_MAJOR_VERSION != 3
        #error "Python major version must be 3"
    #endif

    #ifdef WITH_THREAD
        #if PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION < 13

            #define DECLARE_LOCK_IN_PYOBJECT PyThread_type_lock _mutex_lock;

            #define ACQUIRE_LOCK(obj) do {                              \
                if (!PyThread_acquire_lock((obj)->_mutex_lock, 0)) {    \
                    Py_BEGIN_ALLOW_THREADS                              \
                    PyThread_acquire_lock((obj)->_mutex_lock, 1);       \
                    Py_END_ALLOW_THREADS                                \
                } } while (0)

            #define RELEASE_LOCK(obj) PyThread_release_lock((obj)->_mutex_lock)
        #else
            #define DECLARE_LOCK_IN_PYOBJECT PyMutex _mutex_lock
            #define ACQUIRE_LOCK(obj) PyMutex_Lock(obj->_mutex_lock)
            #define RELEASE_LOCK(obj) PyMutex_Unlock((obj)->_mutex_lock)
        #endif
    #else
        /* Non-threaded Python. */
        #define DECLARE_LOCK_IN_PYOBJECT
        #define ACQUIRE_LOCK(obj)
        #define RELEASE_LOCK(obj)
    #endif

Or do we use the Critical Section API?:
https://docs.python.org/3/c-api/synchronization.html#python-critical-section-api

Thread ID
^^^^^^^^^^

- Use ``unsigned long thread_id = PyThread_get_thread_native_id();`` DONE.
- Add the thread ID to the log file name. DONE.

Linked List(s)
^^^^^^^^^^^^^^^

- Every node on the linked list has the thread ID from which it was pushed.
  This has a widespread effect on node creation, getting an appropriate node
  and node deletion.
- Each node on the linked list has a ``prev`` pointer to the previous node.
  This is a doubly linked list and it means that an individual node
  can be removed, not just the head node.
  This has a modest effect on node creation and node deletion.
- Any thread pushinging to the linked list will need to block
  (for example on ``__enter__``) then release the lock.
- Any thread pop'ing from the linked list will need to block
  (for example on ``__exit__``), then only remove
  the first node that matches that thread's ID respecting later nodes with
  the same thread ID.
  Then release the lock.

Callback Functions
^^^^^^^^^^^^^^^^^^^^^

- The callback function must block before accessing the linked list head.
  Other threads might push or pop on the list.
- The appropriate linked list is passed to the Profile/Trace/Reference Trace
  callback function.
  For Profile/Trace this is statically allocated.
  For Reference Trace this can be passed as the ``*data`` parameter
  or the statically allocated list.
- The callback function identifies the thread ID.
- The callback function walks the linked list to find the first node
  with the appropriate thread ID
  (there maybe later nodes with the same thread ID which represent
  earlier context managers or decorators).
  The callback function then writes to that log file and releases the lock.

Other
^^^^^

- Add lots of asserts to ensure data integrity.

Tests
^^^^^

- Create tests for each of the tracing techniques with Python threading.

Performance Tests
^^^^^^^^^^^^^^^^^^^

- Single threaded application compiled with and without thread support.
  For example the TotalDepth test.
- Multi threaded artificial test with various number of threads.

.. rubric:: Footnotes

.. [#file_name_note] Log file names are simplified here for clarity.
