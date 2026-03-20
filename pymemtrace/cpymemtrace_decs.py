import functools

from pymemtrace import cPyMemTrace


def profile(*dec_args, **dec_kwargs):
    """Decorator that calls the function within a cPyMemTrace.Profile context manager."""

    def profile_inner(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            with cPyMemTrace.Profile(*dec_args, **dec_kwargs):
                result = fn(*args, **kwargs)
            return result

        return wrapper

    return profile_inner


def trace(*dec_args, **dec_kwargs):
    """Decorator that calls the function within a cPyMemTrace.Trace context manager."""

    def trace_inner(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            with cPyMemTrace.Trace(*dec_args, **dec_kwargs):
                result = fn(*args, **kwargs)
            return result

        return wrapper

    return trace_inner


def reference_tracing(*dec_args, **dec_kwargs):
    """Decorator that calls the function within a cPyMemTrace.ReferenceTracing context manager."""

    def reference_tracing_inner(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            with cPyMemTrace.ReferenceTracing(*dec_args, **dec_kwargs):
                result = fn(*args, **kwargs)
            return result

        return wrapper

    return reference_tracing_inner
