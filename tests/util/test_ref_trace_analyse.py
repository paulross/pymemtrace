import io
import sys
import tempfile

import pytest

from pymemtrace import cPyMemTrace
from pymemtrace.util import ref_trace_analyse


@pytest.mark.skipif(not (sys.version_info.minor >= 13), reason='Python >= 3.13')
def test_reference_tracing():
    message = 'test_reference_tracing_to_specific_log_file_nested():'
    with tempfile.NamedTemporaryFile() as file_0:
        # Create the outer context manager.
        with cPyMemTrace.ReferenceTracing(message=message + '#level0', filepath=file_0.name) as trace_0:
            trace_0.write_message_to_log('# Level 0 __enter__')
            # Exercise the outer context manager *before* the inner context manager.
            assert trace_0.log_file_path() == file_0.name
            for i in range(4):
                temp_list = []
                for i in range(4):
                    temp_list.append(b' ' * (1024 ** 2))
                while len(temp_list):
                    temp_list.pop()
            trace_0.write_message_to_log('# Level 0 after populate_list()')
        # Allow exit to close the file.
        with open(file_0.name) as f:
            print()
            print(' log_file_contents '.center(75, '-'))
            print(f.read())
            print(' log_file_contents DONE '.center(75, '-'))

            f.seek(0)
            analysis = ref_trace_analyse.process_file(f, ignore_untracked=False)
            print(' analysis '.center(75, '-'))
            print('\n'.join(analysis.long_str_list(show_full_path=False)))
            print(' analysis DONE '.center(75, '-'))

    # assert file_0_data.startswith(bytes(message + '#level0', 'ascii'))
