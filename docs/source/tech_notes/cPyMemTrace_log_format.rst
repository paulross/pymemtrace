
.. _tech_notes-cpymemtrace_log_file:

``cPyMemTrace`` Log File Format
======================================

``cPyMemTrace`` writes to an ASCII log file.
This section describes that log file.
It may be useful for those that want to process these log files.

.. _tech_notes-cpymemtrace_log_file_name:

Log File Name
-------------

The user can specify a log file name, if not the default is a log file with a name of these components combined.
The components are seperated by '_':

.. list-table:: **cPyMemTrace Logfile Name**
   :widths: 25 25 50
   :header-rows: 1

   * - Component
     - Format
     - Notes
   * - Date
     - YYYYMMDD
     -
   * - Time
     - HHMMSS
     -
   * - Ordinal
     - Integer
     - This is used to discriminate between log files that are created at the same second as
       ``struct tm`` does not have fractions of a second.
       Starting from 0 for each PID.
       Not Zero padded.
   * - Process ID
     - Integer
     - Not Zero padded.
   * - Profilere Type
     - ``'O'``, ``'P'`` or ``'T'``
     - These letters refer, respectively, to (object) Reference Tracing, Profiling and Tracing.
   * - Trace Stack Depth
     - Integer
     - Starting from 0.
       Not Zero padded.
   * - Python Version
     - ``'PY'`` + version
     - The version is the C string ``PY_VERSION`` from the CPython API.

The file extension is ``'.log'``

For example ``20260227_122119_14_50260_T_2_PY3.12.1.log``.

See ``create_filename()`` in ``pymemtrace/src/c/pymemtrace_util.c``.

.. _tech_notes-cpymemtrace_profile_trace_log_file_format:

Profile and Trace Log File Format
---------------------------------

The log file from the Profile or Trace object has the following format.

.. list-table:: **cPyMemTrace Profile/Trace Logfile Line Types**
   :widths: 10 30 50
   :header-rows: 1

   * - Row Type
     - Format
     - Notes
   * - Opening message.
     - Optional, user defined.
     - This will appear verbatim if the ``message`` argument is provided to the constructor.
       For example ``with cPyMemTrace.Profile(message="Hello World") as profiler: ...``.
       The message can be any string and will automatically be followed with a newline.
   * - ``SOF``
     - None
     - There will be only one of these at the start of the data.
   * - ``HEDR:``
     - Space seperated list of column titles.
     - Example ``HEDR: Event        dEvent  Clock        What     File ...``.
       Only one of these. This names the columns. See table below for a description of the columns.
   * - ``FRST:``
     - The first logged event.
     - This will (usually) happen immediately after the ``HEDR:`` row.
       Only one of these. See table below for a description of the columns.
   * - ``NEXT:``
     - A new event.
     - See table below for a description of the columns.
   * - ``PREV:``
     - A previous event.
     - If you are skipping events then this precedes the ``NEXT:`` event as a reminder of what that event was.
       See table below for a description of the columns.
   * - ``MSG:``
     - A arbitrary message.
     - This contains the ``Event``, ``dEvent`` and ``Clock`` columns (see table below) followed by the text message.
       The text message will be preceded with a "# " and any newlines in the message **will** be preserved.
   * - ``LAST:``
     - The last logged event.
     - Only one of these. See table below for a description of the columns.
   * - ``EOF``
     - None
     - The last line in the log file.

The lines that contain space seperated columns are described here:

