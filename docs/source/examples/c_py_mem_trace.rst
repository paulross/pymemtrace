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

There is some discussion about the performance of :py:mod:`pymemtrace.cPyMemTrace` here :ref:`tech_notes-cpymemtrace_perf`

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
    This is described in more detail in :ref:`tech_notes-cpymemtrace_reference_tracing_specific`.

Simple Reference Tracing
---------------------------------------

:py:class:`cPyMemTrace.ReferenceTracingSimple` is a simple tracer that just counts allocations and de-allocations.
It can be used as a context manager thus:

.. code-block:: python

    from pymemtrace import cPyMemTrace

    with cPyMemTrace.ReferenceTracingSimple() as profiler:
        print()
        print('Hi there')
        print(profiler)
        # Do stuff here
        print(f'NEW: {profiler.count_new()}')
        print(f'DEL: {profiler.count_del()}')

And the output might be something like:

.. code-block:: text

    Hi there
    <cPyMemTrace.ReferenceTracingSimple object at 0x600002f019c0>
    NEW: 369347
    DEL: 369110

These profilers can be stacked, the outer one is suspended and then restored whilst the inner one is at work:

.. code-block:: python

    from pymemtrace import cPyMemTrace

    with cPyMemTrace.ReferenceTracingSimple() as profiler_a:
        print()
        print('Hello World')
        print(profiler_a)
        with cPyMemTrace.ReferenceTracingSimple() as profiler_b:
            a = '  Hello World'
            print(a)
            print(f'  {profiler_b}')
            print(f'  NEW: {profiler_b.count_new()}')
            print(f'  DEL: {profiler_b.count_del()}')
        print(f'NEW: {profiler_a.count_new()}')
        print(f'DEL: {profiler_a.count_del()}')

And the output might be:

.. code-block:: text

    Hello World
    <cPyMemTrace.ReferenceTracingSimple object at 0x600000c19390>
      Hello World
      <cPyMemTrace.ReferenceTracingSimple object at 0x600000c00f70>
      NEW: 20
      DEL: 31
    NEW: 24
    DEL: 34

More Useful Reference Tracing
---------------------------------------

The :py:class:`cPyMemTrace.ReferenceTracing` is more sophisticated as it logs out all the allocations and
de-allocations.
It can also filter out unnecessary information such as builtin allocations.

.. note::

    The Reference Tracing callback function ignores PyObject's of type "frame" as this can play havoc with the
    Python runtime.
    See :ref:`tech_notes-cpymemtrace_reference_tracing_pytest` for an example that revealed this problem.

Here we create an example class that just creates a timstamp and allocates memory
(the full code is in ``pymemtrace/examples/ex_cPyMemTrace_RefTrace.py``):

.. code-block:: python

    import datetime
    import random
    import string

    from pymemtrace import cpymemtrace_decs
    from pymemtrace import cPyMemTrace


    class StringAndTime:
        def __init__(self, size: int):
            self.now = datetime.datetime.now()
            self.str = ''.join(random.choices(string.printable, k=size))

Then we invoke this multiple times under the watchful eye of a :py:class:`pymemtrace.cPyMemTrace.ReferenceTracing`
decorator:

.. code-block:: python

    @cpymemtrace_decs.reference_tracing()
    def example_reference_tracing():
        print(f'example_reference_tracing()')
        print(f'Logging to {cPyMemTrace.reference_tracing_log_path()}')
        list_of_str_and_time = []
        for i in range(4):
            str_len = random.randint(1024, 2048)
            v = StringAndTime(str_len)
            list_of_str_and_time.append(v)

    def main():
        example_reference_tracing()
        return 0


    if __name__ == '__main__':
        exit(main())

Running this will give something like:

.. code-block:: shell

    python3.13 pymemtrace/examples/ex_cPyMemTrace_RefTrace.py
    example_reference_tracing()
    Logging to pymemtrace/examples/20260518_114412_0_85511_O_0_PY3.13.2.log

    Process finished with exit code 0

The log file will look like this (abridged).

..
    8<---- Snip ---->8

