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


Tool Characteristics
======================

+---------------------------+-----------------------+-------------------------------+-----------------------+---------------+
| Tool                      | Memory Granularity    | Code Granularity              | Memory Cost           | Runtime Cost  |
+===========================+=======================+===============================+=======================+===============+
| ``process``               | RSS (total Python     | Regular time intervals.       | Near zero             | Near zero     |
|                           | and C Memory)         |                               |                       |               |
+---------------------------+-----------------------+-------------------------------+-----------------------+---------------+
| ``trace_malloc``          | Every Python object   | Per line or function call     | Significant but       | x5 (?)        |
|                           |                       |                               | compensated.          |               |
+---------------------------+-----------------------+-------------------------------+-----------------------+---------------+
| ``debug_malloc_stats``    | Python memory pool    | Snapshots CPython memory      | Minimal except for    | Near zero     |
|                           |                       | either side of a block of     | Python debug builds.  |               |
|                           |                       | code.                         |                       |               |
+---------------------------+-----------------------+-------------------------------+-----------------------+---------------+
| ``cPyMemTrace``           | RSS (total Python     | Per line or function call     | Near zero.            | x10 to x20    |
|                           | and C Memory)         |                               |                       |               |
+---------------------------+-----------------------+-------------------------------+-----------------------+---------------+
| ``DTrace``                | Every ``malloc()``    | Per function call and return. | Minimal except for    | x90 to x100   |
|                           | and ``free()``        |                               | Python debug builds.  |               |
|                           |                       |                               |                       |               |
+---------------------------+-----------------------+-------------------------------+-----------------------+---------------+


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