.. list-table:: **cPyMemTrace Profile/Trace Logfile Line Format**
   :widths: 20 40 50
   :header-rows: 1

   * - Column
     - Format
     - Notes
   * - Row Type
     - None
     - Example ``FRST``, ``MSG`` etc.
   * - Event
     - Event number.
     - Integer. Always increasing. May not be monotonic.
   * - dEvent
     - Difference in numerical event number.
     - Prefixed by a ``'+'``. Always positive. Will be ``'+1'`` unless you are skipping events.
   * - Clock
     - Process time in seconds.
     - Floating point.
   * - What
     - Event type.
     - See the table below and ``WHAT_STRINGS`` in ``pymemtrace/src/cpy/cPyMemTrace.c``
   * - File
     - Executing file.
     - With a production Python executable these will be Python paths or, if C code` something like ``<frozen posixpath>``.
   * - Line
     - Line number in the executing file.
     - Integer starting from 1.
   * - Function
     - The executing function name.
     -
   * - RSS
     - RSS in bytes.
     -
   * - dRSS
     - Delta RSS.
     - Compared to the previous event.

The event types that are reported in the log file are:

.. list-table:: **Logfile Event Types**
   :widths: 50 50
   :header-rows: 1

   * - Event
     - Text in the Log
   * - `PyTrace_CALL <https://docs.python.org/3/c-api/profiling.html#c.PyTrace_CALL>`_
     - ``CALL``
   * - `PyTrace_EXCEPTION <https://docs.python.org/3/c-api/profiling.html#c.PyTrace_EXCEPTION>`_
     - ``EXCEPT``
   * - `PyTrace_LINE <https://docs.python.org/3/c-api/profiling.html#c.PyTrace_LINE>`_
     - ``LINE``
   * - `PyTrace_RETURN <https://docs.python.org/3/c-api/profiling.html#c.PyTrace_RETURN>`_
     - ``RETURN``
   * - `PyTrace_C_CALL <https://docs.python.org/3/c-api/profiling.html#c.PyTrace_C_CALL>`_
     - ``C_CALL``
   * - `PyTrace_C_EXCEPTION <https://docs.python.org/3/c-api/profiling.html#c.PyTrace_C_EXCEPTION>`_
     - ``C_EXCEPT``
   * - `PyTrace_C_RETURN <https://docs.python.org/3/c-api/profiling.html#c.PyTrace_C_RETURN>`_
     - ``C_RETURN``
   * - `PyTrace_OPCODE <https://docs.python.org/3/c-api/profiling.html#c.PyTrace_OPCODE>`_
     - ``OPCODE``


Example
^^^^^^^

Here is an example log file (with event skipping), lightly edited:

..

    .. raw:: latex

        [Continued on the next page]

        \pagebreak

.. raw:: latex

    \begin{landscape}

.. code-block:: text

    SOF
    HEDR: Event  dEvent  Clock        What     File                Line Function        RSS       dRSS
    FRST: 0      +0      3.090020     LINE     test_cpymemtrace.py  265 test_trace      41463808  41463808
    NEXT: 1      +1      3.090202     LINE     test_cpymemtrace.py  266 test_trace      41472000  4096
    MSG:  2      +1      3.090208     # Level 0 __enter__
    PREV: 2      +1      3.090208
    NEXT: 9      +8      3.090725     LINE     test_cpymemtrace.py  185 populate_list   42524672  1052672
    PREV: 9      +8      3.090725     LINE     test_cpymemtrace.py  185 populate_list   42524672  1052672
    NEXT: 11     +2      3.091224     LINE     test_cpymemtrace.py  185 populate_list   43577344  1052672
    8<---- Snip ---->8
    MSG:  97     +82     3.092802     # Level 0 after populate_list()
    MSG:  255    +240    3.093373     # Level 0 just prior to level 1 __enter__
    MSG:  256    +241    3.093467     # Level 0 events should be suspended
    8<---- Snip ---->8
    PREV: 256    +241    3.094199
    NEXT: 401    +386    3.094896     LINE     test_cpymemtrace.py  300 test_trace      45686784  4096
    MSG:  579    +178    3.095950     # Level 0 after level 1 exit
    MSG:  674    +273    3.097299     # Level 0 after level 1 exit and populate_list()
    LAST: 675    +274    3.097455     LINE     test_cpymemtrace.py  265 test_trace      45686784  0
    EOF

.. raw:: latex

    \end{landscape}

Stacked Context Managers
^^^^^^^^^^^^^^^^^^^^^^^^

If Profile/Trace context manager objects are stacked then as the context switches an entry in the *previous*
log will be made.

For example with this code:

.. code-block:: python

    assert cPyMemTrace.profile_wrapper_depth() == 0
    with cPyMemTrace.Profile(0, message='test_profile_depth()') as profiler_0:
        assert cPyMemTrace.profile_wrapper_depth() == 1
        with cPyMemTrace.Profile(0, message='test_profile_depth()') as profiler_1:
            assert cPyMemTrace.profile_wrapper_depth() == 2
            with cPyMemTrace.Profile(message='test_profile_depth()') as profiler_2:
                assert cPyMemTrace.profile_wrapper_depth() == 3
            assert cPyMemTrace.profile_wrapper_depth() == 2
        assert cPyMemTrace.profile_wrapper_depth() == 1
    assert cPyMemTrace.profile_wrapper_depth() == 0

Three separate files will be generated:

- ``20260325_121938_21_95352_P_0_PY3.13.2.log`` the outer file.
- ``20260325_121938_22_95352_P_1_PY3.13.2.log`` the middle file.
- ``20260325_121938_23_95352_P_2_PY3.13.2.log`` the inner file.

