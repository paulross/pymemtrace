
.. _tech_notes-cpymemtrace_reference_tracing:

Technical Note on ``cPyMemTrace`` Reference Tracing
===================================================

From Python 3.13 onwards Python supports
`Reference Tracing <https://docs.python.org/3/c-api/profiling.html#reference-tracing>`_.
This enables us to track every Python allocation and de-allocation.
The class that does this is :py:class:`cPyMemTrace.ReferenceTracing`.

.. warning::

    The Reference Tracing API is in flux.
    It was introduced in Python 3.13 and is fairly immature.
    For example the ``PyRefTracer_TRACKER_REMOVED`` event was supposed to be implemented in Python 3.14
    and it appears in the documentation for that version.
    However ``PyRefTracer_TRACKER_REMOVED`` does not occur in the Python 3.14 source code.
    Perhaps this is a case of the documentation out running the code.


How Reference Tracing Works
---------------------------

Reference tracing is initiated by calling the CPython API
`PyRefTracer_SetTracer <https://docs.python.org/3/c-api/profiling.html#c.PyRefTracer_SetTracer>`_
which has this prototype:

.. code-block:: c

    int PyRefTracer_SetTracer(PyRefTracer tracer, void *data)

The arguments are:

- `PyRefTracer <https://docs.python.org/3/c-api/profiling.html#c.PyRefTracer>`_ which is a callback function,
  the signature is described below.
- A ``void *`` opaque pointer to a structure that will be passed to the callback function as an argument.
  This allows you to hold state between tracing events.
  This can be ``NULL``.

The callback function signature is:

.. code-block:: c

    int (*PyRefTracer)(PyObject*, int event, void *data)

The first parameter is a Python object that has been just created (when event is set to
`PyRefTracer_CREATE <https://docs.python.org/3/c-api/profiling.html#c.PyRefTracer_CREATE>`_)
or about to be destroyed (when event is set to
`PyRefTracer_DESTROY <https://docs.python.org/3/c-api/profiling.html#c.PyRefTracer_DESTROY>`_).

The data argument is the opaque pointer that was provided when
`PyRefTracer_SetTracer <https://docs.python.org/3/c-api/profiling.html#c.PyRefTracer_SetTracer>`_
was called.
This allows arbitrary accumulation of data.

Reference Tracing is fairy new and, as it intercepts every Python object allocation and de-allocation, is very invasive.
This provides a number of failure modes.

A Simple Reference Tracer
-------------------------

Here is an example of a simple reference tracer.
It is based on the CPython 3.13/3.14 code in ``Modules/_testcapimodule.c`` which is, as far as I can see,
the sole test code for Reference Tracing.

First declare a data block that accumulates allocation and de-allocation counts:

.. code-block:: c

    struct simpletracer_data {
        int create_count;
        int destroy_count;
    };

Now write the callback function that will be invoked with each allocation and de-allocation:

.. code-block:: c

    static int simpletracer_callback(PyObject *Py_UNUSED(obj),
                                     PyRefTracerEvent event,
                                     void* data) {
        struct simpletracer_data* the_data = (struct simpletracer_data *)data;
        if (event == PyRefTracer_CREATE) {
            the_data->create_count++;
        } else if (event == PyRefTracer_DESTROY) {
            the_data->destroy_count++;
        } else {
            /* NOTE: PyRefTracer_TRACKER_REMOVED is ignored here as that API is not
             * yet stable.
             * It was claimed in the Python documentation to be implemented in
             * Python 3.14 but was actually only implemented in Python 3.15.
             */
        }
        return 0;
    }

Now some test code that executes this within a CPython runtime.
This is in ``test_reftracer()`` in ``pymemtrace/src/cpy/cPyMemTrace.c``:

.. code-block:: c

    static int
    test_reftracer(void) {
        printf("Starting %s() at %s#%d\n", __FUNCTION__, __FILE_NAME__, __LINE__);
        // Save the current tracer and data to restore it later
        void* current_data;
        PyRefTracer current_tracer = PyRefTracer_GetTracer(&current_data);

        struct simpletracer_data tracer_data = {0};
        void* the_data = &tracer_data;
        // Install a simple tracer function
        if (PyRefTracer_SetTracer(simpletracer_callback, the_data) != 0) {
            goto failed;
        }

        // Check that the tracer was correctly installed
        void* data;
        if (PyRefTracer_GetTracer(&data) != simpletracer_callback || data != the_data) {
            PyErr_SetString(
                PyExc_AssertionError, "The reftracer not correctly installed"
            );
            (void)PyRefTracer_SetTracer(NULL, NULL);
            goto failed;
        }

        // Create a bunch of objects
        PyObject* obj = PyList_New(0);
        if (obj == NULL) {
            goto failed;
        }
        PyObject* obj2 = PyDict_New();
        if (obj2 == NULL) {
            Py_DECREF(obj);
            goto failed;
        }

        // Kill all objects
        Py_DECREF(obj);
        Py_DECREF(obj2);

        // Remove the tracer
        (void)PyRefTracer_SetTracer(NULL, NULL);

        // Check that the tracer was removed
        if (PyRefTracer_GetTracer(&data) != NULL || data != NULL) {
            PyErr_SetString(
                PyExc_ValueError, "The reftracer was not correctly removed"
            );
            goto failed;
        }

        if (tracer_data.create_count != 2) {
            PyErr_SetString(
                PyExc_ValueError, "The object creation was not correctly traced"
            );
            goto failed;
        }

        if (tracer_data.destroy_count != 2) {
            PyErr_SetString(
                PyExc_ValueError, "The object destruction was not correctly traced"
            );
            goto failed;
        }
        PyRefTracer_SetTracer(current_tracer, current_data);
        printf("DONE %s() at %s#%d\n", __FUNCTION__, __FILE_NAME__, __LINE__);
        return 0;
    failed:
        PyRefTracer_SetTracer(current_tracer, current_data);
        printf("FAILED %s() at %s#%d\n", __FUNCTION__, __FILE_NAME__, __LINE__);
        return -1;
    }

A More Useful Reference Tracer
------------------------------

Just counting allocations and de-allocations is not very useful.
:py:class:`pymemtrace.cPyMemTrace.ReferenceTracing` logs each allocation and de-allocation
with the type and location of the action.

This has a number of pitfalls.

Stack Overflow
--------------

If the Reference Tracing callback function interacts with the CPython runtime then that is free to create
or destroy arbitrary objects.
This leads to recursive behaviour which can lead to a stack overflow.

The solution is that the callback function should immediately suspend Reference Tracing before interacting
with the CPython API.
For example:

.. code-block:: c

    static int
    reference_trace_callback(PyObject *obj, PyRefTracerEvent event, void *data) {
        assert(obj);
        assert(data);

        void *data_old = NULL;
        PyRefTracer tracer_old = PyRefTracer_GetTracer(&data_old);
        /* Sanity check. */
        assert(data_old);
        assert(tracer_old);
        assert(tracer_old == &reference_trace_callback);
        if (PyRefTracer_SetTracer(NULL, NULL)) {
            PyErr_SetString(
                PyExc_RuntimeError, "PyRefTracer_SetTracer(NULL, NULL) failed."
            );
            return err_code;
        }

        /* Now we can interact with CPython ... */

        /* Restore the Reference Tracer. */
        if (PyRefTracer_SetTracer(tracer_old, data_old)) {
            PyErr_SetString(
                PyExc_RuntimeError,
                "PyRefTracer_SetTracer(tracer_old, data_old) failed."
            );
            return err_code;
        }
        return 0;
    }

Reference Count Zero
--------------------

