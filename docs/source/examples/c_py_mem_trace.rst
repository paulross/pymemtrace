.. _examples-cpymemtrace:

``pymemtrace.cPyMemTrace`` Examples
*************************************

Introduction
===============================================

:py:mod:`pymemtrace.cPyMemTrace` contains several Python profilers written in C using CPython's C API.

.. list-table:: **pymemtrace.cPyMemTrace Profiling Classes**
   :widths: 50 50
   :header-rows: 1

   * - Class
     - Description
   * - :py:class:`pymemtrace.cPyMemTrace.Profile`
     - A *Profiler* that is suitable for logging Python and C code.
       This ignores Python line, opcode and exception events.
   * - :py:class:`pymemtrace.cPyMemTrace.Trace`
     - A *Tracer* that is suitable for logging pure Python code.
       It ignores C call, and return events.
   * - :py:class:`pymemtrace.cPyMemTrace.ReferenceTracing`
     - A *Reference Tracer* tracks every Python object allocation and de-allocation.
       This is available in Python 3.13+.

.. note::

    A useful debugging technique is to, temporarily, decorate functions of interest with these classes.

    These techniques are described here: :ref:`examples-cpymemtrace_decorators`.

Profilers and Tracers
===============================================

For each class of *profiler* the Python runtime only supports one instance at any point of time.
:py:mod:`pymemtrace.cPyMemTrace` handles this by using three linked lists of *profilers* that are pushed
or pop'd according to the users code.

Each of these *profilers* writes their data to a log file with a name of the form:

.. code-block:: text

    20241107_195847_12_62264_P_0_PY3.13.0b3.log

See :ref:`tech_notes-cpymemtrace_log_file_name` for the log file name and, for the log file format,
:ref:`tech_notes-cpymemtrace_profile_trace_log_file_format`
or :ref:`tech_notes-cpymemtrace_reference_tracing_log_file_format`.

Profile/Trace Events
------------------------

The events that the :py:class:`pymemtrace.cPyMemTrace.Profile` and
:py:class:`pymemtrace.cPyMemTrace.Trace` respond to are:

.. list-table:: **Python Profile/Trace Events**
   :widths: 40 60 15 15 15
   :header-rows: 1

   * - Event
     - Description
     - Profile?
     - Trace?
     - Log
   * - `PyTrace_CALL <https://docs.python.org/3/c-api/profiling.html#c.PyTrace_CALL>`_
     - Call to a Python function.
     - Yes
     - Yes
     - ``CALL``
   * - `PyTrace_EXCEPTION <https://docs.python.org/3/c-api/profiling.html#c.PyTrace_EXCEPTION>`_
     - When raising a Python exception.
     - No
     - Yes
     - ``EXCEPT``
   * - `PyTrace_LINE <https://docs.python.org/3/c-api/profiling.html#c.PyTrace_LINE>`_
     - When processing a Python line.
     - No
     - Yes
     - ``LINE``
   * - `PyTrace_RETURN <https://docs.python.org/3/c-api/profiling.html#c.PyTrace_RETURN>`_
     - When the code is about to return from a Python function.
     - Yes
     - Yes
     - ``RETURN``
   * - `PyTrace_C_CALL <https://docs.python.org/3/c-api/profiling.html#c.PyTrace_C_CALL>`_
     - Call to a C function.
     - Yes
     - No
     - ``C_CALL``
   * - `PyTrace_C_EXCEPTION <https://docs.python.org/3/c-api/profiling.html#c.PyTrace_C_EXCEPTION>`_
     - When raising a Python exception from C code.
     - Yes
     - No
     - ``C_EXCEPT``
   * - `PyTrace_C_RETURN <https://docs.python.org/3/c-api/profiling.html#c.PyTrace_C_RETURN>`_
     - When the code is about to return from a C function.
     - Yes
     - No
     - ``C_RETURN``
   * - `PyTrace_OPCODE <https://docs.python.org/3/c-api/profiling.html#c.PyTrace_OPCODE>`_
     - When a new opcode is about to be executed.
     - No
     - Yes
     - ``OPCODE``

