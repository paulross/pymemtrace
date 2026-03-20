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
 * Reference Tracing
 * -----------------
 *
 * Created by Paul Ross on 08/03/2026.
 * This contains the Python interface to the C reference tracer.
 * See https://docs.python.org/3/c-api/profiling.html#reference-tracing
 *
 * Monitored events are:
 * PyRefTracer_CREATE https://docs.python.org/3/c-api/profiling.html#c.PyRefTracer_CREATE
 * PyRefTracer_DESTROY https://docs.python.org/3/c-api/profiling.html#c.PyRefTracer_DESTROY
 * Possibly: PyRefTracer_TRACKER_REMOVED https://docs.python.org/3/c-api/profiling.html#c.PyRefTracer_TRACKER_REMOVED
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

// TODO: Remove this?
#define PY_MEM_TRACE_WRITE_OUTPUT_PREV_NEXT
//#undef PY_MEM_TRACE_WRITE_OUTPUT_PREV_NEXT


/* Tracing reference counts. */
#if 0
#define TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_BEG(op)                                    \
    fprintf(stdout, "TRACE: %50s() BEG REFCNT %12p %10zd\n", __FUNCTION__, (void *)op, Py_REFCNT(op))

#define TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_END(op)                                    \
    fprintf(stdout, "TRACE: %50s() END REFCNT %12p %10zd\n", __FUNCTION__, (void *)op, Py_REFCNT(op))

#define TRACE_PROFILE_OR_TRACE_REFCNT_SELF_TRACE_FILE_WRAPPER_BEG(self)                         \
    fprintf(stdout, "TRACE: %50s() BEG REFCNT %12p %10zd trace_file_wrapper REFCNT %10zd\n",    \
        __FUNCTION__, (void *)self, Py_REFCNT(self),                                            \
        self->trace_file_wrapper ? Py_REFCNT(self->trace_file_wrapper) : -1                     \
    )

#define TRACE_PROFILE_OR_TRACE_REFCNT_SELF_TRACE_FILE_WRAPPER_END(self)                         \
    fprintf(stdout, "TRACE: %50s() END REFCNT %12p %10zd trace_file_wrapper REFCNT %10zd\n",    \
        __FUNCTION__, (void *)self, Py_REFCNT(self),                                            \
        self->trace_file_wrapper ? Py_REFCNT(self->trace_file_wrapper) : -1                     \
    )
#else
#define TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_BEG(op)
#define TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_END(op)
#define TRACE_PROFILE_OR_TRACE_REFCNT_SELF_TRACE_FILE_WRAPPER_BEG(op)
#define TRACE_PROFILE_OR_TRACE_REFCNT_SELF_TRACE_FILE_WRAPPER_END(op)
#endif

/** Backwards compatibility for object members for Python versions prior to 3.12.
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

// MARK: Python definitions and functions.
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

static const unsigned char MT_U_STRING[] = "";
static const char MT_STRING[] = "";

static const unsigned char *
get_python_file_name(PyFrameObject *frame) {
    if (frame) {
#if PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION >= 11
        /* See https://docs.python.org/3.11/whatsnew/3.11.html#pyframeobject-3-11-hiding */
        const unsigned char *file_name = PyUnicode_1BYTE_DATA(PyFrame_GetCode(frame)->co_filename);
#else
        const unsigned char *file_name = PyUnicode_1BYTE_DATA(frame->f_code->co_filename);
#endif // PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION >= 11
        return file_name;
    }
    return MT_U_STRING;
}

static const char *
get_python_function_name(PyFrameObject *frame, int what, PyObject *arg) {
    const char *func_name = NULL;
    if (frame) {
        if (what == PyTrace_C_CALL || what == PyTrace_C_EXCEPTION || what == PyTrace_C_RETURN) {
            func_name = PyEval_GetFuncName(arg);
        } else {
#if PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION >= 11
            /* See https://docs.python.org/3.11/whatsnew/3.11.html#pyframeobject-3-11-hiding */
            func_name = (const char *) PyUnicode_1BYTE_DATA(PyFrame_GetCode(frame)->co_name);
#else
            func_name = (const char *) PyUnicode_1BYTE_DATA(frame->f_code->co_name);
#endif // PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION >= 11
        }
        return func_name;
    }
    return MT_STRING;
}

int py_frame_get_line_number(PyFrameObject *frame) {
    if (frame) {
        return PyFrame_GetLineNumber(frame);
    }
    return 0;
}

// MARK: cpyTraceFileWrapper object
/**
 * Trace classes could make this available by looking at trace_file_wrapper or profile_file_wrapper.
 */
typedef struct {
    PyObject_HEAD
    FILE *file;
    // Store the file path and provide an API that can return it (or None) from profile_wrapper or trace_wrapper.
    char *log_file_path;
    size_t event_number;
    size_t rss;
    // This determines the granularity of the log file.
    // <0 - A call to trace_or_profile_function() is logged only if the dRSS is >= the page size given by
    //      getpagesize() in unistd.h.
    // 0 - Every call to trace_or_profile_function() is logged.
    // >0 - A call to trace_or_profile_function() is logged only if the dRSS is >= this value.
    // Default is -1. See cpyProfileOrTraceObject_init() and TraceObject_init().
    int d_rss_trigger;
#ifdef PY_MEM_TRACE_WRITE_OUTPUT
    size_t previous_event_number;
    char event_text[PY_MEM_TRACE_EVENT_TEXT_MAX_LENGTH];
#endif
} cpyTraceFileWrapper;

/**
 * Composes an event into the event_text buffer for writing to the log file.
 * No newline is appended.
 *
 * @param trace_wrapper The trace or profile wrapper.
 * @param frame The Python Frame object.
 * @param what The event type. See https://docs.python.org/3/c-api/profiling.html#c.Py_tracefunc
 * @param arg The argument which depends upon \c what . See https://docs.python.org/3/c-api/profiling.html#c.Py_tracefunc
 */
static void
trace_wrapper_write_frame_data_to_event_text(cpyTraceFileWrapper *trace_wrapper, PyFrameObject *frame,
                                             int what, PyObject *arg) {
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_BEG(trace_wrapper);
    size_t rss = getCurrentRSS_alternate();
    long d_rss = rss - trace_wrapper->rss;
#ifdef PY_MEM_TRACE_WRITE_OUTPUT_CLOCK
    double clock_time = (double) clock() / CLOCKS_PER_SEC;
    snprintf(trace_wrapper->event_text, PY_MEM_TRACE_EVENT_TEXT_MAX_LENGTH,
             "%-12zu +%-6ld %-12.6f %-8s %-80s %4d %-32s %12zu %12ld",
             trace_wrapper->event_number, trace_wrapper->event_number - trace_wrapper->previous_event_number,
             clock_time, WHAT_STRINGS[what], get_python_file_name(frame), py_frame_get_line_number(frame),
             get_python_function_name(frame, what, arg), rss, d_rss);
#else
    snprintf(trace_wrapper->event_text, PY_MEM_TRACE_EVENT_TEXT_MAX_LENGTH,
             "%-12zu +%-6ld %-8s %-80s %4d %-32s %12zu %12ld",
             trace_wrapper->event_number, trace_wrapper->event_number - trace_wrapper->previous_event_number,
             WHAT_STRINGS[what], get_python_file_name(frame), py_frame_get_line_number(frame),
             get_python_function_name(frame, what, arg), rss, d_rss);
#endif // PY_MEM_TRACE_WRITE_OUTPUT_CLOCK
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_END(trace_wrapper);
}

/**
 * Composes an event and clock time into the event_text buffer for writing to the log file.
 * No newline is appended.
 *
 * @param trace_wrapper The trace or profile wrapper.
 */
static void
trace_wrapper_write_event_time_to_event_text(cpyTraceFileWrapper *trace_wrapper) {
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_BEG(trace_wrapper);
#ifdef PY_MEM_TRACE_WRITE_OUTPUT_CLOCK
    double clock_time = (double) clock() / CLOCKS_PER_SEC;
    snprintf(trace_wrapper->event_text, PY_MEM_TRACE_EVENT_TEXT_MAX_LENGTH,
             "%-12zu +%-6ld %-12.6f",
             trace_wrapper->event_number, trace_wrapper->event_number - trace_wrapper->previous_event_number,
             clock_time);
#else
    snprintf(trace_wrapper->event_text, PY_MEM_TRACE_EVENT_TEXT_MAX_LENGTH,
             "%-12zu +%-6ld",
             trace_wrapper->event_number, trace_wrapper->event_number - trace_wrapper->previous_event_number,
             );
#endif // PY_MEM_TRACE_WRITE_OUTPUT_CLOCK
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_END(trace_wrapper);
}

/**
 * Writes a formatted message to the log file.
 *
 * The form is:
 *
 * @code
 *  MSG: 3            +1      4.211822     message...
 * @endcode
 *
 * @param trace_wrapper The trace or profile wrapper.
 * @param message The message to write.
 */
static void
trace_wrapper_write_message_to_log_file(cpyTraceFileWrapper *trace_wrapper, const char *message) {
#ifdef PY_MEM_TRACE_WRITE_OUTPUT
    assert(trace_wrapper->file);
    fputs("MSG: ", trace_wrapper->file);
    trace_wrapper_write_event_time_to_event_text(trace_wrapper);
    fputs(trace_wrapper->event_text, trace_wrapper->file);
    fputc(' ', trace_wrapper->file);
    fputs(message, trace_wrapper->file);
    fputc('\n', trace_wrapper->file);
#endif // PY_MEM_TRACE_WRITE_OUTPUT
}

static void
cpyTraceFileWrapper_close_file(cpyTraceFileWrapper *self) {
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_BEG(self);
    if (self->file) {
        // Write LAST event
        fputs("LAST: ", self->file);
        trace_wrapper_write_frame_data_to_event_text(self, PyEval_GetFrame(), PyTrace_LINE, Py_None);
        fputs(self->event_text, self->file);
        fputc('\n', self->file);
        // Write a final line
        fprintf(self->file, "%s\n", MARKER_LOG_FILE_END);
        fclose(self->file);
        self->file = NULL;
    }
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_END(self);
}

/**
 * Deallocate the cpyTraceFileWrapper.
 * @param self The cpyTraceFileWrapper.
 */
