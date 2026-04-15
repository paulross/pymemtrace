
.. _tech_notes-cpymemtrace:

Technical Note on ``cPyMemTrace``
======================================

``cPyMemTrace`` contains Python profilers and tracers written in 'C' that logs the
runtime information including the `Resident Set Size <https://en.wikipedia.org/wiki/Resident_set_size>`_
for every Python and C call and return or object allocation and de-allocation as required.

.. _tech_notes-cpymemtrace_test_data:

Test Program and Data
------------------------------

This tests the performance of ``cPyMenTrace`` with a real world program.
The program reads remote sensing structured text files containing static data and dynamic arrays of floating point data
and summarised them as HTML pages.
The input was 3 files totalling 1.3Mb.
The largest file was 27,330,513 bytes, smallest 4,609 bytes.
The output was 111 HTML files and indexes totaling 7.2Mb
Platform was a Mac Book Pro (late 2018) 2.7 GHz Intel Core i7 running Mac OS Ventura 13.5.

The command used was:

.. code-block::  shell

    time tdlastohtml --log-process=0.25  example_data/LAS/data tmp/LASTOHTML_A

Profiling
---------------------------------------

The :py:class:`pymemtrace.cPyMemTrace.Profile` class that logs Python and C code.
This ignores Python line, opcode and exception events.
``pymemtrace`` provides a decorator :py:func:`pymemtrace.cpymemtrace_decs.profile` that will profile a function.
For example:

.. code-block::  python

    from pymemtrace import cpymemtrace_decs

    @cpymemtrace_decs.profile(
        message="LASToHTML Profile d_rss_trigger=0",
        d_rss_trigger=0,
    )
    def process_arguments(args, log_level):
        # Execution code here.
        pass



.. list-table:: **cPyMemTrace Profiling**
   :widths: 30 15 15 15 15 50
   :header-rows: 1

   * - Setup
     - Time (s)
     - Time Rel.
     - Log Size
     - Log Lines
     - Notes
   * - No Profiling
     - 0.765
     - 1x
     - 0
     - 0
     - Baseline execution.
   * - Profile
     - 6.81
     - 8.9x
     - 399K
     - 2,095
     - ``d_rss_trigger=-1`` 4.4m events handled.
   * - Profile, all events
     - 32.4
     - 42x
     - 831M
     - 4,428,053
     - ``d_rss_trigger=0`` 4.4m events handled.

Tracing
--------

The :py:class:`pymemtrace.cPyMemTrace.Trace` class that logs pure Python code,
it ignores C call, and return events.
``pymemtrace`` provides a decorator :py:func:`pymemtrace.cpymemtrace_decs.trace` that will profile a function.
For example:

.. code-block::  python

    from pymemtrace import cpymemtrace_decs

    @cpymemtrace_decs.trace(
        message="LASToHTML Trace d_rss_trigger=0",
        d_rss_trigger=0,
    )
    def process_arguments(args, log_level):
        # Execution code here.
        pass



.. list-table:: **cPyMemTrace Tracing**
   :widths: 30 15 15 15 15 50
   :header-rows: 1

   * - Setup
     - Time (s)
     - Time Rel.
     - Log Size
     - Log Lines
     - Notes
   * - No Tracing
     - 0.765
     - 1x
     - 0
     - 0
     - Baseline execution.
   * - Trace
     - 13.0
     - 17x
     - 443K
     - 2,326
     - ``d_rss_trigger=-1`` 7m events handled.
   * - Trace, all
     - 47.6
     - 62x
     - 1.3G
     - 7,044,826
     - ``d_rss_trigger=0`` 7m events handled.


Reference Tracing
-----------------

The :py:class:`pymemtrace.cPyMemTrace.Trace` class that logs pure Python code,
it ignores C call, and return events.
``pymemtrace`` provides a decorator :py:func:`pymemtrace.cpymemtrace_decs.trace` that will profile a function.
For example:


.. code-block::  python

    @cpymemtrace_decs.reference_tracing(
        message="LASToHTML Reference Tracing include_builtins=False include_tp_names=['LASSection',]",
        include_builtins=False,
        include_tp_names=['LASSection',],
    )
    def process_arguments(args, log_level):
        # Execution code here.
        pass




.. list-table:: **cPyMemTrace Reference Tracing**
   :widths: 30 15 15 15 15 50
   :header-rows: 1

   * - Setup
     - Time (s)
     - Time Rel.
     - Log Size
     - Log Lines
     - Notes
   * - No Tracing
     - 0.765
     - 1x
     - 0
     - 0
     - Baseline execution.
   * - Ref Trace, no builtins
     - 27.3
     - 36x
     - 170M
     - 716,222
     - ``include_builtins=False``
   * - Ref Trace, with builtins
     - 59.9
     - 78x
     - 1.0G
     - 4,375,211
     - ``include_builtins=True``
   * - Ref Trace, single class
     - 2.02
     - 2.6x
     - 2K
     - 16
     - ``include_builtins=False,`` ``include_tp_names=['LASSection',]``

