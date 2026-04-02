import functools
import sys

from pymemtrace import cPyMemTrace


def profile(*dec_args, **dec_kwargs):
    """Decorator that calls the function within a cPyMemTrace.Profile context manager."""

    def profile_inner(fn):
        @functools.wraps(fn)
        def profile_wrapper(*args, **kwargs):
            with cPyMemTrace.Profile(*dec_args, **dec_kwargs):
                result = fn(*args, **kwargs)
            return result

        return profile_wrapper

    return profile_inner


def trace(*dec_args, **dec_kwargs):
    """Decorator that calls the function within a cPyMemTrace.Trace context manager."""

    def trace_inner(fn):
        @functools.wraps(fn)
        def trace_wrapper(*args, **kwargs):
            with cPyMemTrace.Trace(*dec_args, **dec_kwargs):
                result = fn(*args, **kwargs)
            return result

        return trace_wrapper

    return trace_inner


if sys.version_info >= (3, 13):
    def reference_tracing(*dec_args, **dec_kwargs):
        """Decorator that calls the function within a cPyMemTrace.ReferenceTracing context manager."""

        def reference_tracing_inner(fn):
            @functools.wraps(fn)
            def reference_tracingwrapper(*args, **kwargs):
                with cPyMemTrace.ReferenceTracing(*dec_args, **dec_kwargs):
                    result = fn(*args, **kwargs)
                return result

            return reference_tracingwrapper

        return reference_tracing_inner
