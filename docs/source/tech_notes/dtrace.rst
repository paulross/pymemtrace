

Technical Note on DTrace
==========================

Lorem ipsum [#f1]_


To test the performance of `cPyMenTrace` TotalDepth was used to summarise LAS files in HTML.
Source data was the W005862 directory but with MDT directory removed.
There were 82 LAS files totalling 108,145,150 bytes.
The largest file was 27,330,513 bytes, smallest 4,609 bytes.
Platform was a Mac mini (late 2014) 2.8 GHz Intel Core i5 running macOS Mojave 10.14.6.


Baseline Python 3.9 (standard release build):

 .. image:: images/LASToHTML.log_77077.svg
    :alt: Basic Python 3.9 (release) performance.

Execution time is 34.4 seconds and average CPU% is 85.8 so effective time is 29.5 (s).


Python 3.9 (release) with DTrace support

 .. image:: images/LASToHTML.log_76753.svg
    :alt: Python 3.9 (release) with DTrace capability.

Execution time is 48.6 seconds and average CPU% is 72.4 so effective time is 35.2 (s) which is 19.3% above the baseline.




Python 3.9 (release) with DTrace support and DTrace running

 .. image:: images/LASToHTML.log_77633.svg
    :alt: Python 3.9 (release) with DTrace capability.

TODO: Execution time is 48.6 seconds and average CPU% is 72.4 so effective time is 35.2 (s) which is 19.3% above the baseline.





.. rubric:: Footnotes
.. [#f1] Text of the first footnote.
