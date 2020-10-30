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

#include <time.h>

#include "get_rss.h"



static int
trace_function(PyObject *Py_UNUSED(obj), PyFrameObject *frame, int what, PyObject *arg) {
    int line_number = PyFrame_GetLineNumber(frame);
    PyObject *file_name = frame->f_code->co_filename;
    Py_INCREF(file_name); // Hang on to a 'borrowed' reference.
    size_t rss = getCurrentRSS();
    size_t rss_peak = getPeakRSS();
    clock_t clock_time = clock();
    double clock_seconds = (double) clock_time / CLOCKS_PER_SEC;
    const char* func_name = NULL;
    if (what == PyTrace_C_CALL || what == PyTrace_C_RETURN) {
        func_name = PyEval_GetFuncName(arg);
    }
    fprintf(stdout,
            "%f %d Function: %s#%d %s RSS: %zu Peak RSS: %zu\n",
            clock_seconds, what, PyUnicode_1BYTE_DATA(file_name), line_number, func_name, rss, rss_peak
            );
    Py_DECREF(file_name); // Let go of borrowed reference
    return 0;
}

static PyObject *
trace_function_attach(PyObject *Py_UNUSED(module), PyObject *args, PyObject *kwds) {
    static char *kwlist[] = {"trace", NULL};
    int trace = 0;

    if (! PyArg_ParseTupleAndKeywords(args, kwds, "|p", kwlist, &trace)) {
        return NULL;
    }
    if (trace) {
        PyEval_SetTrace(&trace_function, NULL);
    } else {
        PyEval_SetProfile(&trace_function, NULL);
    }
    Py_RETURN_NONE;
}

static PyObject *
trace_function_detach(PyObject *Py_UNUSED(module)) {
    // TODO: decide which to do.
//    PyEval_SetTrace(NULL, NULL);
    PyEval_SetProfile(NULL, NULL);
    Py_RETURN_NONE;
}

typedef struct {
    PyObject_HEAD
    PyObject *first; /* first name */
    PyObject *last;  /* last name */
    int number;
} CustomObject;

static void
Custom_dealloc(CustomObject *self) {
    Py_XDECREF(self->first);
    Py_XDECREF(self->last);
    Py_TYPE(self)->tp_free((PyObject *) self);
}

static PyObject *
Custom_new(PyTypeObject *type, PyObject *Py_UNUSED(args), PyObject *Py_UNUSED(kwds)) {
    CustomObject *self;
    self = (CustomObject *) type->tp_alloc(type, 0);
    if (self != NULL) {
        self->first = PyUnicode_FromString("");
        if (self->first == NULL) {
            Py_DECREF(self);
            return NULL;
        }
        self->last = PyUnicode_FromString("");
        if (self->last == NULL) {
            Py_DECREF(self);
            return NULL;
        }
        self->number = 0;
    }
    return (PyObject *) self;
}

static int
Custom_init(CustomObject *self, PyObject *args, PyObject *kwds) {
    static char *kwlist[] = {"first", "last", "number", NULL};
    PyObject *first = NULL, *last = NULL, *tmp;

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|UUi", kwlist,
                                     &first, &last,
                                     &self->number))
        return -1;

    if (first) {
        tmp = self->first;
        Py_INCREF(first);
        self->first = first;
        Py_DECREF(tmp);
    }
    if (last) {
        tmp = self->last;
        Py_INCREF(last);
        self->last = last;
        Py_DECREF(tmp);
    }
    return 0;
}

static PyMemberDef Custom_members[] = {
    {"number", T_INT, offsetof(CustomObject, number), 0,
     "custom number"},
    {NULL, 0, 0, 0, NULL}  /* Sentinel */
};

static PyObject *
Custom_getfirst(CustomObject *self, void *Py_UNUSED(closure)) {
    Py_INCREF(self->first);
    return self->first;
}

static int
Custom_setfirst(CustomObject *self, PyObject *value, void *Py_UNUSED(closure)) {
    PyObject *tmp;
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError, "Cannot delete the first attribute");
        return -1;
    }
    if (!PyUnicode_Check(value)) {
        PyErr_SetString(PyExc_TypeError,
                        "The first attribute value must be a string");
        return -1;
    }
    tmp = self->first;
    Py_INCREF(value);
    self->first = value;
    Py_DECREF(tmp);
    return 0;
}

static PyObject *
Custom_getlast(CustomObject *self, void *closure) {
    (void) closure;
    Py_INCREF(self->last);
    return self->last;
}

static int
Custom_setlast(CustomObject *self, PyObject *value, void *Py_UNUSED(closure)) {
    PyObject *tmp;
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError, "Cannot delete the last attribute");
        return -1;
    }
    if (!PyUnicode_Check(value)) {
        PyErr_SetString(PyExc_TypeError,
                        "The last attribute value must be a string");
        return -1;
    }
    tmp = self->last;
    Py_INCREF(value);
    self->last = value;
    Py_DECREF(tmp);
    return 0;
}

static PyGetSetDef Custom_getsetters[] = {
    {"first", (getter) Custom_getfirst, (setter) Custom_setfirst,
     "first name", NULL},
    {"last", (getter) Custom_getlast, (setter) Custom_setlast,
     "last name", NULL},
    {NULL, NULL, NULL, NULL, NULL}  /* Sentinel */
};

static PyObject *
Custom_name(CustomObject *self, PyObject *Py_UNUSED(ignored)) {
    return PyUnicode_FromFormat("%S %S", self->first, self->last);
}

static PyMethodDef Custom_methods[] = {
    {"name", (PyCFunction) Custom_name, METH_NOARGS,
     "Return the name, combining the first and last name"
    },
    {NULL, NULL, 0, NULL}  /* Sentinel */
};

static PyTypeObject CustomType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "custom3.Custom",
    .tp_doc = "Custom objects",
    .tp_basicsize = sizeof(CustomObject),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
    .tp_new = Custom_new,
    .tp_init = (initproc) Custom_init,
    .tp_dealloc = (destructor) Custom_dealloc,
    .tp_members = Custom_members,
    .tp_methods = Custom_methods,
    .tp_getset = Custom_getsetters,
};

static PyMethodDef Custom3Methods[] = {
    {"attach",  (PyCFunction) trace_function_attach,
     METH_VARARGS | METH_KEYWORDS, "Attach a C trace function to the interpreter."},
    {"detach",  (PyCFunction) trace_function_detach,
     METH_NOARGS, "Detach the C trace function to the interpreter."},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

static PyModuleDef custommodule = {
    PyModuleDef_HEAD_INIT,
    .m_name = "custom3",
    .m_doc = "Example module that creates an extension type.",
    .m_size = -1,
    .m_methods = Custom3Methods,
};

PyMODINIT_FUNC
PyInit_custom3(void) {
    PyObject *m;
    if (PyType_Ready(&CustomType) < 0)
        return NULL;

    m = PyModule_Create(&custommodule);
    if (m == NULL)
        return NULL;

    Py_INCREF(&CustomType);
    if (PyModule_AddObject(m, "Custom", (PyObject *) &CustomType) < 0) {
        Py_DECREF(&CustomType);
        Py_DECREF(m);
        return NULL;
    }
    return m;
}
