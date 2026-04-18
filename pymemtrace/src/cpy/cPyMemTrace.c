/** @file
 *
 * Created by Paul Ross on 29/10/2020.
 * This contains the Python interface to the C memory tracer.
 * See https://docs.python.org/3/c-api/init.html#profiling-and-tracing
 *
 * Monitored events are:
 * \c PyTrace_CALL \c PyTrace_C_CALL \c PyTrace_C_EXCEPTION \c PyTrace_C_RETURN \c PyTrace_EXCEPTION
 * \c PyTrace_LINE \c PyTrace_OPCODE \c PyTrace_RETURN
 *
 * The Python events:
 *
 * - \c PyTrace_CALL When a new call to a Python function or method is being reported, or a new entry into a generator.
 * - \c PyTrace_EXCEPTION When when a Python exception has been raised.
 * - \c PyTrace_LINE When a Python line-number event is being reported.
 * - \c PyTrace_OPCODE When a new Python opcode is about to be executed.
 * - \c PyTrace_RETURN When a Python call is about to return.
 *
 * The C Events:
 * - \c PyTrace_C_CALL When a C function is about to be called.
 * - \c PyTrace_C_EXCEPTION When a C function has raised an exception.
 * - \c PyTrace_C_RETURN When a C function has returned.
 *
 * \c PyEval_SetProfile
 * --------------------
 * The profile function is called for all monitored events except PyTrace_LINE PyTrace_OPCODE and PyTrace_EXCEPTION.
 *
 * So this is useful when tracing C extensions.
 *
 * \c PyEval_SetTrace
 * ------------------
 * This is similar to \c PyEval_SetProfile(), except the tracing function does receive Python line-number events
 * and per-opcode events, but does not receive any event related to C function objects being called.
 * Any trace function registered using \c PyEval_SetTrace() will not receive \c PyTrace_C_CALL,
 * \c PyTrace_C_EXCEPTION or \c PyTrace_C_RETURN as a value for the \c what parameter.
 *
 * So this is useful when tracing Python code ignoring C extensions.
 *
 * Reference Tracing (Python 3.13+)
 * --------------------------------
 *
 * Created by Paul Ross on 08/03/2026.
 * This contains the Python interface to the C reference tracer.
 * See https://docs.python.org/3/c-api/profiling.html#reference-tracing
 *
 * Monitored events are:
 * - \c PyRefTracer_CREATE https://docs.python.org/3/c-api/profiling.html#c.PyRefTracer_CREATE
 * - \c PyRefTracer_DESTROY https://docs.python.org/3/c-api/profiling.html#c.PyRefTracer_DESTROY
 * - Possibly: \c PyRefTracer_TRACKER_REMOVED https://docs.python.org/3/c-api/profiling.html#c.PyRefTracer_TRACKER_REMOVED
 */
#define PY_SSIZE_T_CLEAN

#include <Python.h>
#include "structmember.h"
#include "frameobject.h"
/* Used in reference_trace_is_builtin() */
#include "datetime.h"

#include <stdio.h>
#include <time.h>
#include <assert.h>

#include "get_rss.h"
#include "pymemtrace_util.h"

/// PYMEMTRACE_PATH_NAME_MAX_LENGTH is usually 4kB and that should be sufficient.
#define PY_MEM_TRACE_EVENT_TEXT_MAX_LENGTH PYMEMTRACE_PATH_NAME_MAX_LENGTH

/// Whether to write output.
/// TODO: Remove this?
#define PY_MEM_TRACE_WRITE_OUTPUT
//#undef PY_MEM_TRACE_WRITE_OUTPUT

/// Whether to write clock time.
/// TODO: Remove this?
#define PY_MEM_TRACE_WRITE_OUTPUT_CLOCK
//#undef PY_MEM_TRACE_WRITE_OUTPUT_CLOCK

/// Whether to write previous and next.
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

/**
 * Markers for the beginning of the log file.
 * Make NULL for no marker(s).
 */
static const char *MARKER_LOG_FILE_START = "SOF";

/**
 * Markers for the end of the log file.
 * Make NULL for no marker(s).
 */
static const char *MARKER_LOG_FILE_END = "EOF";

// MARK: Python definitions and functions.

/**
 * Defined in \c Include/cpython/pystate.h
 *
 * @code
 * #define PyTrace_CALL 0
 * #define PyTrace_EXCEPTION 1
 * #define PyTrace_LINE 2
 * #define PyTrace_RETURN 3
 * #define PyTrace_C_CALL 4
 * #define PyTrace_C_EXCEPTION 5
 * #define PyTrace_C_RETURN 6
 * #define PyTrace_OPCODE 7
 * @endcode
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

/**
 * Empty unsigned char string placeholder.
 */
//static const unsigned char MT_U_STRING[] = "";

/**
 * Empty char string placeholder.
 */
//static const char MT_STRING[] = "";

#if 0
static const char *
py_frame_get_python_file_name(PyFrameObject *Py_UNUSED(frame)) {
    return NULL;
}
#endif

/**
 * Extracts a pointer to the Python file name within the frame.
 *
 * @param frame The Python frame.
 * @return A pointer to the Python file name or an empty string on failure.
 */
static const char *
py_frame_get_python_file_name(PyFrameObject *frame) {
    static char file_name[PYMEMTRACE_FILE_NAME_MAX_LENGTH];
//    file_name[0] = '\0';
    strcpy(file_name, "<UNKNOWN_FILE_NAME>");
    if (frame) {
#if PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION >= 11
        /* See https://docs.python.org/3.11/whatsnew/3.11.html#pyframeobject-3-11-hiding
         * Note: PyFrame_GetCode returns a strong reference.
         * See: https://docs.python.org/3/c-api/frame.html#c.PyFrame_GetCode
         * */
//        const unsigned char *file_name = PyUnicode_1BYTE_DATA(PyFrame_GetCode(frame)->co_filename);
        PyCodeObject *code_obj = PyFrame_GetCode(frame);
        if (code_obj) {
            strcpy(file_name, (const char *) PyUnicode_1BYTE_DATA(code_obj->co_filename));
        }
        Py_XDECREF(code_obj);
#else
        strcpy(file_name, (const char *) PyUnicode_1BYTE_DATA(frame->f_code->co_filename));
#endif // PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION >= 11
    }
    return file_name;
}

/**
 * Extracts a pointer to the Python function name within the frame.
 *
 * @param frame The Python frame.
 * @param what The \c PyTrace_... event ID.
 * @param arg The Python event, see "Meaning of arg" in https://docs.python.org/3/c-api/profiling.html#c.Py_tracefunc
 * @return A pointer to the Python function name or an empty string on failure.
 */
static const char *
py_frame_get_python_function_name_with_profile_trace_args(PyFrameObject *frame, int what, PyObject *arg) {
    static char func_name[PYMEMTRACE_FUNCTION_NAME_MAX_LENGTH];
//    func_name[0] = '\0';
    strcpy(func_name, "<UNKNOWN_FUNCTION_NAME>");
    if (frame) {
        assert(PyFrame_Check(frame));
        if (what == PyTrace_C_CALL || what == PyTrace_C_EXCEPTION || what == PyTrace_C_RETURN) {
            strcpy(func_name, PyEval_GetFuncName(arg));
        } else {
#if PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION >= 11
            /* See https://docs.python.org/3.11/whatsnew/3.11.html#pyframeobject-3-11-hiding
             * Note: PyFrame_GetCode returns a strong reference.
             * See: https://docs.python.org/3/c-api/frame.html#c.PyFrame_GetCode
             * */
            PyCodeObject *code_obj = PyFrame_GetCode(frame);
            if (code_obj) {
                strcpy(func_name, (const char *) PyUnicode_1BYTE_DATA(code_obj->co_name));
            }
            Py_XDECREF(code_obj);
#else
            if (frame->f_code) {
                strcpy(func_name, (const char *) PyUnicode_1BYTE_DATA(frame->f_code->co_name));
            }
#endif // PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION >= 11
        }
    }
    return func_name;
}

/**
 * Returns the Python line number.
 *
 * @param frame The Python frame.
 * @return The Python line number or zero on failure.
 */
