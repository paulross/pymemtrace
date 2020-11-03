//
// Created by Paul Ross on 29/10/2020.
//

#ifndef CPYMEMTRACE_GET_RSS_H
#define CPYMEMTRACE_GET_RSS_H

#include <stdlib.h>

size_t getPeakRSS(void);
size_t getCurrentRSS(void);
size_t getCurrentRSS_alternate(void);

#endif //CPYMEMTRACE_GET_RSS_H