:py:class:`pymemtrace.cPyMemTrace.ReferenceTracing` responds to every object allocation and de-allocation events.

Logging Changes in RSS
--------------------------------

Here is a simple example using :py:class:`pymemtrace.cPyMemTrace.Profile`:

.. code-block:: python

    from pymemtrace import cPyMemTrace

    def new_str(l: int) -> str:
        return ' ' * l

    with cPyMemTrace.Profile():
        l = []
        for i in range(8):
            l.append(new_str(1024**2))
        while len(l):
            l.pop()

This produces a log file in the current working directory such as:

.. code-block:: text

          Event dEvent  Clock        What     File    #line Function     RSS         dRSS
    NEXT: 0     +0      0.066718     CALL     test.py #   9 new_str  9101312      9101312
    NEXT: 1     +1      0.067265     RETURN   test.py #  10 new_str 10153984      1052672
    PREV: 4     +3      0.067285     CALL     test.py #   9 new_str 10153984            0
    NEXT: 5     +4      0.067777     RETURN   test.py #  10 new_str 11206656      1052672
    PREV: 8     +3      0.067787     CALL     test.py #   9 new_str 11206656            0
    NEXT: 9     +4      0.068356     RETURN   test.py #  10 new_str 12259328      1052672
    PREV: 12    +3      0.068367     CALL     test.py #   9 new_str 12259328            0
    NEXT: 13    +4      0.068944     RETURN   test.py #  10 new_str 13312000      1052672
    PREV: 16    +3      0.068954     CALL     test.py #   9 new_str 13312000            0
    NEXT: 17    +4      0.069518     RETURN   test.py #  10 new_str 14364672      1052672
    PREV: 20    +3      0.069534     CALL     test.py #   9 new_str 14364672            0
    NEXT: 21    +4      0.070101     RETURN   test.py #  10 new_str 15417344      1052672
    PREV: 24    +3      0.070120     CALL     test.py #   9 new_str 15417344            0
    NEXT: 25    +4      0.070663     RETURN   test.py #  10 new_str 16470016      1052672
    PREV: 28    +3      0.070677     CALL     test.py #   9 new_str 16470016            0
    NEXT: 29    +4      0.071211     RETURN   test.py #  10 new_str 17522688      1052672

By default not all events are recorded just any that increase the RSS by one page along with the immediately preceding event.

Logging Every Event
--------------------------------

If all events are needed then change the constructor argument to 0:

.. code-block:: python

    with cPyMemTrace.Profile(0):
        # As before

And the log file looks like this:

.. code-block:: text

          Event dEvent  Clock        What     File    #line Function     RSS         dRSS
    NEXT: 0     +0      0.079408     CALL     test.py #   9 new_str  9105408      9105408
    NEXT: 1     +1      0.079987     RETURN   test.py #  10 new_str 10158080      1052672
    NEXT: 2     +1      0.079994     C_CALL   test.py #  64 append  10158080            0
    NEXT: 3     +1      0.079998     C_RETURN test.py #  64 append  10158080            0
    NEXT: 4     +1      0.080003     CALL     test.py #   9 new_str 10158080            0
    NEXT: 5     +1      0.080682     RETURN   test.py #  10 new_str 11210752      1052672
    NEXT: 6     +1      0.080693     C_CALL   test.py #  64 append  11210752            0
    NEXT: 7     +1      0.080698     C_RETURN test.py #  64 append  11210752            0
    NEXT: 8     +1      0.080704     CALL     test.py #   9 new_str 11210752            0
    NEXT: 9     +1      0.081414     RETURN   test.py #  10 new_str 12263424      1052672
    NEXT: 10    +1      0.081424     C_CALL   test.py #  64 append  12263424            0
    NEXT: 11    +1      0.081429     C_RETURN test.py #  64 append  12263424            0
    NEXT: 12    +1      0.081434     CALL     test.py #   9 new_str 12263424            0
    NEXT: 13    +1      0.081993     RETURN   test.py #  10 new_str 13316096      1052672
    NEXT: 14    +1      0.081998     C_CALL   test.py #  64 append  13316096            0
    ...
    NEXT: 59    +1      0.084531     C_RETURN test.py #  66 pop     17526784            0
    NEXT: 60    +1      0.084535     C_CALL   test.py #  65 len     17526784            0
    NEXT: 61    +1      0.084539     C_RETURN test.py #  65 len     17526784            0
    NEXT: 62    +1      0.084541     C_CALL   test.py #  66 pop     17526784            0
    NEXT: 63    +1      0.084561     C_RETURN test.py #  66 pop     17526784            0
    NEXT: 64    +1      0.084566     C_CALL   test.py #  65 len     17526784            0
    NEXT: 65    +1      0.084568     C_RETURN test.py #  65 len     17526784            0

