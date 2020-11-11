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

pid$target::malloc:entry
/self->file != NULL/
{
    /* So this is slightly not well understood. It seems that self-file and self-> name do not persist to
     * pid$target::malloc:return
     * They are often null or truncated in some way.
     *
     * Instead we report them here but without the terminating '\n' then pid$target::malloc:return can add the pointer
     * value onto the end of the line and terminate it.
     *
     * It seems to work in practice.
     */

    /*
     * arg0 is the buffer size to allocate.
     */
    printf("%6d %16s:%-4d -> %s malloc(%d)", pid, self->file, self->line, self->name, arg0);

    @malloc_func_size[self->file, self->name] = sum(arg0);
    @malloc_func_dist[self->file, self->name] = quantize(arg0);
}

pid$target::malloc:return
/self->file != NULL/
{
    /*
     * arg0 is the program counter.
     * arg1 is the buffer pointer that has been allocated.
     */
    printf(" pntr 0x%x\n", arg1);
}

pid$target::malloc:entry
/self->name == NULL/
{
    @malloc_lib_size[usym(ucaller)] = sum(arg0);
    @malloc_lib_dist[usym(ucaller)] = quantize(arg0);
}

pid$target::free:entry
/self->file != NULL/
{
    /*
     * arg0 is the address to free.
     */
    printf("%6d %16s:%-4d -> %s free(0x%x)\n", pid, self->file, self->line, self->name, arg0);
}

dtrace:::END
{
	printf("\ndtrace:::END\n");
	printf("Python malloc byte distributions by engine caller:\n");
	printa("   %A, total bytes = %@d %@d\n", @malloc_lib_size, @malloc_lib_dist);
	printf("\nPython malloc byte distributions by Python file and function:\n\n");
	printa("   %s, %s, bytes total = %@d %@d\n", @malloc_func_size, @malloc_func_dist);
}