static void
cpyTraceFileWrapper_dealloc(cpyTraceFileWrapper *self) {
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_BEG(self);
    if (self->file) {
        cpyTraceFileWrapper_close_file(self);
    }
    free(self->log_file_path);
    PyObject_Del((PyObject *) self);
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_END(self);
}

/**
 * Allocate the cpyTraceFileWrapper.
 * @param type The cpyTraceFileWrapper type.
 * @param _unused_args
 * @param _unused_kwds
 * @return The cpyTraceFileWrapper instance.
 */
static PyObject *
cpyTraceFileWrapper_new(PyTypeObject *type, PyObject *Py_UNUSED(args), PyObject *Py_UNUSED(kwds)) {
    assert(!PyErr_Occurred());
    cpyTraceFileWrapper *self;
    self = (cpyTraceFileWrapper *) type->tp_alloc(type, 0);
    if (self != NULL) {
        self->file = NULL;
        self->log_file_path = NULL;
    }
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_END(self);
    return (PyObject *) self;
}

// MARK: - cpyTraceFileWrapper members

static PyMemberDef cpyTraceFileWrapper_members[] = {
        {
                "log_file_path",
                Py_T_STRING,
                offsetof(cpyTraceFileWrapper, log_file_path),
                Py_READONLY,
                "The path to the log file being written."
        },
        {
                "event_number",
                Py_T_PYSSIZET,
                offsetof(cpyTraceFileWrapper, event_number),
                Py_READONLY,
                "The current event number."
        },
        {
                "rss",
                Py_T_PYSSIZET,
                offsetof(cpyTraceFileWrapper, rss),
                Py_READONLY,
                "The current Resident Set Size (RSS)."
        },
        {
                "d_rss_trigger",
                Py_T_INT,
                offsetof(cpyTraceFileWrapper, d_rss_trigger),
                Py_READONLY,
                "The delta Resident Set Size (RSS) trigger value."
        },
        {
                "previous_event_number",
                Py_T_PYSSIZET,
                offsetof(cpyTraceFileWrapper, previous_event_number),
                Py_READONLY,
                "The previous event number."
        },
        {
                "event_text",
                Py_T_STRING,
                offsetof(cpyTraceFileWrapper, event_text),
                Py_READONLY,
                "The current event text."
        },
        {NULL, 0, 0, 0, NULL} /* Sentinel */
};

// MARK: - cpyTraceFileWrapper methods

/**
 * Write any string to the existing logfile.
 * Warning: This is not compatible with the log file format.
 *
 * TODO: Remove this in favour of write_message_to_log()?
 *
 * @param self The file wrapper.
 * @param op The Python unicode string.
 * @return None on success, NULL on failure (not a unicode argument).
 */
static PyObject *
cpyTraceFileWrapper_write_to_log(cpyTraceFileWrapper *self, PyObject *op) {
    assert(!PyErr_Occurred());
    if (!self->file) {
        PyErr_SetString(PyExc_IOError, "Log file is closed.");
        return NULL;
    }
    if (!PyUnicode_Check(op)) {
        PyErr_Format(
                PyExc_ValueError,
                "write_to_log() requires a single string, not type %s",
                Py_TYPE(op)->tp_name
        );
        return NULL;
    }
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_BEG(self);
    Py_UCS1 *c_str = PyUnicode_1BYTE_DATA(op);
    fprintf(self->file, "%s\n", c_str);
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_END(self);
    Py_RETURN_NONE;
}

/**
 * Write any string to the existing logfile.
 * Note: This is compatible with the log file format.
 *
 * @param self The file wrapper.
 * @param op The Python unicode string.
 * @return None on success, NULL on failure (not a unicode argument).
 */
static PyObject *
cpyTraceFileWrapper_write_message_to_log(cpyTraceFileWrapper *self, PyObject *op) {
    assert(!PyErr_Occurred());
    if (!self->file) {
        PyErr_SetString(PyExc_IOError, "Log file is closed.");
        return NULL;
    }
    if (!PyUnicode_Check(op)) {
        PyErr_Format(
                PyExc_ValueError,
                "write_message_to_log() requires a single string, not type %s",
                Py_TYPE(op)->tp_name
        );
        return NULL;
    }
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_BEG(self);
    Py_UCS1 *c_str = PyUnicode_1BYTE_DATA(op);
    trace_wrapper_write_message_to_log_file(self, (const char *) c_str);
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_END(self);
    Py_RETURN_NONE;
}

static PyMethodDef cpyTraceFileWrapper_methods[] = {
        /* TODO: Remove this in favour of write_message_to_log()? */
        {
                "write_to_log",         (PyCFunction) cpyTraceFileWrapper_write_to_log,
                METH_O,
                "Write any string to the existing log file with a newline. Returns None."
                " Warning: This is not compatible with the log file format."
        },
        {
                "write_message_to_log", (PyCFunction) cpyTraceFileWrapper_write_message_to_log,
                METH_O,
                "Write a string as a message to the existing log file with a newline. Returns None."
                " Note: This is compatible with the log file format."
        },
        {NULL, NULL, 0, NULL}  /* Sentinel */
};

// MARK: - cpyTraceFileWrapper declaration

static PyTypeObject cpyTraceFileWrapperType = {
        PyVarObject_HEAD_INIT(NULL, 0)
        .tp_name = "cPyMemTrace.cpyTraceFileWrapper",
        .tp_doc = "Wrapper round a trace-to-file object.",
        .tp_basicsize = sizeof(cpyTraceFileWrapper),
        .tp_itemsize = 0,
        .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
        .tp_new = cpyTraceFileWrapper_new,
        .tp_alloc = PyType_GenericAlloc,
        .tp_dealloc = (destructor) cpyTraceFileWrapper_dealloc,
        .tp_members = cpyTraceFileWrapper_members,
        .tp_methods = cpyTraceFileWrapper_methods,
};

// MARK: Static linked list of trace/profile wrappers.
/**
 * A node in the linked list of trace file wrappers.
 *
 * NOTE: Operations on this list do not manipulate the reference counts
 * of the Python objects.
 * That is up to the caller of these functions.
 */
struct cpyTraceFileWrapperLinkedListNode {
    cpyTraceFileWrapper *file_wrapper;
    struct cpyTraceFileWrapperLinkedListNode *next;
};
typedef struct cpyTraceFileWrapperLinkedListNode tcpyTraceFileWrapperLinkedList;

static tcpyTraceFileWrapperLinkedList *static_profile_wrappers = NULL;
static tcpyTraceFileWrapperLinkedList *static_trace_wrappers = NULL;

/**
 * Get the head of the linked list.
 * @param linked_list The linked list, either \c static_profile_wrappers or \c static_trace_wrappers .
 * @return The head node or NULL if the list is empty.
 */
cpyTraceFileWrapper *wrapper_ll_get(tcpyTraceFileWrapperLinkedList *linked_list) {
    if (linked_list) {
        return linked_list->file_wrapper;
    }
    return NULL;
}

/**
 * Push a created trace wrapper on the front of the list.
 * @param linked_list The linked list, either \c static_profile_wrappers or \c static_trace_wrappers .
 * @param node The node to add. The linked list takes ownership of this pointer.
 */
void wrapper_ll_push(tcpyTraceFileWrapperLinkedList **h_linked_list, cpyTraceFileWrapper *node) {
    tcpyTraceFileWrapperLinkedList *new_node = malloc(sizeof(tcpyTraceFileWrapperLinkedList));
    new_node->file_wrapper = node;
    new_node->next = NULL;
    if (*h_linked_list) {
        // Push to front.
        new_node->next = *h_linked_list;
    }
    *h_linked_list = new_node;
}

/**
 * Free the first value on the list and adjust the list pointer.
 * @param linked_list The linked list, either \c static_profile_wrappers or \c static_trace_wrappers .
 */
cpyTraceFileWrapper *
wrapper_ll_pop(tcpyTraceFileWrapperLinkedList **h_linked_list) {
    tcpyTraceFileWrapperLinkedList *tmp = *h_linked_list;
    *h_linked_list = (*h_linked_list)->next;
    cpyTraceFileWrapper *ret = tmp->file_wrapper;
    free(tmp);
    /* NOTE: Caller has to decide whether to decref the tmp->file_wrapper.
     * If call as the result of and __exit__ function then do **not** decref as CPython
     * will automatically do this on completion of the with statement. */
    return ret;
}

/**
 * Return the length of the linked list.
 * @param linked_list The linked list, either \c static_profile_wrappers or \c static_trace_wrappers .
 * @return The length of the linked list
 */
size_t wrapper_ll_length(tcpyTraceFileWrapperLinkedList *p_linked_list) {
    size_t ret = 0;
    while (p_linked_list) {
        ret++;
        p_linked_list = p_linked_list->next;
    }
    return ret;
}

/**
 * Remove all the items in the linked list.
 * @param linked_list The linked list, either \c static_profile_wrappers or \c static_trace_wrappers .
 */
void wrapper_ll_clear(tcpyTraceFileWrapperLinkedList **h_linked_list) {
    tcpyTraceFileWrapperLinkedList *tmp;
    while (*h_linked_list) {
        tmp = *h_linked_list;
        Py_DECREF((*h_linked_list)->file_wrapper);
        free(*h_linked_list);
        *h_linked_list = tmp->next;
    }
}

/**
 * Create a trace function.
 * This is of type \c Py_tracefunc https://docs.python.org/3/c-api/profiling.html#c.Py_tracefunc
 * This is passed to \c PyEval_SetProfile https://docs.python.org/3/c-api/profiling.html#c.PyEval_SetProfile
 * and \c PyEval_SetTrace https://docs.python.org/3/c-api/profiling.html#c.PyEval_SetTrace
 *
 * @param pobj The cpyTraceFileWrapper object.
 * @param frame The Python frame.
 * @param what The event type.
 * @param arg This depends on the value of \c what. See https://docs.python.org/3/c-api/profiling.html#c.Py_tracefunc
 * @return 0 on success, non-zero on failure.
 */
