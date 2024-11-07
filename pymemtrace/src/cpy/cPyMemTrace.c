/** @file
 *
 * Created by Paul Ross on 29/10/2020.
 * This contains the Python interface to the C memory tracer.
 * See https://docs.python.org/3/c-api/init.html#profiling-and-tracing
 *
 * Monitored events are:
 * PyTrace_CALL, PyTrace_C_CALL, PyTrace_C_EXCEPTION, PyTrace_C_RETURN, PyTrace_EXCEPTION,
 * PyTrace_LINE, PyTrace_OPCODE, PyTrace_RETURN
 *
 * The Python events:
 *
 * - PyTrace_CALL When a new call to a Python function or method is being reported, or a new entry into a generator.
 * - PyTrace_EXCEPTION When when a Python exception has been raised.
 * - PyTrace_LINE When a Python line-number event is being reported.
 * - PyTrace_OPCODE When a new Python opcode is about to be executed.
 * - PyTrace_RETURN When a Python call is about to return.
 *
 * The C Events:
 * - PyTrace_C_CALL When a C function is about to be called.
 * - PyTrace_C_EXCEPTION When a C function has raised an exception.
 * - PyTrace_C_RETURN When a C function has returned.
 *
 * PyEval_SetProfile
 * -----------------
 * The profile function is called for all monitored events except PyTrace_LINE PyTrace_OPCODE and PyTrace_EXCEPTION.
 *
 * So this is useful when tracing C extensions.
 *
 * PyEval_SetTrace
 * ---------------
 * This is similar to PyEval_SetProfile(), except the tracing function does receive Python line-number events
 * and per-opcode events, but does not receive any event related to C function objects being called.
 * Any trace function registered using PyEval_SetTrace() will not receive PyTrace_C_CALL, PyTrace_C_EXCEPTION or PyTrace_C_RETURN as a
 * value for the what parameter.
 *
 * So this is useful when tracing Python code ignoring C extensions.
 *
 * TODO: Optionally pass in filename to write the log to.
 * TODO: Optionally pass in a Pytho file objedct to write the log to.
 * TODO: Have stack of profiling functions so then nested cPyMemTrace.Profile()/Trace() can be used.
 *
*/
#define PY_SSIZE_T_CLEAN

#include <Python.h>
#include "structmember.h"
#include "frameobject.h"

#include <stdio.h>
#include <time.h>
#include <assert.h>

#include "get_rss.h"
#include "pymemtrace_util.h"

// PYMEMTRACE_PATH_NAME_MAX_LENGTH is usually 4kB and that should be sufficient.
#define PY_MEM_TRACE_EVENT_TEXT_MAX_LENGTH PYMEMTRACE_PATH_NAME_MAX_LENGTH

#define PY_MEM_TRACE_WRITE_OUTPUT
//#undef PY_MEM_TRACE_WRITE_OUTPUT

#define PY_MEM_TRACE_WRITE_OUTPUT_CLOCK
//#undef PY_MEM_TRACE_WRITE_OUTPUT_CLOCK

#define PY_MEM_TRACE_WRITE_OUTPUT_PREV_NEXT
//#undef PY_MEM_TRACE_WRITE_OUTPUT_PREV_NEXT

/* Backwards compatibility for object members for Python versions prior to 3.12.
 * See:
 * https://docs.python.org/3/c-api/structures.html#member-flags
 * https://docs.python.org/3/c-api/apiabiversion.html#c.PY_VERSION_HEX
 * */

#if PY_VERSION_HEX < 0x030c0000
/* Flags. */
#define Py_READONLY READONLY
/* Types. */
#define Py_T_PYSSIZET T_PYSSIZET
#define Py_T_INT T_INT
#define Py_T_STRING T_STRING
#define Py_T_OBJECT_EX T_OBJECT_EX
#endif

