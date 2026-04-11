History
=======

0.3.2rc0 (TODO)
---------------------

* cPyMemTrace:
    * Much more reliable processing of Reference Tracing events.
    * User filtering of Reference Tracing events to include/exclude specific events.
    * Fix the issue with Reference Tracing where handling type "frame" was causing pytest and
      CPython runtime assert failures.
    * Write profile/trace/reference tracing context switches to the appropriate log file.
    * Add cPyMemTrace.ReferenceTracingSimple as an example. Includes documentation and test code.
    * Add suspend() and resume() methods for Reference Tracing.
    * Document pytest issues with Reference Tracing (now historical information).
* General documentation improvements.
* TODO

0.3.1 (2026-03-23)
---------------------

* pymemtrace:
    * Add decorator for pymemtrace.process.
    * pymemtrace.process can now summarise JSON in the log to stdout.
* cPyMemTrace:
    * Add decorators for Python functions for Profile, Trace and ReferenceTracing.
    * Fix a SIGSEGV when bad keyword arguments were passed to cPyMemTrace.ReferenceTracing.

0.3.0 (2026-03-19)
---------------------

* Add ``process-tree.py`` for logging a process and its children.
* cPyMemTrace:
    * Add Reference Tracing (Python 3.13+) that can record every object allocation or de-allocation.
    * Add an option to log to a specific file.
    * Add an API ``write_message_to_log()`` to inject text into the log file.
    * Better structure of the log file format.
    * Define the log file format.
    * Add debug exploration code with ``debug_cPyMemtrace()``.
    * Fix stacking ``pop()`` issue with trace/profile functions with linked list of ``tTraceFileWrapperLinkedList``.
* Add support for Python 3.14
* Remove support for Python 3.7
* Supported Python versions are: 3.8, 3.9, 3.10, 3.11, 3.12, 3.13, 3.14
* Development Status :: 5 - Production/Stable

0.2.0 (2024-11-17)
---------------------

* cPyMemTrace:
    * Add P/T, stack depth and python version to log file name, example:
      ``"20241107_195847_62264_P_0_PY3.13.0b3.log"``
    * Add stacking of trace/profile functions with linked list of ``tTraceFileWrapperLinkedList``.
    * Add an option to log to a specific file.
    * Add an API ``write_to_log()`` to inject text into the log file.
    * Add an optional message to the log file in ``cPyMemTrace``.
    * Add Python API to get log file being written to by ``cPyMemTrace``.
    * Bug fixes in ``cPyMemTrace.c``
    * Safety fix for file path name lengths.
    * Fix for log files where ``'#'`` was being concatenated.

0.1.7 (2024-09-12)
------------------

* Minor fix for a single test.

0.1.6 (2024-09-11)
------------------

* Add support for Python versions 3.12, 3.13. Now supports Python versions 3.7, 3.8, 3.9, 3.10, 3.11, 3.12, 3.13.

0.1.5 (2023-06-21)
------------------

* Add support for Python versions 3.10, 3.11. Now supports Python versions 3.7, 3.8, 3.9, 3.10, 3.11.

0.1.4 (2022-03-19)
------------------

* Fix Linux build.

0.1.3 (2022-03-17)
------------------

* Fix some tests.

0.1.2 (2022-03-17)
------------------

* Fix source distribution that had missing headers.

0.1.1 (2020-11-17)
------------------

* Add ``cPyMemTrace`` the C level profiler.
* Add DTrace scripts for low level tracing.
* Add ``debug_malloc_stats`` the wrapper around ``sys._debugmallocstats``.
* Add ``process.py`` from the TotalDepth project.
* Add redirect_stdout for ``debug_malloc_stats``.
* Add ``trace_malloc``, a wrapper around the ``tracemalloc`` module.
* Includes extensive documentation and performance measurement.
* First release on PyPI.

0.1.0 (2017-12-04)
------------------

* Initial idea and implementation, never released.
