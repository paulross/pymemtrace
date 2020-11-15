.. _examples-debug_malloc_stats:

``debug_malloc_stats`` Examples
===================================

These Python examples are in :py:mod:`pymemtrace.examples.ex_debug_alloc_stats`

Adding Small Strings
----------------------------

Here is an example of adding small strings to a list under the watchful eye of :py:class:`debug_malloc_stats.DiffSysDebugMallocStats`:

.. code-block:: python

    print(f'example_debug_malloc_stats_for_documentation()')
    with debug_malloc_stats.DiffSysDebugMallocStats() as malloc_diff:
        for i in range(1, 9):
            list_of_strings.append(' ' * (i * 8))
    print(f'DiffSysDebugMallocStats.diff():')
    print(f'{malloc_diff.diff()}')

The output is:

.. code-block:: text

    example_debug_malloc_stats_for_documentation()
    DiffSysDebugMallocStats.diff():
    class   size   num pools   blocks in use  avail blocks
    -----   ----   ---------   -------------  ------------
        1     32          +1             +52           +74
        2     48          +0             +17           -17
        3     64          +0             +33           -33
        4     80          +1             +51            -1
        5     96          +2             +34           +50
        6    112          +0              +2            -2
        7    128          +0              +1            -1
       10    176          +0              +1            -1
       12    208          +0              +1            -1
       17    288          +0              +1            -1
       18    304          +0              +2            -2
       25    416          +0              +3            -3
       26    432          +0              +3            -3
       27    448          +0              +3            -3
       29    480          +0              +3            -3
       30    496          +0              +1            -1
       31    512          +0              +1            -1

    # bytes in allocated blocks        =              +19,904
    # bytes in available blocks        =               -3,808
    -4 unused pools * 4096 bytes       =              -16,384
    # bytes lost to pool headers       =                 +192
    # bytes lost to quantization       =                  +96

      -1 free 1-sized PyTupleObjects * 32 bytes each =                  -32
      +1 free 5-sized PyTupleObjects * 64 bytes each =                  +64
               +2 free PyDictObjects * 48 bytes each =                  +96
               -2 free PyListObjects * 40 bytes each =                  -80
             +1 free PyMethodObjects * 48 bytes each =                  +48


Cost of ``debug_malloc_stats``
-----------------------------------

In :py:mod:`pymemtrace.examples.ex_debug_alloc_stats` are some timing examples of creating a list of strings of varying size
with and without ``debug_malloc_stats``.
Here are some typical results:

.. Commented out typical output:

    $ caffeinate python pymemtrace/examples/ex_debug_malloc_stats.py
    number=10,000 repeat=5 convert=1,000,000
    example_timeit_under_512                                    :     2.746,     2.584,     2.582,     2.664,     2.462 mean=    2.607 min=    2.462 max=    2.746 span=    0.284
    example_timeit_under_512_with_debug_malloc_stats            :  5556.577,  6321.485,  6391.563,  6247.821,  7243.693 mean= 6352.228 min= 5556.577 max= 7243.693 span= 1687.116 x2436.232
    example_timeit_over_512                                     :     5.428,     4.661,     5.704,     6.326,     4.507 mean=    5.325 min=    4.507 max=    6.326 span=    1.819
    example_timeit_over_512_with_debug_malloc_stats             :  7074.884,  6553.412,  7123.040,  6636.192,  6707.841 mean= 6819.074 min= 6553.412 max= 7123.040 span=  569.628 x1280.509
    example_timeit_well_over_512                                :   639.517,   482.394,   562.109,   681.655,   598.415 mean=  592.818 min=  482.394 max=  681.655 span=  199.261
    example_timeit_well_over_512_with_debug_malloc_stats        :  7322.035,  6952.874,  7611.174,  7739.893,  7302.739 mean= 7385.743 min= 6952.874 max= 7739.893 span=  787.019 x  12.459
    (pymemtrace_3.8_A)

.. list-table:: **Times in µs**
   :widths: 25 25 25 25
   :header-rows: 1

   * - Task
     - Without ``debug_malloc_stats``
     - With ``debug_malloc_stats``
     - Ratio
   * - 128 byte strings
     - 2.6
     - 6400
     - x2400
   * - 1024 byte strings
     - 5.3
     - 6800
     - x1300
   * - 1Mb strings
     - 590
     - 7400
     - x12

