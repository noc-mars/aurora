import numpy as np
from datetime import datetime
from utils.constants import *

def depthToPressure(depth, density=1.025, g=9.80665):
    # pressure in kPa
    return depth*density*g

def kPaToDecibars(pressure):
    return pressure/10.
    
def soundVelocity(S, T, P0):
    """SOUND SPEED SEAWATER CHEN AND MILLERO 1977, JASA, 62, 1129-1135
     ----------------------------------------------------------
     UNITS:
       PRESSURE     P0    DECIBARS
       TEMPERATURE  T     DEG CELSIUS (IPTS-68)
       SALINITY     S     (PSS-78)
       SOUND SPEED  SVEL  METERS/SECOND
     ----------------------------------------------------------
     CHECKVALUE:
       SVEL=1731.995 M/S for S=40 (PSS-78), T=40 DEG C, P=10000 DBAR
     ----------------------------------------------------------
     Original fortran code is found in:
       UNESCO technical papers in marine science 44 (1983) -
       'Algorithms for computation of fundamental properties of seawater'
     ----------------------------------------------------------
     Translated to object pascal by:
       Dr. Jan Schulz, 21. May 2008, www.code10.info
       
     Translated to python by:
       Dr. Andrea Munafo, 40. Apr 2020, andrea.munafo@gmail.com
    """
    # SCALE PRESSURE TO BARS
    P  = P0 / 10;
    SR = np.sqrt(np.abs(S))

    # S**2 TERM
    D = 1.727e-3 - 7.9836e-6 * P

    # S**3/2 TERM
    B1 =  7.3637E-5 + 1.7945E-7 * T
    B0 = -1.922E-2  - 4.42E-5   * T
    B  = B0 + B1 * P

    # S**1 TERM
    A3 = (-3.389E-13    * T + 6.649E-12)  * T + 1.100E-10
    A2 = ((7.988E-12    * T - 1.6002E-10) * T + 9.1041E-9) * T - 3.9064E-7
    A1 = (((-2.0122E-10 * T + 1.0507E-8)  * T - 6.4885E-8) * T - 1.2580E-5) * T + 9.4742E-5
    A0 = (((-3.21E-8    * T + 2.006E-6)   * T + 7.164E-5)  * T - 1.262E-2)  * T + 1.389
    A  = ((A3 * P + A2) * P + A1) * P + A0

    # S**0 TERM
    C3 = (-2.3643E-12   * T + 3.8504E-10) * T - 9.7729E-9
    C2 = (((1.0405E-12  * T - 2.5335E-10) * T + 2.5974E-8) * T - 1.7107E-6)  * T + 3.1260E-5
    C1 = (((-6.1185E-10 * T + 1.3621E-7)  * T - 8.1788E-6) * T + 6.8982E-4)  * T + 0.153563
    C0 = ((((3.1464E-9  * T - 1.47800E-6) * T + 3.3420E-4) * T - 5.80852E-2) * T + 5.03711) * T + 1402.388
    C  = ((C3 * P + C2) * P + C1) * P + C0;

    # SOUND SPEED RETURN
    SVEL = C + (A + B * SR + D * S) * S

    return SVEL
 
    
