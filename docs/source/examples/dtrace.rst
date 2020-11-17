.. _examples-dtrace:

DTrace Examples
===================================

Creating a DTrace Build
------------------------------

This requires a Python 3.6+ build with DTrace support which can be built from source.
To create a release build in ``~/tmp/Python-3.9.0/dtrace`` and a virtual environment using that build in
``~/venvs/dtrace`` do the following:

.. code-block:: bash

    cd ~/tmp
    curl -o Python-3.9.0.tgz https://www.python.org/ftp/python/3.9.0/Python-3.9.0.tgz
    tar -xzf Python-3.9.0.tgz
    cd Python-3.9.0
    mkdir dtrace
    cd dtrace
    ../configure --with-dtrace
    make
    ./python.exe -m venv ~/venvs/dtrace

For a debug build that does not use ``pymalloc`` replace the ``configure`` line with, as appropriate:

.. code-block:: bash

    ../configure --with-dtrace --with-pydebug --without-pymalloc --with-valgrind

.. note::

    Since this bypasses Python's small object allocator (``pymalloc``) then every ``malloc()`` and ``free()`` can be
    seen by DTrace.
    This makes the DTrace logs very large.


Checking if Python is DTrace Capable
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

From the commmand line:

.. code-block:: bash

    $ python -m sysconfig | grep WITH_DTRACE
        WITH_DTRACE = "1"

In code:

.. code-block:: python

    if sysconfig.get_config_var('WITH_DTRACE') != 1:
        raise RuntimeError(f'Python at {sys.executable} must be build with DTrace support.')


These Python examples are in :py:mod:`pymemtrace.examples.ex_dtrace`

DTrace and C ``malloc()`` and ``free()``
--------------------------------------------

There is a D script ``toolkit/py_flow_malloc_free.d`` that traces all calls to ``malloc()`` and ``free()``.
It takes the following optional arguments:

.. list-table:: **Options for toolkit/py_flow_malloc_free.d D Script**
   :widths: 30 70
   :header-rows: 1

   * - Option
     - Description
   * - ``-D FULL_FILE_PATH``
     - Include the full path in Python filenames.
   * - ``-D PYTHON_CALL_STACK``
     - Include Python callstack when entering and exiting Python functions.


:py:class:`cMemLeak.CMalloc` is a Python wrapper around a buffer directly allocated in C with ``malloc()``.
Here we create four of them and append them to a list then pop them of lowest index first:

.. code-block:: python

    from pymemtrace import cMemLeak

    def create_cmalloc_list():
        input(f'Waiting to start tracing PID: {os.getpid()} (<cr> to continue):')
        l = []
        for i in range(4):
            block = cMemLeak.CMalloc(1477)
            print(f'Created CMalloc size={block.size:d} buffer=0x{block.buffer:x}')
            l.append(block)
        while len(l):
            # Remove in reverse order
            block = l.pop(0)
            print(f'Pop\'d CMalloc size={block.size:d} buffer=0x{block.buffer:x}')
        l.clear()

Run this in one shell run this code:

.. code-block:: bash

    $ python pymemtrace/examples/ex_dtrace.py


And in the other shell run DTrace (here assuming Python is running as PID 11672 from the first shell).

.. code-block:: bash

    $ sudo dtrace -s toolkit/py_flow_malloc_free.d -p 11672 -C

The output of the first shell is:

.. code-block:: text

    Waiting to start tracing PID: 11672 (<cr> to continue):
    Created CMalloc size=%d buffer=0x%s 1477 0x7fa8e6071400
    Created CMalloc size=%d buffer=0x%s 1477 0x7fa8e6071a00
    Created CMalloc size=%d buffer=0x%s 1477 0x7fa8e6821c00
    Created CMalloc size=%d buffer=0x%s 1477 0x7fa8e681ec00
    Pop'd CMalloc size=%d buffer=0x%s 1477 0x7fa8e6071400
    Pop'd CMalloc size=%d buffer=0x%s 1477 0x7fa8e6071a00
    Pop'd CMalloc size=%d buffer=0x%s 1477 0x7fa8e6821c00
    Pop'd CMalloc size=%d buffer=0x%s 1477 0x7fa8e681ec00

And DTrace records:

.. code-block:: bash

    $ sudo dtrace -s toolkit/py_flow_malloc_free.d -p 11672 -C
    Password:
    dtrace: system integrity protection is on, some features will not be available

    dtrace:::BEGIN
     11672     ex_dtrace.py:48   -> create_cmalloc_list malloc(1477) pntr 0x7fa8e6071400
     11672     ex_dtrace.py:48   -> create_cmalloc_list malloc(1477) pntr 0x7fa8e6071a00
     11672     ex_dtrace.py:48   -> create_cmalloc_list malloc(1477) pntr 0x7fa8e6821c00
     11672     ex_dtrace.py:48   -> create_cmalloc_list malloc(1477) pntr 0x7fa8e681ec00
     11672     ex_dtrace.py:53   -> create_cmalloc_list free(0x7fa8e6071400)
     11672     ex_dtrace.py:53   -> create_cmalloc_list free(0x7fa8e6071a00)
     11672     ex_dtrace.py:53   -> create_cmalloc_list malloc(1) pntr 0x7fa8e5d20c10
     11672     ex_dtrace.py:53   -> create_cmalloc_list free(0x7fa8e6821c00)
     11672     ex_dtrace.py:55   -> create_cmalloc_list free(0x7fa8e5d20c10)

    dtrace:::END
    Python malloc byte distributions by engine caller:
       python`_PyObject_Realloc, total bytes = 608
               value  ------------- Distribution ------------- count
                 256 |                                         0
                 512 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ 1
                1024 |                                         0

       python`_PyObject_Malloc, total bytes = 9264
               value  ------------- Distribution ------------- count
                2048 |                                         0
                4096 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ 2
                8192 |                                         0


    Python malloc byte distributions by Python file and function:

       ex_dtrace.py, create_cmalloc_list, bytes total = 5909
               value  ------------- Distribution ------------- count
                   0 |                                         0
                   1 |@@@@@@@@                                 1
                   2 |                                         0
                   4 |                                         0
                   8 |                                         0
                  16 |                                         0
                  32 |                                         0
                  64 |                                         0
                 128 |                                         0
                 256 |                                         0
                 512 |                                         0
                1024 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@         4
                2048 |                                         0