static int
trace_or_profile_function(PyObject *pobj, PyFrameObject *frame, int what, PyObject *arg) {
    assert(!PyErr_Occurred());
    assert(Py_TYPE(pobj) == &cpyTraceFileWrapperType && "trace_wrapper is not a cpyTraceFileWrapperType.");

    cpyTraceFileWrapper *trace_wrapper = (cpyTraceFileWrapper *) pobj;
    size_t rss = getCurrentRSS_alternate();
#ifdef PY_MEM_TRACE_WRITE_OUTPUT
    long d_rss = rss - trace_wrapper->rss;
    if (labs(d_rss) >= trace_wrapper->d_rss_trigger
        && trace_wrapper->event_number > 0
        && (trace_wrapper->event_number - trace_wrapper->previous_event_number) > 1) {
        // Previous event.
#ifdef PY_MEM_TRACE_WRITE_OUTPUT_PREV_NEXT
        fputs("PREV: ", trace_wrapper->file);
#endif
        fputs(trace_wrapper->event_text, trace_wrapper->file);
        fputc('\n', trace_wrapper->file);
    }
    if (labs(d_rss) >= trace_wrapper->d_rss_trigger && trace_wrapper->event_number) {
        // NOTE: Ignore event number 0 as that is covered by "FRST:" below.
#ifdef PY_MEM_TRACE_WRITE_OUTPUT_PREV_NEXT
        assert(trace_wrapper->file);
        fputs("NEXT: ", trace_wrapper->file);
#endif
        trace_wrapper_write_frame_data_to_event_text(trace_wrapper, frame, what, arg);
        fputs(trace_wrapper->event_text, trace_wrapper->file);
        fputc('\n', trace_wrapper->file);
        trace_wrapper->previous_event_number = trace_wrapper->event_number;
    }
#endif // PY_MEM_TRACE_WRITE_OUTPUT
    trace_wrapper->event_number++;
    trace_wrapper->rss = rss;
    assert(!PyErr_Occurred());
    return 0;
}

static cpyTraceFileWrapper *
new_trace_file_wrapper(int d_rss_trigger, const char *message, const char *specific_filename, int is_profile) {
    static char file_path_buffer[PYMEMTRACE_PATH_NAME_MAX_LENGTH + 1];
    assert(!PyErr_Occurred());
    cpyTraceFileWrapper *trace_wrapper = NULL;
    if (specific_filename) {
        snprintf(file_path_buffer, PYMEMTRACE_PATH_NAME_MAX_LENGTH, "%s", specific_filename);
    } else {
        char trace_type = is_profile ? 'P' : 'T';
        size_t ll_depth = is_profile ? wrapper_ll_length(static_profile_wrappers) : wrapper_ll_length(
                static_trace_wrappers);
        create_filename_within_cwd(trace_type, ll_depth, file_path_buffer, PYMEMTRACE_PATH_NAME_MAX_LENGTH);
    }
    trace_wrapper = (cpyTraceFileWrapper *) cpyTraceFileWrapper_new(&cpyTraceFileWrapperType, NULL, NULL);
    if (trace_wrapper) {
#if DEBUG
        fprintf(stdout, "DEBUG: Profile/Trace opening log file %s\n", file_path_buffer);
#endif
        trace_wrapper->file = fopen(file_path_buffer, "w");
        if (trace_wrapper->file) {
            // Copy the filename
            trace_wrapper->log_file_path = malloc(strlen(file_path_buffer) + 1);
            strcpy(trace_wrapper->log_file_path, file_path_buffer);
            // Write the message to the log file if present.
            // fprintf(stdout, "TRACE: Message \"%s\"\n", message);
            if (message) {
                fprintf(trace_wrapper->file, "%s\n", message);
            }
            fprintf(trace_wrapper->file, "%s\n", MARKER_LOG_FILE_START);
#ifdef PY_MEM_TRACE_WRITE_OUTPUT_CLOCK
#ifdef PY_MEM_TRACE_WRITE_OUTPUT_PREV_NEXT
            fprintf(trace_wrapper->file, "HDR: %-12s %-6s  %-12s %-8s %-80s %4s %-32s %12s %12s\n",
                    "Event", "dEvent", "Clock", "What", "File", "Line", "Function", "RSS", "dRSS"
            );
#else
            fprintf(trace_wrapper->file, "%-12s %-6s  %-12s %-8s %-80s %4s %-32s %12s %12s\n",
                    "Event", "dEvent", "Clock", "What", "File", "Line", "Function", "RSS", "dRSS"
            );
#endif
#else
#ifdef PY_MEM_TRACE_WRITE_OUTPUT_PREV_NEXT
            fprintf(trace_wrapper->file, "HDR: %-12s %-6s  %-8s %-80s %4s %-32s %12s %12s\n",
                    "Event", "dEvent", "What", "File", "Line", "Function", "RSS", "dRSS"
            );
#else
            fprintf(trace_wrapper->file, "%-12s %-6s  %-8s %-80s %4s %-32s %12s %12s\n",
                    "Event", "dEvent", "What", "File", "Line", "Function", "RSS", "dRSS"
            );
#endif
#endif
            fputs("FRST: ", trace_wrapper->file);
            trace_wrapper_write_frame_data_to_event_text(trace_wrapper, PyEval_GetFrame(), PyTrace_LINE, Py_None);
            fputs(trace_wrapper->event_text, trace_wrapper->file);
            fputc('\n', trace_wrapper->file);
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
            cpyTraceFileWrapper_dealloc(trace_wrapper);
            fprintf(stderr, "Can not open writable file for cpyTraceFileWrapper at %s\n", file_path_buffer);
            PyErr_Format(PyExc_IOError, "Can not open log file %s", file_path_buffer);
            return NULL;
        }
    } else {
        fprintf(stderr, "Can not create cpyTraceFileWrapper.\n");
    }
    assert(!PyErr_Occurred());
    return trace_wrapper;
}

// MARK: Get the current log paths.

static PyObject *
get_log_file_path_profile(void) {
    assert(!PyErr_Occurred());
    cpyTraceFileWrapper *wrapper = wrapper_ll_get(static_profile_wrappers);
    if (wrapper) {
        return Py_BuildValue("s", wrapper->log_file_path);
    } else {
        Py_RETURN_NONE;
    }
}

static PyObject *
get_log_file_path_trace(void) {
    assert(!PyErr_Occurred());
    cpyTraceFileWrapper *wrapper = wrapper_ll_get(static_trace_wrappers);
    if (wrapper) {
        return Py_BuildValue("s", wrapper->log_file_path);
    } else {
        Py_RETURN_NONE;
    }
}

// MARK: Common object for Profile or Trace
/**** Context manager for attach_profile/trace_function() and detach_profile/trace_function() ****/
typedef struct {
    PyObject_HEAD
    int d_rss_trigger;
    // Message. Add const char *message here that is a malloc copy of the string given in cpyProfileOrTraceObject_init
    char *message;
    // User can provide a specific filename.
    PyBytesObject *py_specific_filename;
    cpyTraceFileWrapper *trace_file_wrapper;
} cpyProfileOrTraceObject;

static void
cpyProfileOrTraceObject_dealloc(cpyProfileOrTraceObject *self) {
    TRACE_PROFILE_OR_TRACE_REFCNT_SELF_TRACE_FILE_WRAPPER_BEG(self);
    free(self->message);
    Py_XDECREF(self->py_specific_filename);
    Py_XDECREF(self->trace_file_wrapper);
    Py_TYPE(self)->tp_free((PyObject *) self);
    TRACE_PROFILE_OR_TRACE_REFCNT_SELF_TRACE_FILE_WRAPPER_END(self);
}

static PyObject *
cpyProfileOrTraceObject_new(PyTypeObject *type, PyObject *Py_UNUSED(args), PyObject *Py_UNUSED(kwds)) {
    assert(!PyErr_Occurred());
    cpyProfileOrTraceObject *self = (cpyProfileOrTraceObject *) type->tp_alloc(type, 0);
    if (self) {
        TRACE_PROFILE_OR_TRACE_REFCNT_SELF_TRACE_FILE_WRAPPER_BEG(self);
        self->message = NULL;
        self->py_specific_filename = NULL;
        self->trace_file_wrapper = NULL;
        TRACE_PROFILE_OR_TRACE_REFCNT_SELF_TRACE_FILE_WRAPPER_END(self);
    }
    return (PyObject *) self;
}

static int
cpyProfileOrTraceObject_init(cpyProfileOrTraceObject *self, PyObject *args, PyObject *kwds) {
    assert(!PyErr_Occurred());
    TRACE_PROFILE_OR_TRACE_REFCNT_SELF_TRACE_FILE_WRAPPER_BEG(self);
    static char *kwlist[] = {"d_rss_trigger", "message", "filepath", NULL};
    int d_rss_trigger = -1;
    char *message = NULL;
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|isO&", kwlist, &d_rss_trigger, &message, PyUnicode_FSConverter,
                                     &self->py_specific_filename)) {
        assert(PyErr_Occurred());
        return -1;
    }
    self->d_rss_trigger = d_rss_trigger;
    if (message) {
        self->message = malloc(strlen(message) + 1);
        if (self->message) {
            strcpy(self->message, message);
        } else {
            PyErr_Format(PyExc_MemoryError, "cpyProfileOrTraceObject_init() can not allocate memory in type %s.",
                         Py_TYPE(self)->tp_name);
            return -2;
        }
    }
    assert(!PyErr_Occurred());
    TRACE_PROFILE_OR_TRACE_REFCNT_SELF_TRACE_FILE_WRAPPER_END(self);
    return 0;
}

static PyMemberDef cpyProfileOrTraceObject_members[] = {
//        {
//                "_trace_file_wrapper", Py_T_OBJECT_EX, offsetof(cpyProfileOrTraceObject,
//                                                                trace_file_wrapper), Py_READONLY,
//                "The trace file wrapper. This an opaque object with an unpublished API."
//        },
        {NULL, 0, 0, 0, NULL} /* Sentinel */
};

// MARK: Context manager for ProfileObject

/**
 * Attach a new profile wrapper to the \c static_profile_wrapper.
 * @param d_rss_trigger
 * @param message
 * @return The \c static_profile_wrapper or \c NULL on failure in which case an exception will have been set.
 */
static cpyTraceFileWrapper *
py_attach_profile_function(int d_rss_trigger, const char *message, const char *specific_filename) {
    assert(!PyErr_Occurred());
    cpyTraceFileWrapper *wrapper = new_trace_file_wrapper(d_rss_trigger, message, specific_filename, 1);
    if (wrapper) {
        wrapper_ll_push(&static_profile_wrappers, wrapper);
        // This increments the wrapper reference count.
        PyEval_SetProfile(&trace_or_profile_function, (PyObject *) wrapper);
        // Write a marker, in this case it is the line number of the frame.
        trace_or_profile_function((PyObject *) wrapper, PyEval_GetFrame(), PyTrace_LINE, Py_None);
        assert(!PyErr_Occurred());
        return wrapper;
    }
    PyErr_SetString(PyExc_RuntimeError, "py_attach_profile_function(): Could not attach profile function.");
    return NULL;
}