static int
py_frame_get_line_number(PyFrameObject *frame) {
    if (frame) {
        assert(PyFrame_Check(frame));
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
    /// Store the file path and provide an API that can return it (or None) from profile_wrapper or trace_wrapper.
    char *log_file_path;
    /**
     * The event counter starting from 0 this is incremented for every event.
     * See https://docs.python.org/3/c-api/profiling.html#c.Py_tracefunc
     */
    size_t event_number;
    /**
     * The current RSS value in bytes.
     */
    size_t rss;
    /**
     * The RSS value in bytes that was last written to the log file.
     * Used by comparing the change in RSS and deciding whether to report it.
     */
    size_t last_reported_rss;
    /**
     * This determines the granularity of the log file.
     * <0 - A call to \c trace_or_profile_function() is logged only if the dRSS is >= the page size given by
     *  \c getpagesize() in \c unistd.h.
     * 0 - Every call to trace_or_profile_function() is logged.
     * >0 - A call to trace_or_profile_function() is logged only if the dRSS is >= this value.
     * Default is -1. See cpyProfileOrTraceObject_init() and TraceObject_init().
     */
    int d_rss_trigger;
#ifdef PY_MEM_TRACE_WRITE_OUTPUT
    /**
     * The event number of the last output to the log file.
     */
    size_t previous_event_number;
    /**
     * Buffer to compose event texts.
     */
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
    long d_rss = rss - trace_wrapper->last_reported_rss;
#ifdef PY_MEM_TRACE_WRITE_OUTPUT_CLOCK
    double clock_time = (double) clock() / CLOCKS_PER_SEC;
    snprintf(trace_wrapper->event_text, PY_MEM_TRACE_EVENT_TEXT_MAX_LENGTH,
             "%-12zu +%-6ld %-12.6f %-8s %-80s %4d %-32s %12zu %12ld",
             trace_wrapper->event_number, trace_wrapper->event_number - trace_wrapper->previous_event_number,
             clock_time, WHAT_STRINGS[what],
             py_frame_get_python_file_name(frame),
             py_frame_get_line_number(frame),
             py_frame_get_python_function_name_with_profile_trace_args(frame, what, arg),
             rss, d_rss);
#else
    snprintf(trace_wrapper->event_text, PY_MEM_TRACE_EVENT_TEXT_MAX_LENGTH,
             "%-12zu +%-6ld %-8s %-80s %4d %-32s %12zu %12ld",
             trace_wrapper->event_number, trace_wrapper->event_number - trace_wrapper->previous_event_number,
             WHAT_STRINGS[what], py_frame_get_python_file_name(frame), py_frame_get_line_number(frame),
             py_frame_get_python_function_name(frame, what, arg), rss, d_rss);
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
 *  MSG:  3            +1      4.211822     # message...
 * @endcode
 *
 * @param trace_wrapper The trace or profile wrapper.
 * @param message The message to write.
 */
static void
trace_wrapper_write_message_to_log_file(cpyTraceFileWrapper *trace_wrapper, const char *message) {
#ifdef PY_MEM_TRACE_WRITE_OUTPUT
    assert(trace_wrapper->file);
    fputs("MSG:  ", trace_wrapper->file);
    trace_wrapper_write_event_time_to_event_text(trace_wrapper);
    fputs(trace_wrapper->event_text, trace_wrapper->file);
    fputs(" # ", trace_wrapper->file);
    fputs(message, trace_wrapper->file);
    fputc('\n', trace_wrapper->file);
#endif // PY_MEM_TRACE_WRITE_OUTPUT
}

/**
 * Write the last event then teh EOF marker and then close the file.
 *
 * @param self The Profiler or Tracer as a \c cpyTraceFileWrapper
 */
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
 *
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
 *
 * @param type The cpyTraceFileWrapper type.
 * @param _unused_args
 * @param _unused_kwds
 * @return The \c cpyTraceFileWrapper instance.
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

/**
 * \c cpyTraceFileWrapper methods.
 */
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

/**
 * \c cpyTraceFileWrapper declaration.
 */
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

/**
 * Linked list of Profilers.
 * The current one is at the head of this list.
 */
static tcpyTraceFileWrapperLinkedList *static_profile_wrappers = NULL;

/**
 * Linked list of Tracers.
 * The current one is at the head of this list.
 */
static tcpyTraceFileWrapperLinkedList *static_trace_wrappers = NULL;

/**
 * Get the head of the linked list which is the current Profiler/Tracer.
 *
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
 *
 * @param h_linked_list The linked list, either \c static_profile_wrappers or \c static_trace_wrappers .
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
 *
 * @param h_linked_list The linked list, either \c static_profile_wrappers or \c static_trace_wrappers .
 * @return The node at the head of the linked list.
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
 *
 * @param p_linked_list The linked list, either \c static_profile_wrappers or \c static_trace_wrappers .
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
 *
 * @param h_linked_list The linked list, either \c static_profile_wrappers or \c static_trace_wrappers .
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
 * Whether to write a "PREV:" event.
 *
 * This is false on the first event as that is dealt with by the "FRST:"
 * event in new_trace_file_wrapper()
 *
 * This is true if the dRSS is greater or equal to the trigger and there have
 * been more than one events skipped.
 *
 * @param trace_wrapper
 * @param d_rss The difference between the current RSS and the previous RSS.
 * @return 0 or 1.
 */
static int
trace_or_profile_must_write_previous(cpyTraceFileWrapper *trace_wrapper, long d_rss) {
    int ret;
    if (trace_wrapper->event_number == 0) {
        ret = 0;
    } else {
        ret = labs(d_rss) >= trace_wrapper->d_rss_trigger
              && (trace_wrapper->event_number - trace_wrapper->previous_event_number) > 1;
    }
    return ret;
}

/**
 * Whether to write a "NEXT:" event.
 *
 * This is false on the first event as that is dealt with by the "FRST:"
 * event in new_trace_file_wrapper().
 *
 * This is true if the dRSS is greater or equal to the trigger.
 *
 * @param trace_wrapper
 * @param d_rss The difference between the current RSS and the previous RSS.
 * @return 0 or 1.
 */
static int
trace_or_profile_must_write_next(cpyTraceFileWrapper *trace_wrapper, long d_rss) {
    int ret;
    if (trace_wrapper->event_number == 0) {
        ret = 0;
    } else {
        ret = labs(d_rss) >= trace_wrapper->d_rss_trigger;
    }
    return ret;
}

/**
 * The profile/trace callback function.
 * This is of type \c Py_tracefunc https://docs.python.org/3/c-api/profiling.html#c.Py_tracefunc
 * This is passed to \c PyEval_SetProfile https://docs.python.org/3/c-api/profiling.html#c.PyEval_SetProfile
 * and \c PyEval_SetTrace https://docs.python.org/3/c-api/profiling.html#c.PyEval_SetTrace
 * respectively.
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
    long d_rss_to_report = rss - trace_wrapper->last_reported_rss;
    if (trace_or_profile_must_write_previous(trace_wrapper, d_rss_to_report)) {
        // Previous event.
#ifdef PY_MEM_TRACE_WRITE_OUTPUT_PREV_NEXT
        fputs("PREV: ", trace_wrapper->file);
#endif
        fputs(trace_wrapper->event_text, trace_wrapper->file);
        fputc('\n', trace_wrapper->file);
    }
    if (trace_or_profile_must_write_next(trace_wrapper, d_rss_to_report)) {
        // NOTE: Ignore event number 0 as that is covered by "FRST:" below.
#ifdef PY_MEM_TRACE_WRITE_OUTPUT_PREV_NEXT
        assert(trace_wrapper->file);
        fputs("NEXT: ", trace_wrapper->file);
#endif
        trace_wrapper_write_frame_data_to_event_text(trace_wrapper, frame, what, arg);
        fputs(trace_wrapper->event_text, trace_wrapper->file);
        fputc('\n', trace_wrapper->file);
        trace_wrapper->previous_event_number = trace_wrapper->event_number;
        trace_wrapper->last_reported_rss = rss;
    }
#endif // PY_MEM_TRACE_WRITE_OUTPUT
    trace_wrapper->event_number++;
    trace_wrapper->rss = rss;
    assert(!PyErr_Occurred());
    return 0;
}

/**
 * Create a new profile or trace file wrapper.
 * If there is an existing wrapper on the linked list then that file will be annotated before that wrapper is suspended.
 * Caller has to to push this onto the head of the list and register with the appropriate Profile/Trace function.
 *
 * @param d_rss_trigger The RSS trigger to use.
 *  This determines the granularity of the log file.
 *      - <0 A call to \c trace_or_profile_function() is logged only if the dRSS is >= the page size given by
 *      \c getpagesize() in \c unistd.h.
 *      - 0 Every call to trace_or_profile_function() is logged.
 *      - >0 A call to trace_or_profile_function() is logged only if the dRSS is >= this value.
 *  Default is -1. See \c cpyProfileOrTraceObject_init() and \c TraceObject_init()
 * @param message A message to insert at the beginning of the file which is useful when grep'ping a
 *  large number of files.
 * @param specific_filename If a specific file name is need then use this. If NULL a generic filename will be created.
 * @param is_profile Non-zero if this is to be a Profiler, zero if this is to be a Tracer.
 * @return The new wrapper.
 *  Caller has to to push this onto the head of the list and register with the appropriate Profile/Trace function.
 */
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
        {
            cpyTraceFileWrapper *wrapper_old = NULL;
            if (is_profile) {
                wrapper_old = wrapper_ll_get(static_profile_wrappers);
            } else {
                wrapper_old = wrapper_ll_get(static_trace_wrappers);
            }
            if (wrapper_old) {
                if (is_profile) {
                    trace_wrapper_write_message_to_log_file(
                            wrapper_old,
                            "Detaching this profile file wrapper. New file:"
                    );
                } else {
                    trace_wrapper_write_message_to_log_file(
                            wrapper_old,
                            "Detaching this trace file wrapper. New file:"
                    );
                }
                trace_wrapper_write_message_to_log_file(
                        wrapper_old,
                        file_path_buffer
                );
            }
        }
#if DEBUG
        fprintf(stdout, "DEBUG: Profile/Trace opening log file \"%s\"\n", file_path_buffer);
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
            trace_wrapper->last_reported_rss = 0;
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

/**
 * @return The current Profiling log path as a Python string.
 */
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

/**
 * @return The current Tracing log path as a Python string.
 */
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
/**
 * Context manager for \c attach_profile/trace_function() and \c detach_profile/trace_function()
 * */
typedef struct {
    PyObject_HEAD
    int d_rss_trigger;
    // Message. Add const char *message here that is a malloc copy of the string given in cpyProfileOrTraceObject_init
    char *message;
    // User can provide a specific filename.
    PyBytesObject *py_specific_filename;
    cpyTraceFileWrapper *trace_file_wrapper;
} cpyProfileOrTraceObject;

/**
 * Deallocate the \c cpyProfileOrTraceObject freeing all resources.
 * @param self The \c cpyProfileOrTraceObject object.
 */
static void
cpyProfileOrTraceObject_dealloc(cpyProfileOrTraceObject *self) {
    TRACE_PROFILE_OR_TRACE_REFCNT_SELF_TRACE_FILE_WRAPPER_BEG(self);
    free(self->message);
    Py_XDECREF(self->py_specific_filename);
    Py_XDECREF(self->trace_file_wrapper);
    Py_TYPE(self)->tp_free((PyObject *) self);
    TRACE_PROFILE_OR_TRACE_REFCNT_SELF_TRACE_FILE_WRAPPER_END(self);
}

/**
 * Create a new, un-initialised, \c cpyProfileOrTraceObject object.
 *
 * @param type The \c cpyProfileOrTraceObject type.
 * @param _unused_args
 * @param _unused_kwds
 * @return The \c cpyProfileOrTraceObject object or NULL on failure.
 */
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

/**
 * Initialise the \c cpyProfileOrTraceObject object.
 *
 * @param self The \c cpyProfileOrTraceObject object.
 * @param args Python arguments.
 * @param kwds Python keywords.
 * @return 0 on success, non-zero on failure.
 */
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

/**
 * \c cpyProfileOrTraceObject members. Empty.
 */
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
 *
 * @param d_rss_trigger The delta-RSS level at which to write an event.
 * @param message The opening message.
 * @param specific_filename A specific filename, if NULL one will be generated.
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

/**
 * Implement the \c \_\_enter\_\_() method for a context manager.
 * @param self The Profile or Trace object.
 * @return \c self
 */
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

/**
 * Implement the \c \_\_exit\_\_() method for a context manager.
 * @param self The Profile or Trace object.
 * @param _unused_args
 * @return \c True or \c False
 */
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
            trace_wrapper_write_message_to_log_file(
                    trace_file_wrapper,
                    "Re-attaching this profile file wrapper."
            );
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
 * TODO: Deprecate this in favour of \c cpyProfileOrTraceObject_write_message_to_log() ?
 *
 * @param self The Profile or Trace object.
 * @param op A Python Unicode string.
 * @return None on success, NULL on failure (not a unicode argument).
 */
static PyObject *
cpyProfileOrTraceObject_write_to_log(cpyProfileOrTraceObject *self, PyObject *op) {
    return cpyTraceFileWrapper_write_to_log(self->trace_file_wrapper, op);
}

/**
 * Simple wrapper that dispatches to the internal \c self->trace_file_wrapper.
 *
 * @param self The Profile or Trace object.
 * @param op A Python Unicode string.
 * @return None on success, NULL on failure (not a unicode argument).
 */
static PyObject *
cpyProfileOrTraceObject_write_message_to_log(cpyProfileOrTraceObject *self, PyObject *op) {
    return cpyTraceFileWrapper_write_message_to_log(self->trace_file_wrapper, op);
}

/**
 * Profile class methods.
 */
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

/**
 * Profiler Python type definition.
 */
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
 * Attach a new Trace wrapper to the \c static_trace_wrapper.
 *
 * @param d_rss_trigger The delta-RSS level at which to write an event.
 * @param message The opening message.
 * @param specific_filename A specific filename, if NULL one will be generated.
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

/**
 * Implement the \c \_\_enter\_\_() method for a context manager.
 * @param self
 * @return
 */
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

/**
 * Implement the \c \_\_exit\_\_() method for a context manager.
 * @param self
 * @param _unused_args
 * @return
 */
static PyObject *
TraceObject_exit(cpyProfileOrTraceObject *self, PyObject *Py_UNUSED(args)) {
    // No assert(!PyErr_Occurred()); as an exception might have been set by the users code.

    // PyEval_SetTrace() will decrement the reference count that incremented by
    // PyEval_SetTrace() on __enter__
    PyEval_SetTrace(NULL, NULL);
    if (self->trace_file_wrapper) {
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
                    "Re-attaching this trace file wrapper."
            );
        }

        TRACE_PROFILE_OR_TRACE_REFCNT_SELF_TRACE_FILE_WRAPPER_END(self);
        Py_RETURN_FALSE;
    }
    PyErr_Format(PyExc_RuntimeError, "TraceObject.__exit__ has no cpyTraceFileWrapper");
    return NULL;
}

