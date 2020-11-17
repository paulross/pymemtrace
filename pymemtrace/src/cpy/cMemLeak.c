/*
 * Created by Paul Ross on 07/11/2020.
 *
 * Functions to cause memory memory usage and leaks in C and CPython.
 *
*/
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "structmember.h"


/* If defined this reports any malloc and free for CMallocObject, PyRawMallocObject and PyMallocObject. */
/*
#define DEBUG_REPORT_MALLOC_FREE
*/
#undef DEBUG_REPORT_MALLOC_FREE

/******** Allocate a buffer with C's malloc() ********/
typedef struct {
    PyObject_HEAD
    size_t size;
    void *buffer; /* Buffer created by malloc() */
} CMallocObject;

static void
CMallocObject_dealloc(CMallocObject *self) {
#ifdef DEBUG_REPORT_MALLOC_FREE
    fprintf(stdout, "CMallocObject size: %zu free(%p)\n", self->size, self->buffer);
#endif
    free(self->buffer);
    Py_TYPE(self)->tp_free((PyObject *) self);
}

static PyObject *
CMallocObject_new(PyTypeObject *type, PyObject *Py_UNUSED(args), PyObject *Py_UNUSED(kwds)) {
    CMallocObject *self;
    self = (CMallocObject *) type->tp_alloc(type, 0);
    if (self != NULL) {
        self->size = 0;
        self->buffer = NULL;
    }
    return (PyObject *) self;
}

static int
CMallocObject_init(CMallocObject *self, PyObject *args, PyObject *kwds) {
    static char *kwlist[] = {"size", NULL};

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "n", kwlist, &self->size)) {
        return -1;
    }
    if (self->size == 0) {
        self->size = 1;
    }
    self->buffer = malloc(self->size);
#ifdef DEBUG_REPORT_MALLOC_FREE
    fprintf(stdout, "CMallocObject malloc(%zu) -> %p\n", self->size, self->buffer);
#endif
    if (self->buffer == NULL) {
        return -1;
    }
    return 0;
}

static PyObject *
CMallocObject_getsize(CMallocObject *self, void *Py_UNUSED(closure)) {
    return PyLong_FromSsize_t(self->size);
}

static PyObject *
CMallocObject_getbuffer(CMallocObject *self, void *Py_UNUSED(closure)) {
    return PyLong_FromSsize_t((size_t)(self->buffer));
}

static PyMemberDef CMallocObject_members[] = {
//    {"size", T_ULONG, offsetof(CMallocObject, size), 0, "Buffer size."},
    {NULL, 0, 0, 0, NULL}  /* Sentinel */
};

static PyGetSetDef CMallocObject_getsetters[] = {
    {"size", (getter) CMallocObject_getsize, (setter) NULL, "Buffer size.", NULL},
    {"buffer", (getter) CMallocObject_getbuffer, (setter) NULL, "Buffer address.", NULL},
    {NULL, NULL, NULL, NULL, NULL}  /* Sentinel */
};

static PyMethodDef CMallocObject_methods[] = {
    {NULL, NULL, 0, NULL}  /* Sentinel */
};

PyDoc_STRVAR(
    CMallocObjectType_tp_doc,
    "A simple Python object that reserves a block of C memory with ``malloc()`` and frees it with ``free()``."
    " Actual reserved memory is always >=1 byte."
);

static PyTypeObject CMallocObjectType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "cMemLeak.CMallocObject",
    .tp_doc = CMallocObjectType_tp_doc,
    .tp_basicsize = sizeof(CMallocObject),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
    .tp_new = CMallocObject_new,
    .tp_init = (initproc) CMallocObject_init,
    .tp_dealloc = (destructor) CMallocObject_dealloc,
    .tp_members = CMallocObject_members,
    .tp_methods = CMallocObject_methods,
    .tp_getset = CMallocObject_getsetters,
};
/******** END: Allocate a buffer with C's malloc() ********/

/******** Allocate a buffer with Python's raw memory interface ********/
typedef struct {
    PyObject_HEAD
    size_t size;
    void *buffer; /* Buffer created by PyMem_RawMalloc() */
} PyRawMallocObject;

static void
PyRawMallocObject_dealloc(PyRawMallocObject *self) {
#ifdef DEBUG_REPORT_MALLOC_FREE
    fprintf(stdout, "PyRawMallocObject size: %zu free(%p)\n", self->size, self->buffer);
#endif
    PyMem_RawFree(self->buffer);
    Py_TYPE(self)->tp_free((PyObject *) self);
}

static PyObject *
PyRawMallocObject_new(PyTypeObject *type, PyObject *Py_UNUSED(args), PyObject *Py_UNUSED(kwds)) {
    PyRawMallocObject *self;
    self = (PyRawMallocObject *) type->tp_alloc(type, 0);
    if (self != NULL) {
        self->size = 0;
        self->buffer = NULL;
    }
    return (PyObject *) self;
}