// Markers for the beginning and end of the log file.
// Make NULL for no marker(s).
static const char *MARKER_LOG_FILE_START = "SOF";
static const char *MARKER_LOG_FILE_END = "EOF";

#pragma mark TraceFileWrapper object
/*
 * Trace classes could make this available by looking at trace_file_wrapper or profile_file_wrapper.
 */
typedef struct {
    PyObject_HEAD
    FILE *file;
    // Store the file path and provide an API that can return it (or None) from profile_wrapper or trace_wrapper.
    char *log_file_path;
    size_t event_number;
    size_t rss;
    int d_rss_trigger;
#ifdef PY_MEM_TRACE_WRITE_OUTPUT
    size_t previous_event_number;
    char event_text[PY_MEM_TRACE_EVENT_TEXT_MAX_LENGTH];
#endif
} TraceFileWrapper;

static void
TraceFileWrapper_dealloc(TraceFileWrapper *self) {
    if (self->file) {
        if (MARKER_LOG_FILE_END) {
            fprintf(self->file, "%s\n", MARKER_LOG_FILE_END);
        }
        fclose(self->file);
    }
    free(self->log_file_path);
    Py_TYPE(self)->tp_free((PyObject *) self);
}

static PyObject *
TraceFileWrapper_new(PyTypeObject *type, PyObject *Py_UNUSED(args), PyObject *Py_UNUSED(kwds)) {
    TraceFileWrapper *self;
    self = (TraceFileWrapper *) type->tp_alloc(type, 0);
    if (self != NULL) {
        self->file = NULL;
        self->log_file_path = NULL;
    }
    return (PyObject *) self;
}

#pragma mark - TraceFileWrapper members

static PyMemberDef TraceFileWrapper_members[] = {
        {
                "log_file_path",         Py_T_STRING,   offsetof(TraceFileWrapper,
                                                                 log_file_path),         Py_READONLY,
                                                                                                      "The path to the log file being written."
        },
        {
                "event_number",          Py_T_PYSSIZET, offsetof(TraceFileWrapper,
                                                                 event_number),          Py_READONLY, "The current event number."
        },
        {
                "rss",                   Py_T_PYSSIZET, offsetof(TraceFileWrapper,
                                                                 rss),                   Py_READONLY, "The current Resident Set Size (RSS)."
        },
        {
                "d_rss_trigger",         Py_T_INT,      offsetof(TraceFileWrapper,
                                                                 d_rss_trigger),         Py_READONLY, "The delta Resident Set Size (RSS) trigger value."
        },
        {
                "previous_event_number", Py_T_PYSSIZET, offsetof(TraceFileWrapper,
                                                                 previous_event_number), Py_READONLY, "The previous event number."
        },
        {
                "event_text",            Py_T_STRING,   offsetof(TraceFileWrapper,
                                                                 event_text),            Py_READONLY,
                                                                                                      "The current event text."
        },
        {NULL, 0, 0, 0, NULL} /* Sentinel */
};

#pragma mark - TraceFileWrapper methods

static PyObject *
TraceFileWrapper_write_to_log(TraceFileWrapper *self, PyObject *op) {
    if (!PyUnicode_Check(op)) {
        PyErr_Format(PyExc_ValueError, "write_log() requires a single string, not type %s", Py_TYPE(op)->tp_name);
        return NULL;
    }
    Py_UCS1 *c_str = PyUnicode_1BYTE_DATA(op);
    fprintf(self->file, "%s\n", c_str);
    Py_RETURN_NONE;
}

static PyMethodDef TraceFileWrapper_methods[] = {
        {"write_to_log", (PyCFunction) TraceFileWrapper_write_to_log, METH_O,
                "Write a string to the existing log file  with a newline. Returns None."},
        {NULL, NULL, 0, NULL}  /* Sentinel */
};

#pragma mark - TraceFileWrapper declaration

