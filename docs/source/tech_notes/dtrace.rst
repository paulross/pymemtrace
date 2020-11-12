
.. _tech-note-dtrace:

Technical Note on DTrace
==========================


DTrace was also used on the same code and data that was used to test ``cPyMemTrace``.
See :ref:`tech_notes-cpymemtrace_test_data`.

Lorem ipsum [#]_


Baseline Python 3.9
---------------------------

This is using a standard build of Python 3.9 without DTrace support. It establishes a benchmark baseline:

 .. image:: images/LASToHTML.log_77077.svg
    :alt: Basic Python 3.9 (release) performance.

Processed 82 files and 108,145,150 bytes in 34.368 s, 333.2 ms/Mb
Bye, bye!
real        35.49
user        29.72
sys          2.03

Execution time is 34.4 seconds and average CPU% is 85.8 so effective time is 29.5 (s).


Python 3.9 Release with DTrace support, no Tracing
---------------------------------------------------------



 .. image:: images/LASToHTML.log_76753.svg
    :alt: Python 3.9 (release) with DTrace capability.

Execution time is 48.6 seconds and average CPU% is 72.4 so effective time is 35.2 (s) which is x1.19 baseline.
Processed 82 files and 108,145,150 bytes in 48.572 s, 471.0 ms/Mb
Bye, bye!
real        49.54
user        35.56
sys          2.45



Python 3.9 Release with DTrace support, DTrace Tracing
---------------------------------------------------------

Python 3.9 (release) with DTrace support and DTrace running

 .. image:: images/LASToHTML.log_77633.svg
    :alt: Python 3.9 (release) with DTrace capability, DTrace runnning.

Processed 82 files and 108,145,150 bytes in 3134.957 s, 30396.6 ms/Mb
Bye, bye!
real      3220.38
user       902.51
sys       1949.83

TODO: Execution time is 3135 (s) and average CPU% is 28.0 so effective time is 877 (s) which is 19.3% above the baseline.




DTrace log

Has garbage in it.

Need:

``grep -o "[[:print:][:space:]]*" dtrace.log | grep malloc``

Lines:

Total 243,285
malloc 94,882
free 144,684 of wich 74,254 were ``free(0x0)``
Garbage 3719

$ grep -o "[[:print:][:space:]]*" dtrace.log | grep free\(0x0\) | wc -l
   74254





Python 3.9 Debug with DTrace support, no Tracing
---------------------------------------------------------


 .. image:: images/LASToHTML.log_3938.svg
    :alt: Python 3.9 (debug) with DTrace capability, DTrace not tracing.



$ tail -n20 tmp/LAS/cPyMemTrace/LASToHtml_trace_DTraceD_B/LASToHTML.log
2020-11-12 10:20:45,377 - gnuplot.py       -  118 -  3938 - (MainThread) - INFO     - gnuplot stdout: None
Processed 82 files and 108,145,150 bytes in 146.183 s, 1417.4 ms/Mb
Bye, bye!
real       148.55
user       139.99
sys          1.93

(TotalDepth3.9_develop)
paulross@Pauls-Mac-mini  ~/PycharmProjects/TotalDepth (develop)
$ tdprocess tmp/LAS/cPyMemTrace/LASToHtml_trace_DTraceD_B/LASToHTML.log tmp/LAS/cPyMemTrace/LASToHtml_trace_DTraceD_B/gnuplot/
2020-11-12 11:32:27,943 - process.py -  5108 - (MainThread) - INFO     - Extracting data from a log at tmp/LAS/cPyMemTrace/LASToHtml_trace_DTraceD_B/LASToHTML.log to tmp/LAS/cPyMemTrace/LASToHtml_trace_DTraceD_B/gnuplot/
2020-11-12 11:32:27,981 - gnuplot.py -  5108 - (MainThread) - INFO     - gnuplot stdout: None
2020-11-12 11:32:28,000 - gnuplot.py -  5108 - (MainThread) - INFO     - Writing gnuplot data "LASToHTML.log_3938" in path tmp/LAS/cPyMemTrace/LASToHtml_trace_DTraceD_B/gnuplot/
2020-11-12 11:32:28,084 - gnuplot.py -  5108 - (MainThread) - INFO     - gnuplot stdout: None




Python 3.9 Debug with DTrace support, DTrace Tracing
---------------------------------------------------------

$ tail -n20 tmp/LAS/cPyMemTrace/LASToHtml_trace_DTraceD_C/LASToHTML.log
2020-11-12 11:26:01,236 - gnuplot.py       -  118 -  4147 - (MainThread) - INFO     - gnuplot stdout: None
Processed 82 files and 108,145,150 bytes in 3484.416 s, 33784.9 ms/Mb
Bye, bye!
real      3520.61
user      1183.36
sys       2127.22

(TotalDepth3.9_develop)
paulross@Pauls-Mac-mini  ~/PycharmProjects/TotalDepth (develop)
$ tdprocess tmp/LAS/cPyMemTrace/LASToHtml_trace_DTraceD_C/LASToHTML.log tmp/LAS/cPyMemTrace/LASToHtml_trace_DTraceD_C/gnuplot/
2020-11-12 11:32:42,854 - process.py -  5119 - (MainThread) - INFO     - Extracting data from a log at tmp/LAS/cPyMemTrace/LASToHtml_trace_DTraceD_C/LASToHTML.log to tmp/LAS/cPyMemTrace/LASToHtml_trace_DTraceD_C/gnuplot/
2020-11-12 11:32:42,892 - gnuplot.py -  5119 - (MainThread) - INFO     - gnuplot stdout: None
2020-11-12 11:32:43,074 - gnuplot.py -  5119 - (MainThread) - INFO     - Writing gnuplot data "LASToHTML.log_4147" in path tmp/LAS/cPyMemTrace/LASToHtml_trace_DTraceD_C/gnuplot/
2020-11-12 11:32:43,202 - gnuplot.py -  5119 - (MainThread) - INFO     - gnuplot stdout: None


 .. image:: images/LASToHTML.log_4147.svg
    :alt: Python 3.9 (debug) with DTrace capability, DTrace tracing.






+-------------------------------------------------------------------+-----------+-----------+-----------+-------------------+
| Task                                                              | ``real``  | ``user``  | ``sys``   | ``real`` ratio    |
+===================================================================+===========+===========+===========+===================+
| Baseline                                                          | 35.49     | 29.72     | 2.03      | 1.0               |
+-------------------------------------------------------------------+-----------+-----------+-----------+-------------------+
| DTrace, no tracing                                                | 49.54     | 35.56     | 2.45      | x1.395            |
+-------------------------------------------------------------------+-----------+-----------+-----------+-------------------+
| DTrace, trace ``malloc()``, ``free()``. Release with ``pymalloc`` | 3220      | 902.5     | 1950      | x90.73            |
+-------------------------------------------------------------------+-----------+-----------+-----------+-------------------+
| DTrace, no tracing. Debug without ``pymalloc``                    | 148.55    | 139.99    | 1.93      | x4.186            |
+-------------------------------------------------------------------+-----------+-----------+-----------+-------------------+
| DTrace, trace ``malloc()``, ``free()`` Debug without ``pymalloc`` | 3520      | 1183      | 2127      | x99.18            |
+-------------------------------------------------------------------+-----------+-----------+-----------+-------------------+


DTrace Log File
-----------------------



+-------------------------------------------------------------------+---------------+---------------+-------------------+
| Task                                                              | Debug         | Release       | Debug/Release     |
+===================================================================+===============+===============+===================+
| Size                                                              | 11 Gb         | 16 Mb         | x68               |
+-------------------------------------------------------------------+---------------+---------------+-------------------+
| Lines                                                             | 16m           | 243k          | x68               |
+-------------------------------------------------------------------+---------------+---------------+-------------------+
| ``malloc()`` entries                                              | 8,096,729     | 94,880        | x85               |
+-------------------------------------------------------------------+---------------+---------------+-------------------+
| ``free()`` entries                                                | 8,054,421     | 144,684       | x56               |
+-------------------------------------------------------------------+---------------+---------------+-------------------+
| ``free(0x0)`` entries                                             | 38,849        | 74,254        | x0.52             |
+-------------------------------------------------------------------+---------------+---------------+-------------------+







.. rubric:: Footnotes
.. [#] Text of the first footnote.
