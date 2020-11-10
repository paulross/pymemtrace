Tools for Detecting Memory Leaks
====================================

Tools for analysing memory can be characterised by:

======================= ====================================================================================================
Characteristic          Description
======================= ====================================================================================================
**Availability**        Is it within Python or the standard library, needs third party library installation or
                        required a special build of some sort?
**Memory Granularity**  How detailed is the memory measurement? Somewhere between every ``malloc``
                        or the overall memory usage as seen by the OS.
**Runtime Granularity** How detailed is the memory measurement? Per line, per function, for Python or C code?
**Runtime Cost**        What is the extra runtime introduced by using this tool?
**Memory Cost**         What is the extra memory consumption is introduced by using this tool?
**Developer Cost**      How hard it is to use the tool?
======================= ====================================================================================================

Each tool makes trade offs between each of these characteristics.

Platform Tools
------------------

======================= ====================================================================================================
Characteristic          Description
======================= ====================================================================================================
**Availability**        Always.
**Memory Granularity**  Usually the total memory usage by the process.
**Runtime Granularity** Generally periodic at low frequency, typically of the order of seconds.
**Runtime Cost**        Usually none.
**Memory Cost**         Usually none.
**Developer Cost**      Easy.
======================= ====================================================================================================


Windows
^^^^^^^^^^^^^^^^^^^

Linux
^^^^^^^^^^^^^^^^^^^

Mac OS X
^^^^^^^^^^^^^^^^^^^


Python Tools
------------------

Modules from the Standard Library
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``sys``
"""""""""""""""""""""


``gc``
"""""""""""""""""""""


``tracemalloc``
"""""""""""""""""""""


Third Party Modules
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``psutil``
"""""""""""""""""""""


``objgraph``
"""""""""""""""""""""


Debugging Tools
------------------


Building a Debug Version of Python
---------------------------------------


