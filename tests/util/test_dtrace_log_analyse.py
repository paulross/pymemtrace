import io

import pytest

from pymemtrace.util import dtrace_log_analyse


@pytest.mark.parametrize(
    'line, expected',
    (
            (
                    ' 77633  cmn_cmd_opts.py:141  -> set_log_level malloc(560) pntr 0x7fca83ef4240\n',
                    ('77633', 'cmn_cmd_opts.py', '141', 'set_log_level', '560', '0x7fca83ef4240'),
            ),
            (
                    " 77633 rs/paulross/pyenvs/TotalDepth_DTrace_3.9R/lib/python3.9/site-packages/numpy/ma/core.py:3420 -> ction__ internals> malloc(2632) pntr 0x7fca85895000\n",
                    ('77633',
                     'rs/paulross/pyenvs/TotalDepth_DTrace_3.9R/lib/python3.9/site-packages/numpy/ma/core.py',
                     '3420',
                     'ction__ internals>',
                     '2632',
                     '0x7fca85895000',
                     ),
            ),
    )
)
def test_RE_MALLOC(line, expected):
    result = dtrace_log_analyse.RE_MALLOC.match(line)
    assert result is not None
    assert result.groups() == expected


@pytest.mark.parametrize(
    'line, expected',
    (
            (
                    ' 77633       process.py:268  -> _get_process_data free(0x7fca83c00620)\n',
                    ('77633', 'process.py', '268', '_get_process_data', '0x7fca83c00620'),
            ),
            (
                    ' 77633       process.py:268  -> _get_process_data free(0x0)\n',
                    ('77633', 'process.py', '268', '_get_process_data', '0x0'),
            ),
            (
                    ' 77633                 :45   ->  free(0x0)\n',
                    ('77633', None, '45', None, '0x0'),
            ),
            (
                    " 77633 rs/paulross/pyenvs/TotalDepth_DTrace_3.9R/lib/python3.9/site-packages/numpy/ma/core.py:3009 -> ction__ internals> free(0x0)\n",
                    ('77633',
                     'rs/paulross/pyenvs/TotalDepth_DTrace_3.9R/lib/python3.9/site-packages/numpy/ma/core.py',
                     '3009',
                     'ction__ internals>',
                     '0x0'),
            ),
            (
                    " 77633                 :121  -> Æ 4A/ free(0x7fca8518c800)\n",
                    ('77633', None, '121', 'Æ\xa04A/', '0x7fca8518c800'),
            ),
    )
)
def test_RE_FREE(line, expected):
    result = dtrace_log_analyse.RE_FREE.match(line)
    assert result is not None
    assert result.groups() == expected


EXAMPLE_DTRACE_LOG_FILE = """dtrace:::BEGIN
 77633  cmn_cmd_opts.py:141  -> set_log_level malloc(560) pntr 0x7fca83ef4240
 77633      __init__.py:422  -> validate malloc(1114) pntr 0x7fca858e4200
 77633      __init__.py:422  -> validate free(0x7fca858e4200)
 77633     threading.py:817  -> __init__ malloc(576) pntr 0x7fca83ef4470
 77633      __init__.py:471  -> _init malloc(576) pntr 0x7fca83ef46b0
 77633     threading.py:870  -> start malloc(264) pntr 0x7fca83ef21e0
 77633     threading.py:870  -> start malloc(16) pntr 0x7fca83d48a30
 77633     threading.py:574  -> wait malloc(536) pntr 0x7fca83d54be0
 77633     threading.py:364  -> notify malloc(528) pntr 0x7fca83c47e80
 77633       process.py:268  -> _get_process_data free(0x0)
 77633       process.py:268  -> _get_process_data malloc(4096) pntr 0x7fca8408d200
 77633       process.py:268  -> _get_process_data malloc(25) pntr 0x7fca83c00620
 77633       process.py:268  -> _get_process_data malloc(4096) pntr 0x7fca8408e200
 77633       process.py:268  -> _get_process_data free(0x0)
 77633       process.py:268  -> _get_process_data free(0x0)
 77633       process.py:268  -> _get_process_data free(0x0)
 77633       process.py:268  -> _get_process_data free(0x0)
 77633       process.py:268  -> _get_process_data free(0x0)
 77633       process.py:268  -> _get_process_data free(0x0)
 77633       process.py:268  -> _get_process_data free(0x0)
 77633       process.py:268  -> _get_process_data free(0x7fca83c00620)
 77633       process.py:268  -> _get_process_data free(0x7fca8408e200)
 77633       process.py:268  -> _get_process_data free(0x7fca8408d200)
dtrace::END
"""


@pytest.mark.parametrize(
    'dtrace_text, expected',
    (
            (
                    EXAMPLE_DTRACE_LOG_FILE,
                    7,
            ),
    )
)
def test_read_dtrace_log_file_len(dtrace_text, expected):
    file = io.StringIO(dtrace_text)
    result = dtrace_log_analyse.read_dtrace_log_file(file)
    assert len(result) == expected


@pytest.mark.parametrize(
    'dtrace_text, expected',
    (
            (
                    EXAMPLE_DTRACE_LOG_FILE,
                    11,
            ),
    )
)
def test_read_dtrace_log_file_count_mallocs(dtrace_text, expected):
    file = io.StringIO(dtrace_text)
    result = dtrace_log_analyse.read_dtrace_log_file(file)
    assert result.count_mallocs == expected


@pytest.mark.parametrize(
    'dtrace_text, expected',
    (
            (
                    EXAMPLE_DTRACE_LOG_FILE,
                    4,
            ),
    )
)
def test_read_dtrace_log_file_count_frees_non_null(dtrace_text, expected):
    file = io.StringIO(dtrace_text)
    result = dtrace_log_analyse.read_dtrace_log_file(file)
    assert result.count_frees_non_null == expected


@pytest.mark.parametrize(
    'dtrace_text, expected',
    (
            (
                    EXAMPLE_DTRACE_LOG_FILE,
                    8,
            ),
    )
)
def test_read_dtrace_log_file_count_frees_null(dtrace_text, expected):
    file = io.StringIO(dtrace_text)
    result = dtrace_log_analyse.read_dtrace_log_file(file)
    assert result.count_frees_null == expected