Using ``PyMem_RawAlloc``
-------------------------------

:py:class:`cMemLeak.PyRawMalloc` is a Python wrapper around a buffer directly allocated by Python in C with ``PyMem_RawAlloc``.
This bypasses the ``pymalloc`` small object buffer and allocates directly even for small objects.
So this code creates four 128 bytes buffers:

.. code-block:: python

    def create_pyrawmalloc_list():
        l = []
        for i in range(4):
            block = cMemLeak.PyRawMalloc(128)
            print(f'Created PyRawMalloc size={block.size:d} buffer=0x{block.buffer:x}')
            l.append(block)
        while len(l):
            # Remove in reverse order
            block = l.pop(0)
            print(f'Pop\'d PyRawMalloc size={block.size:d} buffer=0x{block.buffer:x}')
        l.clear()

Will be seen by DTrace even in release builds of Python:

.. code-block:: text

    dtrace:::BEGIN
     11879     ex_dtrace.py:61   -> create_pyrawmalloc_list malloc(128) pntr 0x7fa2ee42d0e0
     11879     ex_dtrace.py:61   -> create_pyrawmalloc_list malloc(128) pntr 0x7fa2ee414f50
     11879     ex_dtrace.py:61   -> create_pyrawmalloc_list malloc(128) pntr 0x7fa2ee4147f0
     11879     ex_dtrace.py:61   -> create_pyrawmalloc_list malloc(128) pntr 0x7fa2ee405ba0
     11879     ex_dtrace.py:66   -> create_pyrawmalloc_list free(0x7fa2ee42d0e0)
     11879     ex_dtrace.py:66   -> create_pyrawmalloc_list free(0x7fa2ee414f50)
     11879     ex_dtrace.py:66   -> create_pyrawmalloc_list malloc(1) pntr 0x7fa2ee42ce20
     11879     ex_dtrace.py:66   -> create_pyrawmalloc_list free(0x7fa2ee4147f0)
     11879     ex_dtrace.py:68   -> create_pyrawmalloc_list free(0x7fa2ee42ce20)



Using ``PyMem_Alloc``
-------------------------------

:py:class:`cMemLeak.PyMalloc` is a Python wrapper around a buffer allocated by Python with ``PyMem_Alloc``.
This may or may not be allocateds by the ``pymalloc`` small object buffer depending on its size.
So this code that creates 128 bytes buffers:

.. code-block:: python

    def create_pymalloc_list():
        l = []
        for i in range(4):
            block = cMemLeak.PyMalloc(128)
            print(f'Created PyMalloc size={block.size:d} buffer=0x{block.buffer:x}')
            l.append(block)
        while len(l):
            # Remove in reverse order
            block = l.pop(0)
            print(f'Pop\'d PyMalloc size={block.size:d} buffer=0x{block.buffer:x}')
        l.clear()


.. code-block:: text

    Waiting to start tracing PID: 12135 (<cr> to continue):
    Created PyMalloc size=128 buffer=0x1015e3930
    Created PyMalloc size=128 buffer=0x1015e36b0
    Created PyMalloc size=128 buffer=0x1015e3eb0
    Created PyMalloc size=128 buffer=0x1015e3f30
    Pop'd PyMalloc size=128 buffer=0x1015e3930
    Pop'd PyMalloc size=128 buffer=0x1015e36b0
    Pop'd PyMalloc size=128 buffer=0x1015e3eb0
    Pop'd PyMalloc size=128 buffer=0x1015e3f30


These allocations will be not be seen by DTrace in release builds of Python:

.. code-block:: bash

    $ sudo dtrace -s toolkit/py_flow_malloc_free.d -p 12135 -C
    Password:
    dtrace: system integrity protection is on, some features will not be available

    dtrace:::BEGIN
     12135     ex_dtrace.py:79   -> create_pymalloc_list malloc(1) pntr 0x7fcd2b624120
     12135     ex_dtrace.py:81   -> create_pymalloc_list free(0x7fcd2b624120)

    dtrace:::END
    Python malloc byte distributions by engine caller:
       python`_PyObject_Realloc, total bytes = 608
               value  ------------- Distribution ------------- count
                 256 |                                         0
                 512 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ 1
                1024 |                                         0

       python`_PyObject_Malloc, total bytes = 9264
               value  ------------- Distribution ------------- count
                2048 |                                         0
                4096 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ 2
                8192 |                                         0


    Python malloc byte distributions by Python file and function:

       ex_dtrace.py, create_pymalloc_list, bytes total = 1
               value  ------------- Distribution ------------- count
                   0 |                                         0
                   1 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ 1
                   2 |                                         0

If we change the allocation size to >512 then ``pymalloc`` is skipped:

.. code-block:: python

    block = cMemLeak.PyMalloc(767)

And these are then observed by DTrace:

.. code-block:: bash

    $ sudo dtrace -s toolkit/py_flow_malloc_free.d -p 12263 -C
    dtrace: system integrity protection is on, some features will not be available

    dtrace:::BEGIN
     12263     ex_dtrace.py:74   -> create_pymalloc_list malloc(767) pntr 0x7fb8df50e490
     12263     ex_dtrace.py:74   -> create_pymalloc_list malloc(767) pntr 0x7fb8df50e790
     12263     ex_dtrace.py:74   -> create_pymalloc_list malloc(767) pntr 0x7fb8df50ea90
     12263     ex_dtrace.py:74   -> create_pymalloc_list malloc(767) pntr 0x7fb8df50ed90
     12263     ex_dtrace.py:79   -> create_pymalloc_list free(0x7fb8df50e490)
     12263     ex_dtrace.py:79   -> create_pymalloc_list free(0x7fb8df50e790)
     12263     ex_dtrace.py:79   -> create_pymalloc_list malloc(1) pntr 0x7fb8df500120
     12263     ex_dtrace.py:79   -> create_pymalloc_list free(0x7fb8df50ea90)
     12263     ex_dtrace.py:81   -> create_pymalloc_list free(0x7fb8df500120)

    dtrace:::END
    Python malloc byte distributions by engine caller:
       python`_PyObject_Realloc, total bytes = 608
               value  ------------- Distribution ------------- count
                 256 |                                         0
                 512 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ 1
                1024 |                                         0

       python`_PyObject_Malloc, total bytes = 9264
               value  ------------- Distribution ------------- count
                2048 |                                         0
                4096 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ 2
                8192 |                                         0


    Python malloc byte distributions by Python file and function:

       ex_dtrace.py, create_pymalloc_list, bytes total = 3069
               value  ------------- Distribution ------------- count
                   0 |                                         0
                   1 |@@@@@@@@                                 1
                   2 |                                         0
                   4 |                                         0
                   8 |                                         0
                  16 |                                         0
                  32 |                                         0
                  64 |                                         0
                 128 |                                         0
                 256 |                                         0
                 512 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@         4
                1024 |                                         0


Using ``PyMem_Alloc`` on Small Objects with a Debug Build of Python
-------------------------------------------------------------------------

If you have a debug version of Python that avoids using ``pymalloc`` the DTrace output will record every malloc, however small.
Here we use a very noticeable block size ``block = cMemLeak.PyMalloc(177)``.
Although we are requesting a block of 177 bytes because of the Python build configuration the memory
request is padded with 24 bytes of metadata so we are looking for allocations of 201 bytes.
Here is the output, edited and truncated.

