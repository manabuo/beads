#!/usr/bin/env python

# ----------------------------------------------------------------------------
# "THE BEER-WARE LICENSE" (Revision 42):
# <kn@insecurity.dk> wrote this file.  As long as you retain this notice you
# can do whatever you want with this stuff. If we meet some day, and you think
# this stuff is worth it, you can buy me a beer in return.   Kim Nielsen
# ----------------------------------------------------------------------------

import sys, time, getopt
from PIL import Image, ImageFilter, ImageDraw
from colormath.color_diff import delta_e_cie2000
from colormath.color_objects import sRGBColor, LabColor
from colormath.color_conversions import convert_color
from datetime import timedelta
import math

__version__ = 1.6

""" Fast but inaccurate way to find the distance between 2 colors """
def colordistance(color1, color2):
    return abs( color1[0] - color2[0] ) + abs( color1[1] - color2[1] ) + abs ( color1[2] - color2[2] )

""" help """
def help():
    print "Beads version %s" % __version__
    print "Option:"
    print "-h\t this help"
    print "-q\t be quiet and do not display progress"
    print "-f\t Use a fast way to find the best suited bead. Only used when using a list of beadcolors"
    print "-i\t Specify a input file"
    print "-x\t Set xgrid facter. Default set to 16"
    print "-y\t Set ygrid facter. Default set to 16"
    print "-b\t Specify a input file for beadcolors"
    print "-o\t Output file for final product"
    print "-m\t Mode. Default drawing is a box but if you add beads it will draw with beads"
    print "-c\t background color. Default is 0,0,0 (Black)"
    print "\nExample: ./beads.py -i donald.jpg -b hama.txt -f -o donald_hama.jpg"
    sys.exit(0)

""" Return seconds in days, hours etc """
def epochtoestimated(sec):
    a = timedelta(seconds=sec)

    ret = ''
    days = "%d day(s)" % (a.days)
    hours = "%d hour(s)" % (a.seconds/3600)
    mins = "%d min(s)" % ((a.seconds / 60) % 60)
    secs = "%d sec(s)" % (a.seconds % 60)

    if (a.days > 0):
        ret = ret + days

    if ((a.seconds/3600) > 0):
        if ret!='':
            ret = ret + ","
        ret = ret + hours

    if (((a.seconds / 60) % 60) > 0):
        if ret!='':
            ret = ret + ","
        ret = ret + mins

    if ((a.seconds % 60) > 0):
        if ret!='':
            ret = ret + ","
        ret = ret + secs

    return ret

""" Progress indicater """
def showprogress(cur_val, end_val, start_time, bar_length=20):
    cur_time =  time.time()

    elapsed = cur_time - start_time
    elapsedblock = cur_val / elapsed

    estimated = (end_val - cur_val) / elapsedblock

    percent = float(cur_val) / end_val
    hashes = '#' * int(round(percent * bar_length))
    spaces = ' ' * (bar_length - len(hashes))
    sys.stdout.write("\rPercent: [{0}] {1}% {2}/{3} ETA {4}                           ".format(hashes + spaces, int(round(percent * 100)),cur_val, end_val, epochtoestimated(estimated)))
    sys.stdout.flush()