There is some discussion about the performance of :py:mod:`pymemtrace.cPyMemTrace` here :ref:`tech_notes-cpymemtrace`

.. _examples-cpymemtrace-reference-tracing:

Reference Tracing
===============================================

From Python 3.13 onwards Python supports
`Reference Tracing <https://docs.python.org/3/c-api/profiling.html#reference-tracing>`_.
This enables us to track every Python allocation and de-allocation.

:py:mod:`pymemtrace` supports these Reference Tracing classes:

- :py:class:`cPyMemTrace.ReferenceTracingSimple` is a simple tracer that just counts allocations and de-allocations.
  This is described in detail in :ref:`tech_notes-cpymemtrace_reference_tracing_simple`.
- A more sophisticated tracer that reports where objects were created :py:class:`cPyMemTrace.ReferenceTracing`.
  This is very useful for tracking down where objects were allocated but never de-allocated.

Reference tracing works by registering a callback function that is invoked for every Python object allocation
and de-allocation.

.. warning::

    Reference Tracing is highly invasive and can lead to some undesirable side effects.
    The Reference Tracing API is quite new.
    Some of the documentation for it is wrong.
    This is described in more detail in :ref:`tech_notes-cpymemtrace_reference_tracing`.

.. note::

    The Reference Tracing callback function ignores PyObject's of type "frame" as this can play havoc with the
    Python runtime.
    See :ref:`tech_notes-cpymemtrace_reference_tracing_pytest` for an example that revealed this problem.

Example of Reference Tracing
---------------------------------------

Here we create an example class that just allocates memory:

.. code-block:: python

    class BytesWrapper:
        def __init__(self, length: int):
            self.bytes = b' ' * length

Then we invoke this multiple times under the watchful eye of a :py:class:`pymemtrace.cPyMemTrace.ReferenceTracing`
context manger:

.. code-block:: python

    from pymemtrace import cPyMemTrace

    def make_bytes_wrappers() -> str:
        with cPyMemTrace.ReferenceTracing() as profiler:
            l = []
            for i in range(4):
                length = random.randint(512, 1024) + 1024 ** 2
                l.append(BytesWrapper(length))
                time.sleep(0.25)
            while len(l):
                p = l.pop()
                del p
                time.sleep(0.25)
            return profiler.log_file_path()

The log file will look like this (abridged).

..

    .. raw:: latex

        [Continued on the next page]

        \pagebreak

.. raw:: latex

    \begin{landscape}

