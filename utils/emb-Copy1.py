import logging

import math
import numpy as np
import pymap3d as pm3
from matplotlib import cm
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageChops

import utils.pyall as pa
import utils.shaded_relief as sr
import utils.geodetic


class Emb:
    """ 
    Emb, class to read Kongsberg's EchoSounder Multibeam .all sonar files (Revision R October 2013)
    
    Based on pyALL, available at https://github.com/pktrigg/pyall and created by p.kennedy@fugro.com.
    """
    def __init__(self, filename, logging_level=logging.INFO):
        self._filename = filename
        self._reader = pa.ALLReader(filename)
        self._x_res = 1
        self._y_res = 1  
        self._beam_count = 0
        self._distance_travelled = 0
        self._positioning_system = None
        self._navigation = []
        self._left_extents = 0
        self._right_extents = 0
        self._min_depth = float('Inf')
        self._max_depth = float('-Inf')   
        self._acrossMeans = np.array([])
        self._alongIntervals = np.array([])
        self._leftExtents    = np.array([])
        self._rightExtents   = np.array([])
        
        self._origin = None
        self._waterfall = []
        self._waterfall_nav = []
        self._total_record = None
        self._previous_latitude  = None
        self._previous_longitude = None
        
        logging.basicConfig(level=logging_level)
        self._logger = logging.getLogger(__name__)        

    def get_nav(self, enu=False):
        if len(self._navigation)==0:
            return None
        nav=np.array(self._navigation)
        if enu and len(self._navigation)>=5:
            return nav[:,4], nav[:, 5]
        else:            
            return nav[:,2], nav[:, 3]
       
    def set_nav(self, datagram, counter=0, add_enu=True):  
        """
        Read positioning information from a datagram of type 'P'.
        
        """
        if (self._positioning_system is None): self._positioning_system = datagram.Descriptor                        
        if self._origin is None: self._origin = np.array([datagram.Latitude, datagram.Longitude])
        if self._previous_latitude is None:
                self._previous_latitude  =  datagram.Latitude
                self._previous_longitude =  datagram.Longitude

        r, _, _  = utils.geodetic.calculateRangeBearingFromGeographicals(self._previous_longitude, self._previous_latitude, datagram.Longitude, datagram.Latitude)
        self._distance_travelled += r    
            
        nav = [counter, self._reader.currentRecordDateTime(), datagram.Heading, datagram.Latitude, datagram.Longitude]

        if add_enu:
            east, north, _ = pm3.geodetic2enu(datagram.Latitude, datagram.Longitude, 0, self._origin[0], self._origin[1], 0)

        self._navigation.append(np.array(nav+[east, north]))
        self._previous_latitude  =  datagram.Latitude
        self._previous_longitude =  datagram.Longitude

   
    def set_depth_line(self, datagram, counter=0, navigation=None):
        if datagram.NBeams > 1:                
            datagram.AcrossTrackDistance = [x for x in datagram.AcrossTrackDistance if x != 0.0]
            self._acrossMeans  = np.append(self._acrossMeans, np.average(abs(np.diff(np.asarray(datagram.AcrossTrackDistance)))))
                        
            self._beam_count = max(self._beam_count, len(datagram.Depth)) 
        
            data_depth = np.array(datagram.Depth) + np.array(datagram.TransducerDepth)

            # we need to remember the actual data extents so we can set the color palette mappings to the same limits. 
            self._min_depth = min(self._min_depth, np.min(data_depth))
            self._max_depth = max(self._max_depth, np.max(data_depth))
            self._waterfall.insert(0, data_depth)  
            self._waterfall_nav.insert(0, navigation)
            
    
    def read_datagrams(self, max_number=float('Inf')): 
        """
        Reads multibeam datagrams one at a time and fill up the relevant fields in the class.
        
        Arguments:
        - max_number: maximum number of datagrams to read if available. defaults is until the end of the file.
        
        Output:
        
        """
        self._logger.info(f'Start reading file: {self._filename}')

        dt = 1000 # only for printing        
        counter = 0
        while self._reader.moreData() and counter <= max_number:
            datagram_type, datagram = self._reader.readDatagram()
            self._logger.debug(f'datagram_type: {datagram_type} read.')
            
            if (datagram_type == 'P'):
                datagram.read()
                self.set_nav(datagram, counter)                

            if (datagram_type == 'X') or (datagram_type == 'D'):
                datagram.read()
                self.set_depth_line(datagram, counter, navigation=self._navigation[-1])
                
            counter  = counter + 1    
            if counter % dt == 0:
                if self._total_record is not None:
                    self._logger.debug('File read: {:.2f} % completed.       '.format(counter/self._total_record*100))                    
                else:
                    self._logger.debug('Records read: {:d}'.format(counter))

        self._x_res = np.average(self._acrossMeans)        
        self._y_res = self._distance_travelled / counter
        self._total_record = counter  
        self._logger.info(f'File {self._filename} read correctly.')            
    
    def read(self, add_enu=True):        
        dt = 1000 # only for printing
        
        prevLong = None
        prevLat  = None        
        p_counter  = 0
        counter  = 0
        acrossMeans    = np.array([])
        alongIntervals = np.array([])
        leftExtents    = np.array([])
        rightExtents   = np.array([])
        
        waterfall      = []
        
        while self._reader.moreData():
            datagram_type, datagram = self._reader.readDatagram()
            
            if (datagram_type == 'P'):
                datagram.read()

                if (self._positioning_system == None): self._positioning_system = datagram.Descriptor
                
                if (self._positioning_system == datagram.Descriptor):
                    p_counter +=1
                    
                    if prevLat is None:
                        prevLat  =  datagram.Latitude
                        prevLong =  datagram.Longitude
                        if self._origin is None: self._origin   = np.array([datagram.Latitude, datagram.Longitude])
                        
                    r, bearing1, bearing2  = geodetic.calculateRangeBearingFromGeographicals(prevLong, prevLat, datagram.Longitude, datagram.Latitude)

                    # print (range,bearing1)
                    self._distance_travelled += r
                    nav = [counter, self._reader.currentRecordDateTime(), datagram.Latitude, datagram.Longitude]
                    
                    if add_enu:
                        east, north, _ = pm3.geodetic2enu(datagram.Latitude, datagram.Longitude, 0, self._origin[0], self._origin[1], 0)
                        
                    self._navigation.append(nav+[east, north])
                    
                    prevLat  =  datagram.Latitude
                    prevLong =  datagram.Longitude

            if (datagram_type == 'X') or (datagram_type == 'D'):
                datagram.read()
                
                if datagram.NBeams > 1:                
                    datagram.AcrossTrackDistance = [x for x in datagram.AcrossTrackDistance if x != 0.0]
                    
                    if (len(datagram.AcrossTrackDistance) > 0):
                        acrossMeans  = np.append(acrossMeans, np.average(abs(np.diff(np.asarray(datagram.AcrossTrackDistance)))))
                        leftExtents  = np.append(leftExtents, min(datagram.AcrossTrackDistance))
                        rightExtents = np.append(rightExtents, max(datagram.AcrossTrackDistance))                        
                        self._beam_count = max(self._beam_count, len(datagram.Depth)) 
                    
                    data_depth = np.array(datagram.Depth) + np.array(datagram.TransducerDepth)
                    
