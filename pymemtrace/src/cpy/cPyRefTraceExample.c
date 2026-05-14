//
// Created by Paul Ross on 14/05/2026.
//

#define PY_SSIZE_T_CLEAN

#include <Python.h>
#include "structmember.h"

struct ref_trace_data {
    size_t count_new;
    size_t count_del;
};

static int
ref_trace_callback(PyObject *Py_UNUSED(obj), PyRefTracerEvent event, void *data) {
    assert(data);
    struct ref_trace_data *data_alias = (struct ref_trace_data *) data;

    if (event == PyRefTracer_CREATE) {
        data_alias->count_new++;
    } else if (event == PyRefTracer_DESTROY) {
        data_alias->count_del++;
    } else {
        // Ignore unknown events.
    }
    return 0;
}

typedef struct {
    PyObject_HEAD
    struct ref_trace_data *data;
} cpyRefTraceCount;

static PyObject *
cpyRefTraceCount_new(PyTypeObject *type, PyObject *Py_UNUSED(args), PyObject *Py_UNUSED(kwds)) {
    assert(!PyErr_Occurred());
    cpyRefTraceCount *self;
    self = (cpyRefTraceCount *) type->tp_alloc(type, 0);
    if (self != NULL) {
        self->data = malloc(sizeof(struct ref_trace_data));
        if (!self->data) {
            PyErr_SetString(PyExc_MemoryError, "Can not malloc struct ref_trace_data");
            return NULL;
        }
        self->data->count_new = 0;
        self->data->count_del = 0;
    }
    return (PyObject *) self;
}

static int
cpyRefTraceCount_init(cpyRefTraceCount *self, PyObject *Py_UNUSED(args), PyObject *Py_UNUSED(kwds)) {
    assert(!PyErr_Occurred());
    if (PyRefTracer_SetTracer(&ref_trace_callback, (void *) self->data)) {
        return -1;
    }
    return 0;
}

static void
cpyRefTraceCount_dealloc(cpyRefTraceCount *self) {
    free(self->data);
    self->data = NULL;
    /* De-register the tracer. */
    PyRefTracer_SetTracer(NULL, NULL);
    PyObject_Del((PyObject *) self);
}

static PyObject *
cpyRefTraceCount_count_new(cpyRefTraceCount *self) {
    assert(!PyErr_Occurred());
    return PyLong_FromSize_t(self->data->count_new);
}

static PyObject *
cpyRefTraceCount_count_del(cpyRefTraceCount *self) {
    assert(!PyErr_Occurred());
    return PyLong_FromSize_t(self->data->count_del);
}

static PyMethodDef cpyRefTraceCount_methods[] = {
        {
                "count_new",
                (PyCFunction) cpyRefTraceCount_count_new,
                METH_NOARGS,
                "Return the count of new allocations."
        },
        {
                "count_del",
                (PyCFunction) cpyRefTraceCount_count_del,
                METH_NOARGS,
                "Return the count of de-allocations."
        },
        {NULL, NULL, 0, NULL}  /* Sentinel */
};

static PyTypeObject cpyRefTraceCountType = {
        PyVarObject_HEAD_INIT(NULL, 0)
        .tp_name = "cPyRefTraceExample.RefTraceCount",
        .tp_doc = "A simple Reference Tracing object that counts object allocations and de-allocations.",
        .tp_basicsize = sizeof(cpyRefTraceCount),
        .tp_itemsize = 0,
        .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
        .tp_new = cpyRefTraceCount_new,
        .tp_init = (initproc) cpyRefTraceCount_init,
        .tp_alloc = PyType_GenericAlloc,
        .tp_dealloc = (destructor) cpyRefTraceCount_dealloc,
        .tp_members = NULL,
        .tp_methods = cpyRefTraceCount_methods,
};

PyDoc_STRVAR(
        py_ref_trace_doc,
        "Module that contains an example C Reference Tracer that counts events."
);

static PyModuleDef cPyRefTraceExamplemodule = {
        PyModuleDef_HEAD_INIT,
        .m_name = "cPyRefTraceExample",
        .m_doc = py_ref_trace_doc,
        .m_size = -1,
        .m_methods = NULL,
};

PyMODINIT_FUNC
PyInit_cPyRefTraceExample(void) {
    PyObject *m = PyModule_Create(&cPyRefTraceExamplemodule);
    if (m == NULL) {
        return NULL;
    }
    /* Add the Reference Tracing Simple object. */
    if (PyType_Ready(&cpyRefTraceCountType) < 0) {
        Py_DECREF(m);
        return NULL;
    }
    Py_INCREF(&cpyRefTraceCountType);
    if (PyModule_AddObject(m, "RefTraceCount", (PyObject *) &cpyRefTraceCountType) < 0) {
        Py_DECREF(&cpyRefTraceCountType);
        Py_DECREF(m);
        return NULL;
    }
    return m;
}