static PyObject *
ProfileObject_enter(cpyProfileOrTraceObject *self) {
    TRACE_PROFILE_OR_TRACE_REFCNT_SELF_TRACE_FILE_WRAPPER_BEG(self);
    assert(!PyErr_Occurred());
    if (self->py_specific_filename) {
        self->trace_file_wrapper = py_attach_profile_function(
                self->d_rss_trigger, self->message, PyBytes_AsString((PyObject *) self->py_specific_filename)
        );
    } else {
        self->trace_file_wrapper = py_attach_profile_function(self->d_rss_trigger, self->message, NULL);
    }
    if (self->trace_file_wrapper == NULL) {
        assert(PyErr_Occurred());
        return NULL;
    }
    Py_INCREF(self);
    assert(!PyErr_Occurred());
    TRACE_PROFILE_OR_TRACE_REFCNT_SELF_TRACE_FILE_WRAPPER_END(self);
    return (PyObject *) self;
}

static PyObject *
ProfileObject_exit(cpyProfileOrTraceObject *self, PyObject *Py_UNUSED(args)) {
    TRACE_PROFILE_OR_TRACE_REFCNT_SELF_TRACE_FILE_WRAPPER_BEG(self);
    // No assert(!PyErr_Occurred()); as an exception might have been set by the user.
    if (self->trace_file_wrapper) {
        // PyEval_SetProfile() will decrement the reference count that incremented by
        // PyEval_SetProfile() on __enter__
        PyEval_SetProfile(NULL, NULL);
        cpyTraceFileWrapper *trace_file_wrapper = (cpyTraceFileWrapper *) self->trace_file_wrapper;
        cpyTraceFileWrapper_close_file(trace_file_wrapper);
        /* NOTE: wrapper_ll_pop returns a cpyTraceFileWrapper *.
         * This should **not** be decref'd here as CPython will do that on completion of a
         * with statement. */
        wrapper_ll_pop(&static_profile_wrappers);

        /* Now set the Profile of the previous one if available. */
        trace_file_wrapper = wrapper_ll_get(static_profile_wrappers);
        if (trace_file_wrapper) {
            PyEval_SetProfile(&trace_or_profile_function, (PyObject *) trace_file_wrapper);
            /* Put a marker in the file. */
            assert(trace_file_wrapper->file);
            fprintf(trace_file_wrapper->file, "# Re-attaching previous profile file wrapper.\n");
        }

        TRACE_PROFILE_OR_TRACE_REFCNT_SELF_TRACE_FILE_WRAPPER_END(self);
        Py_RETURN_FALSE;
    }
    PyErr_Format(PyExc_RuntimeError, "TraceObject.__exit__ has no cpyTraceFileWrapper");
    PyEval_SetProfile(NULL, NULL);
    Py_DECREF(self);
    TRACE_PROFILE_OR_TRACE_REFCNT_SELF_TRACE_FILE_WRAPPER_END(self);
    return NULL;
}

/**
 * Simple wrapper that dispatches to the internal \c self->trace_file_wrapper.
 *
 * @param self
 * @param op
 * @return None
 */
static PyObject *
cpyProfileOrTraceObject_write_to_log(cpyProfileOrTraceObject *self, PyObject *op) {
    return cpyTraceFileWrapper_write_to_log(self->trace_file_wrapper, op);
}

/**
 * Simple wrapper that dispatches to the internal \c self->trace_file_wrapper.
 *
 * @param self
 * @param op
 * @return None
 */
static PyObject *
cpyProfileOrTraceObject_write_message_to_log(cpyProfileOrTraceObject *self, PyObject *op) {
    return cpyTraceFileWrapper_write_message_to_log(self->trace_file_wrapper, op);
}

static PyMethodDef cpyProfileObject_methods[] = {
        {"__enter__",            (PyCFunction) ProfileObject_enter, METH_NOARGS,
                "Attach a Profile object to the C runtime."},
        {"__exit__",             (PyCFunction) ProfileObject_exit,  METH_VARARGS,
                "Detach a Profile object from the C runtime."},
        /* TODO: Remove this in favour of write_message_to_log()? */
        {
         "write_to_log",         (PyCFunction) cpyProfileOrTraceObject_write_to_log,
                                                                    METH_O,
                "Write any string to the existing log file with a newline. Returns None."
                " Warning: This is not compatible with the log file format."
        },
        {
         "write_message_to_log", (PyCFunction) cpyProfileOrTraceObject_write_message_to_log,
                                                                    METH_O,
                "Write a string as a message to the existing log file with a newline. Returns None."
                " Note: This is compatible with the log file format."
        },
        {
         "log_file_path",
                                 (PyCFunction) get_log_file_path_profile,
                                                                    METH_NOARGS,
                "Return the current log file path for profiling."
        },
        {NULL, NULL, 0, NULL}  /* Sentinel */
};

static PyTypeObject cpyProfileObjectType = {
        PyVarObject_HEAD_INIT(NULL, 0)
        .tp_name = "cPyMemTrace.Profile",
        .tp_doc = "A context manager to attach a C profile function to the interpreter.\n"
                  "This takes the following optional arguments:\n\n"
                  "- ``d_rss_trigger``: this decides when a trace event gets recorded."
                  " Suitable values:\n\n  - '-1' : whenever an RSS change >= page size (usually 4096 bytes) is noticed."
                  "\n\n  - '0' : every event."
                  "\n\n  - n: whenever an RSS change >= n is noticed."
                  "\n\n  Default is -1."
                  "\n\n- ``message``: An optional message to write to the begining of the log file."
                  "\n\n- ``filepath``: An optional specific path to the log file."
                  "\n  By default this writes to a file in the current working directory named"
                  " ``\"YYYYMMDD_HHMMMSS_<PID>_P_<depth>_PY<Python Version>.log\"``"
                  " For example ``\"20241107_195847_62264_P_0_PY3.13.0b3.log\"``"
                  "\n\nThis is slightly less invasive profiling than ``cPyMemTrace.Trace`` as the profile function is"
                  " called for all monitored events except the Python ``PyTrace_LINE PyTrace_OPCODE`` and"
                  " ``PyTrace_EXCEPTION`` events.",
        .tp_basicsize = sizeof(cpyProfileOrTraceObject),
        .tp_itemsize = 0,
        .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
        .tp_alloc = PyType_GenericAlloc,
        .tp_new = cpyProfileOrTraceObject_new,
        .tp_init = (initproc) cpyProfileOrTraceObject_init,
        .tp_dealloc = (destructor) cpyProfileOrTraceObject_dealloc,
        .tp_methods = cpyProfileObject_methods,
        .tp_members = cpyProfileOrTraceObject_members,
};
/**** END: Context manager for attach_profile_function() and detach_profile_function() ****/

// MARK: Context manager for TraceObject
/**** Context manager for attach_trace_function() and detach_trace_function() ****/

/**
 * Attach a new profile wrapper to the \c static_trace_wrapper.
 * @param d_rss_trigger
 * @param message
 * @return The \c static_trace_wrapper or \c NULL on failure in which case an exception will have been set.
 */
static cpyTraceFileWrapper *
py_attach_trace_function(int d_rss_trigger, const char *message, const char *specific_filename) {
    assert(!PyErr_Occurred());
    cpyTraceFileWrapper *wrapper = new_trace_file_wrapper(d_rss_trigger, message, specific_filename, 0);
    if (wrapper) {
        wrapper_ll_push(&static_trace_wrappers, wrapper);
        // This increments the wrapper reference count.
        PyEval_SetTrace(&trace_or_profile_function, (PyObject *) wrapper);
        // Write a marker, in this case it is the line number of the frame.
        trace_or_profile_function((PyObject *) wrapper, PyEval_GetFrame(), PyTrace_LINE, Py_None);
        assert(!PyErr_Occurred());
        return wrapper;
    }
    PyErr_SetString(PyExc_RuntimeError, "py_attach_trace_function(): Could not attach profile function.");
    return NULL;
}

static PyObject *
TraceObject_enter(cpyProfileOrTraceObject *self) {
    assert(!PyErr_Occurred());
    if (self->py_specific_filename) {
        self->trace_file_wrapper = py_attach_trace_function(
                self->d_rss_trigger, self->message, PyBytes_AsString((PyObject *) self->py_specific_filename)
        );
    } else {
        self->trace_file_wrapper = py_attach_trace_function(self->d_rss_trigger, self->message, NULL);
    }
    if (self->trace_file_wrapper == NULL) {
        assert(PyErr_Occurred());
        return NULL;
    }
    Py_INCREF(self);
    assert(!PyErr_Occurred());
    return (PyObject *) self;
}

static PyObject *
TraceObject_exit(cpyProfileOrTraceObject *self, PyObject *Py_UNUSED(args)) {
    // No assert(!PyErr_Occurred()); as an exception might have been set by the users code.
    if (self->trace_file_wrapper) {
        // PyEval_SetTrace() will decrement the reference count that incremented by
        // PyEval_SetTrace() on __enter__
        PyEval_SetTrace(NULL, NULL);
        cpyTraceFileWrapper *trace_file_wrapper = (cpyTraceFileWrapper *) self->trace_file_wrapper;
        cpyTraceFileWrapper_close_file(trace_file_wrapper);
        /* NOTE: wrapper_ll_pop returns a cpyTraceFileWrapper *.
         * This should **not** be decref'd here as CPython will do that on completion of a
         * with statement. */
        wrapper_ll_pop(&static_trace_wrappers);

        /* Now set the Profile of the previous one if available. */
        trace_file_wrapper = wrapper_ll_get(static_trace_wrappers);
        if (trace_file_wrapper) {
            PyEval_SetTrace(&trace_or_profile_function, (PyObject *) trace_file_wrapper);
            /* Put a marker in the file. */
            assert(trace_file_wrapper->file);
            trace_wrapper_write_message_to_log_file(
                    trace_file_wrapper,
                    "Re-attaching previous trace file wrapper."
            );
        }

        TRACE_PROFILE_OR_TRACE_REFCNT_SELF_TRACE_FILE_WRAPPER_END(self);
        Py_RETURN_FALSE;
    }
    PyErr_Format(PyExc_RuntimeError, "TraceObject.__exit__ has no cpyTraceFileWrapper");
    PyEval_SetTrace(NULL, NULL);
    return NULL;
}