.. raw:: latex

    [Continued on the next page]

    \pagebreak

.. raw:: latex

    \begin{landscape}

.. code-block:: text

    SOF
    HDR:        Clock          Address LiveCnt Type                File                                           Line Function                        RSS      dRSS
    NEW:     1.834382   0x60000281a1d0       1 range_iterator      pymemtrace/examples/ex_cPyMemTrace_RefTrace.py   23 example_reference_tracing  17911808  17911808
    NEW:     1.834498   0x7ff3db813920       1 StringAndTime       pymemtrace/examples/ex_cPyMemTrace_RefTrace.py   25 example_reference_tracing  17920000      8192
    NEW:     1.834551   0x6000028015d0       1 datetime.datetime   pymemtrace/examples/ex_cPyMemTrace_RefTrace.py   11 __init__                   17936384     16384
    NEW:     1.834585   0x600001d23310       1 itertools.repeat    Python-3.13.2/Lib/random.py                     471 choices                    17940480      4096
    DEL:     1.834927   0x600001d23310       0 itertools.repeat    Python-3.13.2/Lib/random.py                     471 choices                    17940480         0
    NEW:     1.835052   0x7ff3db813a80       2 StringAndTime       pymemtrace/examples/ex_cPyMemTrace_RefTrace.py   25 example_reference_tracing  17944576      4096
    NEW:     1.835088   0x600002801850       2 datetime.datetime   pymemtrace/examples/ex_cPyMemTrace_RefTrace.py   11 __init__                   17944576         0
    NEW:     1.835135   0x600001d58070       1 itertools.repeat    Python-3.13.2/Lib/random.py                     471 choices                    17944576         0
    DEL:     1.835501   0x600001d58070       0 itertools.repeat    Python-3.13.2/Lib/random.py                     471 choices                    17956864     12288
    NEW:     1.835592   0x7ff3d9608ba0       3 StringAndTime       pymemtrace/examples/ex_cPyMemTrace_RefTrace.py   25 example_reference_tracing  17956864         0
    NEW:     1.835613   0x60000281a390       3 datetime.datetime   pymemtrace/examples/ex_cPyMemTrace_RefTrace.py   11 __init__                   17956864         0
    NEW:     1.835637   0x600001d42e10       1 itertools.repeat    Python-3.13.2/Lib/random.py                     471 choices                    17956864         0
    DEL:     1.836171   0x600001d42e10       0 itertools.repeat    Python-3.13.2/Lib/random.py                     471 choices                    17956864         0
    NEW:     1.836285   0x7ff3d961a3c0       4 StringAndTime       pymemtrace/examples/ex_cPyMemTrace_RefTrace.py   25 example_reference_tracing  17956864         0
    NEW:     1.836310   0x60000281a550       4 datetime.datetime   pymemtrace/examples/ex_cPyMemTrace_RefTrace.py   11 __init__                   17956864         0
    NEW:     1.836333   0x600001d42e10       1 itertools.repeat    Python-3.13.2/Lib/random.py                     471 choices                    17956864         0
    DEL:     1.836920   0x600001d42e10       0 itertools.repeat    Python-3.13.2/Lib/random.py                     471 choices                    17960960      4096
    DEL:     1.837031   0x60000281a1d0       0 range_iterator      pymemtrace/examples/ex_cPyMemTrace_RefTrace.py   23 example_reference_tracing  17960960         0
    DEL:     1.837050   0x7ff3d9608ba0       3 StringAndTime       pymemtrace/cpymemtrace_decs.py                   45 reference_tracingwrapper   17960960         0
    DEL:     1.837064   0x60000281a390       3 datetime.datetime   pymemtrace/cpymemtrace_decs.py                   45 reference_tracingwrapper   17960960         0
    DEL:     1.837075   0x7ff3db813a80       2 StringAndTime       pymemtrace/cpymemtrace_decs.py                   45 reference_tracingwrapper   17960960         0
    DEL:     1.837085   0x600002801850       2 datetime.datetime   pymemtrace/cpymemtrace_decs.py                   45 reference_tracingwrapper   17960960         0
    DEL:     1.837098   0x7ff3db813920       1 StringAndTime       pymemtrace/cpymemtrace_decs.py                   45 reference_tracingwrapper   17960960         0
    DEL:     1.837108   0x6000028015d0       1 datetime.datetime   pymemtrace/cpymemtrace_decs.py                   45 reference_tracingwrapper   17960960         0
    DEL:     1.837119   0x7ff3d961a3c0       0 StringAndTime       pymemtrace/cpymemtrace_decs.py                   45 reference_tracingwrapper   17960960         0
    DEL:     1.837129   0x60000281a550       0 datetime.datetime   pymemtrace/cpymemtrace_decs.py                   45 reference_tracingwrapper   17960960         0
    NEW:     1.837155   0x60000166d4c0       1 _ModuleLockManager  <frozen importlib._bootstrap>                  1357 _find_and_load             17960960         0
    NEW:     1.837185   0x600000f35860       1 _ModuleLock         <frozen importlib._bootstrap>                   443 _get_module_lock           17960960         0
    NEW:     1.837200   0x6000018715e0       1 _thread.RLock       <frozen importlib._bootstrap>                   253 __init__                   17960960         0
    NEW:     1.837213   0x600001d42d80       1 _thread.lock        <frozen importlib._bootstrap>                   254 __init__                   17960960         0
    NEW:     1.837235   0x6000013396b0       1 _BlockingOnManager  <frozen importlib._bootstrap>                   311 acquire                    17960960         0
    DEL:     1.837282   0x6000013396b0       0 _BlockingOnManager  <frozen importlib._bootstrap>                   311 acquire                    17960960         0
    NEW:     1.837327   0x600001d42d20       1 list_iterator       <frozen importlib._bootstrap>                  1255 _find_spec                 17960960         0
    NEW:     1.837343   0x600001871530       1 _ImportLockContext  <frozen importlib._bootstrap>                  1256 _find_spec                 17960960         0
    NEW:     1.837366   0x600001d42cd0       2 list_iterator       site-packages/_distutils_hack/__init__.py       107 find_spec                  17960960         0
    DEL:     1.837381   0x600001d42cd0       1 list_iterator       site-packages/_distutils_hack/__init__.py       107 find_spec                  17960960         0
    DEL:     1.837409   0x600001871530       0 _ImportLockContext  <frozen importlib._bootstrap>                  1256 _find_spec                 17960960         0
    NEW:     1.837424   0x600001871710       1 _ImportLockContext  <frozen importlib._bootstrap>                  1256 _find_spec                 17960960         0
    NEW:     1.837454   0x600000a31370       1 ModuleSpec          <frozen importlib._bootstrap>                   688 spec_from_loader           17960960         0
    DEL:     1.837475   0x600001871710       0 _ImportLockContext  <frozen importlib._bootstrap>                  1256 _find_spec                 17960960         0
    DEL:     1.837488   0x600001d42d20       0 list_iterator       <frozen importlib._bootstrap>                  1280 _find_spec                 17960960         0
    DEL:     1.837602   0x60000166d4c0       0 _ModuleLockManager  <frozen importlib._bootstrap>                  1357 _find_and_load             17965056      4096
    DEL:     1.837620   0x600000f35860       0 _ModuleLock         <frozen importlib._bootstrap>                  1357 _find_and_load             17965056         0
    DEL:     1.837636   0x6000018715e0       0 _thread.RLock       <frozen importlib._bootstrap>                  1357 _find_and_load             17965056         0
    DEL:     1.837648   0x600001d42d80       0 _thread.lock        <frozen importlib._bootstrap>                  1357 _find_and_load             17965056         0
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


