#!/usr/sbin/dtrace -Zs
/*
 * py_malloc.d - Python libc malloc analysis.
 *               Written for the Python DTrace provider.
 *
 * $Id: py_malloc.d 19 2007-09-12 07:47:59Z brendan $
 *
 * This is an expiremental script to identify who is calling malloc() for
 * memory allocation, and to print distribution plots of the requested bytes.
 * If a malloc() occured while in a Python function, then that function is
 * identified as responsible; else the caller of malloc() is identified as
 * responsible - which will be a function from the Python engine.
 *
 * USAGE: py_malloc.d { -p PID | -c cmd }	# hit Ctrl-C to end
 *
 * Filename and function names are printed if available.
 *
 * COPYRIGHT: Copyright (c) 2007 Brendan Gregg.
 *
 * CDDL HEADER START
 *
 *  The contents of this file are subject to the terms of the
 *  Common Development and Distribution License, Version 1.0 only
 *  (the "License").  You may not use this file except in compliance
 *  with the License.
 *
 *  You can obtain a copy of the license at Docs/cddl1.txt
 *  or http://www.opensolaris.org/os/licensing.
 *  See the License for the specific language governing permissions
 *  and limitations under the License.
 *
 * CDDL HEADER END
 *
 * 09-Sep-2007	Brendan Gregg	Created this.
 */

#pragma D option quiet
//#pragma D option switchrate=10

self int depth;

dtrace:::BEGIN
{
	/*
	printf("Tracing... Hit Ctrl-C to end.\n");
	printf("%s %6s %10s  %16s:%-4s %-8s -- %s\n", "C", "PID", "DELTA(us)",
	    "FILE", "LINE", "TYPE", "FUNC");
	*/
	printf("dtrace:::BEGIN\n");
}

python$target:::function-entry
{
	/*
	self->file = basename(copyinstr(arg0));
	*/
    printf("%6d %16s:%-4d CALL %*s-> %s\n", pid, basename(copyinstr(arg0)), arg2,
            self->depth * 2, "", copyinstr(arg1));
    self->depth++;

//	self->file = copyinstr(arg0);
    self->file = basename(copyinstr(arg0));
	self->name = copyinstr(arg1);
	self->line = arg2;
//	self->malloc_trace = 1;
}

python$target:::function-return
{
    self->depth -= self->depth > 0 ? 1 : 0;
    printf("%6d %16s:%-4d RETN %*s<- %s\n", pid, basename(copyinstr(arg0)), arg2,
            self->depth * 2, "", copyinstr(arg1));
	self->file = 0;
	self->name = 0;
	self->line = 0;
//	self->malloc_trace = 0;
}

python$target:::line
{
//    self->file = copyinstr(arg0);
    self->file = basename(copyinstr(arg0));
    self->name = copyinstr(arg1);
    self->line = arg2;
}

/*
/self->malloc_trace/
 */

pid$target::malloc:entry
/self->file != NULL/
{
    self->malloc_size = arg0;
    printf("%6d %16s:%-4d -> %s malloc(%d)", pid, self->file, self->line, self->name, arg0);

//    self->file_2 = self->file;
//    self->name_2 = self->name;

/*
    printf("PID %d malloc(%d) entry %s -> %s %s\n", pid, arg0, self->file, self->name, self->line);
	@malloc_func_size[self->file, self->name] = sum(arg0);
	@malloc_func_dist[self->file, self->name] = quantize(arg0);
*/
}

/*
/self->malloc_trace/
*/

pid$target::malloc:return
/self->file != NULL/
{
    printf(" pntr 0x%x\n", arg1);
//    printf(" pntr %p\n", arg1);
    /*
    printf("PID %d malloc(Ox%x) return %s -> %s %s\n", pid, arg1, self->file, self->name, self->line);
     */
}

/*
pid$target::malloc:return
/self->file == NULL/
{
    printf("PID %d malloc(%d) returns 0x%x %s %d -> %s\n", pid, self->malloc_size, arg1,
            self->file, self->line, self->name);
}
*/

pid$target::free:entry
/self->file != NULL/
{
//    printf("%6d free(0x%x) %16s:%-4d -> %s\n", pid, arg0, self->file, self->line, self->name);
    printf("%6d %16s:%-4d -> %s free(0x%x)\n", pid, self->file, self->line, self->name, arg0);
//    printf("%6d free(0x%016x) %16s:%-4d -> %s\n", pid, arg0, self->file, self->line, self->name);
/*
	@malloc_func_size[self->file, self->name] = sum(arg0);
	@malloc_func_dist[self->file, self->name] = quantize(arg0);
*/
}

/*
pid$target::malloc:entry
/self->name == NULL/
{
	@malloc_lib_size[usym(ucaller)] = sum(arg0);
	@malloc_lib_dist[usym(ucaller)] = quantize(arg0);
}
*/


dtrace:::END
{
	printf("\ndtrace:::END\n");
/*
	printf("\nPython malloc byte distributions by engine caller,\n\n");
	printa("   %A, total bytes = %@d %@d\n", @malloc_lib_size,
	    @malloc_lib_dist);
	printf("\nPython malloc byte distributions by Python file and ");
	printf("function,\n\n");
	printa("   %s, %s, bytes total = %@d %@d\n", @malloc_func_size,
	    @malloc_func_dist);
*/
}


/*
 * Hmm:
 * "49882 rs/paulross/Documents/workspace/pymemtrace/pymemtrace/examples/memory_exercise.py:19   -> ise.py malloc(52) pntr 0x7f91b79aad10"
 * But we are always taking the basename()
 * ???
 * len('memory_exerc') is 12.
 * len('/Use') is 4
 */