The outer file, ``20260325_121938_21_95352_P_0_PY3.13.2.log``, will have this content when the context switch
takes place and back:

.. code-block:: text

    MSG:  3  +1  9.869994  # Detaching this profile file wrapper. New file:
    MSG:  3  +1  9.869996  # pymemtrace/20260325_121938_22_95352_P_1_PY3.13.2.log
    MSG:  3  +1  9.870580  # Re-attaching this profile file wrapper.

The middle file, ``20260325_121938_22_95352_P_1_PY3.13.2.log``, will have this content when the context switch
takes place and back:

.. code-block:: text

    MSG:  3  +1  9.870162  # Detaching this profile file wrapper. New file:
    MSG:  3  +1  9.870163  # pymemtrace/20260325_121938_23_95352_P_2_PY3.13.2.log
    MSG:  3  +1  9.870437  # Re-attaching this profile file wrapper.

The inner file has no context switches.

.. _tech_notes-cpymemtrace_reference_tracing_log_file_format:

Reference Tracing Log File Format
---------------------------------

The log file from the Reference Tracing object (Python 3.13+) has the following format.

.. list-table:: **cPyMemTrace Reference Tracing Logfile Line Types**
   :widths: 10 30 50
   :header-rows: 1

   * - Row Type
     - Format
     - Notes
   * - Opening message.
     - Optional, user defined.
     - This will appear verbatim if the ``message`` argument is provided to the constructor.
       For example ``with cPyMemTrace.ReferenceTracing(message="Hello World") as profiler: ...``.
       The message can be any string and will automatically be followed with a newline.
   * - ``SOF``
     - None
     - There will be only one of these at the start of the data.
   * - ``HDR:``
     - Space seperated list of column titles.
     - Example ``HDR:  Clock  Address  RefCnt Type  File  Line Function  RSS  dRSS``.
       Only one of these. This names the columns. See table below for a description of the columns.
   * - ``NEW:``
     - When an object is created.
     -
   * - ``DEL:``
     - When an object is deallocated.
     -
   * - ``MSG:``
     - An arbitrary message.
     - This contains the ``Clock`` column (see table below) followed by the text message.
       The text message will be preceded with a "# " and any newlines in the message *will* be preserved.
   * - ``ERR:``
     - An arbitrary message.
     - This contains the ``Clock`` column (see table below) followed by the text message.
       The error message will be preceded with a "# " and any newlines in the message *will* be preserved.
   * - ``EOF``
     - None
     - The last line in the log file.

The lines that contain space seperated columns are described here:

.. list-table:: **cPyMemTrace Profile/Trace Logfile Line Format**
   :widths: 20 40 50
   :header-rows: 1

   * - Column
     - Format
     - Notes
   * - Row Type
     - None
     - Example ``NEW:``, ``DEL:`` etc.
   * - Clock
     - Process time in seconds.
     - Floating point.
   * - Address
     - Object location.
     - Hexadecimal.
   * - RefCnt
     - Object reference count.
     -
   * - Type
     - The type of the object.
     -
   * - File
     - Executing file.
     - With a production Python executable these will be Python paths or, if C code` something like ``<frozen posixpath>``.
   * - Line
     - Line number in the executing file.
     - Integer starting from 1.
   * - Function
     - The executing function name.
     -
   * - RSS
     - RSS in bytes.
     -
   * - dRSS
     - Delta RSS.
     - Compared to the previous line.

The event types that are reported in the log file are:

.. list-table:: **Logfile Event Types**
   :widths: 50 50
   :header-rows: 1

   * - Event
     - Text in the Log
   * - `PyRefTracer_CREATE <https://docs.python.org/3/c-api/profiling.html#c.PyRefTracer_CREATE>`_
     - ``NEW:``
   * - `PyRefTracer_DESTROY <https://docs.python.org/3/c-api/profiling.html#c.PyRefTracer_DESTROY>`_
     - ``DEL:``


Example
^^^^^^^

Here is an example log file lightly edited:

..

    .. raw:: latex

        [Continued on the next page]

        \pagebreak

.. raw:: latex

    \begin{landscape}

