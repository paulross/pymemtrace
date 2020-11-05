pymemtrace
======================

``pymemtrace`` provides various ways of tracing Python memory usage.


cPyMemTrace
-----------------------------

``cPyMemTrace`` provides a couple of ways of tracing total memory usage for every function call and return.



Summary
=====================

+-----------------------+-----------------------+-------------------------------+---------------+---------------+
| Tool                  | Memory Granularity    | Code Granularity              | Memory Cost   | Runtime Cost  |
+=======================+=======================+===============================+===============+===============+
| ``cPyMemTrace``       | RSS                   | Per line or function call     | 0             | x10 to x22    |
+-----------------------+-----------------------+-------------------------------+---------------+---------------+

















The OS's View of Memory
----------------------------------

``pymemtrace`` asks the OS for its opinion of memory usage at each function entry and exit point.
For this to be acurate Python's memory pool system (the Python Object Allocator) must be disabled and this needs a special build of Python with ``--without-pymalloc`` set::

    ../configure --with-pydebug --without-pymalloc
    make

This version of Python runs about 2x to 4x slower without the Python object allocator and this makes ``pymemtrace`` even slower.

Mitigation: Run with the object allocator and accept the inaccuracy. This is probably not that important if we are looking for big memory moves.

The Memory cost of ``pymemtrace``
---------------------------------------------

``pymemtrace`` captures all the data from function call and return points and this can be expensive in a long running process.

Mitigation: Streaming.

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


Features
--------

* TODO

Credits
---------

Phil Smith (AHL) with whom a casual lunch time chat lead to the creation of an earlier, but quite different implemention, of the same idea.

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage

