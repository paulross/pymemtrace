/*
 * Created by Paul Ross on 29/10/2020.
 * This contains the Python interface to the C memory tracer.
 *
 * Monitored events are:
 * PyTrace_CALL
 * PyTrace_C_CALL
 * PyTrace_C_EXCEPTION
 * PyTrace_C_RETURN
 * PyTrace_EXCEPTION
 * PyTrace_LINE
 * PyTrace_OPCODE
 * PyTrace_RETURN
 *
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
 * PyEval_SetProfile: The profile function is called for all monitored events except PyTrace_LINE PyTrace_OPCODE and PyTrace_EXCEPTION.
 *
 * PyEval_setTrace: This is similar to PyEval_SetProfile(), except the tracing function does receive line-number events
 *  and per-opcode events, but does not receive any event related to C function objects being called. Any trace function
 *  registered using PyEval_SetTrace() will not receive PyTrace_C_CALL, PyTrace_C_EXCEPTION or PyTrace_C_RETURN as a
 *  value for the what parameter.
 *
 *
*/
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "structmember.h"
#include "frameobject.h"

#include <stdio.h>
#include <time.h>
//#include <stdlib.h>
#include <unistd.h>
#include <assert.h>

#include "get_rss.h"

typedef struct {
    PyObject_HEAD
    FILE* file;
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

//static int
//TraceFileWrapper_init(TraceFileWrapper *self, PyObject *args, PyObject *kwds) {
//    static char *kwlist[] = {"trace", NULL};
//
//    if (! PyArg_ParseTupleAndKeywords(args, kwds, "|p", kwlist, &self->is_trace)) {
//        return NULL;
//    }
//    return 0;
//}

//static PyMemberDef Custom_members[] = {
//    {NULL, 0, 0, 0, NULL}  /* Sentinel */
//};
//
//static PyGetSetDef Custom_getsetters[] = {
//        {NULL, NULL, NULL, NULL, NULL}  /* Sentinel */
//};
//
//static PyMethodDef Custom_methods[] = {
//        {NULL, NULL, 0, NULL}  /* Sentinel */
//};

static PyTypeObject TraceFileWrapperType = {
        PyVarObject_HEAD_INIT(NULL, 0)
        .tp_name = "cPyMemTrace.TraceFileWrapper",
        .tp_doc = "Wrapper round a trace-to-file object.",
        .tp_basicsize = sizeof(TraceFileWrapper),
        .tp_itemsize = 0,
        .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
        .tp_new = TraceFileWrapper_new,
//        .tp_init = (initproc) TraceFileWrapper_init,
        .tp_dealloc = (destructor) TraceFileWrapper_dealloc,
//        .tp_members = Custom_members,
//        .tp_methods = Custom_methods,
//        .tp_getset = Custom_getsetters,
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
 * These are trimmed to be a maximum of 8 long.
 */
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

static int
trace_or_profile_function(PyObject *trace_wrapper, PyFrameObject *frame, int what, PyObject *arg) {
    assert(Py_TYPE(trace_wrapper) == &TraceFileWrapperType && "trace_wrapper is not a TraceFileWrapperType.");
    int line_number = PyFrame_GetLineNumber(frame);
    PyObject *file_name = frame->f_code->co_filename;
    Py_INCREF(file_name); // Hang on to a 'borrowed' reference.
    size_t rss = getCurrentRSS();
//    size_t rss_peak = getPeakRSS();
    clock_t clock_time = clock();
    double clock_seconds = (double) clock_time / CLOCKS_PER_SEC;
    const char* func_name = NULL;
    if (what == PyTrace_C_CALL || what == PyTrace_C_EXCEPTION || what == PyTrace_C_RETURN) {
        func_name = PyEval_GetFuncName(arg);
    } else {
        func_name = (const char*)PyUnicode_1BYTE_DATA(frame->f_code->co_name);
    }
    fprintf(((TraceFileWrapper *)trace_wrapper)->file,
            "%-12.6f %-8s %-24s#%4d %-32s %12zu\n",
            clock_seconds, WHAT_STRINGS[what], PyUnicode_1BYTE_DATA(file_name), line_number, func_name, rss
            );
    Py_DECREF(file_name); // Let go of borrowed reference
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
    fprintf(stdout, "Created filename: %s\n", filename);
    return filename;
}

static TraceFileWrapper *
new_trace_wrapper() {
    if (trace_wrapper) {
        TraceFileWrapper_dealloc(trace_wrapper);
        trace_wrapper = NULL;
    }
    char *filename = create_filename();
    if (filename) {
        trace_wrapper = (TraceFileWrapper *)TraceFileWrapper_new(&TraceFileWrapperType, NULL, NULL);
        if (trace_wrapper) {
            trace_wrapper->file = fopen(filename, "w");
            if (trace_wrapper->file) {
                fprintf(trace_wrapper->file, "%s\n", filename);
                fprintf(trace_wrapper->file, "%-12s %-8s %-24s#%4s %-32s %12s\n",
                        "Clock", "What", "File", "line", "Function", "RSS"
                );
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
    {"attach_trace",   (PyCFunction) attach_trace_function, METH_NOARGS, "Attach a C trace function to the interpreter."},
    {"detach_trace",   (PyCFunction) detach_trace_function, METH_NOARGS, "Detach the C trace function from the interpreter."},
    {"attach_profile", (PyCFunction) attach_profile_function, METH_NOARGS, "Attach a C profile function to the interpreter."},
    {"detach_profile", (PyCFunction) detach_profile_function, METH_NOARGS, "Detach the C profile function from the interpreter."},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

static PyModuleDef cPyMemTracemodule = {
    PyModuleDef_HEAD_INIT,
    .m_name = "cPyMemTrace",
    .m_doc = "Module that contains C memory tracer functions.",
    .m_size = -1,
    .m_methods = cPyMemTraceMethods,
};

PyMODINIT_FUNC
PyInit_cPyMemTrace(void) {
    PyObject *m;
    if (PyType_Ready(&TraceFileWrapperType) < 0)
        return NULL;

    m = PyModule_Create(&cPyMemTracemodule);
    if (m == NULL)
        return NULL;

//    Py_INCREF(&TraceFileWrapperType);
//    if (PyModule_AddObject(m, "TraceFileWrapper", (PyObject *) &TraceFileWrapperType) < 0) {
//        Py_DECREF(&TraceFileWrapperType);
//        Py_DECREF(m);
//        return NULL;
//    }
    return m;
}