static PyTypeObject TraceFileWrapperType = {
        PyVarObject_HEAD_INIT(NULL, 0)
        .tp_name = "cPyMemTrace.TraceFileWrapper",
        .tp_doc = "Wrapper round a trace-to-file object.",
        .tp_basicsize = sizeof(TraceFileWrapper),
        .tp_itemsize = 0,
        .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
        .tp_new = TraceFileWrapper_new,
        .tp_dealloc = (destructor) TraceFileWrapper_dealloc,
        .tp_members = TraceFileWrapper_members,
        .tp_methods = TraceFileWrapper_methods,
};

#pragma mark The trace_or_profile_function()
/*
 * Defined in Include/cpython/pystate.h
 * #define PyTrace_CALL 0
 * #define PyTrace_EXCEPTION 1
 * #define PyTrace_LINE 2
 * #define PyTrace_RETURN 3
 * #define PyTrace_C_CALL 4
 * #define PyTrace_C_EXCEPTION 5
 * #define PyTrace_C_RETURN 6
 * #define PyTrace_OPCODE 7
 *
 * Here these are trimmed to be a maximum of 8 long.
 */
#ifdef PY_MEM_TRACE_WRITE_OUTPUT
static const char *WHAT_STRINGS[] = {
        "CALL",
        "EXCEPT",
        "LINE",
        "RETURN",
        "C_CALL",
        "C_EXCEPT",
        "C_RETURN",
        "OPCODE",
};
#endif

static int
trace_or_profile_function(PyObject *pobj, PyFrameObject *frame, int what, PyObject *arg) {
    assert(Py_TYPE(pobj) == &TraceFileWrapperType && "trace_wrapper is not a TraceFileWrapperType.");

    TraceFileWrapper *trace_wrapper = (TraceFileWrapper *) pobj;
    size_t rss = getCurrentRSS_alternate();
#ifdef PY_MEM_TRACE_WRITE_OUTPUT
#if PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION >= 11
    /* See https://docs.python.org/3.11/whatsnew/3.11.html#pyframeobject-3-11-hiding */
    const unsigned char *file_name = PyUnicode_1BYTE_DATA(PyFrame_GetCode(frame)->co_filename);
#else
    const unsigned char *file_name = PyUnicode_1BYTE_DATA(frame->f_code->co_filename);
#endif
    int line_number = PyFrame_GetLineNumber(frame);
    const char *func_name = NULL;
    if (what == PyTrace_C_CALL || what == PyTrace_C_EXCEPTION || what == PyTrace_C_RETURN) {
        func_name = PyEval_GetFuncName(arg);
    } else {
#if PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION >= 11
        /* See https://docs.python.org/3.11/whatsnew/3.11.html#pyframeobject-3-11-hiding */
        func_name = (const char *) PyUnicode_1BYTE_DATA(PyFrame_GetCode(frame)->co_name);
#else
        func_name = (const char *) PyUnicode_1BYTE_DATA(frame->f_code->co_name);
#endif
    }
    long d_rss = rss - trace_wrapper->rss;
    if (labs(d_rss) >= trace_wrapper->d_rss_trigger
        && trace_wrapper->event_number > 0
        && (trace_wrapper->event_number - trace_wrapper->previous_event_number) > 1) {
        // Previous event.
#ifdef PY_MEM_TRACE_WRITE_OUTPUT_PREV_NEXT
        fputs("PREV: ", trace_wrapper->file);
#endif
        fputs(trace_wrapper->event_text, trace_wrapper->file);
    }
#ifdef PY_MEM_TRACE_WRITE_OUTPUT_CLOCK
    double clock_time = (double) clock() / CLOCKS_PER_SEC;
    snprintf(trace_wrapper->event_text, PY_MEM_TRACE_EVENT_TEXT_MAX_LENGTH,
             "%-12zu +%-6ld %-12.6f %-8s %-80s %4d %-32s %12zu %12ld\n",
             trace_wrapper->event_number, trace_wrapper->event_number - trace_wrapper->previous_event_number,
             clock_time, WHAT_STRINGS[what], file_name, line_number, func_name, rss, d_rss);
#else
    snprintf(trace_wrapper->event_text, PY_MEM_TRACE_EVENT_TEXT_MAX_LENGTH,
             "%-12zu +%-6ld %-8s %-80s %4d %-32s %12zu %12ld\n",
             trace_wrapper->event_number, trace_wrapper->event_number - trace_wrapper->previous_event_number,
             WHAT_STRINGS[what], file_name, line_number, func_name, rss, d_rss);
#endif // PY_MEM_TRACE_WRITE_OUTPUT_CLOCK
    if (labs(d_rss) >= trace_wrapper->d_rss_trigger) {
#ifdef PY_MEM_TRACE_WRITE_OUTPUT_PREV_NEXT
        fputs("NEXT: ", trace_wrapper->file);
//        fputs("      ", trace_wrapper->file);
#endif
        fputs(trace_wrapper->event_text, trace_wrapper->file);
        trace_wrapper->previous_event_number = trace_wrapper->event_number;
    }
#endif // PY_MEM_TRACE_WRITE_OUTPUT
    trace_wrapper->event_number++;
    trace_wrapper->rss = rss;
    return 0;
}

