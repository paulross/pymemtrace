=====
Usage
=====


The OS's View of Memory
----------------------------------

``pymemtrace`` asks the OS for its opinion of memory usage at each function entry and exit point.
For this to be acurate Python's memory pool system (the Python Object Allocator) must be disabled and this needs a special build of Python with ``--without-pymalloc`` set::

    ../configure --with-pydebug --without-pymalloc
    make

This version of Python runs about 2x to 4x slower without the Python object allocator and this makes ``pymemtrace`` even slower.

Mitigation: Run with the object allocator and accept the inaccuracy. This is probably not that important if we are looking for big memory moves.




To use pymemtrace in a project::

    import pymemtrace