static int
PyRawMallocObject_init(PyRawMallocObject *self, PyObject *args, PyObject *kwds) {
    static char *kwlist[] = {"size", NULL};

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "n", kwlist, &self->size)) {
        return -1;
    }
    if (self->size == 0) {
        self->size = 1;
    }
    self->buffer = PyMem_RawMalloc(self->size);
#ifdef DEBUG_REPORT_MALLOC_FREE
    fprintf(stdout, "PyRawMallocObject malloc(%zu) -> %p\n", self->size, self->buffer);
#endif
    if (self->buffer == NULL) {
        return -1;
    }
    return 0;
}

static PyObject *
PyRawMallocObject_getsize(PyRawMallocObject *self, void *Py_UNUSED(closure)) {
    return PyLong_FromSsize_t(self->size);
}

static PyObject *
PyRawMallocObject_getbuffer(PyRawMallocObject *self, void *Py_UNUSED(closure)) {
    return PyLong_FromSsize_t((size_t)(self->buffer));
}

static PyMemberDef PyRawMallocObject_members[] = {
//    {"size", T_ULONG, offsetof(PyRawMallocObject, size), 0, "Buffer size."},
    {NULL, 0, 0, 0, NULL}  /* Sentinel */
};

static PyGetSetDef PyRawMallocObject_getsetters[] = {
    {"size", (getter) PyRawMallocObject_getsize, (setter) NULL, "Buffer size.", NULL},
    {"buffer", (getter) PyRawMallocObject_getbuffer, (setter) NULL, "Buffer address.", NULL},
    {NULL, NULL, NULL, NULL, NULL}  /* Sentinel */
};

static PyMethodDef PyRawMallocObject_methods[] = {
    {NULL, NULL, 0, NULL}  /* Sentinel */
};

PyDoc_STRVAR(
    PyRawMallocObjectType_tp_doc,
    "A simple Python object that reserves a block of memory with Pythons raw memory allocator."
    " This reserves memory with a call to ``PyMem_RawMalloc()`` and frees it with ``PyMem_RawFree()``."
    " Actual reserved memory is always >=1 byte."
);

static PyTypeObject PyRawMallocObjectType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "cMemLeak.PyRawMallocObject",
    .tp_doc = PyRawMallocObjectType_tp_doc,
    .tp_basicsize = sizeof(PyRawMallocObject),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
    .tp_new = PyRawMallocObject_new,
    .tp_init = (initproc) PyRawMallocObject_init,
    .tp_dealloc = (destructor) PyRawMallocObject_dealloc,
    .tp_members = PyRawMallocObject_members,
    .tp_methods = PyRawMallocObject_methods,
    .tp_getset = PyRawMallocObject_getsetters,
};
/******** END: Allocate a buffer with Python's raw memory interface ********/

/******** Allocate a buffer with Python's pymalloc memory interface ********/
typedef struct {
    PyObject_HEAD
    size_t size;
    void *buffer; /* Buffer created by PyMem_Malloc() */
} PyMallocObject;

static void
PyMallocObject_dealloc(PyMallocObject *self) {
#ifdef DEBUG_REPORT_MALLOC_FREE
    fprintf(stdout, "PyMallocObject size: %zu free(%p)\n", self->size, self->buffer);
#endif
    PyMem_Free(self->buffer);
    Py_TYPE(self)->tp_free((PyObject *) self);
}

static PyObject *
PyMallocObject_new(PyTypeObject *type, PyObject *Py_UNUSED(args), PyObject *Py_UNUSED(kwds)) {
    PyMallocObject *self;
    self = (PyMallocObject *) type->tp_alloc(type, 0);
    if (self != NULL) {
        self->size = 0;
        self->buffer = NULL;
    }
    return (PyObject *) self;
}

static int
PyMallocObject_init(PyMallocObject *self, PyObject *args, PyObject *kwds) {
    static char *kwlist[] = {"size", NULL};

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "n", kwlist, &self->size)) {
        return -1;
    }
    if (self->size == 0) {
        self->size = 1;
    }
    self->buffer = PyMem_Malloc(self->size);
#ifdef DEBUG_REPORT_MALLOC_FREE
    fprintf(stdout, "PyMallocObject malloc(%zu) -> %p\n", self->size, self->buffer);
#endif
    if (self->buffer == NULL) {
        return -1;
    }
    return 0;
}

static PyObject *
PyMallocObject_getsize(PyMallocObject *self, void *Py_UNUSED(closure)) {
    return PyLong_FromSsize_t(self->size);
}

static PyObject *
PyMallocObject_getbuffer(PyMallocObject *self, void *Py_UNUSED(closure)) {
    return PyLong_FromSsize_t((size_t)(self->buffer));
}