static TraceFileWrapper *
new_trace_file_wrapper(TraceFileWrapper *trace_wrapper, int d_rss_trigger, const char *message) {
    static char file_path_buffer[PYMEMTRACE_PATH_NAME_MAX_LENGTH];
    if (trace_wrapper) {
        TraceFileWrapper_dealloc(trace_wrapper);
        trace_wrapper = NULL;
    }
    char *filename = create_filename();
    if (filename) {
#ifdef _WIN32
        char seperator = '\\';
#else
        char seperator = '/';
#endif
        snprintf(file_path_buffer, PYMEMTRACE_PATH_NAME_MAX_LENGTH, "%s%c%s", current_working_directory(), seperator,
                 filename);
        fprintf(stdout, "Opening log file %s\n", file_path_buffer);
        trace_wrapper = (TraceFileWrapper *) TraceFileWrapper_new(&TraceFileWrapperType, NULL, NULL);
        if (trace_wrapper) {
            trace_wrapper->file = fopen(filename, "w");
            if (trace_wrapper->file) {
                // Copy the filename
                trace_wrapper->log_file_path = malloc(strlen(file_path_buffer) + 1);
                strcpy(trace_wrapper->log_file_path, file_path_buffer);
                // Write the message to the log file if present.
                if (message) {
                    fprintf(trace_wrapper->file, "%s\n", message);
                } else if (MARKER_LOG_FILE_START) {
                    fprintf(trace_wrapper->file, "%s\n", MARKER_LOG_FILE_START);
                }
#ifdef PY_MEM_TRACE_WRITE_OUTPUT_CLOCK
#ifdef PY_MEM_TRACE_WRITE_OUTPUT_PREV_NEXT
                fprintf(trace_wrapper->file, "      %-12s %-6s  %-12s %-8s %-80s %4s %-32s %12s %12s\n",
                        "Event", "dEvent", "Clock", "What", "File", "line", "Function", "RSS", "dRSS"
                );
#else
                fprintf(trace_wrapper->file, "%-12s %-6s  %-12s %-8s %-80s %4s %-32s %12s %12s\n",
                        "Event", "dEvent", "Clock", "What", "File", "line", "Function", "RSS", "dRSS"
                );
#endif
#else
#ifdef PY_MEM_TRACE_WRITE_OUTPUT_PREV_NEXT
                fprintf(trace_wrapper->file, "      %-12s %-6s  %-8s %-80s %4s %-32s %12s %12s\n",
                        "Event", "dEvent", "What", "File", "line", "Function", "RSS", "dRSS"
                );
#else
                fprintf(trace_wrapper->file, "%-12s %-6s  %-8s %-80s %4s %-32s %12s %12s\n",
                        "Event", "dEvent", "What", "File", "line", "Function", "RSS", "dRSS"
                );
#endif
#endif
                trace_wrapper->event_number = 0;
                trace_wrapper->rss = 0;
                if (d_rss_trigger < 0) {
                    trace_wrapper->d_rss_trigger = getpagesize();
                } else {
                    trace_wrapper->d_rss_trigger = d_rss_trigger;
                }
#ifdef PY_MEM_TRACE_WRITE_OUTPUT
                trace_wrapper->previous_event_number = 0;
#endif
            } else {
                TraceFileWrapper_dealloc(trace_wrapper);
                fprintf(stderr, "Can not open writable file for TraceFileWrapper at %s\n", filename);
                return NULL;
            }
        } else {
            fprintf(stderr, "Can not create TraceFileWrapper.\n");
        }
    }
    return trace_wrapper;
}

