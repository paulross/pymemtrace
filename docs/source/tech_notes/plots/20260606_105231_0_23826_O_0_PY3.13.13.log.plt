
set grid

set title "Memory and Live Object Count." font ",14"
set xlabel "Elapsed Time (s)"
# set mxtics 5
# set xrange [0:3000]
set xrange [0:110]
# set xtics
# set format x ""

#set logscale y
set ylabel "Memory Usage (Mb)"
set yrange [0:100]
# set ytics 20
# set mytics 2
# set ytics 8,35,3

#set logscale y2
set y2label "Live Object Count"
# set y2range [0:200]
set y2range [0:50]
set y2tics

set pointsize 1
set datafile separator whitespace#"	"
set datafile missing "NaN"

set terminal pngcairo size 1200,800 # choose the file format
set output "20260606_105231_0_23826_O_0_PY3.13.13.log.png" # choose the output device

# set key off

set arrow from 0.529741,5.0 to 0.529741,0 lt -1 lw 1
set label "Read LAS File 150524_WAITSIA-1_MWD_RUN2_HDS1_GR_VIB_MEM_50-2389mMDRT.las" at 0.529741,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 4.000474,5.0 to 4.000474,0 lt -1 lw 1
set label "Write HTML 150524_WAITSIA-1_MWD_RUN2_HDS1_GR_VIB_MEM_50-2389mMDRT.las.html" at 4.000474,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 5.460203,5.0 to 5.460203,0 lt -1 lw 1
set label "Read LAS File 150528_WAITSIA-1_MWD_RUN3_HDS1_PZIG_GR_VIB_RT_30-2700mMDRT.las" at 5.460203,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 11.662234,5.0 to 11.662234,0 lt -1 lw 1
set label "Write HTML 150528_WAITSIA-1_MWD_RUN3_HDS1_PZIG_GR_VIB_RT_30-2700mMDRT.las.html" at 11.662234,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 13.215994,5.0 to 13.215994,0 lt -1 lw 1
set label "Read LAS File 150529_WAITSIA-1_MWD_RUN3_HDS1_PZIG_GR_VIB_RT_30-2901mMDRT.las" at 13.215994,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 19.9342,5.0 to 19.9342,0 lt -1 lw 1
set label "Write HTML 150529_WAITSIA-1_MWD_RUN3_HDS1_PZIG_GR_VIB_RT_30-2901mMDRT.las.html" at 19.9342,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 21.674601,5.0 to 21.674601,0 lt -1 lw 1
set label "Read LAS File 150530_WAITSIA-1_MWD_RUN3_HDS1_PZIG_GR_VIB_RT_30-3232mMDRT.las" at 21.674601,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 28.696487,5.0 to 28.696487,0 lt -1 lw 1
set label "Write HTML 150530_WAITSIA-1_MWD_RUN3_HDS1_PZIG_GR_VIB_RT_30-3232mMDRT.las.html" at 28.696487,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 30.701652,5.0 to 30.701652,0 lt -1 lw 1
set label "Read LAS File 150531_WAITSIA-1_MWD_RUN3_HDS1_PZIG_GR_VIB_RT_30-3317mMDRT.las" at 30.701652,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 38.42309,5.0 to 38.42309,0 lt -1 lw 1
set label "Write HTML 150531_WAITSIA-1_MWD_RUN3_HDS1_PZIG_GR_VIB_RT_30-3317mMDRT.las.html" at 38.42309,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 40.696801,5.0 to 40.696801,0 lt -1 lw 1
set label "Read LAS File 150531_WAITSIA-1_MWD_RUN3_HDS1_PZIG_SGS_VIB_MEM_30-3317mMDRT.las" at 40.696801,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 48.407193,5.0 to 48.407193,0 lt -1 lw 1
set label "Write HTML 150531_WAITSIA-1_MWD_RUN3_HDS1_PZIG_SGS_VIB_MEM_30-3317mMDRT.las.html" at 48.407193,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 50.616646,5.0 to 50.616646,0 lt -1 lw 1
set label "Read LAS File 150607_WAITSIA-1_MWD_RUN4_HDS1_AWR_VIB_RT_30-3444mMDRT.las" at 50.616646,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 61.338626,5.0 to 61.338626,0 lt -1 lw 1
set label "Write HTML 150607_WAITSIA-1_MWD_RUN4_HDS1_AWR_VIB_RT_30-3444mMDRT.las.html" at 61.338626,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 63.89685,5.0 to 63.89685,0 lt -1 lw 1
set label "Read LAS File 150608_WAITSIA-1_MWD_RUN4_HDS1_AWR_VIB_RT_30-3490mMDRT.las" at 63.89685,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 73.689619,5.0 to 73.689619,0 lt -1 lw 1
set label "Write HTML 150608_WAITSIA-1_MWD_RUN4_HDS1_AWR_VIB_RT_30-3490mMDRT.las.html" at 73.689619,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 76.053207,5.0 to 76.053207,0 lt -1 lw 1
set label "Read LAS File 150608_WAITSIA-1_MWD_RUN4_HDS1_AWR_VIB_RT_30-3494mMDRT_TD.las" at 76.053207,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 86.219008,5.0 to 86.219008,0 lt -1 lw 1
set label "Write HTML 150608_WAITSIA-1_MWD_RUN4_HDS1_AWR_VIB_RT_30-3494mMDRT_TD.las.html" at 86.219008,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 88.645984,5.0 to 88.645984,0 lt -1 lw 1
set label "Read LAS File 150609_WAITSIA-1_MWD_RUN4_HDS1_AWR_MEM_30-3493mMDRT.las" at 88.645984,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 98.858174,5.0 to 98.858174,0 lt -1 lw 1
set label "Write HTML 150609_WAITSIA-1_MWD_RUN4_HDS1_AWR_MEM_30-3493mMDRT.las.html" at 98.858174,6.0 left font ",6" rotate by 90 noenhanced front

#set key title "Window Length"
#  lw 2 pointsize 2

set key left

plot "20260606_105231_0_23826_O_0_PY3.13.13.log.dat" using 1:($6 / 1024**2) axes x1y1 title "RSS (Mb), left axis" with lines lt 1 lw 2, \
"20260606_105231_0_23826_O_0_PY3.13.13.log.dat" using 1:2 axes x1y2 title "LASRead, right axis" with lines lt 2 lw 2, \
"20260606_105231_0_23826_O_0_PY3.13.13.log.dat" using 1:3 axes x1y2 title "LASSection, right axis" with lines lt 3 lw 2, \
"20260606_105231_0_23826_O_0_PY3.13.13.log.dat" using 1:5 axes x1y2 title "XhtmlStream, right axis" with lines lt 5 lw 2

reset
