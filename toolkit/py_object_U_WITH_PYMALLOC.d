#!/usr/sbin/dtrace -Zs
/*
 * toolkit/py_object_U_WITH_PYMALLOC.d - Python libc malloc analysis.
 * Written for the Python DTrace provider.
 * This is for debug builds of Python that have WITH_PYMALLOC not defined.
 *
 * This reports the Python call stack and along the way any calls to system malloc() or free().
 * It also reports aggregate memory allocation by Python function.
 *
 * It requires a Python build with at least (Mac OSX) that tracks all memory allocations build with something like:
 * ../configure --with-pydebug --without-pymalloc --with-valgrind --with-dtrace --with-openssl=$(brew --prefix openssl)
 *
 * USAGE (-C is to invoke the C preprocessor on this script):
 * sudo dtrace -C -s toolkit/py_object_U_WITH_PYMALLOC.d -p <PID>
 *
 * Or for full path names:
 * sudo dtrace -C -s toolkit/py_object_U_WITH_PYMALLOC.d -D FULL_FILE_PATH -p <PID>
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

/* For pymalloc calls of: _PyMem_RawMalloc, _PyMem_RawCalloc, _PyMem_RawRealloc, _PyMem_RawFree */

pid$target::_PyMem_RawMalloc:entry
/self->file != NULL/
{
    /* arg1 is the buffer size to allocate. */
    printf("%6d %16s:%-4d -> %s _PyMem_RawMalloc(%d)", pid, self->file, self->line, self->name, arg1);
}

pid$target::_PyMem_RawMalloc:return
/self->file != NULL/
{
    /* arg0 is the PC, arg1 is the buffer location */
    printf(" _PyMem_RawMalloc returns 0x%x\n", arg1);
}

pid$target::_PyMem_RawCalloc:entry
/self->file != NULL/
{
    /* arg1 is the number of elements, arg2 is the element size to allocate. */
    printf("%6d %16s:%-4d -> %s _PyMem_RawCalloc(%d, %d)", pid, self->file, self->line, self->name, arg1, arg2);
}

pid$target::_PyMem_RawCalloc:return
/self->file != NULL/
{
    /* arg0 is the PC, arg1 is the buffer location */
    printf(" _PyMem_RawCalloc returns 0x%x\n", arg1);
}

pid$target::_PyMem_RawRealloc:entry
/self->file != NULL/
{
    /* arg1 is the existing buffer, arg2 is the buffer size. */
    printf("%6d %16s:%-4d -> %s _PyMem_RawRealloc(0x%x, %d)", pid, self->file, self->line, self->name, arg1, arg2);
}

pid$target::_PyMem_RawRealloc:return
{
    /* arg0 is the PC, arg1 is the buffer location */
    printf(" _PyMem_RawRealloc returns 0x%x\n", arg1);
}

pid$target::_PyMem_RawFree:entry
/self->file != NULL/
{
    /* arg1 is the existing buffer. */
    printf("%6d %16s:%-4d -> %s _PyMem_RawFree(0x%x)\n", pid, self->file, self->line, self->name, arg1);
}


dtrace:::END
{
	printf("\ndtrace:::END\n");
}