static PyMethodDef cpyTraceObject_methods[] = {
        {"__enter__",            (PyCFunction) TraceObject_enter, METH_NOARGS,
                "Attach a Trace object to the C runtime."},
        {"__exit__",             (PyCFunction) TraceObject_exit,  METH_VARARGS,
                "Detach a Trace object from the C runtime."},
        /* TODO: Remove this in favour of write_message_to_log()? */
        {
         "write_to_log",         (PyCFunction) cpyProfileOrTraceObject_write_to_log,
                                                                  METH_O,
                "Write any string to the existing log file with a newline. Returns None."
                " Warning: This is not compatible with the log file format."
        },
        {
         "write_message_to_log", (PyCFunction) cpyProfileOrTraceObject_write_message_to_log,
                                                                  METH_O,
                "Write a string as a message to the existing log file with a newline. Returns None."
                " Note: This is compatible with the log file format."
        },
        {
         "log_file_path",
                                 (PyCFunction) get_log_file_path_trace,
                                                                  METH_NOARGS,
                "Return the current log file path for tracing."
        },
        {NULL, NULL, 0, NULL}  /* Sentinel */
};

static PyTypeObject cpyTraceObjectType = {
        PyVarObject_HEAD_INIT(NULL, 0)
        .tp_name = "cPyMemTrace.Trace",
        .tp_doc = "A context manager to attach a C trace function to the interpreter.\n"
                  "This takes the following optional arguments:\n\n"
                  "- ``d_rss_trigger``: this decides when a trace event gets recorded."
                  " Suitable values:\n\n  - '-1' : whenever an RSS change >= page size (usually 4096 bytes) is noticed."
                  "\n\n  - '0' : every event."
                  "\n\n  - n: whenever an RSS change >= n is noticed."
                  "\n\n  Default is -1."
                  "\n\n- ``message``: An optional message to write to the begining of the log file."
                  "\n\n- ``filepath``: An optional specific path to the log file."
                  "\n  By default this writes to a file in the current working directory named"
                  " ``\"YYYYMMDD_HHMMMSS_<PID>_P_<depth>_PY<Python Version>.log\"``"
                  " For example ``\"20241107_195847_62264_P_0_PY3.13.0b3.log\"``"
                  "\n\nThe tracing function does receive Python line-number events and per-opcode events"
                  " but does not receive any event related to C functionss being called."
                  " For that use ``cPyMemTrace.Profile``",
        .tp_basicsize = sizeof(cpyProfileOrTraceObject),
        .tp_itemsize = 0,
        .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
        .tp_alloc = PyType_GenericAlloc,
        .tp_new = cpyProfileOrTraceObject_new,
        .tp_init = (initproc) cpyProfileOrTraceObject_init,
        .tp_dealloc = (destructor) cpyProfileOrTraceObject_dealloc,
        .tp_methods = cpyTraceObject_methods,
        .tp_members = cpyProfileOrTraceObject_members,
};
/**** END: Context manager for attach_trace_function() and detach_trace_function() ****/

// MARK: Reference Tracing. Python 3.13+

#if PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION >= 13

/**
 *
 * Created by Paul Ross on 2026-03-11.
 * This contains the Python interface to the C reference tracer for Python 3.13+.
 * See https://docs.python.org/3/c-api/profiling.html#reference-tracing
 *
 * Monitored events are:
 * PyRefTracer_CREATE https://docs.python.org/3/c-api/profiling.html#c.PyRefTracer_CREATE
 * PyRefTracer_DESTROY https://docs.python.org/3/c-api/profiling.html#c.PyRefTracer_DESTROY
 * Possibly: PyRefTracer_TRACKER_REMOVED https://docs.python.org/3/c-api/profiling.html#c.PyRefTracer_TRACKER_REMOVED
 *
 */

/**
 * Documentation https://docs.python.org/3/c-api/profiling.html#reference-tracing
 * This is for Python 3.13+
 * Example: https://github.com/python/cpython/pull/115945/changes
 *
 * This writes every new/delete to a log file.
 *
 * Following the pattern above this is implemented as context managers with a linked list of logger.
 */

/**
 * The will be the opaque <tt>void *data</tt> structure registered with
 * PyRefTracer_SetTracer function:
 * https://docs.python.org/3/c-api/profiling.html#c.PyRefTracer_SetTracer
 *
 * There will be a stack of these as a linked list:
 *
 * - \c __enter__ will open the file and push a new one to the top of the stack.
 * - \c __exit__ will close the file and pop one of the top of the stack.
 *
 * The callback function writes to the top of the stack.
 */
struct reference_tracing_data {
    /* File name will be const char *create_filename('O', int reference_tracing_data_depth) */
    FILE *log_file;
    /* These counters give an overall state of the allocations and de-allocations.
     * On __exit__ these will be reported to the log file. */
    size_t count_new;
    size_t count_del;
    /* Allow computation of dRSS. */
    size_t rss;
};

/**
 * A node in the linked list of \c reference_trace_allocations_data
 *
 * NOTE: Operations on this list do not manipulate the reference counts
 * of the Python objects.
 * That is up to the caller of these functions.
 */
struct cReferenceTracingLinkedListNode {
    struct reference_tracing_data *data;
    struct cReferenceTracingLinkedListNode *next;
};

/**
 * The linked list of \c reference_tracing_data nodes.
 */
static struct cReferenceTracingLinkedListNode *reference_tracing_ll = NULL;

/**
 * Get the head of the Reference Trancing linked list.
 *
 * @param linked_list The linked list.
 * @return The head node or NULL if the list is empty.
 */
struct reference_tracing_data *
reference_tracing_ll_get_data(struct cReferenceTracingLinkedListNode *linked_list) {
    if (linked_list) {
        return linked_list->data;
    }
    return NULL;
}

/**
 * Push a created <tt>struct reference_tracing_data</tt> on the front of the list.
 *
 * @param linked_list The linked list reference_trace_wrappers.
 * @param node The node to add. The linked list takes ownership of this pointer.
 */
void
reference_tracing_ll_push(
        struct cReferenceTracingLinkedListNode **h_linked_list,
        struct reference_tracing_data *data
) {
    struct cReferenceTracingLinkedListNode *new_node = malloc(
            sizeof(struct cReferenceTracingLinkedListNode)
    );
    new_node->data = data;
    new_node->next = NULL;
    if (*h_linked_list) {
        // Push to front.
        new_node->next = *h_linked_list;
    }
    *h_linked_list = new_node;
}

/**
 * Free the first value on the list and adjust the list pointer.
 * Undefined behaviour if the list is empty.
 *
 * @param linked_list The linked list of <tt>struct cReferenceTracingLinkedListNode</tt>.
 */
struct reference_tracing_data *
reference_tracing_ll_pop(struct cReferenceTracingLinkedListNode **h_linked_list) {
    assert(*h_linked_list);
    struct cReferenceTracingLinkedListNode *tmp = *h_linked_list;
    *h_linked_list = (*h_linked_list)->next;
    struct reference_tracing_data *ret = tmp->data;
    free(tmp);
    /* NOTE: Caller has to fclose the ->log_file. */
    /* NOTE: Caller has to decide whether to decref the tmp->file_wrapper.
     * If call as the result of and __exit__ function then do **not** decref as CPython
     * will automatically do this on completion of the with statement. */
    return ret;
}

/**
 * Return the length of the Reference Tracing linked list.
 *
 * @param linked_list The linked list.
 * @return The length of the linked list
 */
size_t
reference_tracing_ll_length(struct cReferenceTracingLinkedListNode *p_linked_list) {
    size_t ret = 0;
    while (p_linked_list) {
        ret++;
        p_linked_list = p_linked_list->next;
    }
    return ret;
}

static const char NO_FUNCTION_NAME[] = "<no function name>";
#if 0
static const char NO_FILE_NAME[] = "<no file name>";
#endif

#define REFERENCE_TRACING_GET_SIZEOF 0
#define REFERENCE_TRACING_GET_SIZEOF_TRACE 1

/**
 * Returns the size of a Python object by calling \c sys.getsizeof().
 * This is currently segfaulting for reasons unknown.
 *
 * @param obj The Python object.
 * @return The result of \c sys.getsizeof() or 0 on failure.
 */
#if REFERENCE_TRACING_GET_SIZEOF
static long
sys_getsizeof(PyObject* Py_UNUSED(obj)) {
    long ret = -1;
#if REFERENCE_TRACING_GET_SIZEOF
    assert(obj);
#if REFERENCE_TRACING_GET_SIZEOF_TRACE
    printf(
        "TRACE: %s()#%d %p type: %s refcnt %zd\n",
        __FUNCTION__, __LINE__, (void *)obj, Py_TYPE(obj)->tp_name, Py_REFCNT(obj)
    );
#endif // REFERENCE_TRACING_GET_SIZEOF_TRACE
    if (Py_REFCNT(obj) == 0) {
        return -2;
    }
    Py_INCREF(obj);
#if REFERENCE_TRACING_GET_SIZEOF_TRACE
    printf(
            "TRACE: %s()#%d %p type: %s refcnt %zd\n",
            __FUNCTION__, __LINE__, (void *)obj, Py_TYPE(obj)->tp_name, Py_REFCNT(obj)
    );
#endif // REFERENCE_TRACING_GET_SIZEOF_TRACE
//    if (strcmp(Py_TYPE(obj)->tp_name, "frame") == 0) {
//        return -1;
//    }
//    if (strcmp(Py_TYPE(obj)->tp_name, "builtin_function_or_method") == 0) {
//        return -2;
//    }
//    if (strcmp(Py_TYPE(obj)->tp_name, "bytes") == 0) {
//        return -3;
//    }
    PyObject *sys_module = PyImport_ImportModule("sys");
#if REFERENCE_TRACING_GET_SIZEOF_TRACE
    printf(
            "TRACE: %s()#%d %p type: %s refcnt %zd\n",
            __FUNCTION__, __LINE__, (void *)sys_module, Py_TYPE(sys_module)->tp_name, Py_REFCNT(sys_module)
    );
#endif // REFERENCE_TRACING_GET_SIZEOF_TRACE
    if (sys_module) {
#if REFERENCE_TRACING_GET_SIZEOF_TRACE
        printf("WTF\n");
#endif // REFERENCE_TRACING_GET_SIZEOF_TRACE
        PyObject *result = PyObject_CallMethod(sys_module, "getsizeof", "O", obj);
        if (result) {
            ret = PyLong_AsLong(result);
#if REFERENCE_TRACING_GET_SIZEOF_TRACE
            printf(
                    "TRACE: %s()#%d %p ret: %ld\n",
                    __FUNCTION__, __LINE__, (void *)result, ret
            );
#endif // REFERENCE_TRACING_GET_SIZEOF_TRACE
            Py_DECREF(result);
        }
        Py_DECREF(sys_module);
    }
#if REFERENCE_TRACING_GET_SIZEOF_TRACE
    printf(
            "TRACE: %s()#%d %p type: %s refcnt %zd\n",
            __FUNCTION__, __LINE__, (void *)obj, Py_TYPE(obj)->tp_name, Py_REFCNT(obj)
    );
#endif // REFERENCE_TRACING_GET_SIZEOF_TRACE
    Py_DECREF(obj);
#if REFERENCE_TRACING_GET_SIZEOF_TRACE
    printf("TRACE: %s()#%d returns %ld\n", __FUNCTION__, __LINE__, ret);
#endif // REFERENCE_TRACING_GET_SIZEOF_TRACE
#endif // REFERENCE_TRACING_GET_SIZEOF
    return ret;
}
#endif // #if REFERENCE_TRACING_GET_SIZEOF

