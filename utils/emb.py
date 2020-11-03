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
    
    This class is a thin wrappen on top of the open source pyALL.
    
    References:
    - pyALL: https://github.com/pktrigg/pyall.
    - https://www.kongsberg.com/globalassets/maritime/km-products/product-documents/160692_em_datagram_formats.pdf
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

    def __repr__(self):
        return f'Emb: \n' + \
        f'- x resolution (m): {self._x_res} \n' + \
        f'- y resolution (m): {self._y_res} \n' + \
        f'- min depth (m)   : {self._min_depth} \n' + \
        f'- max depth (m)   : {self._max_depth} \n' + \
        f'- datagram count  : {self._total_record} \n'
        
    def get_nav(self, enu=False):
        """
        Reads the navigation variable and returns it.
        
        Argument:
        - enu: boolean variable. If True, the function return ENU values. If False, Latitude, Longitudes values are returned as read from the raw stream.
        """
        if len(self._navigation)==0: 
            self._logging.warning('No navigation data is available. Have you run read_datagrams()?')
            return None
        
        nav=np.array(self._navigation)
        if enu and len(self._navigation)>=5:
            return nav[:,4], nav[:, 5]
        else:            
            return nav[:,2], nav[:, 3]
       
    def set_nav(self, datagram, counter=0, add_enu=True):  
        """
        Read positioning information from a datagram of type 'P' and updates the navigation variable in the class.        
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
        """
        Read depth from a datagram and updates relevant class variables.
        """        
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
        - self._x_res: updates the average resolution across track. 
        - self._y_res: updates the average resolution along track.
        - self._total_record: updates the total number of records read.        
        """
        self._logger.info(f'Start reading file: {self._filename}')

        counter = 0
        while self._reader.moreData() and counter <= max_number:
            datagram_type, datagram = self._reader.readDatagram()
            self._logger.debug(f'datagram_type: {datagram_type} read.')
            
            if (datagram_type == 'P'):
                datagram.read()
                self.set_nav(datagram, counter)                

            if (datagram_type == 'X') or (datagram_type == 'D'):
                datagram.read()
                if len(self._navigation)>0:
                    nav = self._navigation[-1]
                else:
                    nav = None
                self.set_depth_line(datagram, counter, navigation=nav)
                
            counter  = counter + 1    
            if counter % 10000 == 0:
                if self._total_record is not None:
                    self._logger.debug('File read: {:.2f} % completed.       '.format(counter/self._total_record*100))                    
                else:
                    self._logger.debug('Records read: {:d}'.format(counter))

        self._x_res = np.average(self._acrossMeans)        
        self._y_res = self._distance_travelled / counter
        self._total_record = counter  
        self._logger.info(f'File {self._filename} read correctly.')                        

    def close(self):
        """
        Close the current reader.
        """
        self._reader.close()

    def show(self, shade_scale=1, zoom=1, palette=None, idxs=[0, -1]):
        """
        Funtion that shows a waterfall image of the read datagrams.
        No processing is done, and the resulting image only shows the raw data.
        
        Arguments:
        - shade_scale: used to scale the colormap (default: 1)
        - zoom: define the zoom level (default: 1)
        - palette: defines a color palette (see also palette.py). If None, a grey scale palette is used.
        - idxs: tuple that defines the start and end indices of the data to use. (default: [0,-1], i.e. all data is used).
        
        Output:
        - img (PIL)
        """
        
        if len(self._waterfall) <=0:
            self._logger.error('No data available. Please run read_datagrams() first.') 
            return
                
            
        if idxs[0] >= len(self._waterfall):
            self._logger.error(f'Data available are {len(self._waterfall)}. Please select idxs values to be between 0 and {len(self._waterfall)}.') 
            return
        
        # As suggested in PyAll, we interpolate along track to have an approximate isometry
        np_grid = np.array(self._waterfall[idxs[0]:idxs[1]])
        
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
            # Gray scale
            np_grid = np_grid.T * shade_scale * -1.0
            hs  = sr.calcHillshade(np_grid, 1, 45, 30)        
            img = Image.fromarray(hs).convert('RGBA')
        else:
            # Use the selected Palette
            np_grid = np_grid.T            
            cmrgb = cm.colors.ListedColormap(palette._colors, name='from_list', N=None) # calculate color height map
            
            colorMap = cm.ScalarMappable(cmap=cmrgb)
            colorMap.set_clim(vmin=self._min_depth, vmax=self._max_depth)
            
            colorArray = colorMap.to_rgba(np_grid, alpha=None, bytes=True)    
            colorImage = Image.frombuffer('RGBA', (colorArray.shape[1], colorArray.shape[0]), colorArray, 'raw', 'RGBA', 0, 1)
            # Again, following pyAll, we create hillshade a little darker as we are blending it. 
            # No need to invert as we are subtracting the shade from the color image
            np_grid = np_grid * shade_scale 
            hs  = sr.calcHillshade(np_grid, 1, 45, 5)
            img = Image.fromarray(hs).convert('RGBA')
            
            # Blends the two images
            img = ImageChops.subtract(colorImage, img).convert('RGB')
     
        return img
        
    