static PyMemberDef PyMallocObject_members[] = {
//    {"size", T_ULONG, offsetof(PyMallocObject, size), 0, "Buffer size."},
    {NULL, 0, 0, 0, NULL}  /* Sentinel */
};

static PyGetSetDef PyMallocObject_getsetters[] = {
    {"size", (getter) PyMallocObject_getsize, (setter) NULL, "Buffer size.", NULL},
    {"buffer", (getter) PyMallocObject_getbuffer, (setter) NULL, "Buffer address.", NULL},
    {NULL, NULL, NULL, NULL, NULL}  /* Sentinel */
};

static PyMethodDef PyMallocObject_methods[] = {
    {NULL, NULL, 0, NULL}  /* Sentinel */
};

PyDoc_STRVAR(
    PyMallocObjectType_tp_doc,
    "A simple Python object that reserves a block of memory with Pythons pymalloc allocator."
    " This reserves memory with a call to ``PyMem_Malloc()`` and frees it with ``PyMem_Free()``."
    " Actual reserved memory is always >=1 byte."
);

static PyTypeObject PyMallocObjectType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "cMemLeak.PyMallocObject",
    .tp_doc = PyMallocObjectType_tp_doc,
    .tp_basicsize = sizeof(PyMallocObject),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
    .tp_new = PyMallocObject_new,
    .tp_init = (initproc) PyMallocObject_init,
    .tp_dealloc = (destructor) PyMallocObject_dealloc,
    .tp_members = PyMallocObject_members,
    .tp_methods = PyMallocObject_methods,
    .tp_getset = PyMallocObject_getsetters,
};
/******** END: Allocate a buffer with Python's pymalloc memory interface ********/

/*
 * Increments the reference count of the supplied PyObject.
 * This will cause a memory leak.
 */
static PyObject *
py_incref(PyObject *Py_UNUSED(module), PyObject *pobj) {
    Py_INCREF(pobj);
    Py_RETURN_NONE;
}

/*
 * Decrements the reference count of the supplied PyObject.
 * This may cause a segfault.
 */
static PyObject *
py_decref(PyObject *Py_UNUSED(module), PyObject *pobj) {
    Py_DECREF(pobj);
    Py_RETURN_NONE;
}

/*
 * Returns a Python bytes object of specified size.
 * The content is uninitialised.
 */
static PyObject *
py_bytes_of_size(PyObject *Py_UNUSED(module), PyObject *args, PyObject *kwds) {
    static char *kwlist[] = {"size", NULL};
    size_t size;

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "n", kwlist, &size)) {
        return NULL;
    }
    return PyBytes_FromStringAndSize(NULL, size);
}

static PyMethodDef MemLeakMethods[] = {
    {"py_incref",   (PyCFunction) py_incref, METH_O,
     "Increment the reference count of the Python object."},
    {"py_decref",   (PyCFunction) py_decref, METH_O,
     "Decrement the reference count of the Python object."},
    {"py_bytes_of_size",   (PyCFunction) py_bytes_of_size, METH_VARARGS | METH_KEYWORDS,
     "Returns a Python bytes object of specified size. The content is uninitialised."},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

static PyModuleDef cMemLeakmodule = {
    PyModuleDef_HEAD_INIT,
    .m_name = "cMemLeak",
    .m_doc = "A module that contains a variety of ways of exercising memory and creating memory leaks on demand.",
    .m_size = -1,
    .m_methods = MemLeakMethods,
};

PyMODINIT_FUNC
PyInit_cMemLeak(void) {
    PyObject *m;
    m = PyModule_Create(&cMemLeakmodule);
    if (m == NULL) {
        return NULL;
    }
    /* C malloc() */
    if (PyType_Ready(&CMallocObjectType) < 0) {
        return NULL;
    }
    Py_INCREF(&CMallocObjectType);
    if (PyModule_AddObject(m, "CMalloc", (PyObject *) &CMallocObjectType) < 0) {
        Py_DECREF(&CMallocObjectType);
        Py_DECREF(m);
        return NULL;
    }
    /* Python raw malloc() */
    if (PyType_Ready(&PyRawMallocObjectType) < 0) {
        return NULL;
    }
    Py_INCREF(&PyRawMallocObjectType);
    if (PyModule_AddObject(m, "PyRawMalloc", (PyObject *) &PyRawMallocObjectType) < 0) {
        Py_DECREF(&PyRawMallocObjectType);
        Py_DECREF(m);
        return NULL;
    }
    /* Python pymalloc() */
    if (PyType_Ready(&PyMallocObjectType) < 0) {
        return NULL;
    }
    Py_INCREF(&PyMallocObjectType);
    if (PyModule_AddObject(m, "PyMalloc", (PyObject *) &PyMallocObjectType) < 0) {
        Py_DECREF(&PyMallocObjectType);
        Py_DECREF(m);
        return NULL;
    }

    return m;
}
