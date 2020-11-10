
``tracemalloc``
==============================

.. code-block:: python

    print(f'example_trace_malloc_for_documentation()')
    with trace_malloc.TraceMalloc('filename') as tm:
        for i in range(8):
            list_of_strings.append(create_string(1024**2))
    print(f'tm.memory_start={tm.memory_start}')
    print(f'tm.memory_finish={tm.memory_finish}')
    for stat in tm.statistics:
        print(stat)



.. code-block:: text

    example_trace_malloc_for_documentation()
    tm.memory_start=15112
    tm.memory_finish=15840
    pymemtrace/examples/ex_trace_malloc.py:0: size=8194 KiB (+8193 KiB), count=16 (+10), average=512 KiB
    /Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8/tracemalloc.py:0: size=6464 B (+504 B), count=39 (+10), average=166 B
    /Users/paulross/Documents/workspace/pymemtrace/pymemtrace/trace_malloc.py:0: size=3076 B (-468 B), count=10 (-1), average=308 B
    /Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8/logging/__init__.py:0: size=16.3 KiB (-128 B), count=49 (-2), average=340 B
    /Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8/abc.py:0: size=3169 B (+0 B), count=30 (+0), average=106 B
    /Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8/posixpath.py:0: size=480 B (+0 B), count=1 (+0), average=480 B
    /Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8/threading.py:0: size=168 B (+0 B), count=2 (+0), average=84 B
    /Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8/_weakrefset.py:0: size=72 B (+0 B), count=1 (+0), average=72 B


