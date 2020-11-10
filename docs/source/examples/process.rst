
``process``
==============================

.. code-block:: python

    # TODO



.. code-block:: text

    $ python pymemtrace/process.py -p 71519
    2020-11-10 20:46:41,687 - process.py#354 - 71869 - (MainThread) - INFO     - Demonstration of logging a process
    Monitoring 71519
    2020-11-10 20:46:41,689 - process.py#289 - 71869 - (ProcMon   ) - INFO     - ProcessLoggingThread-JSON-START {"timestamp": "2020-11-10 20:46:41.688480", "memory_info": {"rss": 12906496, "vms": 4359774208, "pfaults": 3310, "pageins": 960}, "cpu_times": {"user": 0.248923952, "system": 0.078601624, "children_user": 0.0, "children_system": 0.0}, "elapsed_time": 1396.3783469200134, "pid": 71519}
    2020-11-10 20:46:42,693 - process.py#289 - 71869 - (ProcMon   ) - INFO     - ProcessLoggingThread-JSON {"timestamp": "2020-11-10 20:46:42.693520", "memory_info": {"rss": 12906496, "vms": 4359774208, "pfaults": 3310, "pageins": 960}, "cpu_times": {"user": 0.248923952, "system": 0.078601624, "children_user": 0.0, "children_system": 0.0}, "elapsed_time": 1397.3834369182587, "pid": 71519}
    2020-11-10 20:46:43,697 - process.py#289 - 71869 - (ProcMon   ) - INFO     - ProcessLoggingThread-JSON {"timestamp": "2020-11-10 20:46:43.697247", "memory_info": {"rss": 12906496, "vms": 4359774208, "pfaults": 3310, "pageins": 960}, "cpu_times": {"user": 0.248923952, "system": 0.078601624, "children_user": 0.0, "children_system": 0.0}, "elapsed_time": 1398.3871541023254, "pid": 71519}
    2020-11-10 20:46:44,701 - process.py#289 - 71869 - (ProcMon   ) - INFO     - ProcessLoggingThread-JSON {"timestamp": "2020-11-10 20:46:44.701290", "memory_info": {"rss": 12906496, "vms": 4359774208, "pfaults": 3310, "pageins": 960}, "cpu_times": {"user": 0.248923952, "system": 0.078601624, "children_user": 0.0, "children_system": 0.0}, "elapsed_time": 1399.391231060028, "pid": 71519}
    2020-11-10 20:46:45,705 - process.py#289 - 71869 - (ProcMon   ) - INFO     - ProcessLoggingThread-JSON {"timestamp": "2020-11-10 20:46:45.705679", "memory_info": {"rss": 12906496, "vms": 4359774208, "pfaults": 3310, "pageins": 960}, "cpu_times": {"user": 0.248923952, "system": 0.078601624, "children_user": 0.0, "children_system": 0.0}, "elapsed_time": 1400.3956229686737, "pid": 71519}
    2020-11-10 20:46:46,708 - process.py#289 - 71869 - (ProcMon   ) - INFO     - ProcessLoggingThread-JSON {"timestamp": "2020-11-10 20:46:46.708657", "memory_info": {"rss": 12906496, "vms": 4359774208, "pfaults": 3310, "pageins": 960}, "cpu_times": {"user": 0.248923952, "system": 0.078601624, "children_user": 0.0, "children_system": 0.0}, "elapsed_time": 1401.398586988449, "pid": 71519}
    ^CKeyboardInterrupt!
    2020-11-10 20:46:47,626 - process.py#289 - 71869 - (MainThread) - INFO     - ProcessLoggingThread-JSON-STOP {"timestamp": "2020-11-10 20:46:47.626020", "memory_info": {"rss": 12906496, "vms": 4359774208, "pfaults": 3310, "pageins": 960}, "cpu_times": {"user": 0.248923952, "system": 0.078601624, "children_user": 0.0, "children_system": 0.0}, "elapsed_time": 1402.3160009384155, "pid": 71519}
    Bye, bye!

