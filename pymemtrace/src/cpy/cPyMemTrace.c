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

static void
trace_wrapper_write_frame_data_to_event_text(cpyTraceFileWrapper *trace_wrapper, PyFrameObject *frame,
                                             int what, PyObject *arg) {
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_BEG(trace_wrapper);
    size_t rss = getCurrentRSS_alternate();
    long d_rss = rss - trace_wrapper->rss;
#ifdef PY_MEM_TRACE_WRITE_OUTPUT_CLOCK
    double clock_time = (double) clock() / CLOCKS_PER_SEC;
    snprintf(trace_wrapper->event_text, PY_MEM_TRACE_EVENT_TEXT_MAX_LENGTH,
             "%-12zu +%-6ld %-12.6f %-8s %-80s %4d %-32s %12zu %12ld\n",
             trace_wrapper->event_number, trace_wrapper->event_number - trace_wrapper->previous_event_number,
             clock_time, WHAT_STRINGS[what], get_python_file_name(frame), py_frame_get_line_number(frame),
             get_python_function_name(frame, what, arg), getCurrentRSS_alternate(), d_rss);
#else
    snprintf(trace_wrapper->event_text, PY_MEM_TRACE_EVENT_TEXT_MAX_LENGTH,
             "%-12zu +%-6ld %-8s %-80s %4d %-32s %12zu %12ld\n",
             trace_wrapper->event_number, trace_wrapper->event_number - trace_wrapper->previous_event_number,
             WHAT_STRINGS[what], get_python_file_name(frame), py_frame_get_line_number(frame),
             get_python_function_name(frame, what, arg), getCurrentRSS_alternate(), d_rss);
#endif // PY_MEM_TRACE_WRITE_OUTPUT_CLOCK
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_END(trace_wrapper);
}


