import numpy as np

#      We've got our DEM into python, we've projected our DEM onto a regular grid so that we can easily do some operations on it, and we've seen a little bit about how to use matplotlib to plot.  Now lets start actually doing some things.  In this post we'll calculate slope on the grid we just read in, and use that to create a hillshade. We will then superimpose that hillshade image on our slope map to create an image like the one above.  Specifically we're going to make a second order, or centered, finite-difference approximation of slope. We will calculate the hillshade grid using ESRI's algorithm. To check our work we'll plot both,  with some transparency on the hillshade so that it just gives the slope grid texture.

#      First lets, take a second to review this finite difference approximation.  We can approximate the first derivative at the point Y6 (dashed line) as the difference in the values of Y at the adjacent points (7 and 5) divided by the horizontal distance between those adjacent points.  Think about this as the slope (rise over run) of the little gray triangle in the figure below. Notice that as the spacing between out points increases, we will do an increasingly poor job of approximating the derivative in places where the function curves around a lot.  As mentioned above, this is a 'second-order' finite difference approximation, but we won't get into why this is. One thing that is handy about this approximation is that the slope calculation is centered on the point we are interested in, Y6 in the highlighted example. If we only looked at two neighboring points (e.g. Y7 and Y6) to approximate the first derivative, that approximation would instead be centered between these nodes. There are times that this is useful, but since we are dealing with georeferenced raster data, it would be nice to have the pixels of our slope grid centered at the same points as the original dataset.  To do this in basic python might look something like whats below. Notice that because we are using our neighbors to calculate slope, we can not calculate the slope for the first and final items in our array - leaving us with an array of slope thats two smaller than the one we started with.

def IterateCenteredSlope(y,dx):
    #Function to calculate second order finite difference
    dydx = []  # Initialize an empty list
    for i in range(1,len(y)-1):  # iterate through all pts not at boundaries
        # append the current slope calculation to the list
        dydx.append((y[i+1]-y[i-1])/(2*dx)) 
    return dydx

#  One thing you might notice about this operation, is that instead of going through the data point by point and differencing the neighboring points we can actually just subtract two vectors shifted in opposite directions.  This is shown schematically with the math in the top right of the figure above and it is an easily accomplished operation with numpy arrays. In python it might look something like this:
def npCenteredSlope(y,dx):
    # Where y is a numpy array,
    # Calculate slope by differencing shifted vectors
    dydx = (y[2:] - y[:-2])/(2*dx)
    return dydx

#  This is nice and clean, on large arrays it turns out to be a touch faster too (even after the overhead associated with turning your array into a numpy array.  Our grid is two dimensional, so we can calculate slope in both the row (y) and column (x) directions.  We can do this with the above technique after transforming our dataset to a numpy array (see pt2 near the end, gdalDataset.readAsArray().asType(np.float) ) with a function that looks something like this:
def calcFiniteSlopes(elevGrid, dx):
    # sx,sy = calcFiniteDiffs(elevGrid,dx)
    # calculates finite differences in X and Y direction using the 
    # 2nd order/centered difference method.
    # Applies a boundary condition such that the size and location 
    # of the grids in is the same as that out.

    # Assign boundary conditions
    Zbc = assignBCs(elevGrid)

    #Compute finite differences
    Sx = (Zbc[1:-1, 2:] - Zbc[1:-1, :-2])/(2*dx)
    Sy = (Zbc[2:,1:-1] - Zbc[:-2, 1:-1])/(2*dx)

    return Sx, Sy

#  Here I called a function that we have yet to define, 'assignBCs'. This function takes a numpy array and returns a numpy array that has an additional row and column before and after those specified in the input array. Its nice to create a seperate function for this, as we may want to get smarter with how we define our boundary conditions later. For now, since we are just trying to visualize slopes, lets just repeat the values on the edges of the array. This isn't a great approach (we'll fix it later) - but it only effects things at the margins. Here is what that would look like:
def assignBCs(elevGrid):
    # Pads the boundaries of a grid
    # Boundary condition pads the boundaries with equivalent values 
    # to the data margins, e.g. x[-1,1] = x[1,1]
    # This creates a grid 2 rows and 2 columns larger than the input

    ny, nx = elevGrid.shape  # Size of array
    Zbc = np.zeros((ny + 2, nx + 2))  # Create boundary condition array
    Zbc[1:-1,1:-1] = elevGrid  # Insert old grid in center

    #Assign boundary conditions - sides
    Zbc[0, 1:-1] = elevGrid[0, :]
    Zbc[-1, 1:-1] = elevGrid[-1, :]
    Zbc[1:-1, 0] = elevGrid[:, 0]
    Zbc[1:-1, -1] = elevGrid[:,-1]

    #Assign boundary conditions - corners
    Zbc[0, 0] = elevGrid[0, 0]
    Zbc[0, -1] = elevGrid[0, -1]
    Zbc[-1, 0] = elevGrid[-1, 0]
    Zbc[-1, -1] = elevGrid[-1, 0]

    return Zbc

#  Sweet, we've got ourselves a slope grid (well, two slope grids actually one in the x and y direction). Lets get to visualizing. ESRI nicely summarizes the calculation of hillshades on their website. This is how we could calculate one in python, using our newly created function to find slopes and given the dem, grid spacing, and information about the lighting angle:
def calcHillshade(elevGrid,dx,az,elev):
    #Hillshade = calcHillshade(elevGrid,az,elev)
    #Esri calculation for generating a hillshade, elevGrid is expected to be a numpy array

    # Convert angular measurements to radians
    azRad, elevRad = (360 - az + 90)*np.pi/180, (90-elev)*np.pi/180  
    Sx, Sy = calcFiniteSlopes(elevGrid, dx)  # Calculate slope in X and Y directions

    AspectRad = np.arctan2(Sy, Sx) # Angle of aspect
    SmagRad = np.arctan(np.sqrt(Sx**2 + Sy**2))  # magnitude of slope in radians

    return 255.0 * ((np.cos(elevRad) * np.cos(SmagRad)) + (np.sin(elevRad)* np.sin(SmagRad) * np.cos(azRad - AspectRad)))
