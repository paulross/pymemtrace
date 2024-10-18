/*
 * Created by Paul Ross on 29/10/2020.
 * This contains the Python interface to the C memory tracer.
 *
 * Monitored events are: PyTrace_CALL, PyTrace_C_CALL, PyTrace_C_EXCEPTION, PyTrace_C_RETURN, PyTrace_EXCEPTION,
 * PyTrace_LINE, PyTrace_OPCODE, PyTrace_RETURN
 *
 * PyEval_SetProfile: The profile function is called for all monitored events except PyTrace_LINE PyTrace_OPCODE and PyTrace_EXCEPTION.
 *
 * PyEval_setTrace: This is similar to PyEval_SetProfile(), except the tracing function does receive line-number events
 *  and per-opcode events, but does not receive any event related to C function objects being called. Any trace function
 *  registered using PyEval_SetTrace() will not receive PyTrace_C_CALL, PyTrace_C_EXCEPTION or PyTrace_C_RETURN as a
 *  value for the what parameter.
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

static PyTypeObject TraceFileWrapperType = {
        PyVarObject_HEAD_INIT(NULL, 0)
        .tp_name = "cPyMemTrace.TraceFileWrapper",
        .tp_doc = "Wrapper round a trace-to-file object.",
        .tp_basicsize = sizeof(TraceFileWrapper),
        .tp_itemsize = 0,
        .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
        .tp_new = TraceFileWrapper_new,
        .tp_dealloc = (destructor) TraceFileWrapper_dealloc,
};

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
static const char* WHAT_STRINGS[] = {
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

    TraceFileWrapper *trace_wrapper = (TraceFileWrapper *)pobj;
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
        func_name = (const char *)PyUnicode_1BYTE_DATA(PyFrame_GetCode(frame)->co_name);
#else
        func_name = (const char *)PyUnicode_1BYTE_DATA(frame->f_code->co_name);
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
        snprintf(file_path_buffer, PYMEMTRACE_PATH_NAME_MAX_LENGTH, "%s%c%s", current_working_directory(), seperator, filename);
        fprintf(stdout, "Opening log file %s\n", file_path_buffer);
        trace_wrapper = (TraceFileWrapper *)TraceFileWrapper_new(&TraceFileWrapperType, NULL, NULL);
        if (trace_wrapper) {
            trace_wrapper->file = fopen(filename, "w");
            if (trace_wrapper->file) {
                // Copy the filename
                trace_wrapper->log_file_path = malloc(strlen(file_path_buffer) + 1);
                strcpy(trace_wrapper->log_file_path, file_path_buffer);
                // Write the message to the log file
                fprintf(trace_wrapper->file, "%s\n", message);
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
                } else  {
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

static TraceFileWrapper *static_profile_wrapper = NULL;
static TraceFileWrapper *static_trace_wrapper = NULL;

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

static PyObject *
py_attach_profile_function(int d_rss_trigger, const char *message) {
    static_profile_wrapper = new_trace_file_wrapper(static_profile_wrapper, d_rss_trigger, message);
    if (static_profile_wrapper) {
        PyEval_SetProfile(&trace_or_profile_function, (PyObject *)static_profile_wrapper);
        Py_RETURN_NONE;
    }
    PyErr_SetString(PyExc_RuntimeError, "Could not attach profile function.");
    return NULL;
}

static PyObject *
py_detach_profile_function(void) {
    if (static_profile_wrapper) {
        TraceFileWrapper_dealloc(static_profile_wrapper);
        static_profile_wrapper = NULL;
    }
    PyEval_SetProfile(NULL, NULL);
    Py_RETURN_NONE;
}

static PyObject *
py_attach_trace_function(int d_rss_trigger, const char *message) {
    static_trace_wrapper = new_trace_file_wrapper(static_trace_wrapper, d_rss_trigger, message);
    if (static_trace_wrapper) {
        PyEval_SetTrace(&trace_or_profile_function, (PyObject *)static_trace_wrapper);
        Py_RETURN_NONE;
    }
    PyErr_SetString(PyExc_RuntimeError, "Could not attach trace function.");
    return NULL;
}

static PyObject *
py_detach_trace_function(void) {
    if (static_trace_wrapper) {
        TraceFileWrapper_dealloc(static_trace_wrapper);
        static_trace_wrapper = NULL;
    }
    PyEval_SetTrace(NULL, NULL);
    Py_RETURN_NONE;
}

static PyObject *
py_rss(void) {
    return PyLong_FromSize_t(getCurrentRSS_alternate());
}

static PyObject *
py_rss_peak(void) {
    return PyLong_FromSize_t(getPeakRSS());
}

static PyMethodDef cPyMemTraceMethods[] = {
    {"rss",   (PyCFunction) py_rss, METH_NOARGS, "Return the current RSS in bytes."},
    {"rss_peak",   (PyCFunction) py_rss_peak, METH_NOARGS, "Return the peak RSS in bytes."},
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

/**** Context manager for attach_profile_function() and detach_profile_function() ****/
typedef struct {
    PyObject_HEAD
    int d_rss_trigger;
    // Message. Add const char *message here that is a malloc copy of the string given in ProfileObject_init
    char *message;
} ProfileObject;

