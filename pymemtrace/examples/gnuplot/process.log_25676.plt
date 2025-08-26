
set grid
set title "Memory and CPU Usage." font ",14"
set xlabel "Elapsed Time (s)"
# set mxtics 5
# set xrange [0:3000]
# set xtics
# set format x ""

#set logscale y
set ylabel "Memory Usage (Mb)"
# set yrange [0:500]
# set ytics 20
# set mytics 2
# set ytics 8,35,3

#set logscale y2
set y2label "CPU Usage (%), Page Faults (10,000/s)"
# set y2range [0:200]
set y2tics

set pointsize 1
set datafile separator whitespace#"	"
set datafile missing "NaN"

set terminal png size 1000,700 # choose the file format
set output "process.log_25676.png" # choose the output device

# set key off

set arrow from 0.747189998626709,182.025390625 to 0.747189998626709,0 lt -1 lw 1
set label "String of 305.000 MB" at 0.747189998626709,186.57602539062498 left font ",10" rotate by 90 noenhanced front
set arrow from 1.7748818397521973,182.025390625 to 1.7748818397521973,0 lt -1 lw 1
set label "String of 186.000 MB" at 1.7748818397521973,186.57602539062498 left font ",10" rotate by 90 noenhanced front
set arrow from 3.7933287620544434,182.025390625 to 3.7933287620544434,0 lt -1 lw 1
set label "String of 231.000 MB" at 3.7933287620544434,186.57602539062498 left font ",10" rotate by 90 noenhanced front
set arrow from 5.808132886886597,182.025390625 to 5.808132886886597,0 lt -1 lw 1
set label "String of 262.000 MB" at 5.808132886886597,186.57602539062498 left font ",10" rotate by 90 noenhanced front
set arrow from 7.323624849319458,182.025390625 to 7.323624849319458,0 lt -1 lw 1
set label "String of 298.000 MB" at 7.323624849319458,186.57602539062498 left font ",10" rotate by 90 noenhanced front
set arrow from 9.342360734939575,182.025390625 to 9.342360734939575,0 lt -1 lw 1
set label "String of 217.000 MB" at 9.342360734939575,186.57602539062498 left font ",10" rotate by 90 noenhanced front
set arrow from 10.856239795684814,182.025390625 to 10.856239795684814,0 lt -1 lw 1
set label "String of 364.000 MB" at 10.856239795684814,186.57602539062498 left font ",10" rotate by 90 noenhanced front
set arrow from 12.36946988105774,182.025390625 to 12.36946988105774,0 lt -1 lw 1
set label "String of 236.000 MB" at 12.36946988105774,186.57602539062498 left font ",10" rotate by 90 noenhanced front

#set key title "Window Length"
#  lw 2 pointsize 2

plot "process.log_25676.dat" using 1:($2 / 1024**2) axes x1y1 title "RSS (Mb), left axis" with lines lt 1 lw 2, \
    "process.log_25676.dat" using 1:($3 / 10000) axes x1y2 title "Page Faults (10,000/s), right axis" with lines lt 3 lw 1, \
    "process.log_25676.dat" using 1:5 axes x1y2 title "Mean CPU (%), right axis" with lines lt 2 lw 1, \
    "process.log_25676.dat" using 1:6 axes x1y2 title "Instantaneous CPU (%), right axis" with lines lt 7 lw 1

reset