.. code-block:: bash

    $ sudo dtrace -s toolkit/py_flow_malloc_free.d -p 15114 -C
    Password:
    dtrace: system integrity protection is on, some features will not be available

    dtrace:::BEGIN
     15114     ex_dtrace.py:114  -> main malloc(488) pntr 0x7f7fa4125680
     15114     ex_dtrace.py:74   -> create_pymalloc_list malloc(72) pntr 0x7f7fa1e4f5d0
     15114     ex_dtrace.py:74   -> create_pymalloc_list malloc(72) pntr 0x7f7fa1e578b0
     15114     ex_dtrace.py:74   -> create_pymalloc_list free(0x7f7fa1e4f5d0)
     15114     ex_dtrace.py:75   -> create_pymalloc_list malloc(56) pntr 0x7f7fa1e4f670
     15114     ex_dtrace.py:75   -> create_pymalloc_list malloc(201) pntr 0x7f7fa1e54f80
     15114     ex_dtrace.py:76   -> create_pymalloc_list malloc(96) pntr 0x7f7fa1e4f720
     15114     ex_dtrace.py:76   -> create_pymalloc_list malloc(56) pntr 0x7f7fa1d1ba20
     15114     ex_dtrace.py:76   -> create_pymalloc_list malloc(76) pntr 0x7f7fa1d1d0e0
     15114     ex_dtrace.py:76   -> create_pymalloc_list free(0x7f7fa1d1ba20)
     15114     ex_dtrace.py:76   -> create_pymalloc_list free(0x7f7fa1e4f720)
     15114     ex_dtrace.py:76   -> create_pymalloc_list malloc(56) pntr 0x7f7fa1e4f5d0
     15114     ex_dtrace.py:76   -> create_pymalloc_list malloc(96) pntr 0x7f7fa1e4f720
     15114     ex_dtrace.py:76   -> create_pymalloc_list malloc(85) pntr 0x7f7fa1e57c30
     15114     ex_dtrace.py:76   -> create_pymalloc_list free(0x7f7fa1e4f720)
     15114     ex_dtrace.py:76   -> create_pymalloc_list free(0x7f7fa1e4f5d0)
     15114     ex_dtrace.py:76   -> create_pymalloc_list malloc(120) pntr 0x7f7fa42aea90
     15114     ex_dtrace.py:76   -> create_pymalloc_list free(0x7f7fa1e57c30)
     15114     ex_dtrace.py:76   -> create_pymalloc_list free(0x7f7fa1d1d0e0)
     15114     ex_dtrace.py:76   -> create_pymalloc_list malloc(96) pntr 0x7f7fa1cc22d0
     15114     ex_dtrace.py:76   -> create_pymalloc_list free(0x7f7fa1cc22d0)
     15114     ex_dtrace.py:76   -> create_pymalloc_list malloc(96) pntr 0x7f7fa1cc22d0
     15114     ex_dtrace.py:76   -> create_pymalloc_list malloc(105) pntr 0x7f7fa42aeb10
     15114     ex_dtrace.py:76   -> create_pymalloc_list free(0x7f7fa428de20)
     15114     ex_dtrace.py:76   -> create_pymalloc_list free(0x7f7fa42aeb10)
     15114     ex_dtrace.py:76   -> create_pymalloc_list malloc(152) pntr 0x7f7fa429d240
     15114     ex_dtrace.py:76   -> create_pymalloc_list malloc(208) pntr 0x7f7fa42b0060
     15114     ex_dtrace.py:76   -> create_pymalloc_list free(0x7f7fa429d240)
     15114     ex_dtrace.py:76   -> create_pymalloc_list free(0x7f7fa42b0060)
     15114     ex_dtrace.py:76   -> create_pymalloc_list free(0x7f7fa1cc22d0)
     15114     ex_dtrace.py:76   -> create_pymalloc_list free(0x7f7fa42aea90)
     15114     ex_dtrace.py:77   -> create_pymalloc_list malloc(56) pntr 0x7f7fa429a590
     15114     ex_dtrace.py:75   -> create_pymalloc_list malloc(56) pntr 0x7f7fa428e120
     15114     ex_dtrace.py:75   -> create_pymalloc_list malloc(201) pntr 0x7f7fa429d240
     ...
     15114     ex_dtrace.py:81   -> create_pymalloc_list free(0x7f7fa4123c80)
     15114     ex_dtrace.py:81   -> create_pymalloc_list free(0x7f7fa41209c0)
     15114     ex_dtrace.py:81   -> create_pymalloc_list free(0x7f7fa4116bd0)
     15114     ex_dtrace.py:81   -> create_pymalloc_list free(0x7f7fa4120b30)
     15114     ex_dtrace.py:80   -> create_pymalloc_list free(0x7f7fa4125870)
     15114     ex_dtrace.py:80   -> create_pymalloc_list free(0x7f7fa4120750)
     15114     ex_dtrace.py:81   -> create_pymalloc_list malloc(96) pntr 0x7f7fa4116bd0
     15114     ex_dtrace.py:81   -> create_pymalloc_list malloc(56) pntr 0x7f7fa4120750
     15114     ex_dtrace.py:81   -> create_pymalloc_list malloc(76) pntr 0x7f7fa41220b0
     15114     ex_dtrace.py:81   -> create_pymalloc_list free(0x7f7fa4120750)
     15114     ex_dtrace.py:81   -> create_pymalloc_list free(0x7f7fa4116bd0)
     15114     ex_dtrace.py:81   -> create_pymalloc_list malloc(56) pntr 0x7f7fa4120750
     15114     ex_dtrace.py:81   -> create_pymalloc_list malloc(96) pntr 0x7f7fa4116bd0
     15114     ex_dtrace.py:81   -> create_pymalloc_list malloc(85) pntr 0x7f7fa4120b30
     15114     ex_dtrace.py:81   -> create_pymalloc_list free(0x7f7fa4116bd0)
     15114     ex_dtrace.py:81   -> create_pymalloc_list free(0x7f7fa4120750)
     15114     ex_dtrace.py:81   -> create_pymalloc_list malloc(118) pntr 0x7f7fa4123c80
     15114     ex_dtrace.py:81   -> create_pymalloc_list free(0x7f7fa4120b30)
     15114     ex_dtrace.py:81   -> create_pymalloc_list free(0x7f7fa41220b0)
     15114     ex_dtrace.py:81   -> create_pymalloc_list malloc(96) pntr 0x7f7fa4116bd0
     15114     ex_dtrace.py:81   -> create_pymalloc_list free(0x7f7fa4116bd0)
     15114     ex_dtrace.py:81   -> create_pymalloc_list malloc(96) pntr 0x7f7fa4116bd0
     15114     ex_dtrace.py:81   -> create_pymalloc_list malloc(103) pntr 0x7f7fa41220b0
     15114     ex_dtrace.py:81   -> create_pymalloc_list free(0x7f7fa411f540)
     15114     ex_dtrace.py:81   -> create_pymalloc_list free(0x7f7fa41220b0)
     15114     ex_dtrace.py:81   -> create_pymalloc_list malloc(152) pntr 0x7f7fa4120b30
     15114     ex_dtrace.py:81   -> create_pymalloc_list malloc(208) pntr 0x7f7fa4125870
     15114     ex_dtrace.py:81   -> create_pymalloc_list free(0x7f7fa4120b30)
     15114     ex_dtrace.py:81   -> create_pymalloc_list free(0x7f7fa4125870)
     15114     ex_dtrace.py:81   -> create_pymalloc_list free(0x7f7fa4116bd0)
     15114     ex_dtrace.py:81   -> create_pymalloc_list free(0x7f7fa4123c80)
     15114     ex_dtrace.py:82   -> create_pymalloc_list free(0x7f7fa429a590)
     15114     threading.py:1406 -> _shutdown malloc(488) pntr 0x7f7fa42b0060
     15114     threading.py:985  -> _stop malloc(96) pntr 0x7f7fa42affa0
     15114     threading.py:985  -> _stop malloc(96) pntr 0x7f7fa1cc22d0
     15114     threading.py:985  -> _stop free(0x7f7fa42affa0)
     15114     threading.py:986  -> _stop free(0x7f7fa1cc22d0)
     15114     threading.py:1410 -> _shutdown malloc(96) pntr 0x7f7fa1cc22d0
     15114     threading.py:1410 -> _shutdown malloc(72) pntr 0x7f7fa1cbc970
     15114     threading.py:1410 -> _shutdown free(0x7f7fa1cc22d0)
     15114     threading.py:1410 -> _shutdown free(0x7f7fa1cbc970)
     15114     threading.py:1415 -> _shutdown malloc(96) pntr 0x7f7fa1cc22d0
     15114     threading.py:1415 -> _shutdown malloc(96) pntr 0x7f7fa42affa0
     15114     threading.py:1415 -> _shutdown free(0x7f7fa1cc22d0)
     15114     threading.py:1416 -> _shutdown malloc(80) pntr 0x7f7fa1cbc970
     15114     threading.py:1416 -> _shutdown malloc(88) pntr 0x7f7fa1cc22d0
     15114     threading.py:1416 -> _shutdown free(0x7f7fa1cc22d0)
     15114     threading.py:1417 -> _shutdown free(0x7f7fa42affa0)
     15114      __init__.py:2121 -> shutdown malloc(40) pntr 0x7f7fa428de20
     15114      __init__.py:2121 -> shutdown malloc(96) pntr 0x7f7fa42affa0
     15114      __init__.py:2121 -> shutdown malloc(72) pntr 0x7f7fa1cc22d0
     15114      __init__.py:2121 -> shutdown free(0x7f7fa42affa0)
     15114      __init__.py:1062 -> flush malloc(96) pntr 0x7f7fa42affa0
     15114      __init__.py:1062 -> flush free(0x7f7fa42affa0)
     15114      __init__.py:2130 -> shutdown malloc(472) pntr 0x7f7fa42b0530
     15114      __init__.py:1062 -> flush malloc(424) pntr 0x7f7fa42b0710
     15114      __init__.py:2121 -> shutdown free(0x7f7fa428de20)
     15114      __init__.py:2121 -> shutdown free(0x7f7fa1cc22d0)

    dtrace:::END
    Python malloc byte distributions by engine caller:
       python`_PyMem_RawMalloc, total bytes = 33041
               value  ------------- Distribution ------------- count
                   8 |                                         0
                  16 |                                         2
                  32 |@@@@@@@@@@@@@@@@@@@@@@                   174
                  64 |@@@@@@@@@@@@@@@@@                        133
                 128 |                                         2
                 256 |                                         3
                 512 |                                         1
                1024 |                                         0
                2048 |                                         0
                4096 |                                         2
                8192 |                                         0


    Python malloc byte distributions by Python file and function:

       threading.py, _stop, bytes total = 192
               value  ------------- Distribution ------------- count
                  32 |                                         0
                  64 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ 2
                 128 |                                         0

       ex_dtrace.py, main, bytes total = 488
               value  ------------- Distribution ------------- count
                 128 |                                         0
                 256 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ 1
                 512 |                                         0

       __init__.py, flush, bytes total = 520
               value  ------------- Distribution ------------- count
                  32 |                                         0
                  64 |@@@@@@@@@@@@@@@@@@@@                     1
                 128 |                                         0
                 256 |@@@@@@@@@@@@@@@@@@@@                     1
                 512 |                                         0

       __init__.py, shutdown, bytes total = 680
               value  ------------- Distribution ------------- count
                  16 |                                         0
                  32 |@@@@@@@@@@                               1
                  64 |@@@@@@@@@@@@@@@@@@@@                     2
                 128 |                                         0
                 256 |@@@@@@@@@@                               1
                 512 |                                         0

       threading.py, _shutdown, bytes total = 1016
               value  ------------- Distribution ------------- count
                  32 |                                         0
                  64 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@       6
                 128 |                                         0
                 256 |@@@@@@                                   1
                 512 |                                         0

       ex_dtrace.py, create_pymalloc_list, bytes total = 11148
               value  ------------- Distribution ------------- count
                  16 |                                         0
                  32 |@@@@@@@@                                 21
                  64 |@@@@@@@@@@@@@@@@@@@@@@@@@                66
                 128 |@@@@@@@                                  20
                 256 |                                         0



DTrace and Python's Object Allocator
-----------------------------------------

There are two scripts provided for tracing Python's Object Allocator depending on whether you are using a debug build of
Python (``--without-pymalloc``) or a release version of Python.

.. list-table:: **DTrace and Python's Object Allocator**
   :widths: 10 10 30 30 30
   :header-rows: 1

   * - Python
     - With ``pymalloc``?
     - Compiled With
     - Memory Functions in ``Objects/obmalloc.c``
     - D Script for Tracing
   * - Debug
     - No
     - ``#undef WITH_PYMALLOC``
     - ``_PyMem_RawMalloc``, ``_PyMem_RawCalloc``, ``_PyMem_RawRealloc``, ``_PyMem_RawFree``
     - ``toolkit/py_object_U_WITH_PYMALLOC.d``
   * - Release
     - Yes
     - ``#define WITH_PYMALLOC``
     - ``_PyObject_Malloc``, ``_PyObject_Calloc``, ``_PyObject_Realloc``, ``_PyObject_Free``
     - ``toolkit/py_object_D_WITH_PYMALLOC.d``

Both of these D scripts have these options:

.. list-table:: **Options for toolkit/py_object_?_WITH_PYMALLOC.d D Scripts**
   :widths: 30 70
   :header-rows: 1

   * - Option
     - Description
   * - ``-D FULL_FILE_PATH``
     - Include the full path in Python filenames.
   * - ``-D PYTHON_CALL_STACK``
     - Include Python callstack when entering and exiting Python functions.

Given this Python code that appends four bytes objects to a list:

.. code-block:: python

    def create_py_array_list(size: int):
        l = []
        for i in range(4):
            block = b' ' * size
            print(f'Created {type(block)} size={len(block):d} buffer=0x{id(block):x}')
            l.append(block)
        while len(l):
            # Remove in reverse order
            block = l.pop(0)
            print(f'Pop\'d {type(block)} size={len(block):d} buffer=0x{id(block):x}')
        l.clear()

    def main():
        with_dtrace = sysconfig.get_config_var('WITH_DTRACE')
        if with_dtrace is None or with_dtrace != 1:
            raise RuntimeError(f'Python at {sys.executable} must be build with DTrace support.')
        print('Python at %s is configured with CONFIG_ARGS: %s', sys.executable, sysconfig.get_config_var('CONFIG_ARGS'))
        input(f'Waiting to start tracing PID: {os.getpid()} (<cr> to continue):')
        create_py_array_list(27)
        return 0


    if __name__ == '__main__':
        sys.exit(main())

Debug Example
^^^^^^^^^^^^^^^^^^^^^^^^^

With a debug, DTrace aware version of Python this typically produces this output:

.. code-block:: bash

    $ python pymemtrace/examples/ex_dtrace.py
    Python at pyenvs/pymemtrace_Dtrace_3.9D_A/bin/python is configured with CONFIG_ARGS: '--with-pydebug' '--without-pymalloc' '--with-valgrind' '--with-dtrace' '--with-openssl=/usr/local/opt/openssl@1.1'
    Waiting to start tracing PID: 30273 (<cr> to continue):
    Created <class 'bytes'> size=27 buffer=0x7f859ee67cf0
    Created <class 'bytes'> size=27 buffer=0x7f859ee68300
    Created <class 'bytes'> size=27 buffer=0x7f859ee67d50
    Created <class 'bytes'> size=27 buffer=0x7f859ee681c0
    Pop'd <class 'bytes'> size=27 buffer=0x7f859ee67cf0
    Pop'd <class 'bytes'> size=27 buffer=0x7f859ee68300
    Pop'd <class 'bytes'> size=27 buffer=0x7f859ee67d50
    Pop'd <class 'bytes'> size=27 buffer=0x7f859ee681c0

Monitoring that with DTrace typically gives:

.. code-block:: bash

    $ sudo dtrace -C -s toolkit/py_object_U_WITH_PYMALLOC.d -p 30273
    dtrace: system integrity protection is on, some features will not be available

    dtrace:::BEGIN
     30273     ex_dtrace.py:115  -> main _PyMem_RawMalloc(512) _PyMem_RawMalloc returns 0x7f859ee684b0
     30273     ex_dtrace.py:87   -> create_py_array_list _PyMem_RawMalloc(72) _PyMem_RawMalloc returns 0x7f859ee676e0
     30273     ex_dtrace.py:87   -> create_py_array_list _PyMem_RawMalloc(72) _PyMem_RawMalloc returns 0x7f859ee67730
     30273     ex_dtrace.py:87   -> create_py_array_list _PyMem_RawFree(0x7f859ee676e0)
     30273     ex_dtrace.py:88   -> create_py_array_list _PyMem_RawMalloc(84) _PyMem_RawMalloc returns 0x7f859ee67ce0
     30273     ex_dtrace.py:89   -> create_py_array_list _PyMem_RawMalloc(96) _PyMem_RawMalloc returns 0x7f859ee67d40
     30273     ex_dtrace.py:89   -> create_py_array_list _PyMem_RawMalloc(78) _PyMem_RawMalloc returns 0x7f859ee676e0
     30273     ex_dtrace.py:89   -> create_py_array_list _PyMem_RawMalloc(185) _PyMem_RawMalloc returns 0x7f859ee681b0
     30273     ex_dtrace.py:89   -> create_py_array_list _PyMem_RawMalloc(78) _PyMem_RawMalloc returns 0x7f859ee68270
     30273     ex_dtrace.py:89   -> create_py_array_list _PyMem_RawFree(0x7f859ee68270)
     30273     ex_dtrace.py:89   -> create_py_array_list _PyMem_RawRealloc(0x7f859ee681b0, 88) _PyMem_RawRealloc returns 0x7f859ee681b0
     30273     ex_dtrace.py:89   -> create_py_array_list _PyMem_RawFree(0x7f859ee676e0)
     30273     ex_dtrace.py:89   -> create_py_array_list _PyMem_RawFree(0x7f859ee67d40)
    ...
     30273     ex_dtrace.py:95   -> create_py_array_list _PyMem_RawFree(0x7f859ee16750)
     30273     threading.py:1406 -> _shutdown _PyMem_RawMalloc(488) _PyMem_RawMalloc returns 0x7f85a111d5c0
     30273     threading.py:985  -> _stop _PyMem_RawMalloc(96) _PyMem_RawMalloc returns 0x7f859ed9ada0
     30273     threading.py:985  -> _stop _PyMem_RawMalloc(96) _PyMem_RawMalloc returns 0x7f859ed7d8b0
     30273     threading.py:985  -> _stop _PyMem_RawFree(0x7f859ed9ada0)
     30273     threading.py:986  -> _stop _PyMem_RawFree(0x7f859ed7d8b0)
     30273     threading.py:1410 -> _shutdown _PyMem_RawMalloc(96) _PyMem_RawMalloc returns 0x7f859ed7d8b0
     30273     threading.py:1410 -> _shutdown _PyMem_RawMalloc(72) _PyMem_RawMalloc returns 0x7f85a11872d0
     30273     threading.py:1410 -> _shutdown _PyMem_RawFree(0x7f859ed7d8b0)
     30273     threading.py:1410 -> _shutdown _PyMem_RawFree(0x7f85a11872d0)
     30273     threading.py:1415 -> _shutdown _PyMem_RawMalloc(96) _PyMem_RawMalloc returns 0x7f859ed7d8b0
     30273     threading.py:1415 -> _shutdown _PyMem_RawMalloc(96) _PyMem_RawMalloc returns 0x7f859ed9ada0
     30273     threading.py:1415 -> _shutdown _PyMem_RawFree(0x7f859ed7d8b0)
     30273     threading.py:1416 -> _shutdown _PyMem_RawMalloc(80) _PyMem_RawMalloc returns 0x7f85a11872d0
     30273     threading.py:1416 -> _shutdown _PyMem_RawMalloc(88) _PyMem_RawMalloc returns 0x7f859ed7d8b0
     30273     threading.py:1416 -> _shutdown _PyMem_RawFree(0x7f859ed7d8b0)
     30273     threading.py:1417 -> _shutdown _PyMem_RawFree(0x7f859ed9ada0)
     30273      __init__.py:2121 -> shutdown _PyMem_RawMalloc(40) _PyMem_RawMalloc returns 0x7f85a112b5f0
     30273      __init__.py:2121 -> shutdown _PyMem_RawMalloc(96) _PyMem_RawMalloc returns 0x7f859ed9ada0
     30273      __init__.py:2121 -> shutdown _PyMem_RawMalloc(72) _PyMem_RawMalloc returns 0x7f859ed8cf50
     30273      __init__.py:2121 -> shutdown _PyMem_RawFree(0x7f859ed9ada0)
     30273      __init__.py:1062 -> flush _PyMem_RawMalloc(96) _PyMem_RawMalloc returns 0x7f859ed9ada0
     30273      __init__.py:1062 -> flush _PyMem_RawFree(0x7f859ed9ada0)
     30273      __init__.py:2130 -> shutdown _PyMem_RawMalloc(472) _PyMem_RawMalloc returns 0x7f85a111d840
     30273      __init__.py:1062 -> flush _PyMem_RawMalloc(424) _PyMem_RawMalloc returns 0x7f859ef24e50
     30273      __init__.py:2121 -> shutdown _PyMem_RawFree(0x7f85a112b5f0)
     30273      __init__.py:2121 -> shutdown _PyMem_RawFree(0x7f859ed8cf50)

    dtrace:::END

Release Example
^^^^^^^^^^^^^^^^^^^^^^^^^

With a release, DTrace aware version of Python using ``pymalloc`` this typically produces this output:

.. code-block:: bash

    $ python pymemtrace/examples/ex_dtrace.py
    Python at pyenvs/pymemtrace_Dtrace_3.9R_A/bin/python is configured with CONFIG_ARGS: '--with-dtrace' '--with-openssl=/usr/local/opt/openssl@1.1'
    Waiting to start tracing PID: 30620 (<cr> to continue):
    Created <class 'bytes'> size=27 buffer=0x103196c70
    Created <class 'bytes'> size=27 buffer=0x103459270
    Created <class 'bytes'> size=27 buffer=0x1034592b0
    Created <class 'bytes'> size=27 buffer=0x103459fb0
    Pop'd <class 'bytes'> size=27 buffer=0x103196c70
    Pop'd <class 'bytes'> size=27 buffer=0x103459270
    Pop'd <class 'bytes'> size=27 buffer=0x1034592b0
    Pop'd <class 'bytes'> size=27 buffer=0x103459fb0

And DTrace gives:

.. code-block:: bash

    $ sudo dtrace -C -s toolkit/py_object_D_WITH_PYMALLOC.d -p 30620
    dtrace: system integrity protection is on, some features will not be available

    dtrace:::BEGIN
     30620     ex_dtrace.py:115  -> main _PyObject_Malloc(488) _PyObject_Malloc returns 0x1033cebd0
     30620     ex_dtrace.py:87   -> create_py_array_list _PyObject_Malloc(48) _PyObject_Malloc returns 0x103429810
     30620     ex_dtrace.py:87   -> create_py_array_list _PyObject_Malloc(48) _PyObject_Malloc returns 0x103429870
     30620     ex_dtrace.py:87   -> create_py_array_list _PyObject_Free(0x103429810)
     30620     ex_dtrace.py:88   -> create_py_array_list _PyObject_Malloc(60) _PyObject_Malloc returns 0x103196c70
     30620     ex_dtrace.py:89   -> create_py_array_list _PyObject_Malloc(72) _PyObject_Malloc returns 0x103453df0
     30620     ex_dtrace.py:89   -> create_py_array_list _PyObject_Malloc(54) _PyObject_Malloc returns 0x103459f70
     30620     ex_dtrace.py:89   -> create_py_array_list _PyObject_Malloc(161) _PyObject_Malloc returns 0x1034583a0
     30620     ex_dtrace.py:89   -> create_py_array_list _PyObject_Malloc(54) _PyObject_Malloc returns 0x103459270
     30620     ex_dtrace.py:89   -> create_py_array_list _PyObject_Free(0x103459270)
     30620     ex_dtrace.py:89   -> create_py_array_list _PyObject_Realloc(0x1034583a0, 64)
     30620     ex_dtrace.py:89   -> create_py_array_list _PyObject_Free(0x1034583a0)
     30620     ex_dtrace.py:89   -> create_py_array_list _PyObject_Free(0x103459f70)
     30620     ex_dtrace.py:89   -> create_py_array_list _PyObject_Free(0x103453df0)
     30620     ex_dtrace.py:89   -> create_py_array_list _PyObject_Malloc(72) _PyObject_Malloc returns 0x103453df0
     30620     ex_dtrace.py:89   -> create_py_array_list _PyObject_Malloc(32) _PyObject_Malloc returns 0x1033d8b90
     30620     ex_dtrace.py:89   -> create_py_array_list _PyObject_Malloc(51) _PyObject_Malloc returns 0x103459f70
     30620     ex_dtrace.py:89   -> create_py_array_list _PyObject_Free(0x1033d8b90)
     30620     ex_dtrace.py:89   -> create_py_array_list _PyObject_Free(0x103453df0)
     30620     ex_dtrace.py:89   -> create_py_array_list _PyObject_Malloc(32) _PyObject_Malloc returns 0x1033d8b90
     30620     ex_dtrace.py:89   -> create_py_array_list _PyObject_Malloc(72) _PyObject_Malloc returns 0x103453df0
     30620     ex_dtrace.py:89   -> create_py_array_list _PyObject_Malloc(58) _PyObject_Malloc returns 0x1034592b0
     30620     ex_dtrace.py:89   -> create_py_array_list _PyObject_Free(0x103453df0)
     30620     ex_dtrace.py:89   -> create_py_array_list _PyObject_Free(0x1033d8b90)
     30620     ex_dtrace.py:89   -> create_py_array_list _PyObject_Malloc(99) _PyObject_Malloc returns 0x103421dc0
     30620     ex_dtrace.py:89   -> create_py_array_list _PyObject_Free(0x1034592b0)
     30620     ex_dtrace.py:89   -> create_py_array_list _PyObject_Free(0x103459f70)
     30620     ex_dtrace.py:89   -> create_py_array_list _PyObject_Free(0x103459270)
     30620     ex_dtrace.py:89   -> create_py_array_list _PyObject_Malloc(54) _PyObject_Malloc returns 0x103459270
     30620     ex_dtrace.py:89   -> create_py_array_list _PyObject_Free(0x103459270)
     30620     ex_dtrace.py:89   -> create_py_array_list _PyObject_Malloc(72) _PyObject_Malloc returns 0x103453df0
     30620     ex_dtrace.py:89   -> create_py_array_list _PyObject_Free(0x103453df0)
     30620     ex_dtrace.py:89   -> create_py_array_list _PyObject_Malloc(72) _PyObject_Malloc returns 0x103453df0
     30620     ex_dtrace.py:89   -> create_py_array_list _PyObject_Calloc(2, 8) _PyObject_Calloc returns 0x1030be590
     30620     ex_dtrace.py:89   -> create_py_array_list _PyObject_Malloc(84) _PyObject_Malloc returns 0x103432bd0
    ...
     30620     ex_dtrace.py:94   -> create_py_array_list _PyObject_Malloc(128) _PyObject_Malloc returns 0x103407930
     30620     ex_dtrace.py:94   -> create_py_array_list _PyObject_Malloc(184) _PyObject_Malloc returns 0x10331f330
     30620     ex_dtrace.py:94   -> create_py_array_list _PyObject_Free(0x103407930)
     30620     ex_dtrace.py:94   -> create_py_array_list _PyObject_Free(0x10331f330)
     30620     ex_dtrace.py:94   -> create_py_array_list _PyObject_Free(0x103453df0)
     30620     ex_dtrace.py:94   -> create_py_array_list _PyObject_Free(0x103421dc0)
     30620     ex_dtrace.py:95   -> create_py_array_list _PyObject_Free(0x7fcd8af1be10)
     30620     threading.py:1406 -> _shutdown _PyObject_Malloc(464) _PyObject_Malloc returns 0x10345ab10
     30620     threading.py:985  -> _stop _PyObject_Malloc(72) _PyObject_Malloc returns 0x10326e210
     30620     threading.py:985  -> _stop _PyObject_Malloc(72) _PyObject_Malloc returns 0x1033908f0
     30620     threading.py:985  -> _stop _PyObject_Free(0x10326e210)
     30620     threading.py:986  -> _stop _PyObject_Free(0x1033908f0)
     30620     threading.py:1410 -> _shutdown _PyObject_Malloc(72) _PyObject_Malloc returns 0x10326e210
     30620     threading.py:1410 -> _shutdown _PyObject_Malloc(48) _PyObject_Malloc returns 0x10337bae0
     30620     threading.py:1410 -> _shutdown _PyObject_Free(0x10326e210)
     30620     threading.py:1410 -> _shutdown _PyObject_Free(0x10337bae0)
     30620     threading.py:1415 -> _shutdown _PyObject_Malloc(72) _PyObject_Malloc returns 0x10326e210
     30620     threading.py:1415 -> _shutdown _PyObject_Malloc(72) _PyObject_Malloc returns 0x1033908f0
     30620     threading.py:1415 -> _shutdown _PyObject_Free(0x10326e210)
     30620     threading.py:1416 -> _shutdown _PyObject_Malloc(56) _PyObject_Malloc returns 0x10320a2b0
     30620     threading.py:1416 -> _shutdown _PyObject_Malloc(64) _PyObject_Malloc returns 0x1033920b0
     30620     threading.py:1416 -> _shutdown _PyObject_Free(0x1033920b0)
     30620     threading.py:1417 -> _shutdown _PyObject_Free(0x1033908f0)
     30620      __init__.py:2121 -> shutdown _PyObject_Malloc(16) _PyObject_Malloc returns 0x1030be590
     30620      __init__.py:2121 -> shutdown _PyObject_Malloc(72) _PyObject_Malloc returns 0x10326e210
     30620      __init__.py:2121 -> shutdown _PyObject_Malloc(48) _PyObject_Malloc returns 0x10340f120
     30620      __init__.py:2121 -> shutdown _PyObject_Free(0x10326e210)
     30620      __init__.py:1062 -> flush _PyObject_Malloc(72) _PyObject_Malloc returns 0x10326e210
     30620      __init__.py:1062 -> flush _PyObject_Free(0x10326e210)
     30620      __init__.py:2130 -> shutdown _PyObject_Malloc(448) _PyObject_Malloc returns 0x10345c1f0
     30620      __init__.py:1062 -> flush _PyObject_Malloc(400) _PyObject_Malloc returns 0x1033f9990
     30620      __init__.py:2121 -> shutdown _PyObject_Free(0x1030be590)
     30620      __init__.py:2121 -> shutdown _PyObject_Free(0x10340f120)

    dtrace:::END


Further Analysis
---------------------

There is a in-depth analysis of using DTrace on a real world application in a :ref:`tech_notes-dtrace`.