.. code-block:: text

    SOF
    HDR:        Clock          Address RefCnt Type            File                           Line Function                  RSS      dRSS
    NEW:     0.816183   0x6000025fde70      1 list            test_cpymemtrace.py             293 make_bytes_wrappers  38207488         0
    NEW:     0.816203   0x6000025ec6a0      1 range           test_cpymemtrace.py             294 make_bytes_wrappers  38207488         0
    NEW:     0.816218   0x60000169c210      1 range_iterator  test_cpymemtrace.py             294 make_bytes_wrappers  38207488         0
    DEL:     0.816229   0x6000025ec6a0      0 range           test_cpymemtrace.py             294 make_bytes_wrappers  38207488         0
    8<---- Snip ---->8
    NEW:     0.816531   0x7fa81fbf2a00      1 BytesWrapper    test_cpymemtrace.py             296 make_bytes_wrappers  38207488         0
    NEW:     0.816590   0x7fa823903010      1 bytes           test_cpymemtrace.py             288 __init__             38207488         0
    DEL:     0.816645   0x6000025e34a0      0 tuple           test_cpymemtrace.py             296 make_bytes_wrappers  38207488         0
    8<---- Snip ---->8
    NEW:     0.817109   0x7fa81e7aa280      1 BytesWrapper    test_cpymemtrace.py             296 make_bytes_wrappers  38207488         0
    NEW:     0.817162   0x7fa823600010      1 bytes           test_cpymemtrace.py             288 __init__             38207488         0
    NEW:     0.817250   0x60000169c110      1 int             Python-3.13.2/Lib/random.py     340 randint              38207488         0
    8<---- Snip ---->8
    DEL:     0.817495   0x60000168b350      0 int             test_cpymemtrace.py             295 make_bytes_wrappers  38207488         0
    NEW:     0.817513   0x7fa82347c940      1 BytesWrapper    test_cpymemtrace.py             296 make_bytes_wrappers  38207488         0
    NEW:     0.817602   0x7fa823701010      1 bytes           test_cpymemtrace.py             288 __init__             38207488         0
    NEW:     0.817762   0x600001694d90      1 int             Python-3.13.2/Lib/random.py     340 randint              38207488         0
    NEW:     0.817885   0x600001694c90      1 int             Python-3.13.2/Lib/random.py     317 randrange            38207488         0
    8<---- Snip ---->8
    DEL:     0.818299   0x60000169c510      0 int             test_cpymemtrace.py             295 make_bytes_wrappers  38207488         0
    NEW:     0.818333   0x7fa81fafbe60      1 BytesWrapper    test_cpymemtrace.py             296 make_bytes_wrappers  38207488         0
    NEW:     0.818525   0x7fa823802010      1 bytes           test_cpymemtrace.py             288 __init__             38207488         0
    DEL:     0.818776   0x60000169c210      0 range_iterator  test_cpymemtrace.py             294 make_bytes_wrappers  38207488         0
    DEL:     0.818860   0x7fa81fafbe60      0 BytesWrapper    test_cpymemtrace.py             300 make_bytes_wrappers  38207488         0
    DEL:     0.818875   0x7fa823802010      0 bytes           test_cpymemtrace.py             300 make_bytes_wrappers  38207488         0
    DEL:     0.819012   0x7fa82347c940      0 BytesWrapper    test_cpymemtrace.py             300 make_bytes_wrappers  38207488         0
    DEL:     0.819128   0x7fa823701010      0 bytes           test_cpymemtrace.py             300 make_bytes_wrappers  38207488         0
    DEL:     0.819370   0x7fa81e7aa280      0 BytesWrapper    test_cpymemtrace.py             300 make_bytes_wrappers  38207488         0
    DEL:     0.819447   0x7fa823600010      0 bytes           test_cpymemtrace.py             300 make_bytes_wrappers  38207488         0
    DEL:     0.819582   0x7fa81fbf2a00      0 BytesWrapper    test_cpymemtrace.py             300 make_bytes_wrappers  38207488         0
    DEL:     0.819648   0x7fa823903010      0 bytes           test_cpymemtrace.py             300 make_bytes_wrappers  38207488         0
    NEW:     0.820073   0x600003236b30      1 str             test_cpymemtrace.py             304 make_bytes_wrappers  38211584      4096
    NEW:     0.820357   0x6000067033e0      1 tuple           test_cpymemtrace.py             292 make_bytes_wrappers  38211584         0
    EOF

.. raw:: latex

    \end{landscape}

The file format is described here :ref:`tech_notes-cpymemtrace_reference_tracing_log_file_format`.


Analysing the Log With ``ref_trace_analyse.py``
---------------------------------------------------

This log file can be very large so to help understand it there is a script
:py:mod:`pymemtrace.util.ref_trace_analyse` that can analyse it.

This performs the following analysis:

- If an object is deleted but hasn't been created in the log file a warning is issued.
  These are not significant as they refer to objects created before the log file was started.
