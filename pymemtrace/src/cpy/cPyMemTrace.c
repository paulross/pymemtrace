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
#include <unistd.h>
#include <assert.h>

#include "get_rss.h"

/*
 * Trace classes could make this available by looking at trace_file_wrapper or profile_file_wrapper.
 */
typedef struct {
    PyObject_HEAD
    FILE *file;
    size_t event_number;
    size_t rss;
} TraceFileWrapper;

static void
TraceFileWrapper_dealloc(TraceFileWrapper *self) {
    if (self->file) {
        fclose(self->file);
    }
    Py_TYPE(self)->tp_free((PyObject *) self);
}

static PyObject *
TraceFileWrapper_new(PyTypeObject *type, PyObject *Py_UNUSED(args), PyObject *Py_UNUSED(kwds)) {
    TraceFileWrapper *self;
    self = (TraceFileWrapper *) type->tp_alloc(type, 0);
    if (self != NULL) {
        self->file = NULL;
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

#define PY_MEM_TRACE_WRITE_OUTPUT
//#undef PY_MEM_TRACE_WRITE_OUTPUT
#define PY_MEM_TRACE_WRITE_OUTPUT_CLOCK
//#undef PY_MEM_TRACE_WRITE_OUTPUT_CLOCK
/* If defined as non-zero then only output a result when the difference in RSS is +/- this value. */
#define PY_MEM_TRACE_WRITE_OUTPUT_D_RSS 4096

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
 * These are trimmed to be a maximum of 8 long.
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
    const unsigned char *file_name = PyUnicode_1BYTE_DATA(frame->f_code->co_filename);
    int line_number = PyFrame_GetLineNumber(frame);
    const char *func_name = NULL;
    if (what == PyTrace_C_CALL || what == PyTrace_C_EXCEPTION || what == PyTrace_C_RETURN) {
        func_name = PyEval_GetFuncName(arg);
    } else {
        func_name = (const char *)PyUnicode_1BYTE_DATA(frame->f_code->co_name);
    }
    long d_rss = rss - trace_wrapper->rss;
    if (labs(d_rss) >= PY_MEM_TRACE_WRITE_OUTPUT_D_RSS) {
#ifdef PY_MEM_TRACE_WRITE_OUTPUT_CLOCK
        double clock_time = (double) clock() / CLOCKS_PER_SEC;
        fprintf(trace_wrapper->file,
                "%-12zu %-12.6f %-8s %-120s#%4d %-32s %12zu %12ld %p\n",
                trace_wrapper->event_number, clock_time, WHAT_STRINGS[what], file_name, line_number, func_name, rss,
                d_rss, (void *)frame->f_code->co_filename);
#else
        fprintf(trace_wrapper->file,
                "%-12zu %-8s %-120s#%4d %-32s %12zu %12ld %p\n",
                trace_wrapper->event_number, WHAT_STRINGS[what], file_name, line_number, func_name, rss,
                d_rss, (void *)frame->f_code->co_filename);
#endif
    }
#endif
    trace_wrapper->event_number++;
    trace_wrapper->rss = rss;
    return 0;
}

static TraceFileWrapper *trace_wrapper = NULL;
static TraceFileWrapper *profile_wrapper = NULL;

static char *
create_filename() {
    /* Not thread safe. */
    static char filename[256];
    static struct tm now;
    time_t t = time(NULL);
    gmtime_r(&t, &now);
    size_t len = strftime(filename, 256, "%Y%m%d_%H%M%S", &now);
    if (len == 0) {
        fprintf(stderr, "create_filename(): strftime failed.");
        return NULL;
    }
    pid_t pid = getpid();
    if (snprintf(filename + len, 256 - len - 1, "_%d.log", pid) == 0) {
        fprintf(stderr, "create_filename(): failed to add PID.");
        return NULL;
    }
    return filename;
}

static char *
current_working_directory() {
    static char cwd[PATH_MAX];
    if (getcwd(cwd, sizeof(cwd)) == NULL) {
        fprintf(stderr, "Can not get current working directory.\n");
        return NULL;
    }
    return cwd;
}

static TraceFileWrapper *
new_trace_wrapper() {
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
        fprintf(stdout, "Opening log file %s%c%s\n", current_working_directory(), seperator, filename);
        trace_wrapper = (TraceFileWrapper *)TraceFileWrapper_new(&TraceFileWrapperType, NULL, NULL);
        if (trace_wrapper) {
            trace_wrapper->file = fopen(filename, "w");
            if (trace_wrapper->file) {
//                fprintf(trace_wrapper->file, "%s\n", filename);
#ifdef PY_MEM_TRACE_WRITE_OUTPUT_CLOCK
                fprintf(trace_wrapper->file, "%-12s %-12s %-8s %-120s#%4s %-32s %12s\n",
                        "Event", "Clock", "What", "File", "line", "Function", "RSS"
                );
#else
                fprintf(trace_wrapper->file, "%-12s %-8s %-120s#%4s %-32s %12s\n",
                        "Event", "What", "File", "line", "Function", "RSS"
                );
#endif
                trace_wrapper->event_number = 0;
                trace_wrapper->rss = 0;
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

static PyObject *
attach_trace_function(PyObject *Py_UNUSED(module)) {
    TraceFileWrapper *wrapper = new_trace_wrapper();
    if (wrapper) {
        PyEval_SetTrace(&trace_or_profile_function, (PyObject *)wrapper);
        Py_RETURN_NONE;
    }
    PyErr_SetString(PyExc_RuntimeError, "Could not attach trace function.");
    return NULL;
}

static PyObject *
attach_profile_function(PyObject *Py_UNUSED(module)) {
    TraceFileWrapper *wrapper = new_trace_wrapper();
    if (wrapper) {
        PyEval_SetProfile(&trace_or_profile_function, (PyObject *)wrapper);
        Py_RETURN_NONE;
    }
    PyErr_SetString(PyExc_RuntimeError, "Could not attach profile function.");
    return NULL;
}

static PyObject *
detach_trace_function(PyObject *Py_UNUSED(module)) {
    if (trace_wrapper) {
        TraceFileWrapper_dealloc(trace_wrapper);
        trace_wrapper = NULL;
    }
    PyEval_SetTrace(NULL, NULL);
    Py_RETURN_NONE;
}

static PyObject *
detach_profile_function(PyObject *Py_UNUSED(module)) {
    if (profile_wrapper) {
        TraceFileWrapper_dealloc(profile_wrapper);
        profile_wrapper = NULL;
    }
    PyEval_SetProfile(NULL, NULL);
    Py_RETURN_NONE;
}

static PyMethodDef cPyMemTraceMethods[] = {
    {"_attach_trace",   (PyCFunction) attach_trace_function, METH_NOARGS,
     "Attach a C trace function to the interpreter.\n"
     "This receives Python line-number events and per-opcode events, but does not receive any event related to C"
     " function objects being called (PyTrace_C_CALL, PyTrace_C_EXCEPTION or PyTrace_C_RETURN)."
     },
    {"_detach_trace",   (PyCFunction) detach_trace_function, METH_NOARGS,
     "Detach the C trace function from the interpreter."},
    {"_attach_profile", (PyCFunction) attach_profile_function, METH_NOARGS,
     "Attach a C profile function to the interpreter.\n"
     "This is slightly less invasive profiling as the profile function is called for all monitored events except"
     " the Python PyTrace_LINE PyTrace_OPCODE and PyTrace_EXCEPTION events."
     },
    {"_detach_profile", (PyCFunction) detach_profile_function, METH_NOARGS,
     "Detach the C profile function from the interpreter."},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

/**** Context manager for attach_profile_function() and detach_profile_function() ****/
typedef struct {
    PyObject_HEAD
} ProfileObject;

static void
ProfileObject_dealloc(ProfileObject *self) {
    Py_TYPE(self)->tp_free((PyObject *) self);
}

static PyObject *
ProfileObject_new(PyTypeObject *type, PyObject *Py_UNUSED(args), PyObject *Py_UNUSED(kwds)) {
    ProfileObject *self = (ProfileObject *) type->tp_alloc(type, 0);
    return (PyObject *) self;
}

static int
ProfileObject_init(PyTypeObject *Py_UNUSED(self), PyObject *args, PyObject *kwds) {
    static char *kwlist[] = {NULL};
    if (! PyArg_ParseTupleAndKeywords(args, kwds, "", kwlist)) {
        return -1;
    }
    return 0;
}

static PyObject *
ProfileObject_enter(ProfileObject *self) {
    /* Could use &cPyMemTracemodule */
    attach_profile_function(NULL);
    Py_INCREF(self);
    return (PyObject *) self;
}

static PyObject *
ProfileObject_exit(ProfileObject *Py_UNUSED(self), PyObject *Py_UNUSED(args)) {
    /* Could use &cPyMemTracemodule */
    detach_profile_function(NULL);
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
                  "This is slightly less invasive profiling as the profile function is called for all monitored events except"
                  " the Python PyTrace_LINE PyTrace_OPCODE and PyTrace_EXCEPTION events.",
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
} TraceObject;

static void
TraceObject_dealloc(TraceObject *self) {
    Py_TYPE(self)->tp_free((PyObject *) self);
}

static PyObject *
TraceObject_new(PyTypeObject *type, PyObject *Py_UNUSED(args), PyObject *Py_UNUSED(kwds)) {
    TraceObject *self = (TraceObject *) type->tp_alloc(type, 0);
    return (PyObject *) self;
}

static int
TraceObject_init(PyTypeObject *Py_UNUSED(self), PyObject *args, PyObject *kwds) {
    static char *kwlist[] = {NULL};
    if (! PyArg_ParseTupleAndKeywords(args, kwds, "", kwlist)) {
        return -1;
    }
    return 0;
}

static PyObject *
TraceObject_enter(TraceObject *self) {
    /* Could use cPyMemTracemodule. */
    attach_trace_function(NULL);
    Py_INCREF(self);
    return (PyObject *) self;
}

static PyObject *
TraceObject_exit(TraceObject *Py_UNUSED(self), PyObject *Py_UNUSED(args)) {
    /* Could use cPyMemTracemodule. */
    detach_trace_function(NULL);
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
                  " The tracing function does receive Python line-number events and per-opcode events"
                  " but does not receive any event related to C function objects being called.",
        .tp_basicsize = sizeof(TraceObject),
        .tp_itemsize = 0,
        .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
        .tp_new = TraceObject_new,
        .tp_init = (initproc) TraceObject_init,
        .tp_dealloc = (destructor) TraceObject_dealloc,
        .tp_methods = TraceObject_methods,
};
/**** END: Context manager for attach_trace_function() and detach_trace_function() ****/

static PyModuleDef cPyMemTracemodule = {
    PyModuleDef_HEAD_INIT,
    .m_name = "cPyMemTrace",
    .m_doc = "Module that contains C memory tracer functions.",
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
