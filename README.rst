*******************
pymemtrace
*******************


``pymemtrace`` provides a number of tools for tracking Python memory usage at different levels, different granularities and at different runtime costs.

Summary of the Tools
======================


Here is a summary of the tools:


+---------------------------+-----------------------+-------------------------------+-----------------------+---------------+
| Tool                      | Memory Granularity    | Code Granularity              | Memory Cost           | Runtime Cost  |
+===========================+=======================+===============================+=======================+===============+
| ``process``               | RSS (total Python     | At regular time intervals.    | Near zero             | Near zero     |
|                           | and C Memory)         |                               | compensated.          |               |
+---------------------------+-----------------------+-------------------------------+-----------------------+---------------+
| ``cPyMemTrace``           | RSS (total Python     | Per line or function call     | Near zero             | x10 to x20    |
|                           | and C Memory)         |                               | compensated.          |               |
+---------------------------+-----------------------+-------------------------------+-----------------------+---------------+
| ``trace_malloc``          | Every Python object   | Per line or function call     | Significant but       | x5 (?)        |
|                           |                       |                               | compensated.          |               |
+---------------------------+-----------------------+-------------------------------+-----------------------+---------------+
| ``debug_malloc_stats``    | Python memory pool    | Snapshot CPython memory       | Minimal except for    | Near zero     |
|                           |                       | either side of a block of     | Python debug builds.  |               |
|                           |                       | code.                         | Python debug builds.  |               |
+---------------------------+-----------------------+-------------------------------+-----------------------+---------------+



``process``
================

``process`` logs the total memory usage at regular time intervals.


``cPyMemTrace``
================

``cPyMemTrace`` is a memory tracer written in C that can report total memory usage for every function call and return for both C and Python sections.



``trace_malloc``
================

``trace_malloc`` is a convenient wrapper around the ``tracemalloc`` module that can report Python memory usage by module and line.


``debug_malloc_stats``
==================================

``debug_malloc_stats`` is a convenient wrapper around the ``sys._debugmallocstats`` module that can report Python memory usage by module and line.



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

