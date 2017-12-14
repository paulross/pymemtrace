#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# MIT License
# 
# Copyright (c) 2017 paulross
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# 
# Paul Ross: apaulross@gmail.com

'''
This plots the results of a pymemtrace.MemTrace object in SVG
'''
import collections

# from pymemtrace import MemTrace
from pymemtrace.plot import Coord
from pymemtrace.plot import SVGWriter
from pymemtrace.plot import XmlWrite

MARGINS_ABS = {
    'top'       : Coord.Dim(8, 'mm'),
    'bottom'    : Coord.Dim(8, 'mm'),
    'left'      : Coord.Dim(8, 'mm'),
    'right'     : Coord.Dim(8, 'mm'),
}

MARGIN_AXIS = Coord.Dim(8, 'mm') # Allow for axis text as well
MARGIN_FROM_AXIS = Coord.Dim(4, 'mm')

#: offset is a Coord.Dim(), scale is a float
OffsetScale = collections.namedtuple('OffsetScale', ['offset', 'scale'])

def plot_memtrace_to_path(memtrace, file_path):
    """Plots a pymemtrace.MemTrace object in SVG to the ``file_path``."""
    with open(file_path, 'w') as fobj:
        plot_memtrace_to_file(memtrace, fobj)
        
def plot_memtrace_to_file(memtrace, fobj):
    """Plots a pymemtrace.MemTrace object in SVG to the file like object ``fobj``."""
    with SVGWriter.SVGWriter(fobj, _viewport()) as svgS:
        pass
    
def _viewport():
    view_port = Coord.Box(
        Coord.Dim(200, 'mm'), # x, to right
        Coord.Dim(400, 'mm'), # y, down.
    )
    return view_port

def _compute_scales_offsets(memtrace, viewport):
    result = {
    }