/**
 * Python Trace class methods.
 */
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

/**
 * Trace Python type definition.
 */
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

/**
 * See https://docs.python.org/3/c-api/profiling.html#reference-tracing
 */
#define REFERENCE_TRACING_AVAILABLE PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION >= 13

/**
 * Note: The Python documentation wrongly states that \c PyRefTracer_TRACKER_REMOVED
 * was added in Python 3.14.
 * It was added in Python 3.15.
 *
 * See: https://docs.python.org/3/c-api/profiling.html#c.PyRefTracer_TRACKER_REMOVED
 */
#define REFERENCE_TRACING_TRACKER_REMOVED_AVAILABLE PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION >= 15

// MARK: ReferenceTracingSimple

#if REFERENCE_TRACING_AVAILABLE

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

// This is only used by Reference Tracing as Profile/Trace use
// py_frame_get_python_function_name_with_profile_trace_args()
#if REFERENCE_TRACING_AVAILABLE
/**
 * Returns the function name in a static C buffer.
 *
 * @param frame The Python frame. Can be NULL.
 * @return A pointer to the static string.
 */
static const char *
py_frame_get_python_function_name(PyFrameObject *frame) {
    static char func_name[PYMEMTRACE_FUNCTION_NAME_MAX_LENGTH];
//    func_name[0] = '\0';
    strcpy(func_name, "<UNKNOWN_FUNCTION_NAME>");
    if (frame) {
        assert(PyFrame_Check(frame));
#if PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION >= 11
        /* See https://docs.python.org/3.11/whatsnew/3.11.html#pyframeobject-3-11-hiding
         * Note: PyFrame_GetCode returns a strong reference.
         * See: https://docs.python.org/3/c-api/frame.html#c.PyFrame_GetCode */
        PyCodeObject *code_obj = PyFrame_GetCode(frame);
        if (code_obj) {
            strcpy(func_name, (const char *) PyUnicode_1BYTE_DATA(code_obj->co_name));
        }
        Py_XDECREF(code_obj);
#else
        if (frame->f_code) {
            strcpy(func_name, (const char *) PyUnicode_1BYTE_DATA(frame->f_code->co_name));
        }
#endif // PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION >= 11
    }
    return func_name;
}
#endif // PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION >= 13

/**
 * This will be the opaque <tt>void *data</tt> structure registered with
 * PyRefTracer_SetTracer function:
 * https://docs.python.org/3/c-api/profiling.html#c.PyRefTracer_SetTracer
 *
 * There will be a stack of these as a linked list:
 *
 * - \c \_\_enter\_\_() push a new one to the top of the stack.
 * - \c \_\_exit\_\_() pop one of the top of the stack.
 *
 * The callback function writes to the head of the linked list.
 */
struct reference_tracing_simple_data {
    /* These counters give an overall state of the allocations and de-allocations. */
    size_t count_new;
    size_t count_del;
};

/**
 * A node in the linked list of \c reference_trace_allocations_data
 *
 * NOTE: Operations on this list do not manipulate the reference counts
 * of the Python objects.
 * That is up to the caller of these functions.
 */
struct cReferenceTracingSimpleLinkedListNode {
    struct reference_tracing_simple_data *data;
    struct cReferenceTracingSimpleLinkedListNode *next;
};

/**
 * The linked list of \c reference_tracing_data nodes.
 */
static struct cReferenceTracingSimpleLinkedListNode *reference_tracing_simple_ll = NULL;

/**
 * Get the data object at the head of the Reference Tracing linked list.
 *
 * @return The head node or NULL if the list is empty.
 */
static struct reference_tracing_simple_data *
reference_tracing_simple_ll_get_data(void) {
    if (reference_tracing_simple_ll) {
        return reference_tracing_simple_ll->data;
    }
    return NULL;
}

/**
 * Push a created <tt>struct reference_tracing_data</tt> on the front of the list.
 *
 * @param data The node to add. The linked list takes ownership of this pointer.
 */
static void
reference_tracing_simple_ll_push(struct reference_tracing_simple_data *data) {
    struct cReferenceTracingSimpleLinkedListNode *new_node = malloc(
            sizeof(struct cReferenceTracingSimpleLinkedListNode)
    );
    new_node->data = data;
    new_node->next = NULL;
    if (reference_tracing_simple_ll) {
        // Push to front.
        new_node->next = reference_tracing_simple_ll;
    }
    reference_tracing_simple_ll = new_node;
}

/**
 * Free the first value on the list and adjust the list pointer.
 * Undefined behaviour if the list is empty.
 * The linked list relinquishes ownership of this pointer.
 *
 * \note
 *  Caller has to \c fclose the \c ->log_file
 *
 * \note
 *  Caller has to decide whether to decref the tmp->file_wrapper.
 *  If the call as the result of an \c \_\_exit\_\_() function then do **not** decref as CPython
 *  will automatically do this on completion of the with statement.
 *
 * @return The struct reference_tracing_simple_data from the head node or NULL.
 */
static struct reference_tracing_simple_data *
reference_tracing_simple_ll_pop(void) {
    assert(reference_tracing_simple_ll);
    struct cReferenceTracingSimpleLinkedListNode *tmp = reference_tracing_simple_ll;
    reference_tracing_simple_ll = reference_tracing_simple_ll->next;
    struct reference_tracing_simple_data *ret = tmp->data;
    free(tmp);
    return ret;
}

/**
 * Return the length of the Reference Tracing Simple linked list.
 *
 * @return The length of the linked list
 */
static size_t
reference_tracing_simple_ll_length(void) {
    size_t ret = 0;
    struct cReferenceTracingSimpleLinkedListNode *p_linked_list = reference_tracing_simple_ll;
    while (p_linked_list) {
        ret++;
        p_linked_list = p_linked_list->next;
    }
    return ret;
}

/**
 * The callback function that is passed to \c PyRefTracer_SetTracer.
 * This writes to the log file.
 *
 * Note that this does not need suspend the Reference Tracer as it does not call CPython functions
 * that might allocate/deallocate
 * Python objects otherwise there will be infinite recursion as that will call this callback.
 *
 * @param _unused_obj The Python object being created or destroyed.
 * @param event The event type
 * @param data The opaque data structure that is a <tt>struct reference_tracing_data</tt>.
 * @return 0 on success, non-zero on failure.
 */
static int
reference_tracing_simple_callback(PyObject *Py_UNUSED(obj), PyRefTracerEvent event, void *data) {
//    assert(obj);
    assert(data);
    struct reference_tracing_simple_data *data_alias = (struct reference_tracing_simple_data *) data;

    /* Write the event type. */
    if (event == PyRefTracer_CREATE) {
        // Write the creation of an object.
        data_alias->count_new++;
    } else if (event == PyRefTracer_DESTROY) {
        data_alias->count_del++;
    } else {
        // Ignore unknown events instead of Py_UNREACHABLE();
    }
    return 0;
}

// MARK: cpyReferenceTracingSimple object

/**
 * The Python Reference Tracing Simple wrapper.
 */
typedef struct {
    PyObject_HEAD
    struct reference_tracing_simple_data *data;
} cpyReferenceTracingSimple;

/**
 * Deallocate the cpyReferenceTracing.
 *
 * @param self The cpyReferenceTracing.
 */
static void
cpyReferenceTracingSimple_dealloc(cpyReferenceTracingSimple *self) {
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_BEG(self);
    if (self->data) {
        free(self->data);
        self->data = NULL;
    }
    PyObject_Del((PyObject *) self);
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_END(self);
}

/**
 * Allocate the cpyReferenceTracingSimple.
 *
 * @param type The \c cpyReferenceTracingSimple type.
 * @param _unused_args
 * @param _unused_kwds
 * @return The cpyReferenceTracingSimple instance.
 */
static PyObject *
cpyReferenceTracingSimple_new(PyTypeObject *type, PyObject *Py_UNUSED(args), PyObject *Py_UNUSED(kwds)) {
    assert(!PyErr_Occurred());
    cpyReferenceTracingSimple *self;
    self = (cpyReferenceTracingSimple *) type->tp_alloc(type, 0);
    if (self != NULL) {
        self->data = malloc(sizeof(struct reference_tracing_simple_data));
        if (!self->data) {
            PyErr_SetString(PyExc_MemoryError, "Can not malloc struct reference_tracing_simple_data");
            return NULL;
        }
        self->data->count_new = 0;
        self->data->count_del = 0;
    }
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_END(self);
    return (PyObject *) self;
}

/**
 * Initialise the Reference Tracer, open the log file and write the preamble.
 *
 * @param _unused_self The \c cpyReferenceTracingSimple object.
 * @param args Ignored.
 * @param kwds Ignored.
 * @return 0 on success, -1 on failure.
 */
static int
cpyReferenceTracingSimple_init(cpyReferenceTracingSimple *Py_UNUSED(self), PyObject *args, PyObject *kwds) {
    assert(!PyErr_Occurred());
    TRACE_PROFILE_OR_TRACE_REFCNT_SELF_TRACE_FILE_WRAPPER_BEG(self);
    static char *kwlist[] = {NULL};

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "", kwlist)) {
        assert(PyErr_Occurred());
        return -1;
    }
    TRACE_PROFILE_OR_TRACE_REFCNT_SELF_TRACE_FILE_WRAPPER_END(self);
    return 0;
}

// MARK: - cpyReferenceTracingSimple members

/**
 * \c cpyReferenceTracingSimple members. Empty.
 */
static PyMemberDef cpyReferenceTracingSimple_members[] = {
//        {
//                "count_new",
//                Py_T_STRING,
//                offsetof(cpyReferenceTracingSimple, count_new),
//                Py_READONLY,
//                "The number of new allocations."
//        },
        {NULL, 0, 0, 0, NULL} /* Sentinel */
};

// MARK: - cpyReferenceTracingSimple methods

/**
 * De-register the existing tracer, push new data onto the linked list and register it.
 *
 * @param self The \c cpyReferenceTracingSimple object.
 * @return self on success. NULL on failure.
 */
