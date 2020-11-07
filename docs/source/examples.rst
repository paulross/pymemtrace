*******************
Examples
*******************


``debug_malloc_stats``
==============================


.. code-block:: python

    print(f'example_trace_malloc_for_documentation()')
    with debug_malloc_stats.DiffSysDebugMallocStats() as malloc_diff:
        for i in range(1, 9):
            list_of_strings.append(' ' * (i * 8))
    print(f'DiffSysDebugMallocStats.diff():')
    print(f'{malloc_diff.diff()}')



.. code-block:: text

    example_trace_malloc_for_documentation()
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





The OS's View of Memory
----------------------------------

``pymemtrace`` asks the OS for its opinion of memory usage at each function entry and exit point.
For this to be acurate Python's memory pool system (the Python Object Allocator) must be disabled and this needs a special build of Python with ``--without-pymalloc`` set::

    ../configure --with-pydebug --without-pymalloc
    make

This version of Python runs about 2x to 4x slower without the Python object allocator and this makes ``pymemtrace`` even slower.

Mitigation: Run with the object allocator and accept the inaccuracy. This is probably not that important if we are looking for big memory moves.




To use pymemtrace in a project::

    import pymemtrace
