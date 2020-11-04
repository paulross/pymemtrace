**************************
Tracking Down Memory Leaks
**************************

Introduction
====================

Is it a Leak?
------------------

Sources of Leaks
------------------

A Bit About (C)Python Memory Management
------------------------------------------

Reference Counts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Garbage Collection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

CPython's Object Allocator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

From the Python source code ``Objects/obmalloc.c``:

.. code-block:: text

        _____   ______   ______       ________
       [ int ] [ dict ] [ list ] ... [ string ]       Python core         |
    +3 | <----- Object-specific memory -----> | <-- Non-object memory --> |
        _______________________________       |                           |
       [   Python's object allocator   ]      |                           |
    +2 | ####### Object memory ####### | <------ Internal buffers ------> |
        ______________________________________________________________    |
       [          Python's raw memory allocator (PyMem_ API)          ]   |
    +1 | <----- Python memory (under PyMem manager's control) ------> |   |
        __________________________________________________________________
       [    Underlying general-purpose allocator (ex: C library malloc)   ]
     0 | <------ Virtual memory allocated for the python process -------> |

       =========================================================================
        _______________________________________________________________________
       [                OS-specific Virtual Memory Manager (VMM)               ]
    -1 | <--- Kernel dynamic storage allocation & management (page-based) ---> |
        __________________________________   __________________________________
       [                                  ] [                                  ]
    -2 | <-- Physical memory: ROM/RAM --> | | <-- Secondary storage (swap) --> |


Memory De-allocation
"""""""""""""""""""""