#                     for d in range(len(datagram.Depth)):
#                         datagram.Depth[d] = datagram.Depth[d] + datagram.TransducerDepth

                                        
                    # we need to remember the actual data extents so we can set the color palette mappings to the same limits. 
                    self._min_depth = min(self._min_depth, np.min(data_depth))
                    self._max_depth = max(self._max_depth, np.max(data_depth))

                    waterfall.insert(0, data_depth)            

                    # we need to stretch the data to make it isometric, so lets use numpy interp routing to do that for us
                    # datagram.AcrossTrackDistance.reverse()
                    xp = np.array(datagram.AcrossTrackDistance) #the x distance for the beams of a ping.  we could possibly use the real values here instead todo
                    
                    # datagram.Depth.reverse()
                    # fp = data_depth #the depth list as a numpy array                    
                    # fp = geodetic.medfilt(fp,31)
                    # x = np.linspace(leftExtent, rightExtent, int(outputResolution)) #the required samples needs to be about the same as the original number of samples, spread across the across track range
            counter  = counter + 1    
            if counter % dt == 0:
                if self._total_record is not None:
                    print('\r {:.2f} % completed.       '.format(counter/self._total_record*100), end="")
                else:
                    print('\r {:d} records read...      '.format(counter), end="")

        self._x_res = np.average(acrossMeans)        
        self._y_res = self._distance_travelled / counter
        self._left_extents  = np.min(leftExtents)
        self._right_extents = np.max(rightExtents)
        self._total_record = counter
        print('\r {:f} % completed.   '.format(counter/self._total_record*100), end="")
        self._reader.rewind()
        print(f'Position datagrams: {p_counter}')
        return waterfall
    

    def close(self):
        self._reader.close()

    def show(self, colormap=None, shade_scale=1, zoom=1, palette=None, idxs=[0, -1]):
        if len(self._waterfall) <=0:
            print('Emb: run read_datagrams() first.') 
            return
                
        # we now need to interpolate in the along track direction so we have approximate isometry
        np_grid = np.array(self._waterfall[idxs[0]:idxs[1]])
        print(np_grid.shape)
        
        iso_stretch_factor = np.ceil((self._y_res/self._x_res) * zoom)
        stretched_grid = np.empty((0, int(len(np_grid) * iso_stretch_factor)))    
        print('here')
        
        print(np_grid.T.shape)
        
        for column in np_grid.T:
            y  = np.linspace(0, len(column), len(column) * int(iso_stretch_factor)) # the required samples
            yp = np.arange(len(column)) 
            w2 = np.interp(y, yp, column, left=0.0, right=0.0)
            # w2 = geodetic.medfilt(w2,7)

            stretched_grid = np.append(stretched_grid, [w2], axis=0)

        print('here2')            
        np_grid = stretched_grid
        np_grid = np.ma.masked_values(np_grid, 0.0)
        
        if palette==None:
            np_grid = np_grid.T * shade_scale * -1.0
            hs  = sr.calcHillshade(np_grid, 1, 45, 30)        
            img = Image.fromarray(hs).convert('RGBA')
        else:
            np_grid = np_grid.T
            
            cmrgb = cm.colors.ListedColormap(palette._colors, name='from_list', N=None) # calculate color height map
            
            colorMap = cm.ScalarMappable(cmap=cmrgb)
            colorMap.set_clim(vmin=self._min_depth, vmax=self._max_depth)
            
            colorArray = colorMap.to_rgba(np_grid, alpha=None, bytes=True)    
            colorImage = Image.frombuffer('RGBA', (colorArray.shape[1], colorArray.shape[0]), colorArray, 'raw', 'RGBA', 0, 1)
            # Create hillshade a little darker as we are blending it. we do not need to invert as we are subtracting the shade from the color image
            np_grid = np_grid * shade_scale 
            hs  = sr.calcHillshade(np_grid, 1, 45, 5)
            img = Image.fromarray(hs).convert('RGBA')
            
            # now blend the two images
            img = ImageChops.subtract(colorImage, img).convert('RGB')
     
        return img
        
    def waterfall_img(self, waterfall, colormap=None, shade_scale=1, zoom=1, palette=None):
        # we now need to interpolate in the along track direction so we have approximate isometry
        np_grid = np.array(waterfall)        
        iso_stretch_factor = np.ceil((self._y_res/self._x_res) * zoom)
        stretched_grid = np.empty((0, int(len(np_grid) * iso_stretch_factor)))    
        
        for column in np_grid.T:
            y  = np.linspace(0, len(column), len(column) * int(iso_stretch_factor)) # the required samples
            yp = np.arange(len(column)) 
            w2 = np.interp(y, yp, column, left=0.0, right=0.0)
            # w2 = geodetic.medfilt(w2,7)

            stretched_grid = np.append(stretched_grid, [w2], axis=0)

        np_grid = stretched_grid
        np_grid = np.ma.masked_values(np_grid, 0.0)
        
        if palette==None:
            np_grid = np_grid.T * shade_scale * -1.0
            hs  = sr.calcHillshade(np_grid, 1, 45, 30)        
            img = Image.fromarray(hs).convert('RGBA')
        else:
            np_grid = np_grid.T
            
            cmrgb = cm.colors.ListedColormap(palette._colors, name='from_list', N=None) # calculate color height map
            
            colorMap = cm.ScalarMappable(cmap=cmrgb)
            colorMap.set_clim(vmin=self._min_depth, vmax=self._max_depth)
            
            colorArray = colorMap.to_rgba(np_grid, alpha=None, bytes=True)    
            colorImage = Image.frombuffer('RGBA', (colorArray.shape[1], colorArray.shape[0]), colorArray, 'raw', 'RGBA', 0, 1)
            # Create hillshade a little darker as we are blending it. we do not need to invert as we are subtracting the shade from the color image
            np_grid = np_grid * shade_scale 
            hs  = sr.calcHillshade(np_grid, 1, 45, 5)
            img = Image.fromarray(hs).convert('RGBA')
            
            # now blend the two images
            img = ImageChops.subtract(colorImage, img).convert('RGB')
     
        return img
    