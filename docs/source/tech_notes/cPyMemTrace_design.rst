
.. _tech_notes-cpymemtrace_design:

Technical Note on the ``cPyMemTrace`` Design
=============================================

:py:mod:`pymemtrace.cPyMemTrace` contains Python profilers and tracers written in 'C' that logs the
runtime information including the `Resident Set Size <https://en.wikipedia.org/wiki/Resident_set_size>`_
for every Python and C call and return or object allocation and de-allocation as required.

.. _tech_notes-cpymemtrace_design_stacking_context_managers:

Stacking Context Managers
-------------------------------

The Python runtime can only accept a single Profiler, a single Tracer and a single Reference Tracer
at any time.
So a naive implementation that wrote to a log file would result in this:

.. code-block:: python

    from pymemtrace import cPyMemTrace

    with cPyMemTrace.Profile():
        # Now writing to, say, "A.log"
        with cPyMemTrace.Profile():
            # Writing to "A.log" is closed.
            # Now writing to, say, "B.log"
            pass
        # The log file "B.log" is closed.
        # The log file "A.log" is never re-opened.
        pass

To get round this restriction :py:mod:`pymemtrace.cPyMemTrace` allows the stacking of these objects
with context managers.
Each new context manager suspends the actions of the previous one.
When the new context manager goes out of scope the previous one (if any) is restored.
The log files are annotated to show the suspend/restore timestamps.

Thus :py:mod:`pymemtrace.cPyMemTrace` tracers :py:class:`pymemtrace.cPyMemTrace.Profile`,
:py:class:`pymemtrace.cPyMemTrace.Trace`
and :py:class:`pymemtrace.cPyMemTrace.ReferenceTracing`
context managers can be stacked.
In that case a new log file is started and the previous one is temporarily suspended.
:py:mod:`pymemtrace.cPyMemTrace` only writes to one log file at a time for each tracer.
The log file will have the stack depth in its name, starting from 0.

Internally each Profile/Trace/Reference Tracer has its own, static, linked list of profiling objects.
For example the Profiler has
``static tcpyTraceFileWrapperLinkedList *static_profile_ll``
in ``pymemtrace/src/cpy/cPyMemTrace.c``.

When a new profiler is added to the stack on ``__enter__`` the previous one is suspended.
When the new one does an ``__exit__`` the current one is popped off the
linked list and the previous one (if any) is resumed.
The log files are annotated to show this.
The depth of the stack is included in the file name, see :ref:`tech_notes-cpymemtrace_log_file_name`.

For example:

.. code-block:: python

    from pymemtrace import cPyMemTrace

    with cPyMemTrace.Profile():
        # Now writing to, say, "20241107_195847_11_62264_P_0_PY3.13.0b3.log"
        # Note the "_0_" in the file name.
        with cPyMemTrace.Profile():
            # Writing to "20241107_195847_12_62264_P_0_PY3.13.0b3.log" is suspended.
            # Now writing to, say, "20241107_195847_12_62264_P_1_PY3.13.0b3.log"
            # Note the "_1_" in the file name.
            pass
        # The log file "20241107_195847_12_62264_P_1_PY3.13.0b3.log" is closed.
        # Writing to "20241107_195847_11_62264_P_0_PY3.13.0b3.log" is resumed.
        pass
    # The log file "20241107_195847_11_62264_P_0_PY3.13.0b3.log" is closed.

Or pictorially, when the outer reference tracer is active the linked list looks like this:

.. code-block:: text

    List Node       File Name                                       File State
    ---------       ---------                                       ----------

    Head Node ----> "20241107_195847_11_62264_P_0_PY3.13.0b3.log"   Writing
        |
    NULL Node

And when the inner reference tracer is active the linked list looks like this:

.. code-block:: text

    List Node       File Name                                       File State
    ---------       ---------                                       ----------

    Head Node ----> "20241107_195847_12_62264_P_1_PY3.13.0b3.log"   Writing
        |
    Next Node ----> "20241107_195847_11_62264_P_0_PY3.13.0b3.log"   Suspended
        |
    NULL Node

The outer log file ``20241107_195847_11_62264_P_0_PY3.13.0b3.log`` will have this annotation to show
the context switch and back:

.. code-block:: text

    MSG:  3  +1  9.869994  # Detaching this profile file wrapper. New file: pymemtrace/20241107_195847_12_62264_P_1_PY3.13.0b3.log
    MSG:  3  +1  9.870580  # Re-attaching this profile file wrapper.

The same effect is obtained when using decorators which allows a decorated function to call another decorated function.
See :ref:`examples-cpymemtrace-decorators-stacking`.

The :py:mod:`pymemtrace.cPyMemTrace` module has these functions to give you the stack depth for that tracer:

- :py:meth:`pymemtrace.cPyMemTrace.profile_wrapper_depth` for the
  :py:class:`pymemtrace.cPyMemTrace.Profile` stack.
- :py:meth:`pymemtrace.cPyMemTrace.trace_wrapper_depth` for the
  :py:class:`pymemtrace.cPyMemTrace.Trace` stack.
- :py:meth:`pymemtrace.cPyMemTrace.reference_tracing_wrapper_depth` for the
  :py:class:`pymemtrace.cPyMemTrace.ReferenceTracing` stack.


.. warning::

    The :py:class:`pymemtrace.cPyMemTrace.ReferenceTracing` has methods
    :py:meth:`~pymemtrace.cPyMemTrace.ReferenceTracing.suspend()` that temporarily stops tracing
    and :py:meth:`~pymemtrace.cPyMemTrace.ReferenceTracing.resume()` resumes tracing.
    If these are called out-of-order (say on the outer tracer when the inner tracer is active)
    then a RuntimeError will be thrown.

Stacking Decorators
-------------------

Decorators, since they invoke the respective context manager, work in the same way, suspending
then restoring a log file.
See :ref:`examples-cpymemtrace_decorators` for some examples.

Counting Allocations by Type
----------------------------

The :py:class:`pymemtrace.cPyMemTrace.ReferenceTracing` contains a hash table that holds
the number of live objects by type.
The hash table ke is a C string of the type and the value a long of the count of objects.
Every time an object is allocated the value is increased by one.
Every time an object is de-allocated the value is decreased by one.

The table can be retrieved as a Python dictionary by the method
:py:meth:`~pymemtrace.cPyMemTrace.ReferenceTracing.live_object_counts()`.
If you are using decorators then the module level method
:py:meth:`~pymemtrace.cPyMemTrace.reference_tracing_live_object_counts()`
does the same thing.
