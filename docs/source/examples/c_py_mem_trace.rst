.. _examples-cpymemtrace:

``cPyMemTrace`` Examples
===============================================

``cPyMemTrace`` is a Python profiler written in 'C' that records the `Resident Set Size <https://en.wikipedia.org/wiki/Resident_set_size>`_
for every Python and C call and return.
It writes this data to a log file with a name of the form ``"20241107_195847_62264_P_0_PY3.13.0b3.log"``.

Logging Changes in RSS
--------------------------------

Here is a simple example:

.. code-block:: python

    from pymemtrace import cPyMemTrace

    def create_string(l: int) -> str:
        return ' ' * l

    with cPyMemTrace.Profile():
        l = []
        for i in range(8):
            l.append(create_string(1024**2))
        while len(l):
            l.pop()

This produces a log file in the current working directory:

.. code-block:: text

          Event        dEvent  Clock        What     File    #line Function      RSS           dRSS
    NEXT: 0            +0      0.066718     CALL     test.py #   9 create_string  9101312      9101312
    NEXT: 1            +1      0.067265     RETURN   test.py #  10 create_string 10153984      1052672
    PREV: 4            +3      0.067285     CALL     test.py #   9 create_string 10153984            0
    NEXT: 5            +4      0.067777     RETURN   test.py #  10 create_string 11206656      1052672
    PREV: 8            +3      0.067787     CALL     test.py #   9 create_string 11206656            0
    NEXT: 9            +4      0.068356     RETURN   test.py #  10 create_string 12259328      1052672
    PREV: 12           +3      0.068367     CALL     test.py #   9 create_string 12259328            0
    NEXT: 13           +4      0.068944     RETURN   test.py #  10 create_string 13312000      1052672
    PREV: 16           +3      0.068954     CALL     test.py #   9 create_string 13312000            0
    NEXT: 17           +4      0.069518     RETURN   test.py #  10 create_string 14364672      1052672
    PREV: 20           +3      0.069534     CALL     test.py #   9 create_string 14364672            0
    NEXT: 21           +4      0.070101     RETURN   test.py #  10 create_string 15417344      1052672
    PREV: 24           +3      0.070120     CALL     test.py #   9 create_string 15417344            0
    NEXT: 25           +4      0.070663     RETURN   test.py #  10 create_string 16470016      1052672
    PREV: 28           +3      0.070677     CALL     test.py #   9 create_string 16470016            0
    NEXT: 29           +4      0.071211     RETURN   test.py #  10 create_string 17522688      1052672

By default not all events are recorded just any that increase the RSS by one page along with the immediately preceding event.

Logging Every Event
--------------------------------

If all events are needed then change the constructor argument to 0:

.. code-block:: python

    with cPyMemTrace.Profile(0):
        # As before

And the log file looks like this:

.. code-block:: text

          Event        dEvent  Clock        What     File    #line Function      RSS           dRSS
    NEXT: 0            +0      0.079408     CALL     test.py #   9 create_string  9105408      9105408
    NEXT: 1            +1      0.079987     RETURN   test.py #  10 create_string 10158080      1052672
    NEXT: 2            +1      0.079994     C_CALL   test.py #  64 append        10158080            0
    NEXT: 3            +1      0.079998     C_RETURN test.py #  64 append        10158080            0
    NEXT: 4            +1      0.080003     CALL     test.py #   9 create_string 10158080            0
    NEXT: 5            +1      0.080682     RETURN   test.py #  10 create_string 11210752      1052672
    NEXT: 6            +1      0.080693     C_CALL   test.py #  64 append        11210752            0
    NEXT: 7            +1      0.080698     C_RETURN test.py #  64 append        11210752            0
    NEXT: 8            +1      0.080704     CALL     test.py #   9 create_string 11210752            0
    NEXT: 9            +1      0.081414     RETURN   test.py #  10 create_string 12263424      1052672
    NEXT: 10           +1      0.081424     C_CALL   test.py #  64 append        12263424            0
    NEXT: 11           +1      0.081429     C_RETURN test.py #  64 append        12263424            0
    NEXT: 12           +1      0.081434     CALL     test.py #   9 create_string 12263424            0
    NEXT: 13           +1      0.081993     RETURN   test.py #  10 create_string 13316096      1052672
    NEXT: 14           +1      0.081998     C_CALL   test.py #  64 append        13316096            0
    ...
    NEXT: 59           +1      0.084531     C_RETURN test.py #  66 pop           17526784            0
    NEXT: 60           +1      0.084535     C_CALL   test.py #  65 len           17526784            0
    NEXT: 61           +1      0.084539     C_RETURN test.py #  65 len           17526784            0
    NEXT: 62           +1      0.084541     C_CALL   test.py #  66 pop           17526784            0
    NEXT: 63           +1      0.084561     C_RETURN test.py #  66 pop           17526784            0
    NEXT: 64           +1      0.084566     C_CALL   test.py #  65 len           17526784            0
    NEXT: 65           +1      0.084568     C_RETURN test.py #  65 len           17526784            0