/**
 * The callback function that is passed to \c PyRefTracer_SetTracer.
 * This writes to the log file.
 *
 * @param obj The Python object being created or destroyed.
 * @param event The event type
 * @param data The opaque data structure that is a <tt>struct reference_tracing_data</tt>.
 * @return 0 on success, non-zero on failure.
 */
static int
reference_trace_allocations_callback(PyObject *obj, PyRefTracerEvent event, void *data) {
    assert(obj);
    assert(data);
    struct reference_tracing_data *data_alias = (struct reference_tracing_data *) data;
    assert(data_alias->log_file);

    int err_code = -1;
    /* Write the event type. */
    if (event == PyRefTracer_CREATE) {
        // Write the creation of an object.
        fputs("NEW:", data_alias->log_file);
        data_alias->count_new++;
    } else if (event == PyRefTracer_DESTROY) {
        // Write the destruction of an object.
        fputs("DEL:", data_alias->log_file);
        data_alias->count_del++;
#if 0 // Python 3.14 does not seem to support this so cancel support for this event.
#if PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION >= 14
            } else if (event == PyRefTracer_TRACKER_REMOVED) {
                // Here we must do nothing as the PyRefTracer_SetTracer(NULL, NULL)
                // call (below) will trigger a call to this callback function.
                // fputs("REM", the_data->log_file);
                return 0;
#endif // #if PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION >= 14
#endif // 0
    } else {
        // Ignore unknown events instead of Py_UNREACHABLE();
    }
    /* Write the rest of the event line. */
    static char event_text[PY_MEM_TRACE_EVENT_TEXT_MAX_LENGTH];
    double clock_time = (double) clock() / CLOCKS_PER_SEC;
    /* RSS stuff. */
    size_t rss = getCurrentRSS_alternate();
    long d_rss = (long) rss - (long) data_alias->rss;
    data_alias->rss = rss;
    /* NOTE: We need to disable tracing at this point as PyEval_GetFrame() and
     * sys_getsizeof() create arbitrary Python objects and that will
     * recursively call this callback function causing a SIGABRT. */
    void *data_old = NULL;
    /* Call PyRefTracer PyRefTracer_GetTracer(void **data) */
    PyRefTracer tracer_old = PyRefTracer_GetTracer(&data_old);
    /* Sanity check. */
    assert(data_old);
    assert(data_old == data_alias);
    assert(tracer_old);
    assert(tracer_old == &reference_trace_allocations_callback);
    if (PyRefTracer_SetTracer(NULL, NULL)) {
        PyErr_SetString(PyExc_RuntimeError, "PyRefTracer_SetTracer(NULL, NULL) failed.");
        return err_code;
    }
    err_code--;
    /* Now we can call into Python code. */
    PyFrameObject *frame = PyEval_GetFrame();
    Py_XINCREF(frame);
    /* Get the function name. This does not use get_python_function_name(). */
    const char *func_name = NULL;
    if (frame) {
#if PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION >= 11
        /* See https://docs.python.org/3.11/whatsnew/3.11.html#pyframeobject-3-11-hiding */
        func_name = (const char *) PyUnicode_1BYTE_DATA(PyFrame_GetCode(frame)->co_name);
#else
        func_name = (const char *) PyUnicode_1BYTE_DATA(frame->f_code->co_name);
#endif // PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION >= 11
    } else {
        func_name = NO_FUNCTION_NAME;
    }
#if REFERENCE_TRACING_GET_SIZEOF
    long object_size = sys_getsizeof(obj);
    // Should match:
    //     fprintf(self->data->log_file, "HDR: %12s %16s %16s %-32s %-80s %4s %-40s %16s %16s\n",
    //            "Clock", "Address", "RefCnt", "Sizeof", "Type", "File", "Line", "Function", "RSS", "dRSS"
    //    );
    snprintf(event_text, PY_MEM_TRACE_EVENT_TEXT_MAX_LENGTH,
             " %12.6f %16p %16ld %16ld %-32s %-80s %4d %-40s %16zd %16ld",
             clock_time,
             (void *)obj,
             Py_REFCNT(obj),
             object_size,
             Py_TYPE(obj)->tp_name,
             get_python_file_name(frame),
             py_frame_get_line_number(frame),
             func_name,
             rss,
             d_rss
             );
#else
    // Should match:
    //     fprintf(self->data->log_file, "HDR: %12s %16s %16s %-32s %-80s %4s %-40s %16s %16s\n",
    //            "Clock", "Address", "RefCnt", "Type", "File", "Line", "Function", "RSS", "dRSS"
    //    );
    snprintf(event_text, PY_MEM_TRACE_EVENT_TEXT_MAX_LENGTH,
             " %12.6f %16p %16ld %-32s %-80s %4d %-40s %16zd %16ld",
             clock_time,
             (void *) obj,
             Py_REFCNT(obj),
             Py_TYPE(obj)->tp_name,
             get_python_file_name(frame),
             py_frame_get_line_number(frame),
             func_name,
             rss,
             d_rss
    );
#endif // REFERENCE_TRACING_GET_SIZEOF
    Py_XDECREF(frame);
    assert(data_alias);
    assert(data_alias->log_file);
    fputs(event_text, data_alias->log_file);
    fputc('\n', data_alias->log_file);
    fflush(data_alias->log_file);
    /* Restore the Reference Tracer. */
    if (PyRefTracer_SetTracer(tracer_old, data_old)) {
        PyErr_SetString(PyExc_RuntimeError, "PyRefTracer_SetTracer(tracer_old, data_old) failed.");
        return err_code;
    }
    return 0;
}

// MARK: cpyReferenceTracing object
/**
 * The Python Reference Tracing wrapper.
 */
typedef struct {
    PyObject_HEAD
    struct reference_tracing_data *data;
    // User can provide a specific filename.
    // A PyBytesObject.
    PyObject *py_specific_filename;
    // User can provide a specific message to be written at the beginning of the file.
    char *message;
} cpyReferenceTracing;


/**
 * Deallocate the cpyReferenceTracing.
 *
 * @param self The cpyReferenceTracing.
 */
static void
cpyReferenceTracing_dealloc(cpyReferenceTracing *self) {
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_BEG(self);
    if (self->data) {
        if (self->data->log_file) {
            // Write a final line
            fputs(MARKER_LOG_FILE_END, self->data->log_file);
            fputc('\n', self->data->log_file);
            fclose(self->data->log_file);
            self->data->log_file = NULL;
        }
        free(self->data);
        self->data = NULL;
    }
    /* NOTE: Py_XDECREF as self->py_specific_filename might be NULL.
     * For instance when the wrong keyword arguments are supplied to __init__ */
    Py_XDECREF(self->py_specific_filename);
    self->py_specific_filename = NULL;
    free(self->message);
    PyObject_Del((PyObject *) self);
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_END(self);
}

/**
 * Allocate the cpyReferenceTracing.
 *
 * @param type The cpyReferenceTracing type.
 * @param _unused_args
 * @param _unused_kwds
 * @return The cpyReferenceTracing instance.
 */
static PyObject *
cpyReferenceTracing_new(PyTypeObject *type, PyObject *Py_UNUSED(args), PyObject *Py_UNUSED(kwds)) {
    assert(!PyErr_Occurred());
    cpyReferenceTracing *self;
    self = (cpyReferenceTracing *) type->tp_alloc(type, 0);
    if (self != NULL) {
        self->data = malloc(sizeof(struct reference_tracing_data));
        self->data->log_file = NULL;
        self->data->count_new = 0;
        self->data->count_del = 0;
        self->py_specific_filename = NULL;
        self->message = NULL;
    }
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_END(self);
    return (PyObject *) self;
}

/**
 * Initialise the Reference Tracer, open the log file and write the preamble.
 *
 * @param self
 * @param args
 * @param kwds
 * @return
 */
static int
cpyReferenceTracing_init(cpyReferenceTracing *self, PyObject *args, PyObject *kwds) {
    assert(!PyErr_Occurred());
    TRACE_PROFILE_OR_TRACE_REFCNT_SELF_TRACE_FILE_WRAPPER_BEG(self);
    static char *kwlist[] = {"message", "filepath", NULL};
    char *message = NULL;
//    char *log_file_path = NULL;
//    static char file_path_buffer[PYMEMTRACE_PATH_NAME_MAX_LENGTH + 1];

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|sO&", kwlist, &message, PyUnicode_FSConverter,
                                     &self->py_specific_filename)) {
        assert(PyErr_Occurred());
        return -1;
    }
    if (message) {
        self->message = malloc(strlen(message) + 1);
        if (self->message) {
            strcpy(self->message, message);
        } else {
            PyErr_Format(PyExc_MemoryError, "cpyReferenceTracing_init() can not allocate memory in type %s.",
                         Py_TYPE(self)->tp_name);
            return -2;
        }
    }
    assert(!PyErr_Occurred());
    TRACE_PROFILE_OR_TRACE_REFCNT_SELF_TRACE_FILE_WRAPPER_END(self);
    return 0;
}