.. raw:: latex

    [Continued on the next page]

    \pagebreak

.. raw:: latex

    \begin{landscape}

First running the script:

.. code-block:: text

    python pymemtrace/util/ref_trace_analyse.py --include-historical pymemtrace/examples/20260518_114412_0_85511_O_0_PY3.13.2.log
    File path: pymemtrace/examples/20260518_114412_0_85511_O_0_PY3.13.2.log
    2026-05-18 13:04:41,604 - ref_trace_analyse.py#399 - INFO     - Starting log file: pymemtrace/examples/20260518_114412_0_85511_O_0_PY3.13.2.log
    2026-05-18 13:04:41,606 - ref_trace_analyse.py#379 - INFO     - Lines: 49 NEW: 23 DEL: 22 NEW - DEL: 1 MSG: 0
    2026-05-18 13:04:41,607 - ref_trace_analyse.py#401 - INFO     - Finished log file: pymemtrace/examples/20260518_114412_0_85511_O_0_PY3.13.2.log

Then live objects once the log has completed:

.. code-block:: text

    With include_builtins=False
    Live Objects [1]:
        0x600000a31370 1.837454    1 ModuleSpec                               spec_from_loader                 <frozen_importlib._bootstrap>#688

Then previous objects that were created and destroyed during the log lifetime:

.. code-block:: text

    Previous Objects, sorted by clock [21]:
    0x60000281a1d0 range_iterator      NEW: t: 1.834382 ex_cPyMemTrace_RefTrace.py#23 DEL: dt: 0.002649 ex_cPyMemTrace_RefTrace.py#23
    0x7ff3db813920 StringAndTime       NEW: t: 1.834498 ex_cPyMemTrace_RefTrace.py#25 DEL: dt: 0.002600 cpymemtrace_decs.py#45
    0x6000028015d0 datetime.datetime   NEW: t: 1.834551 ex_cPyMemTrace_RefTrace.py#11 DEL: dt: 0.002557 cpymemtrace_decs.py#45
    0x600001d23310 itertools.repeat    NEW: t: 1.834585 random.py#471 DEL: dt: 0.000342 random.py#471
    0x7ff3db813a80 StringAndTime       NEW: t: 1.835052 ex_cPyMemTrace_RefTrace.py#25 DEL: dt: 0.002023 cpymemtrace_decs.py#45
    0x600002801850 datetime.datetime   NEW: t: 1.835088 ex_cPyMemTrace_RefTrace.py#11 DEL: dt: 0.001997 cpymemtrace_decs.py#45
    0x600001d58070 itertools.repeat    NEW: t: 1.835135 random.py#471 DEL: dt: 0.000366 random.py#471
    0x7ff3d9608ba0 StringAndTime       NEW: t: 1.835592 ex_cPyMemTrace_RefTrace.py#25 DEL: dt: 0.001458 cpymemtrace_decs.py#45
    0x60000281a390 datetime.datetime   NEW: t: 1.835613 ex_cPyMemTrace_RefTrace.py#11 DEL: dt: 0.001451 cpymemtrace_decs.py#45
    0x600001d42e10 itertools.repeat    NEW: t: 1.835637 random.py#471 DEL: dt: 0.000534 random.py#471
    0x7ff3d961a3c0 StringAndTime       NEW: t: 1.836285 ex_cPyMemTrace_RefTrace.py#25 DEL: dt: 0.000834 cpymemtrace_decs.py#45
    0x60000281a550 datetime.datetime   NEW: t: 1.836310 ex_cPyMemTrace_RefTrace.py#11 DEL: dt: 0.000819 cpymemtrace_decs.py#45
    0x600001d42e10 itertools.repeat    NEW: t: 1.836333 random.py#471 DEL: dt: 0.000587 random.py#471
    0x60000166d4c0 _ModuleLockManager  NEW: t: 1.837155 <frozen_importlib._bootstrap>#1357 DEL: dt: 0.000447 <frozen_importlib._bootstrap>#1357
    0x600000f35860 _ModuleLock         NEW: t: 1.837185 <frozen_importlib._bootstrap>#443 DEL: dt: 0.000435 <frozen_importlib._bootstrap>#1357
    0x6000018715e0 _thread.RLock       NEW: t: 1.837200 <frozen_importlib._bootstrap>#253 DEL: dt: 0.000436 <frozen_importlib._bootstrap>#1357
    0x600001d42d80 _thread.lock        NEW: t: 1.837213 <frozen_importlib._bootstrap>#254 DEL: dt: 0.000435 <frozen_importlib._bootstrap>#1357
    0x6000013396b0 _BlockingOnManager  NEW: t: 1.837235 <frozen_importlib._bootstrap>#311 DEL: dt: 0.000047 <frozen_importlib._bootstrap>#311
    0x600001d42d20 list_iterator       NEW: t: 1.837327 <frozen_importlib._bootstrap>#1255 DEL: dt: 0.000161 <frozen_importlib._bootstrap>#1280
    0x600001871530 _ImportLockContext  NEW: t: 1.837343 <frozen_importlib._bootstrap>#1256 DEL: dt: 0.000066 <frozen_importlib._bootstrap>#1256
    0x600001d42cd0 list_iterator       NEW: t: 1.837366 __init__.py#107 DEL: dt: 0.000015 __init__.py#107
    0x600001871710 _ImportLockContext  NEW: t: 1.837424 <frozen_importlib._bootstrap>#1256 DEL: dt: 0.000051 <frozen_importlib._bootstrap>#1256

Then a table of the count of creations and deletions by type:

.. code-block:: text

    Type count [12]:
    Type                                          New      Del  New - Del
    ModuleSpec                                      1        0          1
    StringAndTime                                   4        4          0
    _BlockingOnManager                              1        1          0
    _ImportLockContext                              2        2          0
    _ModuleLock                                     1        1          0
    _ModuleLockManager                              1        1          0
    _thread.RLock                                   1        1          0
    _thread.lock                                    1        1          0
    datetime.datetime                               4        4          0
    itertools.repeat                                4        4          0
    list_iterator                                   2        2          0
    range_iterator                                  1        1          0
    Process time: 0.003 (s)

.. raw:: latex

    [Continued on the next page]

    \pagebreak

.. raw:: latex

    \end{landscape}

``ref_trace_analyse.py`` Options
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``ref_trace_analyse.py`` has these options:

.. code-block:: text

    usage: ref_trace_analyse.py
           [-h] [--full-path] [--include-untracked] [--include-historical]
           [--recurse-files] [-l LOG_LEVEL]
           log_path

    Reads an Reference Tracing log of a process and analyses it.

    positional arguments:
      log_path              Input path to the log.

    options:
      -h, --help            show this help message and exit
      --full-path           Show the full Python file path. [default: False]
      --include-untracked   Include untracked objects. These are objects that are
                            de-allocated with no corresponding allocation.
                            [default: False]
      --include-historical  Ignore objects that were allocated and de-allocated
                            correctly. [default: False]
      --recurse-files       If True then recurse into child log files. [default:
                            False]
      -l, --log_level LOG_LEVEL
                            Log Level (debug=10, info=20, warning=30, error=40,
                            critical=50) [default: 20]


Reference Tracing and Garbage Collection
-----------------------------------------

One of the problems of getting a *clean* reference tracing log, one where all allocations and de-allocations
are matched is that Python has a quite complicated de-allocation strategy.
It is different from, say C++, in that Python's is non-deterministic and may be lazy deferring de-allocations
until long after the :py:class:`pymemtrace.cPyMemTrace.ReferenceTracing` is able to observe.

This makes log analysis tricky, apparently certain types have not been de-allocated
however they might well have been after the :py:class:`pymemtrace.cPyMemTrace.ReferenceTracing`
has called ``__exit__()``.

To make the log file more accurate :py:class:`pymemtrace.cPyMemTrace.ReferenceTracing`
has an option ``gc_collect_on_exit`` which takes an integer.
If 0, 1 or 2 (the default) then the this value is passed to :py:func:`gc.collect()` at the beginning of the
``__exit__`` method.
This means that the :py:mod:`gc` is observed by the :py:class:`pymemtrace.cPyMemTrace.ReferenceTracing`
callback function and as the Garbage Collector works the relevant de-allocations will be
in the log file.
If the value is -1 this does not call :py:func:`gc.collect()` during the ``__exit__`` method.