#pragma mark Static trace/profile functions.
static TraceFileWrapper *static_profile_wrapper = NULL;
static TraceFileWrapper *static_trace_wrapper = NULL;

#pragma mark Get the current log paths.

static PyObject *
get_log_file_path_profile(void) {
    if (static_profile_wrapper) {
        return Py_BuildValue("s", static_profile_wrapper->log_file_path);
    } else {
        Py_RETURN_NONE;
    }
}

static PyObject *
get_log_file_path_trace(void) {
    if (static_trace_wrapper) {
        return Py_BuildValue("s", static_trace_wrapper->log_file_path);
    } else {
        Py_RETURN_NONE;
    }
}

#pragma mark cPyMemTrace methods.

static PyObject *
py_rss(void) {
    return PyLong_FromSize_t(getCurrentRSS_alternate());
}

static PyObject *
py_rss_peak(void) {
    return PyLong_FromSize_t(getPeakRSS());
}

static PyMethodDef cPyMemTraceMethods[] = {
        {"rss",      (PyCFunction) py_rss,      METH_NOARGS, "Return the current RSS in bytes."},
        {"rss_peak", (PyCFunction) py_rss_peak, METH_NOARGS, "Return the peak RSS in bytes."},
        {
         "get_log_file_path_profile",
                     (PyCFunction) get_log_file_path_profile,
                                                METH_NOARGS,
                                                             "Return the current log file path for profiling."
        },
        {
         "get_log_file_path_trace",
                     (PyCFunction) get_log_file_path_trace,
                                                METH_NOARGS,
                                                             "Return the current log file path for tracing."
        },
        {NULL, NULL, 0, NULL}        /* Sentinel */
};

#pragma mark Context manager for ProfileObject
/**** Context manager for attach_profile_function() and detach_profile_function() ****/
typedef struct {
    PyObject_HEAD
    int d_rss_trigger;
    // Message. Add const char *message here that is a malloc copy of the string given in ProfileObject_init
    char *message;
    PyObject *trace_file_wrapper;
} ProfileObject;

static void
ProfileObject_dealloc(ProfileObject *self) {
    free(self->message);
    Py_XDECREF(self->trace_file_wrapper);
    Py_TYPE(self)->tp_free((PyObject *) self);
}

static PyObject *
ProfileObject_new(PyTypeObject *type, PyObject *Py_UNUSED(args), PyObject *Py_UNUSED(kwds)) {
    ProfileObject *self = (ProfileObject *) type->tp_alloc(type, 0);
    self->message = NULL;
    self->trace_file_wrapper = NULL;
    return (PyObject *) self;
}

static int
ProfileObject_init(ProfileObject *self, PyObject *args, PyObject *kwds) {
    static char *kwlist[] = {"d_rss_trigger", "message", NULL};
    int d_rss_trigger = -1;
    char *message = NULL;
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|is", kwlist, &d_rss_trigger, &message)) {
        return -1;
    }
    self->d_rss_trigger = d_rss_trigger;
    if (message) {
        self->message = malloc(strlen(message) + 1);
        if (self->message) {
            strcpy(self->message, message);
        } else {
            return -2;
        }
    }
    return 0;
}