static void
cpyTraceFileWrapper_close_file(cpyTraceFileWrapper *self) {
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_BEG(self);
    if (self->file) {
        // Write LAST event
        fputs("LAST: ", self->file);
        trace_wrapper_write_frame_data_to_event_text(self, PyEval_GetFrame(), PyTrace_LINE, Py_None);
        fputs(self->event_text, self->file);
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
 *
 * @param self The file wrapper.
 * @param op The Python unicode string.
 * @return None on success, NULL on failure (not a unicode argument).
 */
static PyObject *
cpyTraceFileWrapper_write_to_log(cpyTraceFileWrapper *self, PyObject *op) {
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_BEG(self);
    assert(!PyErr_Occurred());
    if (!PyUnicode_Check(op)) {
        PyErr_Format(
                PyExc_ValueError,
                "write_to_log() requires a single string, not type %s",
                Py_TYPE(op)->tp_name
        );
        return NULL;
    }
    Py_UCS1 *c_str = PyUnicode_1BYTE_DATA(op);
    fprintf(self->file, "%s\n", c_str);
    TRACE_TRACE_FILE_WRAPPER_REFCNT_SELF_END(self);
    Py_RETURN_NONE;
}

static PyMethodDef cpyTraceFileWrapper_methods[] = {
        {"write_to_log", (PyCFunction) cpyTraceFileWrapper_write_to_log, METH_O,
                "Write a string to the existing log file  with a newline. Returns None."},
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
    free(tmp);
    /* NOTE: Caller has to decide whether to decref the tmp->file_wrapper.
     * If call as the result of and __exit__ function then do **not** decref as CPython
     * will automatically do this on completion of the with statement. */
    return tmp->file_wrapper;
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
 *
 * @param pobj The cpyTraceFileWrapper object.
 * @param frame The Python frame.
 * @param what The event type.
 * @param arg
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
    }
    if (labs(d_rss) >= trace_wrapper->d_rss_trigger && trace_wrapper->event_number) {
        // NOTE: Ignore event number 0 as that is covered by "FRST:" below.
#ifdef PY_MEM_TRACE_WRITE_OUTPUT_PREV_NEXT
        fputs("NEXT: ", trace_wrapper->file);
#endif
        trace_wrapper_write_frame_data_to_event_text(trace_wrapper, frame, what, arg);
        fputs(trace_wrapper->event_text, trace_wrapper->file);
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
    static char file_path_buffer[PYMEMTRACE_PATH_NAME_MAX_LENGTH];
    assert(!PyErr_Occurred());
    cpyTraceFileWrapper *trace_wrapper = NULL;
    const char *filename;
    if (specific_filename) {
        filename = specific_filename;
    } else {
        char trace_type = is_profile ? 'P' : 'T';
        size_t ll_depth = is_profile ? wrapper_ll_length(static_profile_wrappers) : wrapper_ll_length(
                static_trace_wrappers);
        filename = create_filename(trace_type, ll_depth);
    }
    if (filename) {
#ifdef _WIN32
        char seperator = '\\';
#else
        char seperator = '/';
#endif
        if (filename[0] == seperator) {
            snprintf(file_path_buffer, PYMEMTRACE_PATH_NAME_MAX_LENGTH, "%s", filename);
        } else {
            snprintf(file_path_buffer, PYMEMTRACE_PATH_NAME_MAX_LENGTH, "%s%c%s", current_working_directory(),
                     seperator,
                     filename);
        }
        trace_wrapper = (cpyTraceFileWrapper *) cpyTraceFileWrapper_new(&cpyTraceFileWrapperType, NULL, NULL);
        if (trace_wrapper) {
            fprintf(stdout, "Opening log file %s\n", file_path_buffer);
            trace_wrapper->file = fopen(filename, "w");
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
                fputs("FRST: ", trace_wrapper->file);
                trace_wrapper_write_frame_data_to_event_text(trace_wrapper, PyEval_GetFrame(), PyTrace_LINE, Py_None);
                fputs(trace_wrapper->event_text, trace_wrapper->file);
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
                fprintf(stderr, "Can not open writable file for cpyTraceFileWrapper at %s\n", filename);
                return NULL;
            }
        } else {
            fprintf(stderr, "Can not create cpyTraceFileWrapper.\n");
        }
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


static PyMethodDef cPyMemTraceMethods[] = {
        {"rss",                   (PyCFunction) py_rss,                METH_NOARGS, "Return the current RSS in bytes."},
        {"rss_peak",              (PyCFunction) py_rss_peak,           METH_NOARGS, "Return the peak RSS in bytes."},
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
        {"profile_wrapper_depth", (PyCFunction) profile_wrapper_depth, METH_NOARGS, "Return the depth of the profile wrapper stack."},
        {"trace_wrapper_depth",   (PyCFunction) trace_wrapper_depth,   METH_NOARGS, "Return the depth of the trace wrapper stack."},
        {NULL, NULL, 0, NULL}        /* Sentinel */
};

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
        {
                "trace_file_wrapper", Py_T_OBJECT_EX, offsetof(cpyProfileOrTraceObject,
                                                               trace_file_wrapper), Py_READONLY,
                "The trace file wrapper."
        },
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
        TRACE_PROFILE_OR_TRACE_REFCNT_SELF_TRACE_FILE_WRAPPER_END(self);
        Py_RETURN_FALSE;
    }
    PyErr_Format(PyExc_RuntimeError, "TraceObject.__exit__ has no cpyTraceFileWrapper");
    PyEval_SetProfile(NULL, NULL);
    Py_DECREF(self);
    TRACE_PROFILE_OR_TRACE_REFCNT_SELF_TRACE_FILE_WRAPPER_END(self);
    return NULL;
}

static PyMethodDef cpyProfileOrTraceObject_methods[] = {
        {"__enter__", (PyCFunction) ProfileObject_enter, METH_NOARGS,
                "Attach a Profile object to the C runtime."},
        {"__exit__",  (PyCFunction) ProfileObject_exit,  METH_VARARGS,
                "Detach a Profile object from the C runtime."},
        {NULL, NULL, 0, NULL}  /* Sentinel */
};

static PyTypeObject cpyProfileObjectType = {
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
        .tp_basicsize = sizeof(cpyProfileOrTraceObject),
        .tp_itemsize = 0,
        .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
        .tp_alloc = PyType_GenericAlloc,
        .tp_new = cpyProfileOrTraceObject_new,
        .tp_init = (initproc) cpyProfileOrTraceObject_init,
        .tp_dealloc = (destructor) cpyProfileOrTraceObject_dealloc,
        .tp_methods = cpyProfileOrTraceObject_methods,
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
        Py_RETURN_FALSE;
    }
    PyErr_Format(PyExc_RuntimeError, "TraceObject.__exit__ has no cpyTraceFileWrapper");
    PyEval_SetTrace(NULL, NULL);
    return NULL;
}