static PyObject *
cpyReferenceTracingSimple_enter(cpyReferenceTracingSimple *self) {
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_BEG(self);
    assert(!PyErr_Occurred());
    /* Clear the existing tracer. */
    if (PyRefTracer_SetTracer(NULL, NULL)) {
        PyErr_SetString(PyExc_RuntimeError, "PyRefTracer_SetTracer(NULL, NULL) failed.");
        return NULL;
    }

    /* Push the data onto the head of the linked list. */
    reference_tracing_simple_ll_push(self->data);
    /* Register the existing tracer. */
    if (PyRefTracer_SetTracer(&reference_tracing_simple_callback, self->data)) {
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
 * - Register the previous tracer from the linked list.
 *
 * @param self The \c pyReferenceTracingSimple object.
 * @param _unused_args
 * @return \c True or \c False or NULL on failure.
 */
static PyObject *
cpyReferenceTracingSimple_exit(cpyReferenceTracingSimple *self, PyObject *Py_UNUSED(args)) {
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_BEG(self);
    // No assert(!PyErr_Occurred()); as an exception might have been set by the users code.
    /* De-registers the existing tracer. */
    if (PyRefTracer_SetTracer(NULL, NULL)) {
        PyErr_SetString(PyExc_RuntimeError, "PyRefTracer_SetTracer(NULL, NULL) failed.");
        return NULL;
    }
    if (self->data) {
        // PyRefTracer_SetTracer() will decrement the reference count that incremented by
        // PyRefTracer_SetTracer() on __enter__

        /* Pops the node off the linked list. */
        struct reference_tracing_simple_data *data = reference_tracing_simple_ll_pop();
        assert(data == self->data);
        if (!data) {
            PyErr_SetString(PyExc_RuntimeError, "__exit__ when nothing is on the linked list.");
            return NULL;
        }
        /* Register the previous tracer from the linked list. */
        data = reference_tracing_simple_ll_get_data();
        if (data) {
            PyRefTracer_SetTracer(&reference_tracing_simple_callback, data);
        }
        if (PyErr_Occurred()) {
            Py_RETURN_TRUE;
        }
        Py_RETURN_FALSE;
    }
    PyErr_Format(PyExc_RuntimeError, "ReferenceTracingSimple.__exit__ has no cpyTraceFileWrapper");
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_END(self);
    return NULL;
}


/**
 * This suspends the current Reference Tracing Simple.
 * It does **not** pop it off the linked list but leaves it there to be restored by resume().
 *
 * @return NULL on failure, None on success.
 */
static PyObject *
cpyReferenceTracingSimple_suspend(void) {
    assert(!PyErr_Occurred());
//    struct reference_tracing_simple_data *data = reference_tracing_simple_ll_get_data(
//            reference_tracing_simple_ll
//            );
//    assert(data);

    void *data_old = NULL;
    /* Call PyRefTracer PyRefTracer_GetTracer(void **data) */
    PyRefTracer tracer_old = PyRefTracer_GetTracer(&data_old);
    /* Sanity check. */
    assert(data_old);
//    assert(data_old == data);
    assert(tracer_old);
    if (tracer_old != &reference_tracing_simple_callback) {
        PyErr_SetString(
                PyExc_RuntimeError,
                "PyRefTracer_GetTracer() return value is not the expected callback function."
        );
        return NULL;
    }
    if (PyRefTracer_SetTracer(NULL, NULL)) {
        PyErr_SetString(PyExc_RuntimeError, "PyRefTracer_SetTracer(NULL, NULL) failed.");
        return NULL;
    }
    Py_RETURN_NONE;
}

/**
 * This resumes the current Reference Tracing Simple by re-registering the head of the linked list.
 *
 * @return NULL on failure, None on success.
 */
static PyObject *
cpyReferenceTracingSimple_resume(void) {
    assert(!PyErr_Occurred());
    /* If this function is not paired with suspend() then there might be
     * a Reference Tracer still registered so this call should handle the
     * reference counts correctly. */
    if (PyRefTracer_SetTracer(NULL, NULL)) {
        PyErr_SetString(PyExc_RuntimeError, "PyRefTracer_SetTracer(NULL, NULL) failed.");
        return NULL;
    }
    /* Get the current latest tracer. */
    struct reference_tracing_simple_data *data = reference_tracing_simple_ll_get_data();
    if (data) {
        /* Restore the Reference Tracer. */
        if (PyRefTracer_SetTracer(&reference_tracing_simple_callback, data)) {
            PyErr_SetString(PyExc_RuntimeError, "PyRefTracer_SetTracer(tracer, data) failed.");
            return NULL;
        }
    } else {
        PyErr_SetString(PyExc_RuntimeError, "PyRefTracer.resume() when there is no tracer to register.");
        return NULL;
    }
    Py_RETURN_NONE;
}

/**
 * @return Number of allocations as a Python integer.
 */
static PyObject *
cpyReferenceTracingSimple_count_new(void) {
    assert(!PyErr_Occurred());
    /* Get the current latest tracer. */
    struct reference_tracing_simple_data *data = reference_tracing_simple_ll_get_data();
    if (data) {
        return PyLong_FromLong(data->count_new);
    }
    PyErr_Format(
            PyExc_RuntimeError,
            "%s(): No reference tracing data is on the stack.",
            __FUNCTION__
    );
    return NULL;
}

/**
 * @return Number of de-allocations as a Python integer.
 */
static PyObject *
cpyReferenceTracingSimple_count_del(void) {
    assert(!PyErr_Occurred());
    /* Get the current latest tracer. */
    struct reference_tracing_simple_data *data = reference_tracing_simple_ll_get_data();
    if (data) {
        return PyLong_FromLong(data->count_del);
    }
    PyErr_Format(
            PyExc_RuntimeError,
            "%s(): No reference tracing data is on the stack.",
            __FUNCTION__
    );
    return NULL;
}

/**
 * \c cpyReferenceTracingSimple Python methods.
 */
static PyMethodDef cpyReferenceTracingSimple_methods[] = {
        {
                "__enter__",
                            (PyCFunction) cpyReferenceTracingSimple_enter,
                                                                          METH_NOARGS,
                "Attach a Reference Tracing object to the C runtime.",
        },
        {       "__exit__", (PyCFunction) cpyReferenceTracingSimple_exit, METH_VARARGS,
                "Detach a Reference Tracing object from the C runtime."},
        {
                "suspend",
                            (PyCFunction) cpyReferenceTracingSimple_suspend,
                                                                          METH_NOARGS,
                "Suspend the current Reference Tracer."
        },
        {
                "resume",
                            (PyCFunction) cpyReferenceTracingSimple_resume,
                                                                          METH_NOARGS,
                "Resume the current Reference Tracer."
        },
        {
                "count_new",
                            (PyCFunction) cpyReferenceTracingSimple_count_new,
                                                                          METH_NOARGS,
                "Return the count of new allocations."
        },
        {
                "count_del",
                            (PyCFunction) cpyReferenceTracingSimple_count_del,
                                                                          METH_NOARGS,
                "Return the count of deleted allocations."
        },
        {NULL, NULL, 0, NULL}  /* Sentinel */
};

// MARK: - cpyReferenceTracingSimple declaration

/**
 * The CPython type structure for the \c ReferenceTracingSimple class.
 */
static PyTypeObject cpyReferenceTracingSimpleType = {
        PyVarObject_HEAD_INIT(NULL, 0)
        .tp_name = "cPyMemTrace.ReferenceTracingSimple",
        .tp_doc = "A simple Reference Tracing object that counts object allocations and de-allocations.",
        .tp_basicsize = sizeof(cpyReferenceTracingSimple),
        .tp_itemsize = 0,
        .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
        .tp_new = cpyReferenceTracingSimple_new,
        .tp_init = (initproc) cpyReferenceTracingSimple_init,
        .tp_alloc = PyType_GenericAlloc,
        .tp_dealloc = (destructor) cpyReferenceTracingSimple_dealloc,
        .tp_members = cpyReferenceTracingSimple_members,
        .tp_methods = cpyReferenceTracingSimple_methods,
};

#endif // #if REFERENCE_TRACING_AVAILABLE

// MARK: Reference Tracing to a file
#if REFERENCE_TRACING_AVAILABLE

/**
 *
 * Created by Paul Ross on 2026-03-11.
 * This contains the Python interface to the C reference tracer for Python 3.13+.
 * See https://docs.python.org/3/c-api/profiling.html#reference-tracing
 *
 * Monitored events are:
 * - \c PyRefTracer_CREATE https://docs.python.org/3/c-api/profiling.html#c.PyRefTracer_CREATE
 * - \c PyRefTracer_DESTROY https://docs.python.org/3/c-api/profiling.html#c.PyRefTracer_DESTROY
 * - Possibly: \c PyRefTracer_TRACKER_REMOVED https://docs.python.org/3/c-api/profiling.html#c.PyRefTracer_TRACKER_REMOVED
 *
 * Documentation https://docs.python.org/3/c-api/profiling.html#reference-tracing
 * This is for Python 3.13+
 * Example: https://github.com/python/cpython/pull/115945/changes
 *
 * This writes every allocation/de-allocation to a log file.
 *
 * Following the pattern above, this is implemented as context managers with a linked list of logger.
 *
 * This will be the opaque <tt>void *data</tt> structure registered with
 * \c PyRefTracer_SetTracer function:
 * https://docs.python.org/3/c-api/profiling.html#c.PyRefTracer_SetTracer
 *
 * There will be a stack of these as a linked list:
 *
 * - \c \_\_enter\_\_() will open the file and push a new one to the top of the stack.
 * - \c \_\_exit\_\_() will close the file and pop one of the top of the stack.
 *
 * The callback function writes to the head of the linked list.
 */
struct reference_tracing_data {
    /** The log file.
     * The file name will be <tt>const char *create_filename('O', int reference_tracing_data_depth)</tt> */
    FILE *log_file;
    /** These counters give an overall state of the allocations and de-allocations. */
    size_t count_new;
    size_t count_del;
    /** Allow computation of dRSS. */
    size_t rss;
    /** Flag to include allocation/de-allocation events of builtins.
     * If non-zero the log file and runtime are increased 2x or 4x. */
    int include_builtins;
    /** A Python sequence of strings of typenames to exclude. */
    PyObject *exclude_tp_names;
    /** A Python sequence of strings of typenames to include. */
    PyObject *include_tp_names;
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
 * Get the head of the Reference Tracing linked list as a struct reference_tracing_data.
 *
 * @return The head node or NULL if the list is empty.
 */
static struct reference_tracing_data *
reference_tracing_ll_get_data(void) {
    if (reference_tracing_ll) {
        return reference_tracing_ll->data;
    }
    return NULL;
}

/**
 * Push a created <tt>struct reference_tracing_data</tt> on the front of the list.
 *
 * @param data The node to add. The linked list takes ownership of this pointer.
 */
void
reference_tracing_ll_push(struct reference_tracing_data *data) {
    struct cReferenceTracingLinkedListNode *new_node = malloc(
            sizeof(struct cReferenceTracingLinkedListNode)
    );
    new_node->data = data;
    new_node->next = NULL;
    if (reference_tracing_ll) {
        // Push to front.
        new_node->next = reference_tracing_ll;
    }
    reference_tracing_ll = new_node;
}

/**
 * Free the first value on the list and adjust the list pointer.
 * This gives undefined behaviour if the list is empty.
 * The linked list relinquishes ownership of this pointer.
 *
 * \note
 *  Caller has to \c fclose the \c ->log_file
 *
 * \note
 *  Caller has to decide whether to decref the tmp->file_wrapper.
 *  If the call as the result of an \c \_\_exit\_\_() function then do **not** decref as CPython
 *  will automatically do this on completion of the with statement.
 *
 * @return The struct reference_tracing_data from the head node or NULL.
 */
static struct reference_tracing_data *
reference_tracing_ll_pop(void) {
    assert(reference_tracing_ll);
    struct cReferenceTracingLinkedListNode *tmp = reference_tracing_ll;
    reference_tracing_ll = reference_tracing_ll->next;
    struct reference_tracing_data *ret = tmp->data;
    free(tmp);
    return ret;
}

/**
 * Return the length of the Reference Tracing linked list.
 *
 * @return The length of the linked list
 */
static size_t
reference_tracing_ll_length(void) {
    size_t ret = 0;
    struct cReferenceTracingLinkedListNode *p_linked_list = reference_tracing_ll;
    while (p_linked_list) {
        ret++;
        p_linked_list = p_linked_list->next;
    }
    return ret;
}

// MARK: cpyReferenceTracing object

#if 0
static const char NO_FUNCTION_NAME[] = "<no function name>";
static const char NO_FILE_NAME[] = "<no file name>";
#endif

#if 0
/**
 * From Python/object.h:
 *
 * @code
 *  PyRefTracer_CREATE = 0,
 *  PyRefTracer_DESTROY = 1,
 *  PyRefTracer_TRACKER_REMOVED = 2,
 * @endcode
 *
 * Note: PyRefTracer_TRACKER_REMOVED is Python 3.15+
 */
static const char *REFERENCE_TRACING_EVENT_NAME_STRINGS[] = {
        "PyRefTracer_CREATE",
        "PyRefTracer_DESTROY",
        /* Python 3.15+ */
        "PyRefTracer_TRACKER_REMOVED",
};
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
 * Buffer for composing lines for the log file.
 */
static char reference_tracing_event_text[PY_MEM_TRACE_EVENT_TEXT_MAX_LENGTH];

/**
 * Format and write a prefix and message to the log file.
 * The prefix is typically "MSG" or "ERR"
 *
 * @param data The <tt>struct reference_tracing_data</tt>
 * @param message The message.
 * @param prefix The message prefix such as "MSG" or "ERR".
 * @return Number of bytes written by \c snprintf.
 */
static int
cpyReferenceTracing_write_c_prefix_and_message_to_log(struct reference_tracing_data *data, char *prefix,
                                                      char *message) {
    assert(data);
    assert(data->log_file);
    /* I suspect that this is undefined if the write buffer is the read buffer. */
    assert(message != reference_tracing_event_text);

    double clock_time = (double) clock() / CLOCKS_PER_SEC;
    int ret = snprintf(reference_tracing_event_text, PY_MEM_TRACE_EVENT_TEXT_MAX_LENGTH,
                       "%s: %12.6f # %s",
                       prefix,
                       clock_time,
                       message
    );
    fputs((const char *) reference_tracing_event_text, data->log_file);
    fputc('\n', data->log_file);
    return ret;
}

/**
 * Format and write a message to the log file.
 *
 * @param data The <tt>struct reference_tracing_data</tt>
 * @param message The message.
 * @return Number of bytes written.
 */
static int
cpyReferenceTracing_write_c_message_to_log(struct reference_tracing_data *data, char *message) {
    return cpyReferenceTracing_write_c_prefix_and_message_to_log(data, "MSG", message);
}

/**
 * Format and write an error message to the log file.
 *
 * @param data The <tt>struct reference_tracing_data</tt>
 * @param message The error message.
 * @return Number of bytes written.
 */
static int
cpyReferenceTracing_write_c_error_message_to_log(struct reference_tracing_data *data, char *message) {
    return cpyReferenceTracing_write_c_prefix_and_message_to_log(data, "ERR", message);
}

/**
 * Used as a sanity check when \c reference_trace_allocations_callback() is running.
 * Called functions can test against this to make sure that they have been called
 * when Reference Tracing is on or off.
 */
static int reference_tracing_call_back_is_active = 0;

/**
 * Returns non-zero if the Python object is one of the selected builtins.
 * This function call is designed to be cheap but requires any of the code
 * here to NOT allocate/de-allocate Python objects as that will make
 * \c the reference_trace_allocations_callback() re-entrant.
 *
 * Note that this is Python version specific as some code, such as
 * the \c datetime API change in Python 3.15.
 * See also \c reference_trace_is_builtin_post_suspend()
 *
 * To search the source code for public APIs:
 *
 * @code
 *  grep -nrI "#define Py.*_Check(" . | grep "\.h"
 * @endcode
 *
 * @param op The Python object to check.
 * @return 1 if a builtin, 0 otherwise.
 */
static int
reference_trace_is_builtin_pre_suspend(PyObject *op) {
    assert(op);
    assert(reference_tracing_call_back_is_active);
    if (
            0
            /* Numeric */
            || PyFloat_Check(op)
            || PyLong_Check(op)
            || PyBool_Check(op)
            || PyComplex_Check(op)
            /* Common */
            || PyUnicode_Check(op)
            || PyBytes_Check(op)
            || PyByteArray_Check(op)
            || PyTuple_Check(op)
            || PyList_Check(op)
            || PyDict_Check(op)
            || PyDictKeys_Check(op)
            || PyDictValues_Check(op)
            || PyDictItems_Check(op)
            /* Include/cpython/odictobject.h:21:#define PyODict_Check */
            || PyODict_Check(op)

            || PyFrozenSet_Check(op)
            || PyAnySet_Check(op)
            || PySet_Check(op)

            /* "slice" and "range" */
            || PySlice_Check(op)
            || PyRange_Check(op)

            /* Include/cpython/classobject.h */
            || PyMethod_Check(op)
            || PyInstanceMethod_Check(op)
            || PyCell_Check(op)

            /* Include/cpython/methodobject.h */
            || PyCMethod_Check(op)
            /* Include/cpython/funcobject.h */
            || PyFunction_Check(op)

            /* All iterators ? */
            || PySeqIter_Check(op)
            || PyCallIter_Check(op)

            /* Include/cpython/genobject.h */
            || PyGen_Check(op)

            /* Structural */
            || PyFrame_Check(op)
            || PyFrameLocalsProxy_Check(op)
            || PyCode_Check(op)
            || PyModule_Check(op)

            /* Other. */
            || PyExceptionClass_Check(op)
            || PyExceptionInstance_Check(op)
            || PyWeakref_Check(op)

            /* "traceback" */
            || PyTraceBack_Check(op)

            /* "builtin_function_or_method" */
            || PyCFunction_Check(op)

            || PyPickleBuffer_Check(op)
            /* Include/memoryobject.h:11:#define PyMemoryView_Check */
            || PyMemoryView_Check(op)
            ) {
        return 1;
    }
    /* Python 3.15 change this datetime import API so that the
     * PyDateTimeAPI == NULL
     * test is invalid and PyDateTime_IMPORT might allocate/deallocate Python objects
     * which makes the reference_trace_allocations_callback() re-entrant.
     * See: https://docs.python.org/3.15/whatsnew/3.15.html#changed-c-apis
     * And: https://github.com/python/cpython/issues/141563
     * */
#if PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION < 15
    /* Required aa datetime is a capsule. */
    if (PyDateTimeAPI == NULL) {
        PyDateTime_IMPORT;
    }
    if (
            0
            /* Datetime stuff. This needs #include "datetime.h" */
            || PyDate_Check(op)
            || PyDateTime_Check(op)
            || PyTime_Check(op)
            || PyDelta_Check(op)
            || PyTZInfo_Check(op)
            ) {
        return 1;
    }
#endif // PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION < 15
    return 0;
}

/**
 * Returns non-zero if the Python object is one of the selected builtins.
 * This function call is meant to be used after the Reference Tracing callback
 * has been suspended.
 * That means that any calls here may allocate/de-allocate Python objects.
 *
 * \note
 *  This is Python version specific as some code, such as
 *  the \c datetime API change in Python 3.15.
 *  With Python 3.15+ the PyDateTimeAPI import now triggers arbitrary object
 *  creation so the Reference Tracing must be suspended otherwise teh callback\
 *  will be re-entrant.
 *  See also \c reference_trace_is_builtin_pre_suspend()
 *
 * @param op The Python object to check.
 * @return 1 if a builtin, 0 otherwise.
 */
#if PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION >= 15
static int
reference_trace_is_builtin_post_suspend(PyObject *op) {
    assert(op);
    assert(!reference_tracing_call_back_is_active);
    /* Python 3.15 change this datetime import API so that the
     * PyDateTimeAPI == NULL
     * test is invalid and PyDateTime_IMPORT might allocate/deallocate Python objects
     * which makes the reference_trace_allocations_callback() re-entrant.
     * See: https://docs.python.org/3.15/whatsnew/3.15.html#changed-c-apis
     * And: https://github.com/python/cpython/issues/141563
     * */
    /* Required aa datetime is a capsule. */
    PyDateTime_IMPORT;
    if (
            0
            /* Datetime stuff. This needs #include "datetime.h" */
            || PyDate_Check(op)
            || PyDateTime_Check(op)
            || PyTime_Check(op)
            || PyDelta_Check(op)
            || PyTZInfo_Check(op)
            ) {
        return 1;
    }
    return 0;
}
#else /* Python version prior to 3.15. */
static int
reference_trace_is_builtin_post_suspend(PyObject *Py_UNUSED(op)) {
    return 0;
}
#endif

/**
 * Returns 1 if the \c exclude_tp_names sequence contains the object type name, 0 otherwise.
 *
 * @param data_alias The <tt>struct reference_tracing_data</tt>
 * @param obj The object being traced.
 * @return 1 if the object type is in the \c exclude_tp_names zero otherwise.
 */
static int
reference_trace_type_exclude_matches(struct reference_tracing_data *data_alias, PyObject *obj) {
    assert(data_alias);
    assert(data_alias->exclude_tp_names);
    assert(PySequence_Check(data_alias->exclude_tp_names));
    assert(obj);
    assert(!reference_tracing_call_back_is_active);

    int ret = 0;
    PyObject *obj_tp_name = Py_BuildValue("s", Py_TYPE(obj)->tp_name);
    if (PySequence_Contains(data_alias->exclude_tp_names, obj_tp_name) == 1) {
        ret = 1;
    }
    Py_DECREF(obj_tp_name);
    return ret;
}

/**
 * Returns 1 if the include_tp_names sequence contains the object type name, 0 otherwise.
 *
 * @param data_alias The <tt>struct reference_tracing_data</tt>
 * @param obj The object being traced.
 * @return 1 if the object type is in the \c exclude_tp_names zero otherwise.
 */
static int
reference_trace_type_include_matches(struct reference_tracing_data *data_alias, PyObject *obj) {
    assert(data_alias);
    assert(data_alias->include_tp_names);
    assert(PySequence_Check(data_alias->include_tp_names));
    assert(obj);
    assert(!reference_tracing_call_back_is_active);

    int ret = 0;
    PyObject *obj_tp_name = Py_BuildValue("s", Py_TYPE(obj)->tp_name);
    if (PySequence_Contains(data_alias->include_tp_names, obj_tp_name) == 1) {
        ret = 1;
    }
    Py_DECREF(obj_tp_name);
    return ret;
}

/**
 * The callback function that is passed to \c PyRefTracer_SetTracer.
 * This writes to the log file.
 *
 * Note that this suspends the Reference Tracer whilst calling CPython functions that might allocate/deallocate
 * Python objects otherwise there will be infinite recursion as that will call this callback.
 *
 * Objects of type "frame" are ignored as this causes great confusion with other trace functions, pytest
 * and the Python runtime generally.
 *
 * @param obj The Python object being created or destroyed.
 * @param event The event type
 * @param data The opaque data structure that is a <tt>struct reference_tracing_data</tt>.
 * @return 0 on success, non-zero on failure.
 */
static int
reference_trace_allocations_callback(PyObject *obj, PyRefTracerEvent event, void *data) {
#if PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION >= 13 && PY_MINOR_VERSION < 15
    assert(event == PyRefTracer_CREATE || event == PyRefTracer_DESTROY);
#endif

#if REFERENCE_TRACING_TRACKER_REMOVED_AVAILABLE
    assert(event == PyRefTracer_CREATE || event == PyRefTracer_DESTROY || event == PyRefTracer_TRACKER_REMOVED);
    if (event == PyRefTracer_TRACKER_REMOVED) {
        /* Here we must do nothing as the PyRefTracer_SetTracer(NULL, NULL)
         * call (below) will trigger a call to this callback function.
         * We clould guard against this by checking the result of
         * PyRefTracer_GetTracer with some more logic but we are not that interested
         * in removing tracers at this level.
         * That is handled by the context managers (and decorators).
         */
        return 0;
    }
#endif // #if REFERENCE_TRACING_TRACKER_REMOVED_AVAILABLE

    assert(obj);
    assert(data);
    struct reference_tracing_data *data_alias = (struct reference_tracing_data *) data;
    assert(data_alias->log_file);
    assert(event >= 0 && event <= 3);

    reference_tracing_call_back_is_active = 1;

    /* This does not seem to help in reporting crashes. */
//    fprintf(
//            data_alias->log_file,
//            "%s()%d DEBUG TYPE @ %p is \"%s\"\n",
//            __FUNCTION__, __LINE__, &(Py_TYPE(obj)), Py_TYPE(obj)->tp_name
//            );

    /* Experience shows that frame and code objects are tricky to handle
     * in that getting the file/line/function
     * often causing a SIGSEGV, so we always ignore them. */
    if (PyFrame_Check(obj) || PyCode_Check(obj)) {
        return 0;
    }
    /* Remove builtin types using the specific Python C API.
     * This does not allocate or deallocate any Python objects,
     * so we do not need to suspend tracing. */
    if (data_alias->include_builtins == 0 && reference_trace_is_builtin_pre_suspend(obj)) {
        return 0;
    }

    /* From now on we might call the Python API that might allocate or deallocate
     * Python objects, so we do need to suspend tracing as not doing so will
     * recursively call this callback function causing a SIGABRT. */
    const int ERROR_CODE = -1;
    void *data_old = NULL;
    /* Call PyRefTracer PyRefTracer_GetTracer(void **data) */
    PyRefTracer tracer_old = PyRefTracer_GetTracer(&data_old);
    /* Sanity check. */
    assert(data_old);
    assert(data_old == data_alias);
    assert(tracer_old);
    assert(tracer_old == &reference_trace_allocations_callback);
    if (PyRefTracer_SetTracer(NULL, NULL)) {
        /* Do not set an exception.
         * See: https://docs.python.org/3/c-api/profiling.html#c.PyRefTracer_SetTracer
         * */
//        fprintf(stderr, "PyRefTracer_SetTracer(NULL, NULL) failed.\n");
        cpyReferenceTracing_write_c_error_message_to_log(
                data_alias,
                "PyRefTracer_SetTracer(NULL, NULL) failed."
        );
        return ERROR_CODE;
    }
    reference_tracing_call_back_is_active = 0;

    /* NOTE: Some of this code is a bit repetitive. */

    /* Handle builtin calls that must be done when tracing is suspended. */
    if (data_alias->include_builtins == 0 && reference_trace_is_builtin_post_suspend(obj)) {
        /* Restore the Reference Tracer. */
        if (PyRefTracer_SetTracer(tracer_old, data_old)) {
            /* Do not set an exception.
             * See: https://docs.python.org/3/c-api/profiling.html#c.PyRefTracer_SetTracer */
            cpyReferenceTracing_write_c_error_message_to_log(
                    data_alias,
                    "reference_trace_is_builtin_post_suspend(): PyRefTracer_SetTracer(tracer_old, data_old) failed."
            );
            return ERROR_CODE;
        }
        reference_tracing_call_back_is_active = 1;
        return 0;
    }

    /* Handle user requested exclusion or inclusion. */
    /* Remove types by type name if they are in the exclusion sequence. */
    if (data_alias->exclude_tp_names && reference_trace_type_exclude_matches(data_alias, obj)) {
        /* Restore the Reference Tracer. */
        if (PyRefTracer_SetTracer(tracer_old, data_old)) {
            /* Do not set an exception.
             * See: https://docs.python.org/3/c-api/profiling.html#c.PyRefTracer_SetTracer */
            cpyReferenceTracing_write_c_error_message_to_log(
                    data_alias,
                    "reference_trace_type_exclude_matches(): PyRefTracer_SetTracer(tracer_old, data_old) failed."
            );
            return ERROR_CODE;
        }
        reference_tracing_call_back_is_active = 1;
        return 0;
    }
    /* Remove types by type name if they are not in the inclusion sequence. */
    if (data_alias->include_tp_names && !reference_trace_type_include_matches(data_alias, obj)) {
        /* Restore the Reference Tracer. */
        if (PyRefTracer_SetTracer(tracer_old, data_old)) {
            /* Do not set an exception.
             * See: https://docs.python.org/3/c-api/profiling.html#c.PyRefTracer_SetTracer */
            cpyReferenceTracing_write_c_error_message_to_log(
                    data_alias,
                    "reference_trace_type_include_matches: PyRefTracer_SetTracer(tracer_old, data_old) failed."
            );
            return ERROR_CODE;
        }
        reference_tracing_call_back_is_active = 1;
        return 0;
    }

    double clock_time = (double) clock() / CLOCKS_PER_SEC;
    /* RSS stuff. */
    size_t rss = getCurrentRSS_alternate();
    long d_rss = (long) rss - (long) data_alias->rss;
    data_alias->rss = rss;

    /* Write the event type. */
    if (event == PyRefTracer_CREATE) {
        // Write the creation of an object.
        fputs("NEW:", data_alias->log_file);
        data_alias->count_new++;
    } else if (event == PyRefTracer_DESTROY) {
        // Write the destruction of an object.
        fputs("DEL:", data_alias->log_file);
        data_alias->count_del++;
    } else {
        // Unknown event. Note PyRefTracer_TRACKER_REMOVED is handled above.
        Py_UNREACHABLE();
    }
    /* Write the rest of the event line. */
    /* Now we can call into Python code. */
    PyFrameObject *frame = PyEval_GetFrame();
    Py_XINCREF(frame);
    /* Get the function name. This does not use get_python_function_name()
     * as that needs a profile/trace event "what" and a PyObject *argument. */
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
             py_frame_get_python_file_name(frame),
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
    snprintf(reference_tracing_event_text, PY_MEM_TRACE_EVENT_TEXT_MAX_LENGTH,
             " %12.6f %16p %16ld %-32s %-80s %4d %-40s %16zd %16ld",
             clock_time,
             (void *) obj,
             Py_REFCNT(obj),
             Py_TYPE(obj)->tp_name,
             py_frame_get_python_file_name(frame),
             py_frame_get_line_number(frame),
             py_frame_get_python_function_name(frame),
             rss,
             d_rss
    );
#endif // REFERENCE_TRACING_GET_SIZEOF
    Py_XDECREF(frame);
    assert(data_alias);
    assert(data_alias->log_file);
    fputs(reference_tracing_event_text, data_alias->log_file);
    fputc('\n', data_alias->log_file);
    fflush(data_alias->log_file);
    /* Restore the Reference Tracer. */
    if (PyRefTracer_SetTracer(tracer_old, data_old)) {
        /* Do not set an exception.
         * See: https://docs.python.org/3/c-api/profiling.html#c.PyRefTracer_SetTracer */
        cpyReferenceTracing_write_c_error_message_to_log(
                data_alias,
                "PyRefTracer_SetTracer(tracer_old, data_old) failed."
        );
//        fprintf(stderr, "PyRefTracer_SetTracer(tracer_old, data_old) failed.\n");
        return ERROR_CODE;
    }
    reference_tracing_call_back_is_active = 1;
    return 0;
}

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
    // If >= 0 this will be passed to gc.collect() on __exit__
    // This helps clear up the log by deleting transient objects.
    int gc_collect_on_exit;
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
        Py_XDECREF(self->data->exclude_tp_names);
        self->data->exclude_tp_names = NULL;
        Py_XDECREF(self->data->include_tp_names);
        self->data->include_tp_names = NULL;
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
        self->data->include_builtins = 0;
        self->data->exclude_tp_names = NULL;
        self->data->include_tp_names = NULL;
        self->py_specific_filename = NULL;
        self->message = NULL;
        /* Default to a full gc.collect() */
        self->gc_collect_on_exit = 2;
    }
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_END(self);
    return (PyObject *) self;
}

/**
 * Initialise the Reference Tracer.
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
    static char *kwlist[] = {
            "message", "filepath",
            "include_builtins", "exclude_tp_names", "include_tp_names",
            "gc_collect_on_exit",
            NULL
    };
    char *message = NULL;

    /* Note the defaults are set in cpyReferenceTracing_new() */
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|sO&pOOi", kwlist, &message, PyUnicode_FSConverter,
                                     &self->py_specific_filename,
                                     &(self->data->include_builtins),
                                     &(self->data->exclude_tp_names),
                                     &(self->data->include_tp_names),
                                     &(self->gc_collect_on_exit)
                                     )
                                     ) {
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
    if (self->data->exclude_tp_names) {
        /* Check that the exclude_tp_names supports the sequence protocol. */
        if (!PySequence_Check(self->data->exclude_tp_names)) {
            PyErr_Format(
                    PyExc_TypeError,
                    "cpyReferenceTracing_init() exclude_tp_names must be a sequence, not type %s.",
                    Py_TYPE(self->data->exclude_tp_names)->tp_name
                    );
            return -3;
        }
        /* PyArg_ParseTupleAndKeywords returns a borrowed reference with "O" format. */
        Py_INCREF(self->data->exclude_tp_names);
    }
    if (self->data->include_tp_names) {
        /* Check that the include_tp_names supports the sequence protocol. */
        if (!PySequence_Check(self->data->include_tp_names)) {
            PyErr_Format(
                    PyExc_TypeError,
                    "cpyReferenceTracing_init() include_tp_names must be a sequence, not type %s.",
                    Py_TYPE(self->data->include_tp_names)->tp_name
                    );
            return -3;
        }
        /* PyArg_ParseTupleAndKeywords returns a borrowed reference with "O" format. */
        Py_INCREF(self->data->include_tp_names);
    }
    if (self->gc_collect_on_exit < -1 || self->gc_collect_on_exit > 2) {
        /* -1 is no collection. otherwise this is passed to gc.collect()
         * and that takes a value 0, 1, or 2.
         * See: https://docs.python.org/3/library/gc.html#gc.collect
         * */
        PyErr_Format(
                PyExc_ValueError,
                "cpyReferenceTracing_init() gc_collect_on_exit must be -1, 0, 1, 2 not %i.",
                self->gc_collect_on_exit
        );
        return -4;
    }
    assert(!PyErr_Occurred());
    TRACE_PROFILE_OR_TRACE_REFCNT_SELF_TRACE_FILE_WRAPPER_END(self);
    return 0;
}