static PyObject *
py_attach_profile_function(int d_rss_trigger, const char *message) {
    if (static_profile_wrapper) {
        Py_DECREF(static_profile_wrapper);
    }
    static_profile_wrapper = new_trace_file_wrapper(static_profile_wrapper, d_rss_trigger, message);
    if (static_profile_wrapper) {
        PyEval_SetProfile(&trace_or_profile_function, (PyObject *) static_profile_wrapper);
        Py_INCREF(static_profile_wrapper);
        // Write a marker, in this case it is the line number of the frame.
        trace_or_profile_function((PyObject *) static_profile_wrapper, PyEval_GetFrame(), PyTrace_LINE, Py_None);
        return (PyObject *) static_profile_wrapper;
    }
    PyErr_SetString(PyExc_RuntimeError, "Could not attach profile function.");
    return NULL;
}

static PyObject *
ProfileObject_enter(ProfileObject *self) {
    PyObject *trace_file_wrapper = py_attach_profile_function(self->d_rss_trigger, self->message);
    if (trace_file_wrapper == NULL) {
        return NULL;
    }
    self->trace_file_wrapper = trace_file_wrapper;
    Py_INCREF(self);
    return (PyObject *) self;
}

static PyObject *
ProfileObject_exit(ProfileObject *Py_UNUSED(self), PyObject *Py_UNUSED(args)) {
    if (static_profile_wrapper) {
        // Write a marker, in this case it is the line number of the frame.
        trace_or_profile_function((PyObject *) static_profile_wrapper, PyEval_GetFrame(), PyTrace_LINE, Py_None);
        fflush(static_profile_wrapper->file);
        Py_DECREF(static_profile_wrapper);
        /* TODO: Create list/stack of profilers. */
        static_profile_wrapper = NULL;
    }
    PyEval_SetProfile(NULL, NULL);
    Py_RETURN_FALSE;
}

static PyMemberDef ProfileObject_members[] = {
        {
                "trace_file_wrapper", Py_T_OBJECT_EX, offsetof(ProfileObject,
                                                               trace_file_wrapper), Py_READONLY,
                "The trace file wrapper."
        },
        {NULL, 0, 0, 0, NULL} /* Sentinel */
};

static PyMethodDef ProfileObject_methods[] = {
        {"__enter__", (PyCFunction) ProfileObject_enter, METH_NOARGS,
                "Attach a Profile object to the C runtime."},
        {"__exit__",  (PyCFunction) ProfileObject_exit,  METH_VARARGS,
                "Detach a Profile object from the C runtime."},
        {NULL, NULL, 0, NULL}  /* Sentinel */
};

static PyTypeObject ProfileObjectType = {
        PyVarObject_HEAD_INIT(NULL, 0)
        .tp_name = "cPyMemTrace.Profile",
        .tp_doc = "A context manager to attach a C profile function to the interpreter.\n"
                  "This takes one optional argument, ``d_rss_trigger``, that decides when a trace event gets recorded."
                  " Suitable values:\n\n-1 : whenever an RSS change >= page size (usually 4096 bytes) is noticed."
                  "\n\n0 : every event.\n\nn: whenever an RSS change >= n is noticed."
                  "\n\nDefault is -1."
                  "\n\nThis is slightly less invasive profiling than ``cPyMemTrace.Trace`` as the profile function is"
                  " called for all monitored events except the Python ``PyTrace_LINE PyTrace_OPCODE`` and"
                  " ``PyTrace_EXCEPTION`` events."
                  "\n\nThis writes to a file in the current working directory named \"YYYYmmdd_HHMMSS_<PID>.log\"",
        .tp_basicsize = sizeof(ProfileObject),
        .tp_itemsize = 0,
        .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
        .tp_new = ProfileObject_new,
        .tp_init = (initproc) ProfileObject_init,
        .tp_dealloc = (destructor) ProfileObject_dealloc,
        .tp_methods = ProfileObject_methods,
        .tp_members = ProfileObject_members,
};
/**** END: Context manager for attach_profile_function() and detach_profile_function() ****/