static PyMethodDef TraceObject_methods[] = {
        {"__enter__", (PyCFunction) TraceObject_enter, METH_NOARGS,
                "Attach a Trace object to the C runtime."},
        {"__exit__",  (PyCFunction) TraceObject_exit,  METH_VARARGS,
                "Detach a Trace object from the C runtime."},
        {NULL, NULL, 0, NULL}  /* Sentinel */
};

static PyTypeObject cpyTraceObjectType = {
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
        .tp_basicsize = sizeof(cpyProfileOrTraceObject),
        .tp_itemsize = 0,
        .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
        .tp_alloc = PyType_GenericAlloc,
        .tp_new = cpyProfileOrTraceObject_new,
        .tp_init = (initproc) cpyProfileOrTraceObject_init,
        .tp_dealloc = (destructor) cpyProfileOrTraceObject_dealloc,
        .tp_methods = TraceObject_methods,
        .tp_members = cpyProfileOrTraceObject_members,
};
/**** END: Context manager for attach_trace_function() and detach_trace_function() ****/

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
    return m;
}

#if 0

int
main(int argc, char **argv) {
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
//    int py_run_main = Py_RunMain();
//    fprintf(stdout, "Py_RunMain() returned %d\n", py_run_main);
//    if (py_run_main) {
//        return py_run_main;
//    }

#if 0
    if (PyType_Ready(&cpyTraceFileWrapperType) < 0) {
        return -8;
    }
    Py_INCREF(&cpyTraceFileWrapperType);

    cpyTraceFileWrapper *trace_wrapper = (cpyTraceFileWrapper *) cpyTraceFileWrapper_new(&cpyTraceFileWrapperType, NULL, NULL);
    fprintf(stdout, "cpyTraceFileWrapper *trace_wrapper:\n");
    PyObject_Print((PyObject*)trace_wrapper, stdout, Py_PRINT_RAW);

    Py_DECREF((PyObject*)trace_wrapper);
#endif

    if (PyType_Ready(&cpyProfileObjectType) < 0) {
        return -16;
    }
    Py_INCREF(&cpyProfileObjectType);

    cpyProfileOrTraceObject *profile_object = (cpyProfileOrTraceObject *) cpyProfileOrTraceObject_new(&cpyProfileObjectType, NULL, NULL);
    PyObject *py_args = Py_BuildValue("()");
    PyObject *py_kwargs = Py_BuildValue("{}");
    int init = cpyProfileOrTraceObject_init(profile_object, py_args, py_kwargs);
    fprintf(stdout, "cpyProfileOrTraceObject_init() returned %d\n", init);
    PyObject_Print((PyObject *) profile_object, stdout, Py_PRINT_RAW);
    fprintf(stdout, "\n");

    PyObject *result_enter = ProfileObject_enter(profile_object);
    fprintf(stdout, "result_enter:\n");
    PyObject_Print(result_enter, stdout, Py_PRINT_RAW);
    fprintf(stdout, "\n");
    PyObject *result_exit = ProfileObject_exit(profile_object, NULL);
    fprintf(stdout, "result_exit: ");
    if (result_exit) {
        PyObject_Print(result_exit, stdout, Py_PRINT_RAW);
    } else {
        fprintf(stdout, "NULL");
    }
    fprintf(stdout, "\n");

    Py_DECREF(py_args);
    Py_DECREF(py_kwargs);
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
    PyConfig_Clear(&config);
    return Py_FinalizeEx();
}

#endif
