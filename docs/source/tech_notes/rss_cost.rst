.. _tech_notes-rss_cost:

Cost of Calculating RSS
=============================

Obtaining the Resident Set Size is not something that is done very frequently.
Typically, monitoring software runs at a frequency of one second or so more so the cost of obtaining the RSS value is
not significant.
However with memory profiling the RSS is required per function call or per line and the cost of calculating RSS becomes
a bottleneck.
For example see the :ref:`tech_notes-cpymemtrace`.

Here is a comparative look at what that cost is.
The platform is a Mac mini (late 2014) 2.8 GHz Intel Core i5 running macOS Mojave 10.14.6.

Using ``psutil``
-----------------------

Here is the cost of calculating the RSS with ``psutil``:

.. code-block:: python

    >>> import timeit
    >>> timeit.repeat('p.memory_info().rss', setup='import psutil; p = psutil.Process()', number=1_000_000, repeat=5)
    [9.89, 14.32, 12.00, 14.67, 13.77]

So that takes typically 13 µs (range 9.8 to 14.3).

Using ``cPyMemTrace``
-----------------------

``cPyMemTrace`` uses code in ``pymemtrace/src/c/get_rss.c``.
This is accessed from Python in ``cPyMemTrace.c``.
Here is the cost:

.. code-block:: python

    >>> import timeit
    >>> timeit.repeat('cPyMemTrace.rss()', setup='import cPyMemTrace', number=1_000_000, repeat=5)
    [1.656, 1.649, 1.636, 1.626, 1.646]

So 1.64 µs ± 0.015 µs which agrees very closely with our estimate of 1.5 µs from :ref:`tech_notes-cpymemtrace`.

Peak RSS (not available in ``psutil``) is much faster for some reason:

.. code-block:: python

    >>> timeit.repeat('cPyMemTrace.rss_peak()', setup='import cPyMemTrace', number=1_000_000, repeat=5)
    [0.650, 0.628, 0.638, 0.629, 0.633]

So 	0.636 µs ± 0.011 µs.

It looks like this is the best we can do and x8 faster than psutil.