#pragma mark Context manager for TraceObject
/**** Context manager for attach_trace_function() and detach_trace_function() ****/
typedef struct {
    PyObject_HEAD
    int d_rss_trigger;
    char *message;
    PyObject *trace_file_wrapper;
} TraceObject;


static void
TraceObject_dealloc(TraceObject *self) {
    free(self->message);
    Py_XDECREF(self->trace_file_wrapper);
    Py_TYPE(self)->tp_free((PyObject *) self);
}

static PyObject *
TraceObject_new(PyTypeObject *type, PyObject *Py_UNUSED(args), PyObject *Py_UNUSED(kwds)) {
    TraceObject *self = (TraceObject *) type->tp_alloc(type, 0);
    self->message = NULL;
    self->trace_file_wrapper = NULL;
    return (PyObject *) self;
}

static int
TraceObject_init(TraceObject *self, PyObject *args, PyObject *kwds) {
    static char *kwlist[] = {"d_rss_trigger", "message", NULL};
    int d_rss_trigger = -1;
    char *message = NULL;
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|is", kwlist, &d_rss_trigger, &message)) {
        return -1;
    }
    self->d_rss_trigger = d_rss_trigger;
    if (message) {
        self->message = malloc(strlen(message) + 1);
        if (self->message) {
            strcpy(self->message, message);
        } else {
            return -2;
        }
    }
    return 0;
}

static PyObject *
py_attach_trace_function(int d_rss_trigger, const char *message) {
    if (static_trace_wrapper) {
        Py_DECREF(static_trace_wrapper);
    }
    static_trace_wrapper = new_trace_file_wrapper(static_trace_wrapper, d_rss_trigger, message);
    if (static_trace_wrapper) {
        PyEval_SetTrace(&trace_or_profile_function, (PyObject *) static_trace_wrapper);
        Py_INCREF(static_trace_wrapper);
        // Write a marker, in this case it is the line number of the frame.
        trace_or_profile_function((PyObject *) static_trace_wrapper, PyEval_GetFrame(), PyTrace_LINE, Py_None);
        return (PyObject *) static_trace_wrapper;
    }
    PyErr_SetString(PyExc_RuntimeError, "Could not attach trace function.");
    return NULL;
}

static PyObject *
TraceObject_enter(TraceObject *self) {
    PyObject *trace_file_wrapper = py_attach_trace_function(self->d_rss_trigger, self->message);
    if (trace_file_wrapper == NULL) {
        return NULL;
    }
    self->trace_file_wrapper = trace_file_wrapper;
    Py_INCREF(self);
    return (PyObject *) self;
}

static PyObject *
TraceObject_exit(TraceObject *Py_UNUSED(self), PyObject *Py_UNUSED(args)) {
    if (static_trace_wrapper) {
        // Write a marker, in this case it is the line number of the frame.
        trace_or_profile_function((PyObject *) static_trace_wrapper, PyEval_GetFrame(), PyTrace_LINE, Py_None);
        fflush(static_trace_wrapper->file);
        Py_DECREF(static_trace_wrapper);
        /* TODO: Create list/stack of profilers. */
        static_trace_wrapper = NULL;
    }
    PyEval_SetTrace(NULL, NULL);
    Py_RETURN_FALSE;
}

static PyMemberDef TraceObject_members[] = {
        {
                "trace_file_wrapper", Py_T_OBJECT_EX, offsetof(TraceObject,
                                                               trace_file_wrapper), Py_READONLY,
                "The trace file wrapper."
        },
        {NULL, 0, 0, 0, NULL} /* Sentinel */
};