To show the effect of using the Garbage Collector a test :ref:`tech_notes-cpymemtrace_perf_test_data` was run without
Garbage Collection (``gc_collect_on_exit=-1``) and a full garbage collection (``gc_collect_on_exit=2``).
The logs were analysed with :py:mod:`pymemtrace.util.ref_trace_analyse`.

Firstly without garbage collection:

.. raw:: latex

    [Continued on the next page]

    \pagebreak

    \begin{landscape}

.. code-block:: text

    $ python pymemtrace/util/ref_trace_analyse.py 20260417_115810_0_61868_O_0_PY3.14.2.log
    File path: 20260417_115810_0_61868_O_0_PY3.14.2.log
    2026-04-17 13:04:06,003 - ref_trace_analyse.py#338 - INFO     - Lines: 16 NEW: 12 DEL: 0 NEW - DEL: 12 MSG: 0
    Initial Message:
    LASToHTML Reference Tracing include_builtins=False
    Untracked Objects [0]:
    Type                                        Count
    Live Objects [12]:
        0x0001099c4a50    1 LASSection                               _proc_section_generic            LASRead.py#821
        0x000117ef6710    1 LASSection                               _proc_section_generic            LASRead.py#821
        0x000117ef6850    1 LASSection                               _proc_section_generic            LASRead.py#821
        0x000117f02660    1 LASSection                               _proc_section_generic            LASRead.py#821
        0x000117f0e210    1 LASSection                               _proc_section_generic            LASRead.py#821
        0x000117f6c9d0    1 LASSection                               _proc_section_generic            LASRead.py#821
        0x000117f6f230    1 LASSection                               _proc_section_generic            LASRead.py#821
        0x000117f73250    1 LASSection                               _proc_section_generic            LASRead.py#821
        0x0001180c9590    1 LASSection                               _proc_section_generic            LASRead.py#821
        0x0001180c96a0    1 LASSection                               _proc_section_generic            LASRead.py#821
        0x000118185310    1 LASSection                               _proc_section_generic            LASRead.py#821
        0x000118185400    1 LASSection                               _proc_section_generic            LASRead.py#821
    Previous Objects [0]:
    Type count [1]:
    Type                                          New      Del  New - Del
    LASSection                                     12        0         12
    Process time: 0.001 (s)

.. raw:: latex

    \end{landscape}

It appears that several ``LASSection`` objects are still alive indicating a memory leak.
However running the same test with a full garbage collection (``gc_collect_on_exit=2``) shows a more
accurate picture demonstrating that all the objects of interest have been correctly de-allocated.

.. raw:: latex

    [Continued on the next page]

    \pagebreak

    \begin{landscape}