// MARK: - cpyReferenceTracing members

/**
 * \c cpyReferenceTracing members. Empty.
 */
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
cpyReferenceTracing_write_python_message_to_log(cpyReferenceTracing *self, PyObject *op) {
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
    cpyReferenceTracing_write_c_message_to_log(self->data, (char *) c_str);
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_END(self);
    Py_RETURN_NONE;
}

/**
 * Run a \c gc.collect()
 * See: https://docs.python.org/3/library/gc.html#gc.collect
 *
 * @param self The Reference Tracing object.
 * @return The result of gc.collect(), a count of the objects collected.
 */
static long
cpyReferenceTracing_invoke_gc_collect(cpyReferenceTracing *self) {
    /* NOTE: No assert(!PyErr_Occurred()); as on __exit__
     * an exception might have been set by the users code. */
//    assert(!PyErr_Occurred());
    assert(self->gc_collect_on_exit >= 0 && self->gc_collect_on_exit <= 2);
    PyObject *gc_module = PyImport_ImportModule("gc");
    long ret = 0;
    if (!gc_module) {
        PyErr_SetString(
            PyExc_ImportError,
            "cpyReferenceTracing_invoke_gc_collect() can not import the \"gc\" module."
        );
        ret= -1;
    } else {
        PyObject *result = PyObject_CallMethod(gc_module, "collect", "i", self->gc_collect_on_exit);
        if (result) {
            ret = PyLong_AsLong(result);
#if DEBUG
            fprintf(
                stdout,
                "DEBUG: %s#%d gc.collect(%d) collected %ld objects.\n",
                __FUNCTION__, __LINE__, self->gc_collect_on_exit, ret
            );
#endif
            Py_DECREF(result);
        } else {
            PyErr_Format(
                PyExc_RuntimeError,
                "cpyReferenceTracing_invoke_gc_collect() invoking \"gc.collect(%d)\" failed.",
                self->gc_collect_on_exit
            );
            ret = -2;
        }
        Py_DECREF(gc_module);
    }
    return ret;
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
        PyErr_SetString(PyExc_RuntimeError, "PyRefTracer_SetTracer(NULL, NULL) failed.");
        return NULL;
    }
    /* Open the log file. */
    char *new_log_filename = NULL;
    if (self->py_specific_filename) {
        /* User supplied filename. */
        new_log_filename = PyBytes_AS_STRING(self->py_specific_filename);
    } else {
        /* Default to a standard log file name in the current working directory. */
        size_t ll_depth = reference_tracing_ll_length();
        int err_code = create_filename_within_cwd('O', ll_depth, file_path_buffer, PYMEMTRACE_PATH_NAME_MAX_LENGTH);
        if (err_code <= 0) {
            PyErr_Format(
                    PyExc_RuntimeError, "%s#%d Can not print to buffer, error %d", __FUNCTION__, __LINE__, err_code
            );
            return NULL;
        }
        self->py_specific_filename = (PyObject *) PyBytes_FromString(file_path_buffer);
        new_log_filename = file_path_buffer;
    }
