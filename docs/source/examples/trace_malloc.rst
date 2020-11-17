.. _examples-trace_malloc:

``trace_malloc`` Examples
==============================

``trace_malloc`` contains some utility wrappers around the :py:mod:`tracemalloc` module.
It can compensate for the memory used by :py:mod:`tracemalloc` module.

These Python examples are in :py:mod:`pymemtrace.examples.ex_trace_malloc`


Using ``trace_malloc`` Directly
----------------------------------------


Adding 1Mb Strings
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Here is an example of adding 1Mb strings to a list under the watchful eye of :py:class:`trace_malloc.TraceMalloc`:

.. code-block:: python

    from pymemtrace import trace_malloc

    list_of_strings = []
    print(f'example_trace_malloc_for_documentation()')
    with trace_malloc.TraceMalloc('filename') as tm:
        for i in range(8):
            list_of_strings.append(' ' * 1024**2)
    print(f' tm.memory_start={tm.memory_start}')
    print(f'tm.memory_finish={tm.memory_finish}')
    print(f'         tm.diff={tm.diff}')
    for stat in tm.statistics:
        print(stat)

Typical output is:

.. code-block:: text

    example_trace_malloc_for_documentation()
     tm.memory_start=13072
    tm.memory_finish=13800
             tm.diff=8388692
    pymemtrace/examples/ex_trace_malloc.py:0: size=8194 KiB (+8193 KiB), count=16 (+10), average=512 KiB
    /Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8/tracemalloc.py:0: size=6464 B (+504 B), count=39 (+10), average=166 B
    Documents/workspace/pymemtrace/pymemtrace/trace_malloc.py:0: size=3076 B (-468 B), count=10 (-1), average=308 B
    /Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8/logging/__init__.py:0: size=16.3 KiB (-128 B), count=49 (-2), average=340 B
    /Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8/abc.py:0: size=3169 B (+0 B), count=30 (+0), average=106 B
    /Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8/posixpath.py:0: size=480 B (+0 B), count=1 (+0), average=480 B
    /Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8/threading.py:0: size=168 B (+0 B), count=2 (+0), average=84 B
    /Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8/_weakrefset.py:0: size=72 B (+0 B), count=1 (+0), average=72 B


To eliminate the lines that is caused by ``tracemalloc`` itself change the last two lines to:

.. code-block:: python

    for stat in tm.net_statistics:
        print(stat)

Which removes the line:

.. code-block:: text

    /Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8/tracemalloc.py:0: size=6464 B (+504 B), count=39 (+10), average=166 B


Using ``trace_malloc`` as a Decorator
----------------------------------------

``trace_malloc`` provides a function decorator that can log the tracemalloc memory usage caused by execution a function.
For example:

.. code-block:: python

    from pymemtrace import trace_malloc

    @trace_malloc.trace_malloc_log(logging.INFO)
    def example_decorator_for_documentation(list_of_strings):
        for i in range(8):
            list_of_strings.append(create_string(1024**2))

    list_of_strings = []
    example_decorator_for_documentation(list_of_strings)

Would log something like the following:

.. code-block:: text

    2020-11-15 18:37:39,194 -   trace_malloc.py#87   - 10121 - (MainThread) - INFO     - TraceMalloc memory delta: 8,389,548 for "example_decorator_for_documentation()"




Cost of ``trace_malloc``
-----------------------------------

In :py:mod:`pymemtrace.examples.ex_trace_malloc` are some timing examples of creating a list of strings of varying size
with and without :py:class:`trace_malloc.TraceMalloc`.
Here are some typical results:

.. Commented out typical output:

    $ /usr/bin/time -lp caffeinate python pymemtrace/examples/ex_trace_malloc.py
    number=10,000 repeat=5 convert=1,000,000
    example_timeit_under_512                                    :     8.139,     5.642,     4.479,     4.401,     5.994 mean=    5.731 min=    4.401 max=    8.139 span=    3.739
    example_timeit_under_512_with_trace_malloc('filename')      :  4868.405,  4898.027,  4786.358,  4753.629,  4781.850 mean= 4817.654 min= 4753.629 max= 4898.027 span=  144.398 x 840.645
    example_timeit_under_512_with_trace_malloc('lineno')        :  5050.222,  5043.958,  5034.344,  5031.117,  5021.919 mean= 5036.312 min= 5021.919 max= 5050.222 span=   28.303 x 878.799
    example_timeit_under_512_with_trace_malloc('traceback')     :  5037.949,  5052.557,  5054.989,  5050.296,  5050.368 mean= 5049.232 min= 5037.949 max= 5054.989 span=   17.040 x 881.053
    example_timeit_over_512                                     :    18.541,    17.827,    17.576,    17.529,    17.595 mean=   17.814 min=   17.529 max=   18.541 span=    1.012
    example_timeit_over_512_with_trace_malloc('filename')       :  5068.476,  5053.528,  5065.614,  5050.911,  5497.147 mean= 5147.135 min= 5050.911 max= 5497.147 span=  446.236 x 288.945
    example_timeit_over_512_with_trace_malloc('lineno')         :  5470.068,  5237.150,  5166.904,  5162.868,  5170.988 mean= 5241.596 min= 5162.868 max= 5470.068 span=  307.201 x 294.248
    example_timeit_over_512_with_trace_malloc('traceback')      :  5094.635,  5105.176,  5111.833,  5097.936,  5083.761 mean= 5098.668 min= 5083.761 max= 5111.833 span=   28.071 x 286.224
    example_timeit_well_over_512                                :  1080.574,  1069.804,  1071.831,  1072.760,  1073.760 mean= 1073.746 min= 1069.804 max= 1080.574 span=   10.771
    example_timeit_well_over_512_with_trace_malloc('filename')  :  6260.360,  6241.928,  6252.577,  6258.768,  6252.283 mean= 6253.183 min= 6241.928 max= 6260.360 span=   18.432 x   5.824
    example_timeit_well_over_512_with_trace_malloc('lineno')    :  6370.560,  6388.218,  6390.206,  6383.660,  6387.620 mean= 6384.053 min= 6370.560 max= 6390.206 span=   19.646 x   5.946
    example_timeit_well_over_512_with_trace_malloc('traceback') :  6295.303,  6309.619,  6300.180,  6305.292,  6320.041 mean= 6306.087 min= 6295.303 max= 6320.041 span=   24.738 x   5.873
    real      2521.90
    user      2484.92
    sys         28.66
      26484736  maximum resident set size
             0  average shared memory size
             0  average unshared data size
             0  average unshared stack size
          7366  page reclaims
           670  page faults
             0  swaps
             0  block input operations
             0  block output operations
             0  messages sent
             0  messages received
             0  signals received
            74  voluntary context switches
        917533  involuntary context switches
    (pymemtrace_3.8_A)


Using key_type 'filename'
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table:: **Times in µs tracing** ``filename``
   :widths: 25 25 25 25
   :header-rows: 1

   * - Task
     - Without ``trace_malloc.TraceMalloc``
     - With ``trace_malloc.TraceMalloc``
     - Ratio
   * - 256 byte strings
     - 5.7
     - 4800
     - x840
   * - 1024 byte strings
     - 18
     - 5100
     - x290
   * - 1Mb strings
     - 1100
     - 6300
     - x5.8


Using key_type 'lineno'
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table:: **Times in µs tracing** ``lineno``
   :widths: 25 25 25 25
   :header-rows: 1

   * - Task
     - Without ``trace_malloc.TraceMalloc``
     - With ``trace_malloc.TraceMalloc``
     - Ratio
   * - 256 byte strings
     - 5.7
     - 5000
     - x880
   * - 1024 byte strings
     - 18
     - 5200
     - x290
   * - 1Mb strings
     - 1100
     - 6400
     - x5.9


Using key_type 'traceback'
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table:: **Times in µs tracing** ``traceback``
   :widths: 25 25 25 25
   :header-rows: 1

   * - Task
     - Without ``trace_malloc.TraceMalloc``
     - With ``trace_malloc.TraceMalloc``
     - Ratio
   * - 256 byte strings
     - 5.7
     - 5000
     - x880
   * - 1024 byte strings
     - 18
     - 5100
     - x290
   * - 1Mb strings
     - 1100
     - 6300
     - x5.9

