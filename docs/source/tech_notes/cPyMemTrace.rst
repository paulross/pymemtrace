Technical Note on cPyMemTrace
======================================

Memory Usage Monitored by ``process.py``
``process.py`` is a RSS monitor from TotalDepth that runs in a seperate thread and reports the RSS at regular intervals.
The cost in runtime and memory is minimal.
The tick time was set to 0.25s for no use of cPyMemTrace and 1.0s when using cPyMenTrace.

No use of ``cPyMemTrace``
--------------------------------------------

Output in ``tmp/LAS/cPyMemTrace/LASToHtml_no_trace/LASToHTML.log`` which took 25.802 s (250.2 ms/Mb), ``process.py``:

.. image:: images/LASToHTML.log_8631.svg
    :alt: Benchmark.
    :width: 700
    :align: center


``cPyMemTrace`` No Events Computed, No Events Logged
-------------------------------------------------------

This was to establish the overhead of calling ``trace_or_profile_function()`` but merely incrementing the event counter.
Nothing is calculated.
Nothing is logged.
Output in `tmp/LAS/cPyMemTrace/LASToHtml_trace_C/LASToHTML.log`.
Time was 29.346 s, x1.137

.. image:: images/LASToHTML.log_9434.svg
    :alt: Benchmark.
    :width: 700
    :align: center



``cPyMemTrace`` RSS Only Computed, No Events Logged
-------------------------------------------------------

This was to establish the overhead of calling `trace_or_profile_function()` as before but also computing just the RSS.
Nothing is logged.
Output in `tmp/LAS/cPyMemTrace/LASToHtml_trace_D/LASToHTML.log`. Time was 241.212 s, x9.349
It is notable that the CPU is averaging around 35%:

.. image:: images/LASToHTML.log_9552.svg
    :alt: Benchmark.
    :width: 700
    :align: center


``cPyMemTrace`` All Events Computed, No Events Logged
-------------------------------------------------------

This was to establish the overhead of calling ``trace_or_profile_function()`` and extracting all the log file data but not actually logging any of it.
Output in ``tmp/LAS/cPyMemTrace/LASToHtml_trace_B/LASToHTML.log``.
Time was 252.640 s, x9.791

.. image:: images/LASToHTML.log_9236.svg
    :alt: Benchmark.
    :width: 700
    :align: center

``cPyMemTrace`` All Events Computed, RSS changes >=4096 bytes Logged
-------------------------------------------------------------------------

This was to establish the overhead of calling ``trace_or_profile_function()`` and extracting all the log file data but only logging them if the RSS changed by >=±4096 bytes (one page).
Output in ``tmp/LAS/cPyMemTrace/LASToHtml_trace_E/LASToHTML.log``.
Time was 246.278 s, x9.545
There were 138,243,077 events.
The log file contained:
Lines: 74,518 (i.e. 1 in 1,855 events)
Words: 670,302
Bytes: 16,393,947

.. image:: images/LASToHTML.log_9685.svg
    :alt: Benchmark.
    :width: 700
    :align: center


``cPyMemTrace`` Event RSS changes >=4096 bytes and Previous Event Logged
-------------------------------------------------------------------------

This was a comprimise of only logging events if the RSS changed by >=±4096 bytes (one page) **plus** the immediatly previous event.
This costs as much as logging every event (as any event can be a previous event) but the log file is much more managble.
Output in ``tmp/LAS/cPyMemTrace/LASToHtml_trace_J/LASToHTML.log``.
Time was 574.448 s, x22.3 Out of 138,243,077 events the log file contained:
Lines: 146,037 (about 1 in 950 of the full log).
Words: 1,604,835
Bytes: 28,341,012

.. image:: images/LASToHTML.log_20328.svg
    :alt: Benchmark.
    :width: 700
    :align: center

It is notable that the CPU is around 50%.


``cPyMemTrace`` Every Event Computed and Logged
-------------------------------------------------------------------------

Output in ``tmp/LAS/cPyMemTrace/LASToHtml_trace_A/LASToHTML.log``.
Time was 576.656 s (5591.3 ms/Mb), x22.349
The log file contained 138,243,335 events.
Lines: 138,243,335
Words: 1,235,888,202
Bytes: 30,413,538,865