#if DEBUG
    fprintf(stdout, "DEBUG: Reference Tracing opening log file \"%s\"\n", new_log_filename);
#endif
    self->data->log_file = fopen(new_log_filename, "w");
    if (!self->data->log_file) {
        PyErr_Format(PyExc_IOError, "Can not open log file %s", new_log_filename);
        return NULL;
    }
    /* Write suspension message in the old file. */
    struct reference_tracing_data *data_old = reference_tracing_ll_get_data();
    if (data_old) {
        cpyReferenceTracing_write_c_message_to_log(
                data_old, "Detaching this Reference Tracing file wrapper. New file:"
        );
        cpyReferenceTracing_write_c_message_to_log(
                data_old, new_log_filename
        );
    }
    /* Write the opening message in the new log file. */
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
    reference_tracing_ll_push(self->data);
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
 * @param self The \c cpyReferenceTracing object.
 * @param _unused_args
 * @return \c True or \c False NULL on failure.
 */
static PyObject *
cpyReferenceTracing_exit(cpyReferenceTracing *self, PyObject *Py_UNUSED(args)) {
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_BEG(self);
    /* NOTE: No assert(!PyErr_Occurred()); as an exception might have been set by the users code. */

    /* Invoke gc.collect() if required, and we DO want to trace de-allocations so,
     * we do this before de-registering the tracer. */
    if (self->gc_collect_on_exit >= 0) {
        if (cpyReferenceTracing_invoke_gc_collect(self) < 0) {
            /* gc.collect() failure. */
            assert(PyErr_Occurred());
            Py_RETURN_TRUE;
        }
    }

    /* De-registers the existing tracer.
     * PyRefTracer_SetTracer() will decrement the reference count that incremented by
     * PyRefTracer_SetTracer() on __enter__
     * */
    if (PyRefTracer_SetTracer(NULL, NULL)) {
        PyErr_SetString(PyExc_RuntimeError, "PyRefTracer_SetTracer(NULL, NULL) failed.");
        return NULL;
    }
    if (self->data) {
        /* Pops the node off the linked list. */
        struct reference_tracing_data *data = reference_tracing_ll_pop();
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
        data = reference_tracing_ll_get_data();
        if (data) {
            /* Report re-attaching the reference tracer. */
            cpyReferenceTracing_write_c_message_to_log(data, "Re-attaching this trace file wrapper.");
            PyRefTracer_SetTracer(&reference_trace_allocations_callback, data);
        }
        if (PyErr_Occurred()) {
            Py_RETURN_TRUE;
        }
        Py_RETURN_FALSE;
    }
    PyErr_Format(PyExc_RuntimeError, "ReferenceTracing.__exit__ has no cpyTraceFileWrapper");
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_END(self);
    return NULL;
}