// MARK: - cpyReferenceTracing members

static PyMemberDef cpyReferenceTracing_members[] = {
//        {
//                "log_file_path",
//                Py_T_STRING,
//                offsetof(cpyReferenceTracing, log_file_path),
//                Py_READONLY,
//                "The path to the log file being written."
//        },
        {NULL, 0, 0, 0, NULL} /* Sentinel */
};

// MARK: - cpyReferenceTracing methods

/**
 * Write any string to the existing logfile.
 * Note: This is compatible with the log file format.
 *
 * @param self The file wrapper.
 * @param op The Python unicode string.
 * @return None on success, NULL on failure (not a unicode argument).
 */
static PyObject *
cpyReferenceTracing_write_message_to_log(cpyReferenceTracing *self, PyObject *op) {
    assert(!PyErr_Occurred());
    if (!self->data->log_file) {
        PyErr_SetString(PyExc_IOError, "Log file is closed.");
        return NULL;
    }
    if (!PyUnicode_Check(op)) {
        PyErr_Format(
                PyExc_ValueError,
                "write_message_to_log() requires a single string, not type %s",
                Py_TYPE(op)->tp_name
        );
        return NULL;
    }
    Py_UCS1 *c_str = PyUnicode_1BYTE_DATA(op);
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_BEG(self);
    fputs("MSG: ", self->data->log_file);
    fputs((const char *) c_str, self->data->log_file);
    fputc('\n', self->data->log_file);
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_END(self);
    Py_RETURN_NONE;
}

/**
 * De-register the existing tracer, push new data onto the linked list and register it.
 *
 * @param self
 * @return
 */
static PyObject *
cpyReferenceTracing_enter(cpyReferenceTracing *self) {
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_BEG(self);
    assert(!PyErr_Occurred());
    static char file_path_buffer[PYMEMTRACE_PATH_NAME_MAX_LENGTH + 1];
    /* Clear the existing tracer. */
    if (PyRefTracer_SetTracer(NULL, NULL)) {
        return NULL;
    }
    /* Open the log file. */
    char *debug_filename = NULL;
    if (self->py_specific_filename) {
        /* User supplied filename. */
        debug_filename = PyBytes_AS_STRING(self->py_specific_filename);
    } else {
        /* Default to a standard log file name in the current working directory. */
        size_t ll_depth = reference_tracing_ll_length(reference_tracing_ll);
        int err_code = create_filename_within_cwd('O', ll_depth, file_path_buffer, PYMEMTRACE_PATH_NAME_MAX_LENGTH);
        if (err_code <= 0) {
            PyErr_Format(
                    PyExc_RuntimeError, "%s#%d Can not print to buffer, error %d", __FUNCTION__, __LINE__, err_code
            );
            return NULL;
        }
        self->py_specific_filename = (PyObject *)PyBytes_FromString(file_path_buffer);
        debug_filename = file_path_buffer;
    }
    self->data->log_file = fopen(debug_filename, "w");
    if (!self->data->log_file) {
        PyErr_Format(PyExc_IOError, "Can not open log file %s", debug_filename);
        return NULL;
    }
#if DEBUG
    fprintf(
            stdout,
            "DEBUG: Reference Tracing opening log file \"%s\"\n",
            PyBytes_AS_STRING(self->py_specific_filename)
            );
#endif
    /* Write the opening message. */
    if (self->message) {
        fputs(self->message, self->data->log_file);
        fputc('\n', self->data->log_file);
    }
    /* Write the header. */
    fputs(MARKER_LOG_FILE_START, self->data->log_file);
    fputc('\n', self->data->log_file);
#if REFERENCE_TRACING_GET_SIZEOF
    fprintf(self->data->log_file, "HDR: %12s %16s %16s %16s %-32s %-80s %4s %-40s %16s %16s\n",
        "Clock", "Address", "RefCnt", "Sizeof", "Type", "File", "Line", "Function", "RSS", "dRSS"
    );
#else
    fprintf(self->data->log_file, "HDR: %12s %16s %16s %-32s %-80s %4s %-40s %16s %16s\n",
            "Clock", "Address", "RefCnt", "Type", "File", "Line", "Function", "RSS", "dRSS"
    );
#endif // REFERENCE_TRACING_GET_SIZEOF
    /* Push the data onto the head of the linked list. */
    reference_tracing_ll_push(&reference_tracing_ll, self->data);
    /* Register the existing tracer. */
    if (PyRefTracer_SetTracer(&reference_trace_allocations_callback, self->data)) {
        return NULL;
    }
    Py_INCREF(self);
    assert(!PyErr_Occurred());
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_END(self);
    return (PyObject *) self;
}

/**
 * This:
 * - De-registers the existing tracer.
 * - Pops the node off the linked list.
 * - Finish up the file.
 * - Close the file.
 * - Register the previous tracer from the linked list.
 *
 * @param self
 * @param _unused_args
 * @return
 */
static PyObject *
cpyReferenceTracing_exit(cpyReferenceTracing *self, PyObject *Py_UNUSED(args)) {
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_BEG(self);
    // No assert(!PyErr_Occurred()); as an exception might have been set by the users code.
    if (self->data) {
        // PyRefTracer_SetTracer() will decrement the reference count that incremented by
        // PyRefTracer_SetTracer() on __enter__

        /* De-registers the existing tracer. */
        PyRefTracer_SetTracer(NULL, NULL);
        /* Pops the node off the linked list. */
        struct reference_tracing_data *data = reference_tracing_ll_pop(&reference_tracing_ll);
        assert(data == self->data);
        if (!data) {
            PyErr_SetString(PyExc_RuntimeError, "__exit__ when nothing is on the linked list.");
            return NULL;
        }
        /* Finish up the file. */
        fputs(MARKER_LOG_FILE_END, data->log_file);
        fputc('\n', data->log_file);
        /* Close the file. */
        fclose(self->data->log_file);
        self->data->log_file = NULL;
        /* Register the previous tracer from the linked list. */
        data = reference_tracing_ll_get_data(reference_tracing_ll);
        if (data) {
            PyRefTracer_SetTracer(&reference_trace_allocations_callback, data);
        }
        if (PyErr_Occurred()) {
            Py_RETURN_TRUE;
        }
        Py_RETURN_FALSE;
    }
    PyErr_Format(PyExc_RuntimeError, "ReferenceTracing.__exit__ has no cpyTraceFileWrapper");
    PyEval_SetTrace(NULL, NULL);
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_END(self);
    return NULL;
}


static PyObject *
cpyReferenceTracing_get_log_file_path(cpyReferenceTracing *self, PyObject *Py_UNUSED(arg)) {
    assert(!PyErr_Occurred());
    if (self->py_specific_filename) {
        return Py_BuildValue("s", PyBytes_AS_STRING(self->py_specific_filename));
    } else {
        Py_RETURN_NONE;
    }
}

static PyMethodDef cpyReferenceTracing_methods[] = {
        {
                "__enter__",
                            (PyCFunction) cpyReferenceTracing_enter,
                                                                    METH_NOARGS,
                "Attach a Reference Tracing object to the C runtime.",
        },
        {       "__exit__", (PyCFunction) cpyReferenceTracing_exit, METH_VARARGS,
                "Detach a Reference Tracing object from the C runtime."},
        {
                "write_message_to_log",
                            (PyCFunction) cpyReferenceTracing_write_message_to_log,
                                                                    METH_O,
                "Write a string as a message to the existing log file with a newline. Returns None."
        },
        {
                "log_file_path",
                            (PyCFunction) cpyReferenceTracing_get_log_file_path,
                                                                    METH_NOARGS,
                "Return the current log file path for the Reference Tracer."
        },
        {NULL, NULL, 0, NULL}  /* Sentinel */
};

// MARK: - cpyReferenceTracing declaration

static PyTypeObject cpyReferenceTracingType = {
        PyVarObject_HEAD_INIT(NULL, 0)
        .tp_name = "cPyMemTrace.ReferenceTracing",
        .tp_doc = "A Reference Tracing object that reports object allocations and de-allocations."
                  "A context manager to attach a C profile function to the interpreter.\n"
                  "This takes the following optional arguments:\n\n"
                  "\n\n- ``message``: An optional message to write to the begining of the log file."
                  "\n\n- ``filepath``: An optional specific path to the log file."
                  "\n  By default this writes to a file in the current working directory named"
                  " ``\"YYYYMMDD_HHMMMSS_<int>_<PID>_O_<depth>_PY<Python Version>.log\"``"
                  " For example ``\"20241107_195847_12_62264_O_0_PY3.13.0b3.log\"``"
                  "\n",
        .tp_basicsize = sizeof(cpyReferenceTracing),
        .tp_itemsize = 0,
        .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
        .tp_new = cpyReferenceTracing_new,
        .tp_init = (initproc) cpyReferenceTracing_init,
        .tp_alloc = PyType_GenericAlloc,
        .tp_dealloc = (destructor) cpyReferenceTracing_dealloc,
        .tp_members = cpyReferenceTracing_members,
        .tp_methods = cpyReferenceTracing_methods,
};

#endif // #if PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION >= 13

// MARK: cPyMemTrace methods.

static PyObject *
py_rss(void) {
    assert(!PyErr_Occurred());
    return PyLong_FromSize_t(getCurrentRSS_alternate());
}

static PyObject *
py_rss_peak(void) {
    assert(!PyErr_Occurred());
    return PyLong_FromSize_t(getPeakRSS());
}

static PyObject *
profile_wrapper_depth(void) {
    assert(!PyErr_Occurred());
    return Py_BuildValue("n", wrapper_ll_length(static_profile_wrappers));
}

static PyObject *
trace_wrapper_depth(void) {
    assert(!PyErr_Occurred());
    return Py_BuildValue("n", wrapper_ll_length(static_trace_wrappers));
}

#if PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION >= 13
static PyObject *
reference_tracing_wrapper_depth(void) {
    assert(!PyErr_Occurred());
    return Py_BuildValue("n", reference_tracing_ll_length(reference_tracing_ll));
}
#endif