There is some discussion about the performance of ``cPyMemTrace`` here :ref:`tech_notes-cpymemtrace`

Stacking Context Managers
-------------------------------

The ``cPyMemTrace`` profile and trace context managers can be stacked.
In that case a new log file is started and the previous one is temporarily suspended.
``cPyMemTrace`` only writes to one log file at a time.
The log file has the stack depth in its name.
For example:

.. code-block:: python

    from pymemtrace import cPyMemTrace

    with cPyMemTrace.Profile():
        # Now writing to, say, "20241107_195847_62264_P_0_PY3.13.0b3.log"
        # Note the "_0_" in the file name.
        with cPyMemTrace.Profile():
            # Writing to "20241107_195847_62264_P_0_PY3.13.0b3.log" is suspended.
            # Now writing to, say, "20241107_195847_62264_P_1_PY3.13.0b3.log"
            # Note the "_1_" in the file name.
            pass
        # The log file "20241107_195847_62264_P_1_PY3.13.0b3.log" is closed.
        # Writing to "20241107_195847_62264_P_0_PY3.13.0b3.log" is resumed.
        pass
    # The log file "20241107_195847_62264_P_0_PY3.13.0b3.log" is closed.

When running all the tests example log files will be generated in the ``tests`` directory.

The module level function will give you the stack depth:

.. code-block:: python

    assert cPyMemTrace.profile_wrapper_depth() == 0
    with cPyMemTrace.Profile():
        assert cPyMemTrace.profile_wrapper_depth() == 1
        with cPyMemTrace.Profile():
            assert cPyMemTrace.profile_wrapper_depth() == 2
            with cPyMemTrace.Profile():
                assert cPyMemTrace.profile_wrapper_depth() == 3
            assert cPyMemTrace.profile_wrapper_depth() == 2
        assert cPyMemTrace.profile_wrapper_depth() == 1
    assert cPyMemTrace.profile_wrapper_depth() == 0

Logging to a Temporary File
------------------------------

By default the log is written to a file in the current working directory.
To write to a specific file, and then read it follow this pattern:

.. code-block:: python

    import tempfile

    with tempfile.NamedTemporaryFile() as file:
        with cPyMemTrace.Trace(0, message='# Trace level0', filepath=file.name) as trace:
            trace.trace_file_wrapper.write_message_to_log('# Level 0 __enter__')
            temp_list = []
            for i in range(16):
                temp_list.append(b' ' * (1024 ** 2))
            trace.trace_file_wrapper.write_message_to_log('# Level 0 after populating list.')
            while len(temp_list):
                temp_list.pop()
            trace.trace_file_wrapper.write_message_to_log('# Level 0 after deleting the list.')
        file.flush()
        file_data = file.read()
        print()
        print(' filedata '.center(75, '-'))
        for line in file_data.split(b'\n'):
            print(line.decode('ascii'))
        print(' file_data DONE '.center(75, '-'))

See ``tests.test_cpymemtrace.test_trace_to_specific_log_file_nested()`` for a more complicated example.
