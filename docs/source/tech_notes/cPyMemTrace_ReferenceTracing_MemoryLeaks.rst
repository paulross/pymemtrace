
.. _tech_notes-cpymemtrace_reference_tracing_memory_leaks:

Using Reference Tracing to Detect Memory Leaks
===================================================

Reference Tracing logs every allocation and de-allocation and this can be very useful in detecting
memory leaks.
In this example we will deliberately create a memory leak and see how this is detected in the
log file.

Creating a Memory Leak
----------------------

The :py:mod:`pymemtrace.cMemLeak` has a number of classes that can create a memory demand.
The reference count of these objects can be manipulated directly and so we can cause a leak.
For example using :py:class:`pymemtrace.cMemLeak.CMalloc`:

.. code-block:: python

    from pymemtrace import cMemLeak

    obj = cMemLeak.CMalloc(1024)
    obj.inc_refcnt(1)

By incrementing the reference count we have prohibited the Python runtime from ever de-allocating the object.
A memory leak.

Lets create a function that creates a number of these objects and, optionally, leaks them.

.. code-block:: python

    from pymemtrace import cMemLeak

    def create_tmp_list_of_memory_objects(cause_leak: bool):
        l = []
        for i in range(4):
            obj = cMemLeak.CMalloc(1024)
            if cause_leak:
                obj.inc_refcnt(1)
            l.append(obj)
        while len(l):
            l.pop()


Using Reference Tracing
-----------------------

Firstly with no leak:

.. code-block:: python

    from pymemtrace import cPyMemTrace

    with cPyMemTrace.ReferenceTracing(
            include_tp_names=['cMemLeak.CMalloc',],
    ) as profiler:
        create_tmp_list_of_memory_objects(False)

This creates a log file that we can analyse with :py:mod:`pymemtrace.util.ref_trace_analyse`:

.. raw:: latex

    [Continued on the next page]

    \pagebreak

.. raw:: latex

    \begin{landscape}

.. code-block:: text

    File path: 20260419_120519_0_71199_O_0_PY3.13.2.log
    2026-04-19 13:05:37,142 - ref_trace_analyse.py#338 - INFO     - Lines: 12 NEW: 4 DEL: 4 NEW - DEL: 0 MSG: 0
    Initial Message:
    test_reference_tracing_deliberate_leak_to_cwd(): Class: CMallocObject Leak: False
    Untracked Objects [0]:
    Type                                        Count
    Live Objects [0]:
    Previous Objects [4]:
        0x6000034c1f90 cMemLeak.CMallocObject                   NEW: test_cpymemtrace.py#818 DEL: test_cpymemtrace.py#823
        0x6000034c2550 cMemLeak.CMallocObject                   NEW: test_cpymemtrace.py#818 DEL: test_cpymemtrace.py#823
        0x6000034c25d0 cMemLeak.CMallocObject                   NEW: test_cpymemtrace.py#818 DEL: test_cpymemtrace.py#823
        0x6000034c2690 cMemLeak.CMallocObject                   NEW: test_cpymemtrace.py#818 DEL: test_cpymemtrace.py#885
    Type count [1]:
    Type                                          New      Del  New - Del
    cMemLeak.CMallocObject                          4        4          0
    Process time: 0.001 (s)

.. raw:: latex

    \end{landscape}

This shows that the four objects were allocated and then de-allocated correctly.

Now with a leak:

.. code-block:: python

    from pymemtrace import cPyMemTrace

    with cPyMemTrace.ReferenceTracing(
            include_tp_names=['cMemLeak.CMalloc',],
    ) as profiler:
        create_tmp_list_of_memory_objects(True)

And this log file analysed with :py:mod:`pymemtrace.util.ref_trace_analyse` gives:

.. raw:: latex

    [Continued on the next page]

    \pagebreak

.. raw:: latex

    \begin{landscape}

.. code-block:: text

    python pymemtrace/util/ref_trace_analyse.py 20260419_120519_1_71199_O_0_PY3.13.2.log
    File path: 20260419_120519_1_71199_O_0_PY3.13.2.log
    2026-04-19 13:05:55,774 - ref_trace_analyse.py#338 - INFO     - Lines: 8 NEW: 4 DEL: 0 NEW - DEL: 4 MSG: 0
    Initial Message:
    test_reference_tracing_deliberate_leak_to_cwd(): Class: CMallocObject Leak: True
    Untracked Objects [0]:
    Type                                        Count
    Live Objects [4]:
        0x6000034c4090    1 cMemLeak.CMallocObject                   create_tmp_list_of_memory_objects test_cpymemtrace.py#818
        0x6000034c4110    1 cMemLeak.CMallocObject                   create_tmp_list_of_memory_objects test_cpymemtrace.py#818
        0x6000034c4290    1 cMemLeak.CMallocObject                   create_tmp_list_of_memory_objects test_cpymemtrace.py#818
        0x6000034c4390    1 cMemLeak.CMallocObject                   create_tmp_list_of_memory_objects test_cpymemtrace.py#818
    Previous Objects [0]:
    Type count [1]:
    Type                                          New      Del  New - Del
    cMemLeak.CMallocObject                          4        0          4
    Process time: 0.001 (s)

.. raw:: latex

    \end{landscape}


And that shows that the four objects are still 'alive'.

Whilst Reference Tracing can not pinpoint where a missing de-allocation should be it can certainly narrow down
what types are not being de-allocated correctly.
