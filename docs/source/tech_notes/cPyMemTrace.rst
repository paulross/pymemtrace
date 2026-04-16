
.. _tech_notes-cpymemtrace:

Technical Note on ``cPyMemTrace`` Performance
=============================================

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

Platform was a Mac Book Pro (late 2018) 2.7 GHz Intel Core i7 running macOS Ventura 13.5.

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

In this exercise there were 4.4m profiling events.
When ``d_rss_trigger=-1`` then only events that change the RSS by >= the page size (4096 bytes) are reported.
When ``d_rss_trigger=0`` then all events are reported.

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
     - ``d_rss_trigger=-1``
   * - Profile, all events
     - 32.4
     - 42x
     - 831M
     - 4,428,053
     - ``d_rss_trigger=0``

As expected reporting every event is about four times as expensive (in time) compared to those events
that trigger large changes in the RSS.

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

In this exercise there were 7m profiling events.
When ``d_rss_trigger=-1`` then only events that change the RSS by >= the page size (4096 bytes) are reported.
When ``d_rss_trigger=0`` then all events are reported.

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
     - ``d_rss_trigger=-1``
   * - Trace, all
     - 47.6
     - 62x
     - 1.3G
     - 7,044,826
     - ``d_rss_trigger=0``

This is similar to Profiling but the event count is much larger and that shows up in the runtime cost.

Reference Tracing
-----------------

The :py:class:`pymemtrace.cPyMemTrace.ReferenceTracing` class that logs every allocation and de-allocation.
The log file format is different to the Profile/Traace file format.
See :ref:`tech_notes-cpymemtrace_log_file` for the details.
``pymemtrace`` provides a decorator :py:func:`pymemtrace.cpymemtrace_decs.reference_tracing` that will
profile a function.

Here are the code examples, firstly reference tracing all except the builtin types (``int``, ``str`` etc.).
This is the default:

.. code-block::  python

    @cpymemtrace_decs.reference_tracing(
        message="LASToHTML Reference Tracing include_builtins=False",
        include_builtins=False,
    )
    def process_arguments(args, log_level):
        # Execution code here.
        pass

Then reference tracing *including* all the Python builtins:

.. code-block::  python

    @cpymemtrace_decs.reference_tracing(
        message="LASToHTML Reference Tracing include_builtins=True",
        include_builtins=True,
    )
    def process_arguments(args, log_level):
        # Execution code here.
        pass

Finally reference tracing but only reporting on a specific type and no builtin types:

.. code-block::  python

    @cpymemtrace_decs.reference_tracing(
        message=(
            "LASToHTML Reference Tracing include_builtins=False"
            " include_tp_names=['LASSection',]"
        ),
        include_builtins=False,
        include_tp_names=['LASSection',],
    )
    def process_arguments(args, log_level):
        # Execution code here.
        pass

Here are the results compared to the baseline of no tracing:

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

Reference tracing is extremely invasive as it records *every* Python object allocation and de-allocation.
Including builtins can double the executions times compared to ignoring them.

Reference tracing a single type is remarkably effective and efficient.
