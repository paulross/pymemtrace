//
// Created by Paul Ross on 29/10/2020.
//
// Source: https://www.gnu.org/software/libc/manual/html_node/Example-of-Getopt.html
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#include <libproc.h>

#include "get_rss.h"
#include "cpy/cPyMemTrace.h"

void macosx_get_short_pid_info(void) {
    printf("STRT: %s\n", __PRETTY_FUNCTION__);
    pid_t pid = getpid();
    struct proc_bsdshortinfo proc;

    int st = proc_pidinfo(pid, PROC_PIDT_SHORTBSDINFO, 0,
                          &proc, PROC_PIDT_SHORTBSDINFO_SIZE);

    if (st != PROC_PIDT_SHORTBSDINFO_SIZE) {
        fprintf(stderr, "Cannot get process info\n");
    }
    printf(" pid: %d\n", (int)proc.pbsi_pid);
    printf("ppid: %d\n", (int)proc.pbsi_ppid);
    printf("comm: %s\n",      proc.pbsi_comm);
    //printf("name: %s\n",      proc.pbsi_name);
    printf(" uid: %d\n", (int)proc.pbsi_uid);
    printf(" gid: %d\n", (int)proc.pbsi_gid);
    printf("DONE: %s\n", __PRETTY_FUNCTION__);
}

void macosx_get_pid_info(void) {
    printf("STRT: %s\n", __PRETTY_FUNCTION__);
    pid_t pid = getpid();
    struct proc_bsdinfo proc;
    int st = proc_pidinfo(pid, PROC_PIDTBSDINFO, 0, &proc, PROC_PIDTBSDINFO_SIZE);
    printf("Result: %d %lu\n", st, sizeof(proc));
    printf("name: %s\n", proc.pbi_name);
    printf("DONE: %s\n", __PRETTY_FUNCTION__);
}

/* PROC_PIDTASKINFO in /Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX10.14.sdk/usr/include/sys/proc_info.h:647 */
void macosx_get_task_info(void) {
    printf("STRT: %s\n", __PRETTY_FUNCTION__);
    pid_t pid = getpid();
    struct proc_taskinfo proc;
    int st = proc_pidinfo(pid, PROC_PIDTASKINFO, 0, &proc, PROC_PIDTASKINFO_SIZE);
    printf("Result: %d %lu\n", st, sizeof(proc));
    printf("RSS: %llu\n", proc.pti_resident_size);
    printf("DONE: %s\n", __PRETTY_FUNCTION__);
}

void macosx_get_taskall_info(void) {
    printf("STRT: %s\n", __PRETTY_FUNCTION__);
    pid_t pid = getpid();
    struct proc_taskallinfo proc;
    int st = proc_pidinfo(pid, PROC_PIDTASKALLINFO, 0, &proc, PROC_PIDTASKALLINFO_SIZE);
    printf("Result: %d %lu\n", st, sizeof(proc));
    printf("name: %s\n", proc.pbsd.pbi_name);
    printf("DONE: %s\n", __PRETTY_FUNCTION__);
}

void macosx_get_just_rss_info(void) {
    printf("STRT: %s\n", __PRETTY_FUNCTION__);
    pid_t pid = getpid();
    struct proc_taskallinfo proc;
    int st = proc_pidinfo(pid, PROC_PID_RUSAGE, 0, &proc, PROC_PID_RUSAGE_SIZE);
    printf("Result: %d %lu\n", st, sizeof(proc));
    printf("name: %s\n", proc.pbsd.pbi_name);
    printf("DONE: %s\n", __PRETTY_FUNCTION__);
}

#if 1
int
main (int argc, char **argv) {
#if 0 /* Example of processing command line  options. */
    int aflag = 0;
    int bflag = 0;
    char *cvalue = NULL;
    int index;
    int c;

    opterr = 0;

    while ((c = getopt (argc, argv, "abc:")) != -1)
        switch (c)
        {
            case 'a':
                aflag = 1;
                break;
            case 'b':
                bflag = 1;
                break;
            case 'c':
                cvalue = optarg;
                break;
            case '?':
                if (optopt == 'c')
                    fprintf (stderr, "Option -%c requires an argument.\n", optopt);
                else if (isprint (optopt))
                    fprintf (stderr, "Unknown option `-%c'.\n", optopt);
                else
                    fprintf (stderr,
                             "Unknown option character `\\x%x'.\n",
                             optopt);
                return 1;
            default:
                abort ();
        }

    printf ("aflag = %d, bflag = %d, cvalue = %s\n",
            aflag, bflag, cvalue);
    for (index = optind; index < argc; index++)
        printf ("Non-option argument %s\n", argv[index]);
#endif /* END: Example of processing command line  options. */

    size_t rss = getCurrentRSS();
    size_t rss_peak = getPeakRSS();
    printf("RSS: %zu Peak RSS: %zu\n", rss, rss_peak);

    printf("\n");
    macosx_get_short_pid_info();

    printf("\n");
    macosx_get_pid_info();

    printf("\n");
    macosx_get_task_info();

    printf("\n");
    macosx_get_taskall_info();

    printf("\n");
    macosx_get_just_rss_info();

    printf("\n");
    int debug_result;
    debug_result = debug_cPyMemtrace(argc, argv);
    printf("Debug result: %d", debug_result);

    return 0;
}
#endif