- An error will be reported if an object has been created at a particular address without being
  previously deleted at the same address.
  These are not significant as they (mostly?) refer to objects that are everlasting objects
  within the Python process.
- Any objects that were created within the log run but not de-allocated are listed
  along with the function, file, and line where it was created.
- Any objects that were created and deleted within the log run are listed.
- A count of objects created and deleted by object type.

For example the output will be something like:

..

    .. raw:: latex

        [Continued on the next page]

        \pagebreak

.. raw:: latex

    \begin{landscape}

First warnings:

.. code-block:: text

    2026-03-18 11:51:12,278 - ref_trace_analyse.py#107 - WARNING  - DEL: on untracked object of type "builtin_function_or_method" at 0x60000670f980 on line 3

Then live objects once the log has completed:

.. code-block:: text

    Live Objects [4]:
        0x600001694c90    1 int                                      make_bytes_wrappers              test_cpymemtrace.py#295
        0x6000025fde70    1 list                                     make_bytes_wrappers              test_cpymemtrace.py#293
        0x600003236b30    1 str                                      make_bytes_wrappers              test_cpymemtrace.py#304
        0x6000067033e0    1 tuple                                    make_bytes_wrappers              test_cpymemtrace.py#292

Then previous objects that were created and destroyed during the log lifetime:

.. code-block:: text

    Previous Objects [26]:
        0x60000168b0d0 int                                      NEW: random.py#340 DEL: random.py#340
        0x60000168b190 int                                      NEW: random.py#322 DEL: test_cpymemtrace.py#295
    8<---- Snip ---->8
        0x6000025ec6a0 range                                    NEW: test_cpymemtrace.py#294 DEL: test_cpymemtrace.py#294
        0x6000067035c0 builtin_function_or_method               NEW: random.py#248 DEL: random.py#322
    8<---- Snip ---->8
        0x7fa81e7aa280 BytesWrapper                             NEW: test_cpymemtrace.py#296 DEL: test_cpymemtrace.py#300
        0x7fa81fafbe60 BytesWrapper                             NEW: test_cpymemtrace.py#296 DEL: test_cpymemtrace.py#300
        0x7fa81fbf2a00 BytesWrapper                             NEW: test_cpymemtrace.py#296 DEL: test_cpymemtrace.py#300
        0x7fa82347c940 BytesWrapper                             NEW: test_cpymemtrace.py#296 DEL: test_cpymemtrace.py#300
        0x7fa823600010 bytes                                    NEW: test_cpymemtrace.py#288 DEL: test_cpymemtrace.py#300

.. raw:: latex

    [Continued on the next page]

    \pagebreak

Then a table of the count of creations and deletions by type:

.. code-block:: text

    Type count [10]:
    Type                                          New      Del  New - Del
    BytesWrapper                                    4        4          0
    builtin_function_or_method                      4        5         -1
    bytes                                           4        4          0
    int                                            19       18          1
    8<---- Snip ---->8
    list                                            1        0          1
    str                                             1        0          1
    tuple                                           2        1          1
    Process time: 0.004 (s)

.. raw:: latex

    \end{landscape}

Managing the Log File Output
------------------------------

`Reference Tracing <https://docs.python.org/3/c-api/profiling.html#reference-tracing>`_ is highly invasive.
Events are created for all object allocations and de-allocations and this means the log file can be enormous.
:py:class:`cPyMemTrace.ReferenceTracing` supports a nuber of constructor arguments to make the log file more useful,
and much smaller.