/**
 * Returns the path to the Reference Tracing log file as a Python string.
 * @param self The \c cpyReferenceTracing object.
 * @param _unused_arg
 * @return The path or None on failure.
 */
static PyObject *
cpyReferenceTracing_get_log_file_path(cpyReferenceTracing *self, PyObject *Py_UNUSED(arg)) {
    assert(!PyErr_Occurred());
    if (self->py_specific_filename) {
        return Py_BuildValue("s", PyBytes_AS_STRING(self->py_specific_filename));
    } else {
        Py_RETURN_NONE;
    }
}

/**
 * This suspends the current reference tracer.
 * This notes this action in the log file.
 * It does **not** pop it off the linked list but leaves it there to be restored by resume().
 *
 * @return NULL on failure, None on success.
 */
static PyObject *
cpyReferenceTracing_suspend(void) {
    assert(!PyErr_Occurred());
    struct reference_tracing_data *data = reference_tracing_ll_get_data();
    if (!data) {
        PyErr_Format(
                PyExc_RuntimeError,
                "%s()#%d Head of list is NULL.", __FUNCTION__, __LINE__
        );
        return NULL;
    }
    if (!data->log_file) {
        PyErr_Format(
                PyExc_RuntimeError,
                "%s()#%d Head of list, the file pointer is NULL.", __FUNCTION__, __LINE__
        );
        return NULL;
    }

    cpyReferenceTracing_write_c_message_to_log(data, "Suspending reference tracing.");
    void *data_old = NULL;
    /* Call PyRefTracer PyRefTracer_GetTracer(void **data) */
    PyRefTracer tracer_old = PyRefTracer_GetTracer(&data_old);
    /* Sanity check. */
    assert(data_old);
    if (data_old != data) {
        PyErr_Format(
                PyExc_RuntimeError,
                "%s()#%d Head of list tracer does not match the registered one.", __FUNCTION__, __LINE__
        );
        return NULL;
    }
    assert(tracer_old);
    if (tracer_old != &reference_trace_allocations_callback) {
        PyErr_Format(
                PyExc_RuntimeError,
                "%s()#%d PyRefTracer_GetTracer() return value is not the expected callback function.",
                __FUNCTION__, __LINE__
        );
        return NULL;
    }
    if (PyRefTracer_SetTracer(NULL, NULL)) {
        PyErr_Format(
                PyExc_RuntimeError,
                "%s()#%d PyRefTracer_SetTracer(NULL, NULL) failed.",
                __FUNCTION__, __LINE__
        );
        return NULL;
    }
    Py_RETURN_NONE;
}

/**
 * This resumes the current reference tracer by re-registering the head of the linked list.
 * This notes this action in the log file.
 *
 * @return NULL on failure, None on success.
 */
static PyObject *
cpyReferenceTracing_resume(void) {
    /* If this function is not paired with suspend() then there might be
     * a Reference Tracer still registered so this call should handle the
     * reference counts correctly. */
    if (PyRefTracer_SetTracer(NULL, NULL)) {
        PyErr_Format(
                PyExc_RuntimeError,
                "%s()#%d PyRefTracer_SetTracer(NULL, NULL) failed.",
                __FUNCTION__, __LINE__
        );
        return NULL;
    }
    /* Get the current latest tracer. */
    struct reference_tracing_data *data = reference_tracing_ll_get_data();
    if (data) {
        cpyReferenceTracing_write_c_message_to_log(data, "Resuming reference tracing.");
        /* Restore the Reference Tracer. */
        if (PyRefTracer_SetTracer(&reference_trace_allocations_callback, data)) {
            PyErr_SetString(PyExc_RuntimeError, "PyRefTracer_SetTracer(tracer, data) failed.");
            PyErr_Format(
                    PyExc_RuntimeError,
                    "%s()#%d PyRefTracer_SetTracer(tracer, data) failed.",
                    __FUNCTION__, __LINE__
            );
            return NULL;
        }
        cpyReferenceTracing_write_c_message_to_log(data, "Resuming reference tracing.");
    } else {
        PyErr_SetString(PyExc_RuntimeError, "PyRefTracer.resume() when there is no tracer to register.");
        return NULL;
    }
    Py_RETURN_NONE;
}

/**
 * @return Number of allocations of interest from the Reference Tracer.
 */
static PyObject *
cpyReferenceTracing_count_new(void) {
    assert(!PyErr_Occurred());
    /* Get the current latest tracer. */
    struct reference_tracing_data *data = reference_tracing_ll_get_data();
    if (data) {
        return PyLong_FromLong(data->count_new);
    }
    PyErr_Format(
            PyExc_RuntimeError,
            "%s(): No reference tracing data is on the stack.",
            __FUNCTION__
    );
    return NULL;
}

/**
 * @return Number of de-allocations of interest from the Reference Tracer.
 */
static PyObject *
cpyReferenceTracing_count_del(void) {
    assert(!PyErr_Occurred());
    /* Get the current latest tracer. */
    struct reference_tracing_data *data = reference_tracing_ll_get_data();
    if (data) {
        return PyLong_FromLong(data->count_del);
    }
    PyErr_Format(
            PyExc_RuntimeError,
            "%s(): No reference tracing data is on the stack.",
            __FUNCTION__
    );
    return NULL;
}