static void
ProfileObject_dealloc(ProfileObject *self) {
    free(self->message);
    Py_TYPE(self)->tp_free((PyObject *) self);
}

static PyObject *
ProfileObject_new(PyTypeObject *type, PyObject *Py_UNUSED(args), PyObject *Py_UNUSED(kwds)) {
    ProfileObject *self = (ProfileObject *) type->tp_alloc(type, 0);
    self->message = NULL;
    return (PyObject *) self;
}

static int
ProfileObject_init(ProfileObject *self, PyObject *args, PyObject *kwds) {
    static char *kwlist[] = {"d_rss_trigger", "message", NULL};
    int d_rss_trigger = -1;
    char *message = NULL;
    if (! PyArg_ParseTupleAndKeywords(args, kwds, "|is", kwlist, &d_rss_trigger, &message)) {
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
ProfileObject_enter(ProfileObject *self) {
    if (py_attach_profile_function(self->d_rss_trigger, self->message) == NULL) {
        return NULL;
    }
    Py_INCREF(self);
    return (PyObject *) self;
}

static PyObject *
ProfileObject_exit(ProfileObject *Py_UNUSED(self), PyObject *Py_UNUSED(args)) {
    py_detach_profile_function();
    Py_RETURN_FALSE;
}

static PyMethodDef ProfileObject_methods[] = {
        {"__enter__", (PyCFunction) ProfileObject_enter, METH_NOARGS,
         "Attach a Profile object to the C runtime."},
        {"__exit__", (PyCFunction) ProfileObject_exit, METH_VARARGS,
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
                  "\n\nThis writes to a file in the current working directory named \"YYYYmmdd_HHMMSS_<PID>.log\""
                  ,
        .tp_basicsize = sizeof(ProfileObject),
        .tp_itemsize = 0,
        .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
        .tp_new = ProfileObject_new,
        .tp_init = (initproc) ProfileObject_init,
        .tp_dealloc = (destructor) ProfileObject_dealloc,
        .tp_methods = ProfileObject_methods,
};
/**** END: Context manager for attach_profile_function() and detach_profile_function() ****/

/**** Context manager for attach_trace_function() and detach_trace_function() ****/
typedef struct {
    PyObject_HEAD
    int d_rss_trigger;
    char *message;
} TraceObject;

static void
TraceObject_dealloc(TraceObject *self) {
    free(self->message);
    Py_TYPE(self)->tp_free((PyObject *) self);
}

static PyObject *
TraceObject_new(PyTypeObject *type, PyObject *Py_UNUSED(args), PyObject *Py_UNUSED(kwds)) {
    TraceObject *self = (TraceObject *) type->tp_alloc(type, 0);
    self->message = NULL;
    return (PyObject *) self;
}

static int
TraceObject_init(TraceObject *self, PyObject *args, PyObject *kwds) {
    static char *kwlist[] = {"d_rss_trigger", "message", NULL};
    int d_rss_trigger = -1;
    char *message =NULL;
    if (! PyArg_ParseTupleAndKeywords(args, kwds, "|is", kwlist, &d_rss_trigger, &message)) {
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
TraceObject_enter(TraceObject *self) {
    /* Could use cPyMemTracemodule. */
    if (py_attach_trace_function(self->d_rss_trigger, self->message) == NULL) {
        return NULL;
    }
    Py_INCREF(self);
    return (PyObject *) self;
}

static PyObject *
TraceObject_exit(TraceObject *Py_UNUSED(self), PyObject *Py_UNUSED(args)) {
    /* Could use cPyMemTracemodule. */
    py_detach_trace_function();
    Py_RETURN_FALSE;
}

static PyMethodDef TraceObject_methods[] = {
        {"__enter__", (PyCFunction) TraceObject_enter, METH_NOARGS,
         "Attach a Trace object to the C runtime."},
        {"__exit__", (PyCFunction) TraceObject_exit, METH_VARARGS,
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
                  "\n\nThis writes to a file in the current working directory named \"YYYYmmdd_HHMMSS_<PID>.log\""
                  ,
        .tp_basicsize = sizeof(TraceObject),
        .tp_itemsize = 0,
        .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
        .tp_new = TraceObject_new,
        .tp_init = (initproc) TraceObject_init,
        .tp_dealloc = (destructor) TraceObject_dealloc,
        .tp_methods = TraceObject_methods,
};
/**** END: Context manager for attach_trace_function() and detach_trace_function() ****/

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
    if(m == NULL) {
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
