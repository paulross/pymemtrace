
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
   * - Trace/Profile
     - ``'T'`` or ``'P'``
     -
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

.. _tech_notes-cpymemtrace_log_file_format:

Log File Format
---------------

The log file has the following format.
Firstly each line starts with text that describes the row type:

.. list-table:: **cPyMemTrace Logfile Line Types**
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
   * - ``MESG:``
     - A message.
     - This contains the ``Event``, ``dEvent`` and ``Clock`` columns (see table below) followed by the text message.
   * - ``LAST:``
     - The last logged event.
     - Only one of these. See table below for a description of the columns.
   * - ``EOF``
     - None
     - The last line in the log file.

The lines that contain space seperated columns are described here:

.. list-table:: **cPyMemTrace Logfile Line Format**
   :widths: 20 40 50
   :header-rows: 1

   * - Column
     - Format
     - Notes
   * - Row Type
     - None
     - Example ``FRST``, ``MESG`` etc.
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
-------

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
    MESG: 2      +1      3.090208     # Level 0 __enter__
    PREV: 2      +1      3.090208
    NEXT: 9      +8      3.090725     LINE     test_cpymemtrace.py  185 populate_list   42524672  1052672
    PREV: 9      +8      3.090725     LINE     test_cpymemtrace.py  185 populate_list   42524672  1052672
    NEXT: 11     +2      3.091224     LINE     test_cpymemtrace.py  185 populate_list   43577344  1052672
    8<---- Snip ---->8
    MESG: 97     +82     3.092802     # Level 0 after populate_list()
    MESG: 255    +240    3.093373     # Level 0 just prior to level 1 __enter__
    MESG: 256    +241    3.093467     # Level 0 events should be suspended
    8<---- Snip ---->8
    MESG: 256    +241    3.094199     Re-attaching previous trace file wrapper.
    PREV: 256    +241    3.094199
    NEXT: 401    +386    3.094896     LINE     test_cpymemtrace.py  300 test_trace      45686784  4096
    MESG: 579    +178    3.095950     # Level 0 after level 1 exit
    MESG: 674    +273    3.097299     # Level 0 after level 1 exit and populate_list()
    LAST: 675    +274    3.097455     LINE     test_cpymemtrace.py  265 test_trace      45686784  0
    EOF

.. raw:: latex

    \end{landscape}