static PyMethodDef TraceObject_methods[] = {
        {"__enter__", (PyCFunction) TraceObject_enter, METH_NOARGS,
                "Attach a Trace object to the C runtime."},
        {"__exit__",  (PyCFunction) TraceObject_exit,  METH_VARARGS,
                "Detach a Trace object from the C runtime."},
        {NULL, NULL, 0, NULL}  /* Sentinel */
};

static PyTypeObject TraceObjectType = {
        PyVarObject_HEAD_INIT(NULL, 0)
        .tp_name = "cPyMemTrace.Trace",
        .tp_doc = "A context manager to attach a C profile function to the interpreter.\n"
                  "This takes one optional argument, ``d_rss_trigger``, that decides when a trace event gets recorded."
                  " Suitable values:\n\n-1 : whenever an RSS change >= page size (usually 4096 bytes) is noticed."
                  "\n\n0 : every event.\n\nn: whenever an RSS change >= n is noticed."
                  "\n\nDefault is -1."
                  "\n\nThe tracing function does receive Python line-number events and per-opcode events"
                  " but does not receive any event related to C functionss being called."
                  " For that use ``cPyMemTrace.Profile``"
                  "\n\nThis writes to a file in the current working directory named \"YYYYmmdd_HHMMSS_<PID>.log\"",
        .tp_basicsize = sizeof(TraceObject),
        .tp_itemsize = 0,
        .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
        .tp_new = TraceObject_new,
        .tp_init = (initproc) TraceObject_init,
        .tp_dealloc = (destructor) TraceObject_dealloc,
        .tp_methods = TraceObject_methods,
        .tp_members = TraceObject_members,
};
/**** END: Context manager for attach_trace_function() and detach_trace_function() ****/

#pragma mark cPyMemTrace module

const char *PY_MEM_TRACE_DOC = "Module that contains C memory tracer classes and functions.";

PyDoc_STRVAR(py_mem_trace_doc,
             "Module that contains C memory tracer classes and functions."
             "\nNotably this has Profile() and Trace() that can attach to the Python runtime and report memory usage events."
);

static PyModuleDef cPyMemTracemodule = {
        PyModuleDef_HEAD_INIT,
        .m_name = "cPyMemTrace",
        .m_doc = py_mem_trace_doc,
        .m_size = -1,
        .m_methods = cPyMemTraceMethods,
};

PyMODINIT_FUNC
PyInit_cPyMemTrace(void) {
    PyObject *m = PyModule_Create(&cPyMemTracemodule);
    if (m == NULL) {
        return NULL;
    }
    /* TODO: decref the refcounts properly on failure. */

    /* This is a PyObject that wraps a C FILE object.
     * It is not visible at module level so PyModule_AddObject is not called.
     */
    if (PyType_Ready(&TraceFileWrapperType) < 0) {
        return NULL;
    }
    Py_INCREF(&TraceFileWrapperType);

    /* Add the Profile object. */
    if (PyType_Ready(&ProfileObjectType) < 0) {
        Py_DECREF(m);
        return NULL;
    }
    Py_INCREF(&ProfileObjectType);
    if (PyModule_AddObject(m, "Profile", (PyObject *) &ProfileObjectType) < 0) {
        Py_DECREF(&ProfileObjectType);
        Py_DECREF(m);
        return NULL;
    }

    /* Add the Trace object. */
    if (PyType_Ready(&TraceObjectType) < 0) {
        Py_DECREF(m);
        return NULL;
    }
    Py_INCREF(&TraceObjectType);
    if (PyModule_AddObject(m, "Trace", (PyObject *) &TraceObjectType) < 0) {
        Py_DECREF(&TraceObjectType);
        Py_DECREF(m);
        return NULL;
    }
    return m;
}