static PyMethodDef cPyMemTraceMethods[] = {
        {
                "rss",
                (PyCFunction) py_rss,
                METH_NOARGS,
                "Return the current RSS in bytes.",
        },
        {
                "rss_peak",
                (PyCFunction) py_rss_peak,
                METH_NOARGS,
                "Return the peak RSS in bytes.",
        },
        {
                "profile_wrapper_depth",
                (PyCFunction) profile_wrapper_depth,
                METH_NOARGS,
                "Return the depth of the profile wrapper stack.",
        },
        {
                "trace_wrapper_depth",
                (PyCFunction) trace_wrapper_depth,
                METH_NOARGS,
                "Return the depth of the trace wrapper stack.",
        },
#if PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION >= 13
        {
                "reference_tracing_wrapper_depth",
                (PyCFunction) reference_tracing_wrapper_depth,
                METH_NOARGS,
                "Return the depth of the Reference Tracing wrapper stack.",
        },
#endif
        {NULL, NULL, 0, NULL}        /* Sentinel */
};

// MARK: cPyMemTrace module

PyDoc_STRVAR(py_mem_trace_doc,
             "Module that contains C memory tracer classes and functions."
             "\nNotably this has Profile() and Trace() that can attach to the Python runtime and report memory usage"
             " events."
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
    if (PyType_Ready(&cpyTraceFileWrapperType) < 0) {
        return NULL;
    }
    Py_INCREF(&cpyTraceFileWrapperType);

    /* Add the Profile object. */
    if (PyType_Ready(&cpyProfileObjectType) < 0) {
        Py_DECREF(m);
        return NULL;
    }
    Py_INCREF(&cpyProfileObjectType);
    if (PyModule_AddObject(m, "Profile", (PyObject *) &cpyProfileObjectType) < 0) {
        Py_DECREF(&cpyProfileObjectType);
        Py_DECREF(m);
        return NULL;
    }

    /* Add the Trace object. */
    if (PyType_Ready(&cpyTraceObjectType) < 0) {
        Py_DECREF(m);
        return NULL;
    }
    Py_INCREF(&cpyTraceObjectType);
    if (PyModule_AddObject(m, "Trace", (PyObject *) &cpyTraceObjectType) < 0) {
        Py_DECREF(&cpyTraceObjectType);
        Py_DECREF(m);
        return NULL;
    }

#if PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION >= 13
    /* Add the Reference Tracing object. */
    if (PyType_Ready(&cpyReferenceTracingType) < 0) {
        Py_DECREF(m);
        return NULL;
    }
    Py_INCREF(&cpyReferenceTracingType);
    if (PyModule_AddObject(m, "ReferenceTracing", (PyObject *) &cpyReferenceTracingType) < 0) {
        Py_DECREF(&cpyReferenceTracingType);
        Py_DECREF(m);
        return NULL;
    }
#endif // #if PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION >= 13

    return m;
}

int
debug_cPyMemtrace(int argc, char **argv) {
    printf("Testing cPyMemTrace. argc=%d\n", argc);
    for (int i = 0; i < argc; ++i) {
        printf("Arg[%d]: %s\n", i, argv[i]);
    }

    // TODO: Initialisation for different Python versions.
    PyStatus status;
    PyConfig config;

    PyConfig_InitPythonConfig(&config);
    config.isolated = 1;
    status = PyConfig_SetBytesArgv(&config, argc, argv);
    if (PyStatus_Exception(status)) {
        return -1;
    }
//    Py_Initialize();
    status = Py_InitializeFromConfig(&config);
    if (PyStatus_Exception(status)) {
        return -2;
    }

    /* Run the repl. exit() in the console to terminate, the rest of this code will not run. */
#if 0
    int py_run_main = Py_RunMain();
    fprintf(stdout, "Py_RunMain() returned %d\n", py_run_main);
    if (py_run_main) {
        return py_run_main;
    }
#endif

    {
        /* Debug trace wrapper. */
        {
            if (PyType_Ready(&cpyTraceFileWrapperType) < 0) {
                return -8;
            }
            Py_INCREF(&cpyTraceFileWrapperType);

            cpyTraceFileWrapper *trace_wrapper = (cpyTraceFileWrapper *) cpyTraceFileWrapper_new(
                    &cpyTraceFileWrapperType, NULL, NULL
            );
            fprintf(stdout, "cpyTraceFileWrapper *trace_wrapper:\n");
            PyObject_Print((PyObject *) trace_wrapper, stdout, Py_PRINT_RAW);

            PyFrameObject *frame_object = PyEval_GetFrame();
            trace_wrapper_write_frame_data_to_event_text(trace_wrapper, frame_object, PyTrace_CALL, Py_None);

            Py_DECREF((PyObject *) trace_wrapper);
        }
    }
    /* END: Debug trace wrapper. */

    /* Debug profile wrapper. */
    {
        if (PyType_Ready(&cpyProfileObjectType) < 0) {
            return -16;
        }
        Py_INCREF(&cpyProfileObjectType);

        cpyProfileOrTraceObject *profile_object = (cpyProfileOrTraceObject *) cpyProfileOrTraceObject_new(
                &cpyProfileObjectType, NULL, NULL
        );
        {
            PyObject *py_args = Py_BuildValue("()");
//            PyObject *py_kwargs = Py_BuildValue("{}");

            PyObject *py_kwargs = Py_BuildValue("{ss}", "filepath", "Profile_foo_bar_baz.log");
            PyObject_Print((PyObject *) py_kwargs, stdout, Py_PRINT_RAW);
            fputc('\n', stdout);
            int init = cpyProfileOrTraceObject_init(profile_object, py_args, py_kwargs);

            Py_DECREF(py_args);
            Py_DECREF(py_kwargs);
            fprintf(stdout, "cpyProfileOrTraceObject_init() returned %d\n", init);
            PyObject_Print((PyObject *) profile_object, stdout, Py_PRINT_RAW);
            fprintf(stdout, "\n");
        }

        /* This attaches the profiler to the Python runtime. */
        PyObject *result_enter = ProfileObject_enter(profile_object);
        fprintf(stdout, "result_enter:\n");
        PyObject_Print(result_enter, stdout, Py_PRINT_RAW);
        fprintf(stdout, "\n");

#if 0
        /* TODO: Write to the profiler by calling a Python function. */
    PyObject *code_object = Py_CompileStringObject(
            "import os; os.getpid()\n" /* const char *str */,
            NULL /*PyObject *filename */,
            Py_eval_input /* int start */,
            NULL /* PyCompilerFlags *flags */,
            -1 /* int optimize */
    );
    fprintf(stdout, "Py_CompileStringObject: ");
    PyObject_Print(code_object, stdout, Py_PRINT_RAW);
    fprintf(stdout, "\n");
    PyObject *eval_result = PyEval_EvalCode(
            code_object /* PyObject *co */,
            NULL /* PyObject *globals */,
            NULL /* PyObject *locals */
    );
    fprintf(stdout, "Py_CompileStringObject: ");
    PyObject_Print(eval_result, stdout, Py_PRINT_RAW);
    fprintf(stdout, "\n");
#endif

        /* This detaches the profiler from the Python runtime. */
        PyObject *result_exit = ProfileObject_exit(profile_object, NULL);
        fprintf(stdout, "result_exit: ");
        if (result_exit) {
            PyObject_Print(result_exit, stdout, Py_PRINT_RAW);
        } else {
            fprintf(stdout, "NULL");
        }
        fprintf(stdout, "\n");

        /* Context manager example:
         *  with cPyMemTrace.Profile(message=message) as profiler:
         *      # profiler will have refcount of 2, one from the ctor, one from __enter__.
         *  # profiler has a refcount of 1 as __exit__ decrements self..
         *  del profiler
         *  # profiler has a refcount of 0 and is deallocated.
         */
        fprintf(stdout, "First decref from %zd\n", Py_REFCNT(profile_object));
        Py_DECREF((PyObject *) profile_object);
        fprintf(stdout, "Second decref from %zd\n", Py_REFCNT(profile_object));
        Py_DECREF((PyObject *) profile_object);
    }
    /* END: Debug profile wrapper. */

#if PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION >= 13
    /* Debug Reference Tracing wrapper. */
    {
        if (PyType_Ready(&cpyReferenceTracingType) < 0) {
            return -32;
        }
        Py_INCREF(&cpyReferenceTracingType);

        cpyReferenceTracing *ref_tracing_object = (cpyReferenceTracing *) cpyReferenceTracing_new(
                &cpyReferenceTracingType, NULL, NULL
        );
        {
            PyObject *py_args = Py_BuildValue("()");
            PyObject *py_kwargs = Py_BuildValue("{ss}", "filepath", "foo_bar_baz.log");
            PyObject_Print((PyObject *) py_kwargs, stdout, Py_PRINT_RAW);
            fputc('\n', stdout);
            int init = cpyReferenceTracing_init(ref_tracing_object, py_args, py_kwargs);
            Py_DECREF(py_args);
            Py_DECREF(py_kwargs);
            fprintf(stdout, "cpyReferenceTracing_init() returned %d\n", init);
            PyObject_Print((PyObject *) ref_tracing_object, stdout, Py_PRINT_RAW);
            fprintf(stdout, "\n");

            PyObject *result_enter = cpyReferenceTracing_enter(ref_tracing_object);
            fprintf(stdout, "result_enter:\n");
            PyObject_Print(result_enter, stdout, Py_PRINT_RAW);
            fprintf(stdout, "\n");

            /* This detaches the profiler from the Python runtime. */
            PyObject *result_exit = cpyReferenceTracing_exit(ref_tracing_object, NULL);
            fprintf(stdout, "result_exit: ");
            if (result_exit) {
                PyObject_Print(result_exit, stdout, Py_PRINT_RAW);
            } else {
                fprintf(stdout, "NULL");
            }
            fprintf(stdout, "\n");
            Py_DECREF(result_enter);
        }
        Py_DECREF(ref_tracing_object);
    }
    /* End: Debug Reference Tracing wrapper. */
#endif // PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION >= 13

#if 0
    PyObject *bytes_obj = PyBytes_FromStringAndSize(NULL, 1024);
    long getsize = sys_getsizeof(bytes_obj);
    printf("sys_getsizeof() result: %ld\n", getsize);
    Py_DECREF(bytes_obj);
#endif

    /* Cleanup. */
    PyConfig_Clear(&config);
    return Py_FinalizeEx();
}
