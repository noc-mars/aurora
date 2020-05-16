import csv
import utils.geodetic
import math
from matplotlib import cm
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageChops 
import numpy as np

class Palette:
    def __init__(self, filename):
        """
        Reads a .pal file and convert it to a list of n*RGB values
        
        Based on pyALL, available at https://github.com/pktrigg/pyall and created by p.kennedy@fugro.com.
        """
        colors = []
        with open(filename,'r') as f:
            next(f) # skip headings
            next(f) # skip headings
            next(f) # skip headings
            reader=csv.reader(f, delimiter='\t')
            for red,green,blue in reader:
                thiscolor = [float(red)/255.0, float(green) / 255.0, float(blue) / 255.0]
                colors.append(thiscolor)

        # now interpolate the colors so we have a broader spectrum
        reds = [ seq[0] for seq in colors ]
        x  = np.linspace(1, len(reds), 256) #the desied samples needs to be about the same as the original number of samples
        xp = np.linspace(1, len(reds), len(reds)) #the actual sample spacings
        newReds = np.interp(x, xp, reds, left=0.0, right=0.0)

        greens = [ seq[1] for seq in colors ]
        x = np.linspace(1, len(greens), 256) #the desied samples needs to be about the same as the original number of samples
        xp = np.linspace(1, len(greens), len(greens)) #the actual sample spacings
        newGreens = np.interp(x, xp, greens, left=0.0, right=0.0)

        blues = [ seq[2] for seq in colors ]
        x = np.linspace(1, len(blues), 256) #the desied samples needs to be about the same as the original number of samples, spread across the across track range
        xp = np.linspace(1, len(blues), len(blues)) #the actual sample spacings
        newBlues = np.interp(x, xp, blues, left=0.0, right=0.0)

        colors = []
        for i in range(0,len(newReds)):
            colors.append([newReds[i], newGreens[i], newBlues[i]])
        self._colors = colors
        