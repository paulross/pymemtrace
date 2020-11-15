#!/usr/sbin/dtrace -Zs
/*
 * py_flow_malloc.d - Python libc malloc analysis. Written for the Python DTrace provider.
 *
 * This reports the Python call stack and along the way any calls to system malloc() or free().
 * It also reports aggregate memory allocation by Python function.
 *
 * It requires a Python build with at least (Mac OSX):
 * ../configure --with-dtrace --with-openssl=$(brew --prefix openssl)
 *
 * This will build a 'release' version of Python with pymalloc, the small memory allocator for memory <=512 bytes.
 *
 * For a 'debug' version that tracks all memory allocations build with something like:
 * ../configure --with-pydebug --without-pymalloc --with-valgrind --with-dtrace --with-openssl=$(brew --prefix openssl)
 *
 * USAGE (-C is to invoke the C preprocessor on this script):
 * sudo dtrace -C -s toolkit/py_flow_malloc_free.d -p <PID>
 *
 * Or for full path names:
 * sudo dtrace -C -s toolkit/py_flow_malloc_free.d -D FULL_FILE_PATH -p <PID>
 *
 * Use -D PYTHON_CALL_STACK if you want the Python call stack (verbose).
 *
 * From Objects/obmalloc.c:
 *
 * #define MALLOC_ALLOC {NULL, _PyMem_RawMalloc, _PyMem_RawCalloc, _PyMem_RawRealloc, _PyMem_RawFree}
 * #ifdef WITH_PYMALLOC
 * #  define PYMALLOC_ALLOC {NULL, _PyObject_Malloc, _PyObject_Calloc, _PyObject_Realloc, _PyObject_Free}
 * #endif
 *
 * #define PYRAW_ALLOC MALLOC_ALLOC
 * #ifdef WITH_PYMALLOC
 * #  define PYOBJ_ALLOC PYMALLOC_ALLOC
 * #else
 * #  define PYOBJ_ALLOC MALLOC_ALLOC
 * #endif
 * #define PYMEM_ALLOC PYOBJ_ALLOC

 *
 * Copyright (c) 2020 Paul Ross.
 * Acknowledgments to py_malloc.d which is Copyright (c) 2007 Brendan Gregg.
 *
 */

#pragma D option quiet
//#pragma D option switchrate=10

self int depth;

dtrace:::BEGIN
{
	printf("dtrace:::BEGIN\n");
#ifdef PYTHON_CALL_STACK
	printf("%s %6s %10s  %16s:%-4s %-8s -- %s\n", "C", "PID", "DELTA(us)",
	    "FILE", "LINE", "TYPE", "FUNC");
#endif
}

python$target:::function-entry
{
#ifdef PYTHON_CALL_STACK
    printf("%6d %16s:%-4d CALL %*s-> %s\n", pid,
#ifdef FULL_FILE_PATH
            copyinstr(arg0),
#else
            basename(copyinstr(arg0)),
#endif
            arg2,
            self->depth * 2, "",
            copyinstr(arg1));
    self->depth++;
#endif

#ifdef FULL_FILE_PATH
    self->file = copyinstr(arg0);
#else
    self->file = basename(copyinstr(arg0));
#endif
	self->name = copyinstr(arg1);
	self->line = arg2;
}

python$target:::function-return
{
#ifdef PYTHON_CALL_STACK
    self->depth -= self->depth > 0 ? 1 : 0;
    printf("%6d %16s:%-4d RTN  %*s<- %s\n", pid,
#ifdef FULL_FILE_PATH
            copyinstr(arg0),
#else
            basename(copyinstr(arg0)),
#endif
            arg2,
            self->depth * 2, "", copyinstr(arg1));
#endif
	self->file = 0;
	self->name = 0;
	self->line = 0;
}

python$target:::line
{
#ifdef FULL_FILE_PATH
    self->file = copyinstr(arg0);
#else
    self->file = basename(copyinstr(arg0));
#endif
    self->name = copyinstr(arg1);
    self->line = arg2;
}

/*
/self->file != NULL/
*/

/* For pymalloc calls of: _PyObject_Malloc, _PyObject_Calloc, _PyObject_Realloc, _PyObject_Free */

pid$target::_PyObject_Malloc:entry
/self->file != NULL/
{
    /* arg1 is the buffer size to allocate. */
    printf("%6d %16s:%-4d -> %s _PyObject_Malloc(%d)", pid, self->file, self->line, self->name, arg1);
}

pid$target::_PyObject_Malloc:return
/self->file != NULL/
{
    /* arg0 is the PC, arg1 is the buffer location */
    printf(" _PyObject_Malloc returns 0x%x\n", arg1);
}

pid$target::_PyObject_Calloc:entry
/self->file != NULL/
{
    /* arg1 is the number of elements, arg2 is the element size to allocate. */
    printf("%6d %16s:%-4d -> %s _PyObject_Calloc(%d, %d)", pid, self->file, self->line, self->name, arg1, arg2);
}

pid$target::_PyObject_Calloc:return
/self->file != NULL/
{
    /* arg0 is the PC, arg1 is the buffer location */
    printf(" _PyObject_Calloc returns 0x%x\n", arg1);
}

pid$target::_PyObject_Realloc:entry
/self->file != NULL/
{
    /* arg1 is the existing buffer, arg2 is the buffer size. */
    printf("%6d %16s:%-4d -> %s _PyObject_Realloc(0x%x, %d)\n", pid, self->file, self->line, self->name, arg1, arg2);
}

#if 0
/* Probe not available. */
pid$target::_PyObject_Realloc:return
{
    /* arg0 is the PC, arg1 is the buffer location */
    printf(" _PyObject_Realloc returns 0x%x\n", arg1);
}
#endif

pid$target::_PyObject_Free:entry
/self->file != NULL/
{
    /* arg1 is the existing buffer. */
    printf("%6d %16s:%-4d -> %s _PyObject_Free(0x%x)\n", pid, self->file, self->line, self->name, arg1);
}


dtrace:::END
{
	printf("\ndtrace:::END\n");
}