""" Turn an image into a mosaic to turn in into a beads image """
def beads(image, beadcolors={}, fastcolor=False, progress=True, xgrid=8, ygrid=8, output='', mode='box', bgcolor=(0,0,0)):

    predefinedcolors = False
    if len(beadcolors):
        predefinedcolors = True

    start_time =  time.time()
    o = Image.open(image)

    if o.mode!='RGB':
        print "Mode: %s not supported" % (o.mode)
        sys.exit(1)

    orig = o.convert('P', palette=Image.ADAPTIVE).convert('RGB')

    optimalx = int(orig.width/xgrid)*xgrid
    optimaly = int(orig.height/ygrid)*ygrid
    im = Image.new(orig.mode, (optimalx,optimaly), bgcolor)

    xblocks = orig.width/xgrid
    yblocks = orig.height/ygrid

    blockpixels = xgrid*ygrid
    numblocks = xblocks*yblocks

    ystart = 0
    blocks = 0
    for y in xrange(0,yblocks):
        xstart = 0
        for x in xrange(0,xblocks):
            box = (xstart, ystart, xstart+xgrid, ystart+ygrid)
            region = orig.crop(box)

            ravg, gavg, bavg = 0, 0, 0
            for yr in xrange(0,region.height):
                for xr in xrange(0,region.width):
                    travg, tgavg, tbavg = region.getpixel((xr,yr))
                    ravg+=travg
                    gavg+=tgavg
                    bavg+=tbavg

            nr, ng, nb = (ravg/blockpixels), (gavg/blockpixels), (bavg/blockpixels)

            if predefinedcolors:
                index = beadcolors.keys()[0]
                if fastcolor:
                    closest = colordistance((nr, ng, nb), (beadcolors[index][0], beadcolors[index][1], beadcolors[index][2]))
                else:
                    rgblab = convert_color(sRGBColor( nr, ng, nb), LabColor)
                    closest = delta_e_cie2000(rgblab, convert_color(sRGBColor( beadcolors[index][0], beadcolors[index][1], beadcolors[index][2] ), LabColor))

                for key in beadcolors:
                    hr = beadcolors[key][0]
                    hg = beadcolors[key][1]
                    hb = beadcolors[key][2]

                    if fastcolor:
                        delta = colordistance((nr, ng, nb), (hr, hg, hb))
                    else:
                        beadlab = convert_color(sRGBColor( hr, hg, hb ), LabColor)
                        delta = delta_e_cie2000(rgblab, beadlab)

                    if delta < closest:
                        index = key
                        closest = delta

                nr, ng, nb = beadcolors[index][0], beadcolors[index][1], beadcolors[index][2]

            """ Clean canvas """
            regionout = Image.new(region.mode, region.size, bgcolor)
            if mode=='beads':
                d = ImageDraw.Draw(regionout)
                r=0
                d.ellipse((0-r, 0-r, region.width+r, region.height+r), fill=(nr, ng, nb))
                r=-1*(math.sqrt(region.width*2))
                d.ellipse((0-r, 0-r, region.width+r, region.height+r), fill=bgcolor)
            else:
                for yr in xrange(0,region.height):
                    for xr in xrange(0,region.width):
                        regionout.putpixel((xr,yr),(nr, ng, nb))
 
            im.paste(regionout, box)
            blocks+=1
            if progress:
                showprogress(blocks, numblocks, start_time)

            xstart+=xgrid
        ystart+=ygrid

    if mode!='beads':
        d = ImageDraw.Draw(im)
        for y in xrange(0,im.height,ygrid):
            for x in xrange(0,im.width,xgrid):
                d.line((x,y,im.height,y),fill=bgcolor)
                d.line((x,0,x,im.height),fill=bgcolor)
        d.line((im.width-1,0,im.width-1,im.height),fill=bgcolor)

    if output=='':
        im.show()
    else:
        if output!=image:
            im.save(output)
    print ""

if __name__ == "__main__":

    xgrid, ygrid = 16, 16
    image = ''
    output = ''
    bgcolor = (0,0,0)
    bgcolortmp = ''
    progress = True
    fastcolor = False
    beadsfile = ''
    mode = 'box'
    argv = sys.argv[1:]
    opts, args = getopt.getopt(argv,"hqfi:x:y:b:o:m:c:",[])
    for opt, arg in opts:
        if opt =='-h':
            help()
        if opt in ('-q'):
            progress = False
        if opt in ('-x'):
            xgrid = int(arg)
        if opt in ('-y'):
            ygrid = int(arg)
        if opt in ('-f'):
            fastcolor = True
        if opt in ('-b'):
            beadsfile = arg
        if opt in ('-i'):
            image = arg
        if opt in ('-m'):
            mode = arg
        if opt in ('-c'):
            bgcolortmp = arg
            tmp = bgcolortmp.split(',')
            bgcolor = (int(tmp[0]), int(tmp[1]), int(tmp[2]))
        if opt in ('-o'):
            output = arg

    if beadsfile=='':
        beadslist = {}
    else:
        beadslist = eval(open(beadsfile).read())

    if image=='':
        print "No input image specified\n"
        help()

    beads(image, beadslist, fastcolor, progress, xgrid, ygrid, output, mode, bgcolor)