.. image:: images/LASToHTML.log_8692.svg
    :alt: Benchmark.
    :width: 700
    :align: center

Summary
==================

Here are the overall times and the event rate for different configurations:

| Trace? | Calculate? | Log?                            | Time (s) | Ratio   | Events Loged   | Actual Events/s |
| ------ | ---------- | ------------------------------- | -------- | ------- | -------------- | --------------- |
| No     | No         | No                              | 25.8     | x1.0    | 0              | 5.4m            |
| Yes    | No         | No                              | 29.4     | x1.14   | 0              | 4.7m            |
| Yes    | RSS        | No                              | 241.2    | x9.35   | 0              | 0.57m           |
| Yes    | All        | No                              | 252.6    | x9.79   | 0              | 0.55m           |
| Yes    | All        | dRSS >= 4096                    | 246.3    | x9.55   | 74,518         | 0.56m           |
| Yes    | All        | dRSS >= 4096 and previous event | 574.5    | x22.3   | 146,037        | 0.24m           |
| Yes    | All        | All                             | 576.6    | x22.3   | 138,243,335    | 0.24m           |


### Cost of Tracing

For the 138,243,335 events (or 74,517 that are >= 4096) the run time can be used to calculate the the cost per event:

| Part of Tracing                    | Runtime cost in µs/event. | Notes.                                  |
| ---------------------------------- | ------------------------- | --------------------------------------- |
| Typical Python code                | 0.1 to 0.2                |                                         |
| Attach and call C a trace function | 0.2                       | This is gratifingly quick.              |
| Calculate RSS                      | 1.5                       | This is quite slow.                     |
| Log an event                       | 2.5                       | Also slow. Formatting (?).              |


It is fairly understandable that the formatting and logging takes a while but it is interesting that computing the RSS is so expensive.


### RSS Cost

For comparison here is the cost of calsulating the RSS with `psutil`:


```import timeit
timeit.repeat('p.memory_info().rss', setup='import psutil; p = psutil.Process()', number=1_000_000, repeat=5)
[9.89, 14.32, 12.00, 14.67, 13.77]
```

So that takes typically 13 µs (range 9.8 to 14.3).

Here is the cost of calculating the RSSwith `cPyMemTrace`:

```
>>> import timeit
>>> timeit.repeat('cPyMemTrace.rss()', setup='import cPyMemTrace', number=1_000_000, repeat=5)
[1.656, 1.649, 1.636, 1.626, 1.646]
```

So 1.64 µs ± 0.015 µs which agrees very closely with our estimate of 1.5 µs above.

And peak RSS:

```
>>> timeit.repeat('cPyMemTrace.rss_peak()', setup='import cPyMemTrace', number=1_000_000, repeat=5)
[0.650, 0.628, 0.638, 0.629, 0.633]
```

So 	0.636 µs ± 0.011 µs.

It looks like this is the best we can do and x8 faster than psutil.

## Conclusion

* The C code is much faster than the previous pymemtrace code.
* A x10 to x22 runtime cost is the best we can do.
* Zero memory cost is great.































Lorem ipsum [#f1]_


To test the performance of `cPyMenTrace` TotalDepth was used to summarise LAS files in HTML.
Source data was the W005862 directory but with MDT directory removed.
There were 82 LAS files totalling 108,145,150 bytes.
The largest file was 27,330,513 bytes, smallest 4,609 bytes.
Platform was a Mac mini (late 2014) 2.8 GHz Intel Core i5 running macOS Mojave 10.14.6.


Baseline Python 3.9 (standard release build):

 .. image:: images/LASToHTML.log_77077.svg
    :alt: Basic Python 3.9 performance.

Execution time is 34.4 seconds and average CPU% is 85.8 so effective time is 29.5 (s).


Python 3.9 (release) with DTrace support

 .. image:: images/LASToHTML.log_76753.svg
    :alt: Python 3.9 (release) with DTrace capability.

Execution time is 48.6 seconds and average CPU% is 72.4 so effective time is 35.2 (s) which is 19.3% above the baseline.





.. rubric:: Footnotes
.. [#f1] Text of the first footnote.
