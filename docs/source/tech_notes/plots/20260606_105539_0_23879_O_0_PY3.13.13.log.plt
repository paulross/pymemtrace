
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
set output "20260606_105539_0_23879_O_0_PY3.13.13.log.png" # choose the output device

# set key off

set arrow from 0.562613,5.0 to 0.562613,0 lt -1 lw 1
set label "Read LAS File 150524_WAITSIA-1_MWD_RUN2_HDS1_GR_VIB_MEM_50-2389mMDRT.las" at 0.562613,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 3.736349,5.0 to 3.736349,0 lt -1 lw 1
set label "Write HTML 150524_WAITSIA-1_MWD_RUN2_HDS1_GR_VIB_MEM_50-2389mMDRT.las.html" at 3.736349,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 5.491128,5.0 to 5.491128,0 lt -1 lw 1
set label "Read LAS File 150528_WAITSIA-1_MWD_RUN3_HDS1_PZIG_GR_VIB_RT_30-2700mMDRT.las" at 5.491128,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 11.222667,5.0 to 11.222667,0 lt -1 lw 1
set label "Write HTML 150528_WAITSIA-1_MWD_RUN3_HDS1_PZIG_GR_VIB_RT_30-2700mMDRT.las.html" at 11.222667,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 12.686431,5.0 to 12.686431,0 lt -1 lw 1
set label "Read LAS File 150529_WAITSIA-1_MWD_RUN3_HDS1_PZIG_GR_VIB_RT_30-2901mMDRT.las" at 12.686431,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 18.753147,5.0 to 18.753147,0 lt -1 lw 1
set label "Write HTML 150529_WAITSIA-1_MWD_RUN3_HDS1_PZIG_GR_VIB_RT_30-2901mMDRT.las.html" at 18.753147,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 20.447979,5.0 to 20.447979,0 lt -1 lw 1
set label "Read LAS File 150530_WAITSIA-1_MWD_RUN3_HDS1_PZIG_GR_VIB_RT_30-3232mMDRT.las" at 20.447979,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 27.476546,5.0 to 27.476546,0 lt -1 lw 1
set label "Write HTML 150530_WAITSIA-1_MWD_RUN3_HDS1_PZIG_GR_VIB_RT_30-3232mMDRT.las.html" at 27.476546,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 29.484706,5.0 to 29.484706,0 lt -1 lw 1
set label "Read LAS File 150531_WAITSIA-1_MWD_RUN3_HDS1_PZIG_GR_VIB_RT_30-3317mMDRT.las" at 29.484706,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 36.807381,5.0 to 36.807381,0 lt -1 lw 1
set label "Write HTML 150531_WAITSIA-1_MWD_RUN3_HDS1_PZIG_GR_VIB_RT_30-3317mMDRT.las.html" at 36.807381,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 38.877812,5.0 to 38.877812,0 lt -1 lw 1
set label "Read LAS File 150531_WAITSIA-1_MWD_RUN3_HDS1_PZIG_SGS_VIB_MEM_30-3317mMDRT.las" at 38.877812,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 46.468448,5.0 to 46.468448,0 lt -1 lw 1
set label "Write HTML 150531_WAITSIA-1_MWD_RUN3_HDS1_PZIG_SGS_VIB_MEM_30-3317mMDRT.las.html" at 46.468448,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 48.455073,5.0 to 48.455073,0 lt -1 lw 1
set label "Read LAS File 150607_WAITSIA-1_MWD_RUN4_HDS1_AWR_VIB_RT_30-3444mMDRT.las" at 48.455073,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 58.358943,5.0 to 58.358943,0 lt -1 lw 1
set label "Write HTML 150607_WAITSIA-1_MWD_RUN4_HDS1_AWR_VIB_RT_30-3444mMDRT.las.html" at 58.358943,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 60.65943,5.0 to 60.65943,0 lt -1 lw 1
set label "Read LAS File 150608_WAITSIA-1_MWD_RUN4_HDS1_AWR_VIB_RT_30-3490mMDRT.las" at 60.65943,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 70.681695,5.0 to 70.681695,0 lt -1 lw 1
set label "Write HTML 150608_WAITSIA-1_MWD_RUN4_HDS1_AWR_VIB_RT_30-3490mMDRT.las.html" at 70.681695,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 73.036775,5.0 to 73.036775,0 lt -1 lw 1
set label "Read LAS File 150608_WAITSIA-1_MWD_RUN4_HDS1_AWR_VIB_RT_30-3494mMDRT_TD.las" at 73.036775,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 83.210919,5.0 to 83.210919,0 lt -1 lw 1
set label "Write HTML 150608_WAITSIA-1_MWD_RUN4_HDS1_AWR_VIB_RT_30-3494mMDRT_TD.las.html" at 83.210919,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 85.728323,5.0 to 85.728323,0 lt -1 lw 1
set label "Read LAS File 150609_WAITSIA-1_MWD_RUN4_HDS1_AWR_MEM_30-3493mMDRT.las" at 85.728323,6.0 left font ",6" rotate by 90 noenhanced front
set arrow from 95.359477,5.0 to 95.359477,0 lt -1 lw 1
set label "Write HTML 150609_WAITSIA-1_MWD_RUN4_HDS1_AWR_MEM_30-3493mMDRT.las.html" at 95.359477,6.0 left font ",6" rotate by 90 noenhanced front

#set key title "Window Length"
#  lw 2 pointsize 2

set key left

plot "20260606_105539_0_23879_O_0_PY3.13.13.log.dat" using 1:($6 / 1024**2) axes x1y1 title "RSS (Mb), left axis" with lines lt 1 lw 2, \
"20260606_105539_0_23879_O_0_PY3.13.13.log.dat" using 1:2 axes x1y2 title "LASRead, right axis" with lines lt 2 lw 2, \
"20260606_105539_0_23879_O_0_PY3.13.13.log.dat" using 1:3 axes x1y2 title "LASSection, right axis" with lines lt 3 lw 2, \
"20260606_105539_0_23879_O_0_PY3.13.13.log.dat" using 1:5 axes x1y2 title "XhtmlStream, right axis" with lines lt 5 lw 2

reset
