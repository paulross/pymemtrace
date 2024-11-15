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

void macosx_get_pid_info(void) {
    printf("macosx_get_pid_info()\n");
    pid_t pid = getpid();
    struct proc_bsdinfo proc;
    int st = proc_pidinfo(pid, PROC_PIDTBSDINFO, 0, &proc, PROC_PIDTBSDINFO_SIZE);
    printf("Result: %d %lu\n", st, sizeof(proc));
    printf("name: %s\n", proc.pbi_name);
}

/* PROC_PIDTASKINFO in /Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX10.14.sdk/usr/include/sys/proc_info.h:647 */
void macosx_get_task_info(void) {
    printf("macosx_get_task_info()\n");
    pid_t pid = getpid();
    struct proc_taskinfo proc;
    int st = proc_pidinfo(pid, PROC_PIDTASKINFO, 0, &proc, PROC_PIDTASKINFO_SIZE);
    printf("Result: %d %lu\n", st, sizeof(proc));
    printf("RSS: %llu\n", proc.pti_resident_size);
}

void macosx_get_taskall_info(void) {
    printf("macosx_get_taskall_info()\n");
    pid_t pid = getpid();
    struct proc_taskallinfo proc;
    int st = proc_pidinfo(pid, PROC_PIDTASKALLINFO, 0, &proc, PROC_PIDTASKALLINFO_SIZE);
    printf("Result: %d %lu\n", st, sizeof(proc));
    printf("name: %s\n", proc.pbsd.pbi_name);
}

void macosx_get_just_rss_info(void) {
    printf("macosx_get_just_rss_info()\n");
    pid_t pid = getpid();
    struct proc_taskallinfo proc;
    int st = proc_pidinfo(pid, PROC_PID_RUSAGE, 0, &proc, PROC_PID_RUSAGE_SIZE);
    printf("Result: %d %lu\n", st, sizeof(proc));
    printf("name: %s\n", proc.pbsd.pbi_name);
}

void macosx_get_short_pid_info(void) {
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
}

#if 1
int
main (int argc, char **argv)
{
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

    return 0;
}
#endif
