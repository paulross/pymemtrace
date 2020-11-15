*******************
Introduction
*******************


``pymemtrace`` provides tools for tracking and understanding Python memory usage at different levels, different granularities and at different runtime costs.

Tools
======================

TODO: Links for these.

* ``process`` logs the total memory usage at regular time intervals.
  It can plot this with plotting programs such as gnuplot.
* ``trace_malloc`` is a convenience wrapper around the ``tracemalloc`` module that can report Python memory usage by module and line.
  This can take memory snapshots before and after code blocks.
* ``debug_malloc_stats`` is a wrapper around the ``sys._debugmallocstats`` module that can take snapshots of memory before and after code execution.
  It can then report the Python memory pool usage and Python memory usage by type.
* ``cPyMemTrace`` is a memory tracer written in C that can report total memory usage for every function call/return for both C and Python sections.
* DTrace: There are a number of D scripts that can trace the fundamental ``malloc()`` and ``free()`` system calls.
  See :ref:`examples-dtrace`


Tool Characteristics
======================

Each tool can be characterised by:

- *Memory Granularity*: In how much detail is a memory change is observed.
  An example of *coarse* memory granularity is measuring the
  `Resident Set Size <https://en.wikipedia.org/wiki/Resident_set_size>`_ which is normally in chunks of 4096 bytes.
  An example of *fine* memory granularity is recording every ``malloc()`` and ``free()``.
- *Execution Granularity*: In how much code detail is the memory change observed.
  An example of *coarse* execution granularity is measuring the memory usage every second.
  An example of *fine* execution granularity is recording the memory usage every Python line.
- *Memory Cost*: How much extra memory does the tool need.
- *Execution Cost*: How much is the execution time affected.



.. list-table:: **Tool Characteristics**
   :widths: 15 30 30 30 30
   :header-rows: 1

   * - Tool
     - Memory Granularity
     - Execution Granularity
     - Memory Cost
     - Execution Cost
   * - ``process``
     - RSS (total Python and C memory).
     - Regular time intervals.
     - Near zero.
     - Near zero.
   * - ``trace_malloc``
     - Every Python object.
     - Per Python line, per function call.
     - Significant but compensated.
     - x900 for small objects, x6 for large objects.
   * - ``debug_malloc_stats``
     - Pythom memory pool.
     - Snapshots the CPython memory pool either side of a block of code.
     - Minimal except with Python debug builds.
     - x2000+ for small objects, x12 for large objects.
   * - ``cPyMemTrace``
     - RSS (total Python and C memory).
     - Per Python line, function and per C function call.
     - Near zero.
     - x10 to x20.
   * - DTrace
     - Every ``malloc()`` and ``free()``.
     - Per function call and return.
     - Minimal except with Python debug builds.
     - x90 to x100.

.. Commented out for now:

    .. image:: https://img.shields.io/pypi/v/pymemtrace.svg
            :target: https://pypi.python.org/pypi/pymemtrace
    
    .. image:: https://img.shields.io/travis/paulross/pymemtrace.svg
            :target: https://travis-ci.org/paulross/pymemtrace
    
    .. image:: https://readthedocs.org/projects/pymemtrace/badge/?version=latest
            :target: https://pymemtrace.readthedocs.io/en/latest/?badge=latest
            :alt: Documentation Status
    
    .. image:: https://pyup.io/repos/github/paulross/pymemtrace/shield.svg
         :target: https://pyup.io/repos/github/paulross/pymemtrace/
         :alt: Updates
    

Python memory tracing.

* Free software: MIT license

.. Commented out for now:

    * Documentation: https://pymemtrace.readthedocs.io.

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage

