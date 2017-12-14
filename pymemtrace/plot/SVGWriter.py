#!/usr/bin/env python
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

"""An SVG writer."""

__author__  = 'Paul Ross'
__date__    = '2011-07-10'
__rights__  = 'Copyright (c) 2008-2017 Paul Ross'

from . import XmlWrite
from . import Coord

#: Write the function name in a SVG comment.
SVG_COMMENT_FUNCTIONS = False

class ExceptionSVGWriter(Exception):
    """Exception class for SVGWriter."""
    pass

def dimToTxt(theDim):
    """Converts a Coord.Dim() object to text for SVG units.

    Examples:

    ``(2.0 / 3.0, 'in')`` becomes ``'0.667in'``

    ``(2.0 / 3.0, 'mm')`` becomes ``'0.7mm'``

    ``(23.123, 'px')`` becomes ``'23px'``

    :param theDim: The dimension
    :type theDim: ``cpip.plot.Coord.Dim([float, str]), cpip.plot.Coord.Dim([int, str])``

    :returns: ``str`` -- Text suitable for writing SVG, for example '0.667in'.
    """
    return Coord.UNIT_MAP_DEFAULT_FORMAT_WITH_UNITS[theDim.units] % (theDim.value, theDim.units)

class SVGWriter(XmlWrite.XmlStream):
    """An XML writer specialised for writing SVG."""
    def __init__(self, theFile, theViewPort, rootAttrs=None, mustIndent=True):
        """Initialise the stream with a file and Coord.Box() object.
        The view port units must be the same for width and depth.

        :param theFile: Output file.
        :type theFile: ``_io.TextIOWrapper``

        :param theViewPort: Viewport.
        :type theViewPort: ``cpip.plot.Coord.Box([cpip.plot.Coord.Dim([int, str]), cpip.plot.Coord.Dim([int, <class 'str'>])])``

        :param rootAttrs: Root element attributes.
        :type rootAttrs: ``dict({str : [str]})``

        :param mustIndent: Indent elements or write them inline.
        :type mustIndent: ``bool``

        :returns: ``NoneType``
        """
        super(SVGWriter, self).__init__(theFile, mustIndent=mustIndent)
        self._viewPort = theViewPort
        self._rootAttrs = rootAttrs
            
    def __enter__(self):
        """Context management.

        :returns: ``cpip.plot.SVGWriter.SVGWriter`` -- <insert documentation for return values>
        """
        super(SVGWriter, self).__enter__()
        self._file.write(u"""\n<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">""")
        _attrs = {
            'xmlns'         : 'http://www.w3.org/2000/svg',
            'version'       : '1.1',
            'width'         : dimToTxt(self._viewPort.width),
            'height'        : dimToTxt(self._viewPort.depth),
        }
        if self._rootAttrs:
            _attrs.update(self._rootAttrs)
        self.startElement('svg', _attrs)
        return self
    
class SVGGroup(XmlWrite.Element):
    """See: http://www.w3.org/TR/2003/REC-SVG11-20030114/struct.html#GElement
    """
    def __init__(self, theXmlStream, attrs=None):
        """Initialise the group with a stream.

        Sadly we can't use ``**kwargs`` because of Python restrictions on keyword
        names. For example ``stroke-width`` that is not a valid keyword
        argument (although ``stroke_width`` would be). So instead we pass in an
        optional dictionary {string : string, ...}

        :param theXmlStream: The SVG stream.
        :type theXmlStream: :py:class:`cpip.plot.SVGWriter.SVGWriter`

        :param attrs: Element attributes.
        :type attrs: ``dict({str : [<class 'str'>, str]}), dict({str : [str]})``

        :returns: ``NoneType``
        """
        super(SVGGroup, self).__init__(theXmlStream, 'g', attrs)

class SVGRect(XmlWrite.Element):
    """See: http://www.w3.org/TR/2003/REC-SVG11-20030114/shapes.html#RectElement
    """
    def __init__(self, theXmlStream, thePoint, theBox, attrs=None):
        """Initialise the rectangle with a stream, a :py:class:`cpip.plot.Coord.Pt`
        and a :py:class:`cpip.plot.Coord.Box` objects.

        Typical attributes:

        ``{'fill' : "blue", 'stroke' : "black", 'stroke-width' : "2", }``

        <insert documentation for function>

        :param theXmlStream: The SVG stream.
        :type theXmlStream: :py:class:`cpip.plot.SVGWriter.SVGWriter`

        :param thePoint: Starting point.
        :type thePoint: ``cpip.plot.Coord.Pt([cpip.plot.Coord.Dim([float, str]), cpip.plot.Coord.Dim([float, <class 'str'>])])``

        :param theBox: The box.
        :type theBox: ``cpip.plot.Coord.Box([cpip.plot.Coord.Dim([float, str]), <class 'cpip.plot.Coord.Dim'>]), cpip.plot.Coord.Box([cpip.plot.Coord.Dim([float, str]), cpip.plot.Coord.Dim([float, <class 'str'>])]), cpip.plot.Coord.Box([cpip.plot.Coord.Dim([float, str]), cpip.plot.Coord.Dim([int, <class 'str'>])]), cpip.plot.Coord.Box([cpip.plot.Coord.Dim([int, str]), cpip.plot.Coord.Dim([int, <class 'str'>])])``

        :param attrs: Element attributes.
        :type attrs: ``dict({str : [<class 'str'>, str]}), dict({str : [str]})``

        :returns: ``NoneType``
        """
        myAttrs = {
                    'x'         : dimToTxt(thePoint.x),
                    'y'         : dimToTxt(thePoint.y),
                    'width'     : dimToTxt(theBox.width),
                    'height'    : dimToTxt(theBox.depth),
                }
        if attrs:
            myAttrs.update(attrs)
        super(SVGRect, self).__init__(theXmlStream, 'rect', myAttrs)
    
class SVGCircle(XmlWrite.Element):
    """A circle in SVG. See: http://www.w3.org/TR/2003/REC-SVG11-20030114/shapes.html#CircleElement
    """
    def __init__(self, theXmlStream, thePoint, theRadius, attrs=None):
        """Initialise the circle with a stream, a :py:class:`cpip.plot.Coord.Pt`
        and a :py:class:`cpip.plot.Coord.Dim` objects.

        :param theXmlStream: The SVG stream.
        :type theXmlStream: :py:class:`cpip.plot.SVGWriter.SVGWriter`

        :param ptFrom: Starting point.
        :type ptFrom: ``cpip.plot.Coord.Pt([cpip.plot.Coord.Dim([float, str]), cpip.plot.Coord.Dim([float, <class 'str'>])])``

        :param theRadius: X radius.
        :type ptTo: ``cpip.plot.Coord.Dim([float, str])``

        :param attrs: Element attributes.
        :type attrs: ``dict({str : [str]})``

        :returns: ``NoneType``
        """
        _attrs = {
                    'cx'        : dimToTxt(thePoint.x),
                    'cy'        : dimToTxt(thePoint.y),
                    'r'         : dimToTxt(theRadius),
                }
        if attrs:
            _attrs.update(attrs)
        super(SVGCircle, self).__init__(theXmlStream, 'circle', _attrs)
    
class SVGElipse(XmlWrite.Element):
    """An elipse in SVG. See: http://www.w3.org/TR/2003/REC-SVG11-20030114/shapes.html#EllipseElement
    """
    def __init__(self, theXmlStream, ptFrom, theRadX, theRadY, attrs=None):
        """Initialise the elipse with a stream, a :py:class:`cpip.plot.Coord.Pt`
        and a :py:class:`cpip.plot.Coord.Dim` objects.

        :param theXmlStream: The SVG stream.
        :type theXmlStream: :py:class:`cpip.plot.SVGWriter.SVGWriter`

        :param ptFrom: Starting point.
        :type ptFrom: ``cpip.plot.Coord.Pt([cpip.plot.Coord.Dim([float, str]), cpip.plot.Coord.Dim([float, <class 'str'>])])``

        :param theRadX: X radius.
        :type ptTo: ``cpip.plot.Coord.Dim([float, str])``

        :param theRadY: Y radius.
        :type ptTo: ``cpip.plot.Coord.Dim([float, str])``

        :param attrs: Element attributes.
        :type attrs: ``dict({str : [str]})``

        :returns: ``NoneType``
        """
        _attrs = {
                    'cx'        : dimToTxt(ptFrom.x),
                    'cy'        : dimToTxt(ptFrom.y),
                    'rx'        : dimToTxt(theRadX),
                    'ry'        : dimToTxt(theRadY),
                }
        if attrs:
            _attrs.update(attrs)
        super(SVGElipse, self).__init__(theXmlStream, 'elipse', _attrs)
    
class SVGLine(XmlWrite.Element):
    """A line in SVG. See: http://www.w3.org/TR/2003/REC-SVG11-20030114/shapes.html#LineElement
    """
    def __init__(self, theXmlStream, ptFrom, ptTo, attrs=None):
        """Initialise the line with a stream, and two :py:class:`cpip.plot.Coord.Pt` objects.

        :param theXmlStream: The SVG stream.
        :type theXmlStream: :py:class:`cpip.plot.SVGWriter.SVGWriter`

        :param ptFrom: Starting point.
        :type ptFrom: ``cpip.plot.Coord.Pt([cpip.plot.Coord.Dim([float, str]), cpip.plot.Coord.Dim([float, <class 'str'>])])``

        :param ptTo: Ending point.
        :type ptTo: ``cpip.plot.Coord.Pt([cpip.plot.Coord.Dim([float, str]), cpip.plot.Coord.Dim([float, <class 'str'>])])``

        :param attrs: Element attributes.
        :type attrs: ``dict({str : [str]})``

        :returns: ``NoneType``
        """
        _attrs = {
                    'x1'        : dimToTxt(ptFrom.x),
                    'y1'        : dimToTxt(ptFrom.y),
                    'x2'        : dimToTxt(ptTo.x),
                    'y2'        : dimToTxt(ptTo.y),
                }
        if attrs:
            _attrs.update(attrs)
        super(SVGLine, self).__init__(theXmlStream, 'line', _attrs)
    
class SVGPointList(XmlWrite.Element):
    """An abstract class that takes a list of points, derived by polyline and polygon.
    """
    def __init__(self, theXmlStream, name, pointS, attrs):
        """Initialise the element with a stream, a name, and a list of
        :py:class:`cpip.plot.Coord.Pt` objects.

        NOTE: The units of the points are ignored, it is up to the caller to convert
        them to the User Coordinate System.

        :param theXmlStream: The SVG stream.
        :type theXmlStream: :py:class:`cpip.plot.SVGWriter.SVGWriter`

        :param name: Element name.
        :type name: ``NoneType, str``

        :param pointS: List of points
        :type thePoint: ``list[cpip.plot.Coord.Pt([cpip.plot.Coord.Dim([float, str]), cpip.plot.Coord.Dim([float, <class 'str'>])])]``

        :param attrs: Element attributes.
        :type attrs: ``dict({str : [str]})``

        :returns: ``NoneType``
        """
        _attrs = {
            'points' : ' '.join(['%s,%s' % (p.x.value, p.y.value) for p in pointS])
        }
        if attrs:
            _attrs.update(attrs)
        super(SVGPointList, self).__init__(theXmlStream, name, _attrs)

class SVGPolyline(SVGPointList):
    """A polyline in SVG. See: http://www.w3.org/TR/2003/REC-SVG11-20030114/shapes.html#PolylineElement
    """
    def __init__(self, theXmlStream, pointS, attrs=None):
        """    Initialise the polyline with a stream, and a list of
        :py:class:`cpip.plot.Coord.Pt` objects.

        NOTE: The units of the points are ignored, it is up to the caller to convert
        them to the User Coordinate System.

        :param theXmlStream: The SVG stream.
        :type theXmlStream: :py:class:`cpip.plot.SVGWriter.SVGWriter`

        :param pointS: List of points
        :type thePoint: ``list[cpip.plot.Coord.Pt([cpip.plot.Coord.Dim([float, str]), cpip.plot.Coord.Dim([float, <class 'str'>])])]``

        :param attrs: Element attributes.
        :type attrs: ``dict({str : [str]})``

        :returns: ``NoneType``
        """
        super(SVGPolyline, self).__init__(theXmlStream, 'polyline', pointS, attrs)
    
class SVGPolygon(SVGPointList):
    """A polygon in SVG. See: http://www.w3.org/TR/2003/REC-SVG11-20030114/shapes.html#PolygonElement
    """
    def __init__(self, theXmlStream, pointS, attrs=None):
        """Initialise the polygon with a stream, and a list of
        :py:class:`cpip.plot.Coord.Pt` objects.

        NOTE: The units of the points are ignored, it is up to the caller to convert
        them to the User Coordinate System.

        :param theXmlStream: The SVG stream.
        :type theXmlStream: :py:class:`cpip.plot.SVGWriter.SVGWriter`

        :param pointS: List of points
        :type thePoint: ``list[cpip.plot.Coord.Pt([cpip.plot.Coord.Dim([float, str]), cpip.plot.Coord.Dim([float, <class 'str'>])])]``

        :param attrs: Element attributes.
        :type attrs: ``dict({str : [str]})``

        :returns: ``NoneType``
        """
        super(SVGPolygon, self).__init__(theXmlStream, 'polygon', pointS, attrs)
    
class SVGText(XmlWrite.Element):
    """Text in SVG. See: http://www.w3.org/TR/2003/REC-SVG11-20030114/text.html#TextElement
    """
    def __init__(self, theXmlStream, thePoint, theFont, theSize, attrs=None):
        """Initialise the text with a stream, a :py:class:`cpip.plot.Coord.Pt` and font as a string and
        size as an integer. If thePoint is ``None`` then no location will be specified
        (for example for use inside a ``<defs>`` element.

        :param theXmlStream: The SVG stream.
        :type theXmlStream: :py:class:`cpip.plot.SVGWriter.SVGWriter`

        :param thePoint: Place to write the text.
        :type thePoint: ``cpip.plot.Coord.Pt([cpip.plot.Coord.Dim([float, str]), cpip.plot.Coord.Dim([float, <class 'str'>])])``

        :param theFont: Font.
        :type theFont: ``NoneType, str``

        :param theSize: Size
        :type theSize: ``NoneType, int``

        :param attrs: Element attributes.
        :type attrs: ``dict({str : [str]})``

        :returns: ``NoneType``
        """
        _attrs = {}
        if theFont is not None:
            _attrs['font-family'] = theFont
        if theSize is not None:
            _attrs['font-size'] = '%s' % theSize
        if thePoint is not None:
            _attrs['x'] = dimToTxt(thePoint.x)
            _attrs['y'] = dimToTxt(thePoint.y)
        if attrs:
            _attrs.update(attrs)
        super(SVGText, self).__init__(theXmlStream, 'text', _attrs)
