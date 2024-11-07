=======
History
=======

0.2.0 (TODO: Date)
------------------

* cPyMemTrace:
    * Add an option to log to a specific file.
    * Add an API write_to_log() to inject text into the log file.
    * Add an optional message to the log file in cPyMemTrace.
    * Add Python API to get log file being written to by cPyMemTrace.
    * Bug fixes in cPyMemTrace.c
    * Safety fix for file path name lengths.
    * Fix for log files where '#' was being concatenated.

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

* Add cPyMemTrace the C level profiler.
* Add DTrace scripts for low level tracing.
* Add debug_malloc_stats the wrapper around sys._debugmallocstats.
* Add process from the TotalDepth project.
* Add redirect_stdout for debug_malloc_stats.
* Add trace_malloc, a wrapper around the tracemalloc module.
* Includes extensive documentation and performance measurement.
* First release on PyPI.

0.1.0 (2017-12-04)
------------------

* Initial idea and implementation, never released.