/**
 * \c cpyReferenceTracing methods.
 */
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
                            (PyCFunction) cpyReferenceTracing_write_python_message_to_log,
                                                                    METH_O,
                "Write a string as a message to the existing log file with a newline. Returns None."
        },
        {
                "log_file_path",
                            (PyCFunction) cpyReferenceTracing_get_log_file_path,
                                                                    METH_NOARGS,
                "Return the current log file path for the Reference Tracer."
        },
        {
                "suspend",
                            (PyCFunction) cpyReferenceTracing_suspend,
                                                                    METH_NOARGS,
                "Suspend the current Reference Tracer."
        },
        {
                "resume",
                            (PyCFunction) cpyReferenceTracing_resume,
                                                                    METH_NOARGS,
                "Resume the latest Reference Tracer."
        },
        {
                "count_new",
                            (PyCFunction) cpyReferenceTracing_count_new,
                                                                    METH_NOARGS,
                "Return the count of new allocations."
        },
        {
                "count_del",
                            (PyCFunction) cpyReferenceTracing_count_del,
                                                                    METH_NOARGS,
                "Return the count of deleted allocations."
        },
        {NULL, NULL, 0, NULL}  /* Sentinel */
};

// MARK: - cpyReferenceTracing declaration

/**
 * Specification of the Python \c cpyReferenceTracingType type.
 */
static PyTypeObject cpyReferenceTracingType = {
        PyVarObject_HEAD_INIT(NULL, 0)
        .tp_name = "cPyMemTrace.ReferenceTracing",
        .tp_doc = "A Reference Tracing object that reports object allocations and de-allocations."
                  " A context manager to attach a C profile function to the interpreter.\n"
                  "This takes the following optional arguments:\n\n"
                  "\n\n- ``message``: An optional message to write to the begining of the log file."
                  "\n\n- ``filepath``: An optional specific path to the log file."
                  "\n  By default this writes to a file in the current working directory named"
                  " ``\"YYYYMMDD_HHMMMSS_<int>_<PID>_O_<depth>_PY<Python Version>.log\"``"
                  " For example ``\"20241107_195847_12_62264_O_0_PY3.13.0b3.log\"``"
                  "\n\n- ``include_builtins``: Include builtin types. By default most builtins are ignored."
                  "\n\n- ``exclude_tp_names``: A sequence of strings of type names to exclude in the output."
                  "\n\n- ``include_tp_names``: A sequence of strings of type names to include in the output."
                  " ``exclude_tp_names`` takes precedence over this."
                  "\n\n- ``gc_collect_on_exit``: An integer to be passed to gc.collect() on __exit__."
                  " This can make the log files more accurate in tracking de-allocations."
                  " 2 (the default) means full garbage collection."
                  " -1 means no garbage collection."
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

#endif // #if REFERENCE_TRACING_AVAILABLE

// MARK: cPyMemTrace methods.

/**
 * @return The current RSS in bytes as a Python integer.
 */
static PyObject *
py_rss(void) {
    assert(!PyErr_Occurred());
    return PyLong_FromSize_t(getCurrentRSS_alternate());
}

/**
 * @return The peak RSS in bytes as a Python integer.
 */
static PyObject *
py_rss_peak(void) {
    assert(!PyErr_Occurred());
    return PyLong_FromSize_t(getPeakRSS());
}

/**
 * @return The number of Profilers o in the linked list as a Python integer.
 */
static PyObject *
profile_wrapper_depth(void) {
    assert(!PyErr_Occurred());
    return Py_BuildValue("n", wrapper_ll_length(static_profile_wrappers));
}

/**
 * @return The number of Tracers in the linked list as a Python integer.
 */
static PyObject *
trace_wrapper_depth(void) {
    assert(!PyErr_Occurred());
    return Py_BuildValue("n", wrapper_ll_length(static_trace_wrappers));
}

#if REFERENCE_TRACING_AVAILABLE

/**
 * @return The number of Simple Reference Tracers in the linked list as a Python integer.
 */
static PyObject *
reference_tracing_simple_wrapper_depth(void) {
    assert(!PyErr_Occurred());
    return Py_BuildValue("n", reference_tracing_simple_ll_length());
}

/**
 * @return The number of Reference Tracers in the linked list as a Python integer.
 */
static PyObject *
reference_tracing_wrapper_depth(void) {
    assert(!PyErr_Occurred());
    return Py_BuildValue("n", reference_tracing_ll_length());
}

#endif // #if REFERENCE_TRACING_AVAILABLE

/**
 * \c cPyMemTrace module functions.
 */
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
#if REFERENCE_TRACING_AVAILABLE
        {
                "reference_tracing_simple_wrapper_depth",
                (PyCFunction) reference_tracing_simple_wrapper_depth,
                METH_NOARGS,
                "Return the depth of the Reference Tracing Simple wrapper stack.",
        },
        {
                "reference_tracing_wrapper_depth",
                (PyCFunction) reference_tracing_wrapper_depth,
                METH_NOARGS,
                "Return the depth of the Reference Tracing wrapper stack.",
        },
#endif // #if REFERENCE_TRACING_AVAILABLE
        {NULL, NULL, 0, NULL}        /* Sentinel */
};

// MARK: cPyMemTrace module

PyDoc_STRVAR(py_mem_trace_doc,
             "Module that contains C memory tracer classes and functions."
             "\nNotably this has Profile() and Trace() that can attach to the Python runtime and report memory usage"
             " events."
);

/**
 * \c cPyMemTrace module definition.
 */
static PyModuleDef cPyMemTracemodule = {
        PyModuleDef_HEAD_INIT,
        .m_name = "cPyMemTrace",
        .m_doc = py_mem_trace_doc,
        .m_size = -1,
        .m_methods = cPyMemTraceMethods,
};

/**
 * \c cPyMemTrace module initialisation.
 */
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

#if REFERENCE_TRACING_AVAILABLE
    /* Add the Reference Tracing Simple object. */
    if (PyType_Ready(&cpyReferenceTracingSimpleType) < 0) {
        Py_DECREF(m);
        return NULL;
    }
    Py_INCREF(&cpyReferenceTracingSimpleType);
    if (PyModule_AddObject(m, "ReferenceTracingSimple", (PyObject *) &cpyReferenceTracingSimpleType) < 0) {
        Py_DECREF(&cpyReferenceTracingSimpleType);
        Py_DECREF(m);
        return NULL;
    }
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
#endif // #if REFERENCE_TRACING_AVAILABLE

    return m;
}

// MARK: Debug code.

#if REFERENCE_TRACING_AVAILABLE

/** Debug example of a simple Reference Tracing object. */
struct simpletracer_data {
    int create_count;
    int destroy_count;
};

/**
 * Debug callback for a simple Reference Tracing object.
 * @param _unused_obj
 * @param event
 * @param data
 * @return
 */
static int simpletracer_callback(PyObject *Py_UNUSED(obj), PyRefTracerEvent event, void *data) {
    struct simpletracer_data *the_data = (struct simpletracer_data *) data;
    if (event == PyRefTracer_CREATE) {
        the_data->create_count++;
    } else {
        the_data->destroy_count++;
    }
    return 0;
}

/**
 * Debug example a simple Reference Tracing object.
 * @return 0 on success, non-zero on failure.
 */
static int
test_reftracer(void) {
    printf("Starting %s() at %s#%d\n", __FUNCTION__, __FILE_NAME__, __LINE__);
    // Save the current tracer and data to restore it later
    void *current_data;
    PyRefTracer current_tracer = PyRefTracer_GetTracer(&current_data);

    struct simpletracer_data tracer_data = {0};
    void *the_data = &tracer_data;
    // Install a simple tracer function
    if (PyRefTracer_SetTracer(simpletracer_callback, the_data) != 0) {
        goto failed;
    }

    // Check that the tracer was correctly installed
    void *data;
    if (PyRefTracer_GetTracer(&data) != simpletracer_callback || data != the_data) {
        PyErr_SetString(PyExc_AssertionError, "The reftracer not correctly installed");
        (void) PyRefTracer_SetTracer(NULL, NULL);
        goto failed;
    }

    // Create a bunch of objects
    PyObject *obj = PyList_New(0);
    if (obj == NULL) {
        goto failed;
    }
    PyObject *obj2 = PyDict_New();
    if (obj2 == NULL) {
        Py_DECREF(obj);
        goto failed;
    }

    // Kill all objects
    Py_DECREF(obj);
    Py_DECREF(obj2);

    // Remove the tracer
    (void) PyRefTracer_SetTracer(NULL, NULL);

    // Check that the tracer was removed
    if (PyRefTracer_GetTracer(&data) != NULL || data != NULL) {
        PyErr_SetString(PyExc_ValueError, "The reftracer was not correctly removed");
        goto failed;
    }

    if (tracer_data.create_count != 2) {
        PyErr_SetString(PyExc_ValueError, "The object creation was not correctly traced");
        goto failed;
    }

    if (tracer_data.destroy_count != 2) {
        PyErr_SetString(PyExc_ValueError, "The object destruction was not correctly traced");
        goto failed;
    }
    PyRefTracer_SetTracer(current_tracer, current_data);
    printf("DONE %s() at %s#%d\n", __FUNCTION__, __FILE_NAME__, __LINE__);
    return 0;
    failed:
    PyRefTracer_SetTracer(current_tracer, current_data);
    printf("FAILED %s() at %s#%d\n", __FUNCTION__, __FILE_NAME__, __LINE__);
    return -1;
}

#endif // REFERENCE_TRACING_AVAILABLE

/**
 * Debug code.
 *
 * @param argc Printed. Ignored.
 * @param argv Printed. Ignored.
 * @return The result of \c Py_FinalizeEx()
 */
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
         *  # profiler has a refcount of 1 as __exit__ decrements self.
         *  del profiler
         *  # profiler has a refcount of 0 and is deallocated.
         */
        fprintf(stdout, "First decref from %zd\n", Py_REFCNT(profile_object));
        Py_DECREF((PyObject *) profile_object);
        fprintf(stdout, "Second decref from %zd\n", Py_REFCNT(profile_object));
        Py_DECREF((PyObject *) profile_object);
    }
    /* END: Debug profile wrapper. */

#if REFERENCE_TRACING_AVAILABLE
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
    test_reftracer();
    /* End: Debug Reference Tracing wrapper. */
#endif // REFERENCE_TRACING_AVAILABLE

#if 0
    PyObject *bytes_obj = PyBytes_FromStringAndSize(NULL, 1024);
    long getsize = sys_getsizeof(bytes_obj);
    printf("sys_getsizeof() result: %ld\n", getsize);
    Py_DECREF(bytes_obj);
#endif

    // PyFrame_GetCode is Python 3.9+
#if PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION >= 9
    PyFrameObject *frame = PyEval_GetFrame();
    if (frame) {
        PyCodeObject *a = PyFrame_GetCode(frame);
        PyObject_Print((PyObject *) a, stdout, Py_PRINT_RAW);
        PyCodeObject *b = PyFrame_GetCode(frame);
        PyObject_Print((PyObject *) b, stdout, Py_PRINT_RAW);
    }
#endif

    /* Cleanup. */
    PyConfig_Clear(&config);
    return Py_FinalizeEx();
}