.. list-table:: **ReferenceTracing Default Filtering**
   :widths: 15 20 50
   :header-rows: 1

   * - Object Type
     - Action
     - Notes
   * - ``Frame`` or ``Code``
     - Always ignored.
     - During development it was discovered that handling these types often created a ``SIGSEGV`` or
       an assertion failure with debug versions of Python.
   * - Builtin Objects
     - By default these are ignored
     - If ``include_builtins=True`` is set then these will be reported.
       Typically this makes the running time and the log file size 2x to 4x bigger.
       The builtin types are those C types that have a ``Py*_Check()`` function.
       These include all numeric types, containers (tuple, list, dict, set, frozenset), strings, bytes and so on.
       See ``reference_trace_is_builtin()`` in ``pymemtrace/src/cpy/cPyMemTrace.c`` for the specific criteria [#]_.

For example this will log all the builtin actions:

.. code-block:: python

    @cpymemtrace_decs.reference_tracing(
        message="some_function() include_builtins=True",
        include_builtins=True,
    )
    def some_function():
        pass

Further filtering can be specified by the user providing a sequence (list, tuple, set etc.) of strings.
Then if the ``tp_name`` appears in the sequence the event will be either recorded in or excluded from the log:

.. list-table:: **ReferenceTracing User Filtering**
   :widths: 30 70
   :header-rows: 1

   * - Option
     - Notes
   * - ``exclude_tp_names=[...]``
     - Ignore these types if their ``tp_name`` appears in this sequence.
       ``reference_trace_type_include_matches()`` handles this logic.
   * - ``include_tp_names=[...]``
     - Only write these events to the log if their ``tp_name`` appears in this sequence.
       The ``exclude_tp_names=[...]`` option takes precedence.
       ``reference_trace_type_exclude_matches()`` handles this logic.

For example this will eliminate tuple and list iterators from the log:

.. code-block:: python

    @cpymemtrace_decs.reference_tracing(
        message="some_function() exclude tuple and list iterators",
        exclude_tp_names=['tuple_iterator', 'list_iterator',],
    )
    def some_function():
        pass

This example will *only* log the events of ``MySpecialType``:

.. code-block:: python

    @cpymemtrace_decs.reference_tracing(
        message="some_function() only MySpecialType",
        include_tp_names=['MySpecialType',],
    )
    def some_function():
        pass

See the code in ``reference_trace_include_this_object()`` in ``pymemtrace/src/cpy/cPyMemTrace.c``
for the implementation of all this logic.


Common Features
=====================

This describes the common features of these three tracing techniques.

Stacking Context Managers
-------------------------------

The Python runtime can only accept a single Profiler, a single Tracer and a single Reference Tracer.
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

Internally each Profile/Trace/Reference Tracer has its own linked list of profiling objects.
As a new one is added to the stack the previous one is suspended.
When the new one does an ``__exit__`` the previous one (if any) is resumed.
The log files are annotated to show this.

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

    MSG:  3  +1  9.869994  # Detaching this profile file wrapper. New file:
    MSG:  3  +1  9.869996  # pymemtrace/20241107_195847_12_62264_P_1_PY3.13.0b3.log
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

Writing Messages to a Log File
------------------------------

To make log files more useful the user can inject messages into the log file in two ways:

- On construction of the Trace/Profile/Reference Tracing object using the ``message=<message>`` argument.
  This message will be reproduced verbatim and will be followed by a newline.
- At any time during the running of Trace/Profile/Reference Tracing object with the
  ``write_message_to_log_file()`` API.
  This message will be preceded with a ``MESG:`` or ``MSG:`` string, then the message is reproduced verbatim and
  will be followed by a newline.

.. note::

    New lines *within* messages will be respected.
    This may affect your parsing of the log file.

This example illustrates both techniques.
Firstly the code (slightly edited), here we create a profiler with a start message then allocate, then delete, a
randomly sized string of between 100 Mb and 500 Mb.
Before the allocation and after deletion we write an appropriate message to the log file.

.. code-block:: python

    with cPyMemTrace.Profile(d_rss_trigger=-1, message="Start message") as profiler:
        for i in range(8):
            str_len = random.randint(100 * 1024**2, 500 * 1024**2)
            profiler.write_message_to_log(f'Before allocation of {str_len} bytes.')
            s = ' ' * str_len
            time.sleep(0.5)
            del s
            profiler.write_message_to_log(f'After de-allocation of {str_len} bytes.')
            time.sleep(0.5)
        time.sleep(0.5)

Here is a typical log file:

.. raw:: latex

    \begin{landscape}

.. code-block:: text

    Start message
    SOF
    HEDR: Event  dEvent  Clock        What     File                           Line Function                  RSS         dRSS
    FRST: 0      +0      3.153048     LINE     test_cpymemtrace.py             201 test_messaging       41754624     41754624
    MESG: 18     +17     3.153134     Before allocation of 179379131 bytes.
    PREV: 18     +17     3.153134    
    NEXT: 19     +18     3.232753     C_CALL   test_cpymemtrace.py             206 sleep                221143040    179380224
    PREV: 19     +18     3.232753     C_CALL   test_cpymemtrace.py             206 sleep                221143040    179380224
    NEXT: 21     +2      3.249982     C_CALL   test_cpymemtrace.py             208 write_message_to_log  41762816   -179380224
    MESG: 22     +1      3.250007     After de-allocation of 179379131 bytes.
    MESG: 42     +21     3.250190     Before allocation of 198138484 bytes.
    PREV: 42     +21     3.250190    
    NEXT: 43     +22     3.344885     C_CALL   test_cpymemtrace.py             206 sleep                239902720    198139904
    PREV: 43     +22     3.344885     C_CALL   test_cpymemtrace.py             206 sleep                239902720    198139904
    NEXT: 45     +2      3.362191     C_CALL   test_cpymemtrace.py             208 write_message_to_log  41762816   -198139904
    MESG: 46     +1      3.362201     After de-allocation of 198138484 bytes.
    MESG: 66     +21     3.362277     Before allocation of 392320729 bytes.
    PREV: 66     +21     3.362277    
    NEXT: 67     +22     3.541612     C_CALL   test_cpymemtrace.py             206 sleep                434085888    392323072
    PREV: 67     +22     3.541612     C_CALL   test_cpymemtrace.py             206 sleep                434085888    392323072
    NEXT: 69     +2      3.573907     C_CALL   test_cpymemtrace.py             208 write_message_to_log  41762816   -392323072
    MESG: 70     +1      3.573918     After de-allocation of 392320729 bytes.
    MESG: 90     +21     3.574011     Before allocation of 504746338 bytes.
    PREV: 90     +21     3.574011    
    NEXT: 91     +22     3.803951     C_CALL   test_cpymemtrace.py             206 sleep                546512896    504750080
    PREV: 91     +22     3.803951     C_CALL   test_cpymemtrace.py             206 sleep                546512896    504750080
    NEXT: 93     +2      3.845491     C_CALL   test_cpymemtrace.py             208 write_message_to_log  41762816   -504750080
    MESG: 94     +1      3.845500     After de-allocation of 504746338 bytes.
    MESG: 114    +21     3.845611     Before allocation of 312965383 bytes.
    PREV: 114    +21     3.845611
    NEXT: 115    +22     3.993233     C_CALL   test_cpymemtrace.py             206 sleep                354729984    312967168
    PREV: 115    +22     3.993233     C_CALL   test_cpymemtrace.py             206 sleep                354729984    312967168
    NEXT: 117    +2      4.018102     C_CALL   test_cpymemtrace.py             208 write_message_to_log  41762816   -312967168
    MESG: 118    +1      4.018114     After de-allocation of 312965383 bytes.
    MESG: 138    +21     4.018275     Before allocation of 438944001 bytes.
    PREV: 138    +21     4.018275
    NEXT: 139    +22     4.231798     C_CALL   test_cpymemtrace.py             206 sleep                480710656    438947840
    PREV: 139    +22     4.231798     C_CALL   test_cpymemtrace.py             206 sleep                480710656    438947840
    NEXT: 141    +2      4.275196     C_CALL   test_cpymemtrace.py             208 write_message_to_log  41762816   -438947840
    MESG: 142    +1      4.275208     After de-allocation of 438944001 bytes.
    MESG: 162    +21     4.275367     Before allocation of 279020117 bytes.
    PREV: 162    +21     4.275367
    NEXT: 163    +22     4.424839     C_CALL   test_cpymemtrace.py             206 sleep                320786432    279023616
    PREV: 163    +22     4.424839     C_CALL   test_cpymemtrace.py             206 sleep                320786432    279023616
    NEXT: 165    +2      4.446285     C_CALL   test_cpymemtrace.py             208 write_message_to_log  41762816   -279023616
    MESG: 166    +1      4.446297     After de-allocation of 279020117 bytes.
    MESG: 186    +21     4.446371     Before allocation of 442963008 bytes.
    PREV: 186    +21     4.446371
    NEXT: 187    +22     4.643456     C_CALL   test_cpymemtrace.py             206 sleep                484728832    442966016
    PREV: 187    +22     4.643456     C_CALL   test_cpymemtrace.py             206 sleep                484728832    442966016
    NEXT: 189    +2      4.678978     C_CALL   test_cpymemtrace.py             208 write_message_to_log  41762816   -442966016
    MESG: 190    +1      4.678990     After de-allocation of 442963008 bytes.
    LAST: 196    +7      4.679326     LINE     test_cpymemtrace.py             201 test_messaging        41762816            0
    EOF

.. raw:: latex

    \end{landscape}

Logging to a Temporary File
------------------------------

By default the log is written to a file in the current working directory.
To write to a specific file, and then read it follow this pattern:

.. code-block:: python

    import tempfile

    with tempfile.NamedTemporaryFile() as file:
        with cPyMemTrace.Trace(0, message='# Trace level0', filepath=file.name) as trace:
            trace.trace_file_wrapper.write_message_to_log('# Level 0 __enter__')
            temp_list = []
            for i in range(16):
                temp_list.append(b' ' * (1024 ** 2))
            trace.trace_file_wrapper.write_message_to_log(
                '# Level 0 after populating list.'
            )
            while len(temp_list):
                temp_list.pop()
            trace.trace_file_wrapper.write_message_to_log(
                '# Level 0 after deleting the list.'
            )
        file.flush()
        file_data = file.read()
        print()
        print(' filedata '.center(75, '-'))
        for line in file_data.split(b'\n'):
            print(line.decode('ascii'))
        print(' file_data DONE '.center(75, '-'))

See ``tests.test_cpymemtrace.test_trace_to_specific_log_file_nested()`` for a more complicated example.

.. _examples-cpymemtrace_decorators:

Decorators
------------

Often it is more convenient to use these as decorators of a particular function of interest.
The decorators take the constructor arguments and will write to the appropriate file.

For example:

.. code-block:: python

    from pymemtrace import cpymemtrace_decs

    @cpymemtrace_decs.reference_tracing(
        message='Testing some really important function',
    )
    def really_important_function():
        pass

.. _examples-cpymemtrace-decorators-mingling:

Mingling Decorators
^^^^^^^^^^^^^^^^^^^

Profile, Trace and Reference tracing decorators can be co-mingled.
For example:

.. code-block:: python

    from pymemtrace import cpymemtrace_decs

    @cpymemtrace_decs.trace(
        message='Trace the inner function',
    )
    def inner_function():
        pass

    @cpymemtrace_decs.reference_tracing(
        message='Reference trace the outer function that calls the inner function',
    )
    def outer_function():
        inner_function()

This will result in two specific log files:

- The outer one reference traces both the outer function and the inner function.
- The inner function is just traced alone.

See ``tests/test_cpymemtrace_decs.py()`` for some examples.

.. _examples-cpymemtrace-decorators-stacking:

Stacking Decorators
^^^^^^^^^^^^^^^^^^^

Decorators allow a decorated function to call another decorated function.
Decorated functions that call other such decorated functions will behave appropriately with each registering
the profiler and writing to its unique log file.
For example:

.. code-block:: python

    from pymemtrace import cpymemtrace_decs

    @cpymemtrace_decs.reference_tracing(
        message='Reference trace the inner function',
    )
    def inner_function():
        pass

    @cpymemtrace_decs.reference_tracing(
        message='Reference trace the outer function that calls the inner function',
    )
    def outer_function():
        inner_function()

This will result in two specific log files, one for the inner function and one for the outer which does not
include events for the inner function.

.. todo::

    Maybe write a merge script that takes a log file and merges it with all the descendents.

.. rubric:: Footnotes
.. [#] A handy way to find these is to use ``grep -nrI "#define Py.*_Check(" . | grep "\.h"`` on the Python source.