def conductivityToSalinity(C, t, p):
    """
    Calculates Practical Salinity, SP, from conductivity, C, primarily
    using the PSS-78 algorithm.  Note that the PSS-78 algorithm for Practical
    Salinity is only valid in the range 2 < SP < 42.  If the PSS-78 algorithm
    produces a Practical Salinity that is less than 2 then the Practical
    Salinity is recalculated with a modified form of the Hill et al. (1986)
    formula. The modification of the Hill et al. (1986) expression is to ensure
    that it is exactly consistent with PSS-78 at SP = 2.  Note that the input
    values of conductivity need to be in units of mS/cm (not S/m).
    Parameters
    
    From https://github.com/TEOS-10/python-gsw/blob/master/gsw/gibbs/practical_salinity.py
    ----------
    C : array
        conductivity [mS cm :sup:`-1`]
    t : array
        in-situ temperature [:math:`^\circ` C (ITS-90)]
    p : array
        sea pressure [dbar]
        (i.e. absolute pressure - 10.1325 dbar)
    Returns
    -------
    SP : array
         Practical Salinity [psu (PSS-78), unitless]
    Examples
    --------
    TODO
    References
    ----------
    .. [1] Culkin and Smith, 1980:  Determination of the Concentration of
       Potassium Chloride Solution Having the Same Electrical Conductivity, at
       15C and Infinite Frequency, as Standard Seawater of Salinity 35.0000
       (Chlorinity 19.37394), IEEE J. Oceanic Eng, 5, 22-23.
    .. [2] Hill, K.D., T.M. Dauphinee & D.J. Woods, 1986: The extension of the
       Practical Salinity Scale 1978 to low salinities. IEEE J. Oceanic Eng.,
       11, 109 - 112.
    .. [3] IOC, SCOR and IAPSO, 2010: The international thermodynamic equation
       of seawater - 2010: Calculation and use of thermodynamic properties.
       Intergovernmental Oceanographic Commission, Manuals and Guides No. 56,
       UNESCO (English), 196 pp.  Appendix E.
    .. [4] Unesco, 1983: Algorithms for computation of fundamental properties
       of seawater.  Unesco Technical Papers in Marine Science, 44, 53 pp.
    """

    C, t, p = np.broadcast_arrays(C, t, p, subok=True)

    t68 = t * 1.00024
    ft68 = (t68 - 15) / (1 + k * (t68 - 15))

    # The dimensionless conductivity ratio, R, is the conductivity input, C,
    # divided by the present estimate of C(SP=35, t_68=15, p=0) which is
    # 42.9140 mS/cm (=4.29140 S/m), (Culkin and Smith, 1980).

    R = 0.023302418791070513 * C  # 0.023302418791070513 = 1./42.9140

    # rt_lc corresponds to rt as defined in the UNESCO 44 (1983) routines.
    rt_lc = c[0] + (c[1] + (c[2] + (c[3] + c[4] * t68) * t68) * t68) * t68
    Rp = (1 + (p * (e[0] + e[1] * p + e[2] * p ** 2)) /
         (1 + d[0] * t68 + d[1] * t68 ** 2 + (d[2] + d[3] * t68) * R))
    Rt = R / (Rp * rt_lc)

    #Rt[Rt < 0] = np.ma.masked
    Rtx = np.sqrt(Rt)

    SP = (a[0] + (a[1] + (a[2] + (a[3] + (a[4] + a[5] * Rtx) * Rtx) * Rtx) *
                  Rtx) * Rtx + ft68 *
          (b[0] + (b[1] + (b[2] + (b[3] + (b[4] + b[5] * Rtx) * Rtx) * Rtx) *
                   Rtx) * Rtx))

    # The following section of the code is designed for SP < 2 based on the
    # Hill et al. (1986) algorithm.  This algorithm is adjusted so that it is
    # exactly equal to the PSS-78 algorithm at SP = 2.

    I2, = np.nonzero(np.ravel(SP) < 2)
    if len(I2) > 0:
        Hill_ratio = Hill_ratio_at_SP2(t[I2])
        x = 400 * Rt[I2]
        sqrty = 10 * Rtx[I2]
        part1 = 1 + x * (1.5 + x)
        part2 = 1 + sqrty * (1 + sqrty * (1 + sqrty))
        SP_Hill_raw = SP[I2] - a[0] / part1 - b[0] * ft68[I2] / part2
        SP[I2] = Hill_ratio * SP_Hill_raw

    SP = np.maximum(SP, 0)  # Ensure that SP is non-negative.

    return SP


def eTimeToEpoch(eTime):
    eTime = [eTime] if (not isinstance(eTime, list) and not isinstance(eTime,np.ndarray)) else eTime
    epoch = []
    for et in eTime:
        utc_time = datetime.strptime(et, "%d-%b-%Y %H:%M:%S")
        epoch_time = (utc_time - datetime(1970, 1, 1)).total_seconds()
        epoch.append(epoch_time)
    return epoch

def epochToString(epoch):
    epoch = [epoch] if not isinstance(epoch, list) else epoch
    strings = []
    for e in epoch:
        strings.append(e.fromtimestamp(epoch).strftime('%c'))
    return strings