.. code-block:: text

    $ python pymemtrace/util/ref_trace_analyse.py 20260417_120226_0_62036_O_0_PY3.14.2.log
    File path: 20260417_120226_0_62036_O_0_PY3.14.2.log
    2026-04-17 13:04:17,387 - ref_trace_analyse.py#338 - INFO     - Lines: 28 NEW: 12 DEL: 12 NEW - DEL: 0 MSG: 0
    Initial Message:
    LASToHTML Reference Tracing include_builtins=False, gc_collect_on_exit=2
    Untracked Objects [0]:
    Type                                        Count
    Live Objects [0]:
    Previous Objects [12]:
        0x00010c6d0a50 LASSection                               NEW: LASRead.py#821 DEL: cpymemtrace_decs.py#44
        0x00011ac12710 LASSection                               NEW: LASRead.py#821 DEL: cpymemtrace_decs.py#44
        0x00011ac12850 LASSection                               NEW: LASRead.py#821 DEL: cpymemtrace_decs.py#44
        0x00011ac1e660 LASSection                               NEW: LASRead.py#821 DEL: cpymemtrace_decs.py#44
        0x00011ac29eb0 LASSection                               NEW: LASRead.py#821 DEL: cpymemtrace_decs.py#44
        0x00011ac8c9d0 LASSection                               NEW: LASRead.py#821 DEL: cpymemtrace_decs.py#44
        0x00011ac8f230 LASSection                               NEW: LASRead.py#821 DEL: cpymemtrace_decs.py#44
        0x00011ac93150 LASSection                               NEW: LASRead.py#821 DEL: cpymemtrace_decs.py#44
        0x00011acad310 LASSection                               NEW: LASRead.py#821 DEL: cpymemtrace_decs.py#44
        0x00011acad400 LASSection                               NEW: LASRead.py#821 DEL: cpymemtrace_decs.py#44
        0x00011ad29590 LASSection                               NEW: LASRead.py#821 DEL: cpymemtrace_decs.py#44
        0x00011ad296a0 LASSection                               NEW: LASRead.py#821 DEL: cpymemtrace_decs.py#44
    Type count [1]:
    Type                                          New      Del  New - Del
    LASSection                                     12       12          0
    Process time: 0.002 (s)

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
       See :ref:`tech_notes-cpymemtrace_perf_reference_tracing_performance` for a comprehensive
       performance analysis.
       The builtin types are those C types that have a ``Py*_Check()`` function.
       These include all numeric types, containers (tuple, list, dict, set, frozenset), strings, bytes and so on.
       See ``reference_trace_is_builtin_pre_suspend()`` in ``pymemtrace/src/cpy/cPyMemTrace.c``
       for the specific criteria [#]_.

See the code in ``reference_trace_allocations_callback()`` in ``pymemtrace/src/cpy/cPyMemTrace.c``
for the implementation of all this logic.

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

If you want *some* of the builtins, but not all, to appear in the log along with
your special type then use this pattern:
This example will *only* log the events of ``MySpecialType`` and the builtin ``list``:

.. code-block:: python

    @cpymemtrace_decs.reference_tracing(
        message="some_function() only MySpecialType and lists",
        # This allows all builtins.
        include_builtins=True,
        # Then this filters out all of the builtins apart from lists.
        include_tp_names=['MySpecialType', 'list'],
    )
    def some_function():
        pass

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

This is described in more detail in :ref:`tech_notes-cpymemtrace_design_stacking_context_managers`.

.. _examples-cpymemtrace_decorators:

Decorators
------------

Often it is more convenient to use these as decorators of a particular function of interest.
The decorators take the constructor arguments and will write to the appropriate file.

The decorators, being pure Python code, are in :py:mod:`pymemtrace.cpymemtrace_decs`
and can be used like this:

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

Or running tracing *and* reference tracing simultaneosuly on the same function:

.. code-block:: python

    from pymemtrace import cpymemtrace_decs

    @cpymemtrace_decs.trace(
        message='Trace the outer function',
    )
    @cpymemtrace_decs.reference_tracing(
        message='Reference trace the outer function that calls the inner function',
    )
    def outer_function():
        # Do great stuff here...
        pass

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

Writing Messages to a Log File
------------------------------

To make log files more useful the user can inject messages into the log file in two ways:

- On construction of the Trace/Profile/Reference Tracing object using the ``message=<message>`` argument.
  This message will be reproduced verbatim and will be followed by a newline.
- At any time during the running of Trace/Profile/Reference Tracing object with the
  ``write_message_to_log_file()`` API.
  This message will be preceded with a ``MSG:`` string, then the message is reproduced verbatim and
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
    MSG:  18     +17     3.153134     Before allocation of 179379131 bytes.
    PREV: 18     +17     3.153134    
    NEXT: 19     +18     3.232753     C_CALL   test_cpymemtrace.py             206 sleep                221143040    179380224
    PREV: 19     +18     3.232753     C_CALL   test_cpymemtrace.py             206 sleep                221143040    179380224
    NEXT: 21     +2      3.249982     C_CALL   test_cpymemtrace.py             208 write_message_to_log  41762816   -179380224
    MSG:  22     +1      3.250007     After de-allocation of 179379131 bytes.
    MSG:  42     +21     3.250190     Before allocation of 198138484 bytes.
    PREV: 42     +21     3.250190    
    NEXT: 43     +22     3.344885     C_CALL   test_cpymemtrace.py             206 sleep                239902720    198139904
    PREV: 43     +22     3.344885     C_CALL   test_cpymemtrace.py             206 sleep                239902720    198139904
    NEXT: 45     +2      3.362191     C_CALL   test_cpymemtrace.py             208 write_message_to_log  41762816   -198139904
    MSG:  46     +1      3.362201     After de-allocation of 198138484 bytes.
    MSG:  66     +21     3.362277     Before allocation of 392320729 bytes.
    PREV: 66     +21     3.362277    
    NEXT: 67     +22     3.541612     C_CALL   test_cpymemtrace.py             206 sleep                434085888    392323072
    PREV: 67     +22     3.541612     C_CALL   test_cpymemtrace.py             206 sleep                434085888    392323072
    NEXT: 69     +2      3.573907     C_CALL   test_cpymemtrace.py             208 write_message_to_log  41762816   -392323072
    MSG:  70     +1      3.573918     After de-allocation of 392320729 bytes.
    MSG:  90     +21     3.574011     Before allocation of 504746338 bytes.
    PREV: 90     +21     3.574011    
    NEXT: 91     +22     3.803951     C_CALL   test_cpymemtrace.py             206 sleep                546512896    504750080
    PREV: 91     +22     3.803951     C_CALL   test_cpymemtrace.py             206 sleep                546512896    504750080
    NEXT: 93     +2      3.845491     C_CALL   test_cpymemtrace.py             208 write_message_to_log  41762816   -504750080
    MSG:  94     +1      3.845500     After de-allocation of 504746338 bytes.
    MSG:  114    +21     3.845611     Before allocation of 312965383 bytes.
    PREV: 114    +21     3.845611
    NEXT: 115    +22     3.993233     C_CALL   test_cpymemtrace.py             206 sleep                354729984    312967168
    PREV: 115    +22     3.993233     C_CALL   test_cpymemtrace.py             206 sleep                354729984    312967168
    NEXT: 117    +2      4.018102     C_CALL   test_cpymemtrace.py             208 write_message_to_log  41762816   -312967168
    MSG:  118    +1      4.018114     After de-allocation of 312965383 bytes.
    MSG:  138    +21     4.018275     Before allocation of 438944001 bytes.
    PREV: 138    +21     4.018275
    NEXT: 139    +22     4.231798     C_CALL   test_cpymemtrace.py             206 sleep                480710656    438947840
    PREV: 139    +22     4.231798     C_CALL   test_cpymemtrace.py             206 sleep                480710656    438947840
    NEXT: 141    +2      4.275196     C_CALL   test_cpymemtrace.py             208 write_message_to_log  41762816   -438947840
    MSG:  142    +1      4.275208     After de-allocation of 438944001 bytes.
    MSG:  162    +21     4.275367     Before allocation of 279020117 bytes.
    PREV: 162    +21     4.275367
    NEXT: 163    +22     4.424839     C_CALL   test_cpymemtrace.py             206 sleep                320786432    279023616
    PREV: 163    +22     4.424839     C_CALL   test_cpymemtrace.py             206 sleep                320786432    279023616
    NEXT: 165    +2      4.446285     C_CALL   test_cpymemtrace.py             208 write_message_to_log  41762816   -279023616
    MSG:  166    +1      4.446297     After de-allocation of 279020117 bytes.
    MSG:  186    +21     4.446371     Before allocation of 442963008 bytes.
    PREV: 186    +21     4.446371
    NEXT: 187    +22     4.643456     C_CALL   test_cpymemtrace.py             206 sleep                484728832    442966016
    PREV: 187    +22     4.643456     C_CALL   test_cpymemtrace.py             206 sleep                484728832    442966016
    NEXT: 189    +2      4.678978     C_CALL   test_cpymemtrace.py             208 write_message_to_log  41762816   -442966016
    MSG:  190    +1      4.678990     After de-allocation of 442963008 bytes.
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

.. rubric:: Footnotes
.. [#] A handy way to find these is to use ``grep -nrI "#define Py.*_Check(" . | grep "\.h"`` on the Python source.