.. code-block:: text

    SOF
    HDR:        Clock          Address RefCnt Type            File                           Line Function       RSS           dRSS
    NEW:     0.764831   0x60000283e9b0      1 list            test_cpymemtrace.py             251 test_function  33738752         0
    NEW:     0.764859   0x600002836db0      1 range           test_cpymemtrace.py             252 test_function  33738752         0
    NEW:     0.764878   0x600001bb3390      1 range_iterator  test_cpymemtrace.py             252 test_function  33738752         0
    DEL:     0.764892   0x600002836db0      0 range           test_cpymemtrace.py             252 test_function  33738752         0
    8<---- Snip ---->8
    NEW:     0.765234   0x7f890a500010      1 bytes           test_cpymemtrace.py             243 create_bytes   33742848         0
    DEL:     0.765293   0x600001bb3510      0 int             test_cpymemtrace.py             253 test_function  33742848         0
    NEW:     0.765362   0x600001bd6290      1 int             Python-3.13.2/Lib/random.py     340 randint        26435584  -7307264
    NEW:     0.765427   0x600001bd5c50      1 int             Python-3.13.2/Lib/random.py     317 randrange      26435584         0
    8<---- Snip ---->8
    NEW:     0.766302   0x7f890a601010      1 bytes           test_cpymemtrace.py             243 create_bytes   27488256   1052672
    DEL:     0.766443   0x600001bd5c50      0 int             test_cpymemtrace.py             253 test_function  27488256         0
    8<---- Snip ---->8
    NEW:     0.768496   0x7f890a803010      1 bytes           test_cpymemtrace.py             243 create_bytes   29593600   1052672
    DEL:     0.768540   0x600001bb7650      0 int             test_cpymemtrace.py             253 test_function  29593600         0
    DEL:     0.768586   0x600001bb3390      0 range_iterator  test_cpymemtrace.py             252 test_function  29593600         0
    DEL:     0.768727   0x7f890a702010      0 bytes           test_cpymemtrace.py             258 test_function  29593600         0
    DEL:     0.768916   0x7f890a601010      0 bytes           test_cpymemtrace.py             258 test_function  29593600         0
    DEL:     0.769104   0x7f890a500010      0 bytes           test_cpymemtrace.py             258 test_function  29593600         0
    NEW:     0.769310   0x600002677500      1 str             test_cpymemtrace.py             259 test_function  29593600         0
    NEW:     0.769354   0x6000024b47a0      1 tuple           test_cpymemtrace.py             250 test_function  29593600         0
    EOF

.. raw:: latex

    \end{landscape}

Stacked Context Managers
^^^^^^^^^^^^^^^^^^^^^^^^

If Reference Tracing context manager objects are stacked then as the context switches an entry in the *previous*
log will be made.

For example with this code:

.. code-block:: python

    assert cPyMemTrace.reference_tracing_wrapper_depth() == 0
    with cPyMemTrace.ReferenceTracing('test_reference_trace_depth(): ref_trace_0') as ref_trace_0:
        assert cPyMemTrace.reference_tracing_wrapper_depth() == 1
        with cPyMemTrace.ReferenceTracing('test_reference_trace_depth(): ref_trace_1') as ref_trace_1:
            assert cPyMemTrace.reference_tracing_wrapper_depth() == 2
            with cPyMemTrace.ReferenceTracing('test_reference_trace_depth(): ref_trace_2') as ref_trace_2:
                assert cPyMemTrace.reference_tracing_wrapper_depth() == 3
            assert cPyMemTrace.reference_tracing_wrapper_depth() == 2
        assert cPyMemTrace.reference_tracing_wrapper_depth() == 1
    assert cPyMemTrace.reference_tracing_wrapper_depth() == 0

Three separate files will be generated:

- ``20260325_121857_8_95352_O_0_PY3.13.2.log`` the outer file for ref_trace_0.
- ``20260325_121858_9_95352_O_1_PY3.13.2.log`` the middle file for ref_trace_1.
- ``20260325_121858_10_95352_O_2_PY3.13.2.log`` the inner file for ref_trace_2.

The outer file, ``20260325_121857_8_95352_O_0_PY3.13.2.log``, will have this content when the context switch
takes place and back.
The second column is the clock:

.. code-block:: text

    MSG:     0.889521 # Detaching this Reference Tracing file wrapper. New file:
    MSG:     0.889528 # pymemtrace/20260325_121858_9_95352_O_1_PY3.13.2.log
    MSG:     0.890656 # Re-attaching this trace file wrapper.

The middle file, ``20260325_121858_9_95352_O_1_PY3.13.2.log``, will have this content when the context switch
takes place and back:

.. code-block:: text

    MSG:     0.890185 # Detaching this Reference Tracing file wrapper. New file:
    MSG:     0.890191 # pymemtrace/20260325_121858_10_95352_O_2_PY3.13.2.log
    MSG:     0.890488 # Re-attaching this trace file wrapper.

The inner file has no context switches.
