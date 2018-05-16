# -*- coding: utf-8 -*-
"""
/***************************************************************************
 qgsAzmDistOffset2LatLon
                                 A QGIS plugin
 Calculates lat, lon base on lat, lon reference pint and azimuth, distance and offset to second point
                              -------------------
        begin                : 2018-04-30
        git sha              : $Format:%H$
        copyright            : (C) 2018 by Paweł Strzelewicz
        email                : @
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
#from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtCore import *
from PyQt4.QtGui import QAction, QIcon, QMessageBox, QWidget
from qgis.core import *
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from qga_azm_dist_offset2latlon_dialog import qgsAzmDistOffset2LatLonDialog
import os.path

import re
import math
import datetime

""" This section contains general constants, function to perform validation of input data and calculations """

# Parameters of WGS84 ellipsoid
WGS84_A = 6378137.0         # semi-major axis of the WGS84 ellipsoid in m
WGS84_B = 6356752.314245    # semi-minor axis of the WGS84 ellipsoid in m
WGS84_F = 1 / 298.257223563 # flatttening of the WGS84 ellipsoid

# Special constants to use instead of False, to avoid ambigous where result of function might equal 0 and 
# and result of fucntion will be used in if statements etc.
VALID     = 'valid'
NOT_VALID = 'not_valid'

# Coordinate type constant
C_LAT = 'lat'
C_LON = 'lon'

""" Distance """

# Units of measure
UOM_M  = 'M'
UOM_KM = 'KM'
UOM_F  = 'FEET'
UOM_SM = 'SM'
UOM_NM = 'NM'

# Conversion factors
F_FEET2M = 0.3048   # Feet to meteres
F_NM2M   = 1852     # Nautical miles to meters
F_SM2M   = 1609.344 # Statue milse to meters

# Patern for distance regular expression
REGEX_DIST = re.compile(r'^\d+(\.\d+)?$') # examples of valid: 0, 0.000, 0.32, 123.455;, examples of invalid: -1.22, s555, 234s5

def validate_distance(d):
    """ Distance validation.
    :param d: string, distance to validate
    :return is_valid: constant VALID if distance is valid, constant NOT_VALID if distance is not valid (e.g distance is less than 0)
    """
    if REGEX_DIST.match(d):
        is_valid = VALID
    else:
        is_valid = NOT_VALID
    return is_valid

def distance2m(d, unit):
    """ Converts distance given in feet, nautical miles, statue miles etc. to distance in meters
    :param d: float, diatance
    :param unit: constant unit of measure, unit of measure
    :return d_m: float, distance in meters
    """
    if unit == UOM_M:
        d_m = d
    elif unit == UOM_KM:
        d_m = d * 1000
    elif unit == UOM_F:
        d_m = d * F_FEET2M
    elif unit == UOM_SM:
        d_m = d * F_SM2M
    elif unit == UOM_NM:
        d_m = d * F_NM2M
    
    return d_m

""" Azimuth, bearning """

REGEX_AZM_DD      = re.compile(r'^360(\.[0]+)?$|^3[0-5][0-9](\.\d+)?$|^[1-2][0-9]{2}(\.\d+)?$|^[1-9][0-9](\.\d+)?$|^\d(\.\d+)?$')
REGEX_MAGVAR_DD   = re.compile(r'^[EW]360(\.[0]+)?$|^[EW]3[0-5][0-9](\.\d+)?$|^[EW][1-2][0-9]{2}(\.\d+)?$|^[EW][1-9][0-9](\.\d+)?$|^[EW][1-9](\.\d+)?$|^[EW]0\.d+$|^0(\.0+)?$')

def validate_azm_dd(a):
    """ Azimuth in DD (decimal degrees) format validation.
    :param a: string, azimuth to validate
    :return is_valid: constant, VALID if a is valid azimuth, NOT_VALID if a is not valid azimuth
    """
    if REGEX_AZM_DD.match(a):
        is_valid = VALID
    else:
        is_valid = NOT_VALID
    return is_valid
    
def validate_magvar(mv):
    """ Magnetic variation validation.
    Format decimal degrees with E or W prefix (easter or western magnetic variation)
    """
    if REGEX_MAGVAR_DD.match(mv):
        try:
            magvar = float(mv)
            result = magvar  # Note: result is True, if result = float(mv) in this case = 0 which equal False!
        except ValueError:
            magvar = float(mv[1:])
            prefix = mv[0]
            if prefix == 'W':
                result = -magvar
            else:
                result = magvar
    else:
        result = NOT_VALID
    return result

""" Latitude, longitude formats """

# Patterns for differnet cooridnate formats
REGEX_LAT_DMS_shdp = re.compile(r'''^
                                (?P<hem>[NSns])               # Hemisphere indicator
                                (?P<deg>[0-8]\d|90)           # Degreess
                                (\s|-)                        # Delimiter
                                (?P<min>[0-5]\d)              # Minutes
                                (\s|-)                        # Delimiter
                                (?P<sec>[0-5]\d\.\d+|[0-5]\d) # Seconds and decimal seconds
                                $''', re.VERBOSE)
REGEX_LON_DMS_shdp = re.compile(r'''^
                                (?P<hem>[EeWw])                     # Hemisphere indicator
                                (?P<deg>[0-1][0-7]\d|0\d\d|180)     # Degreess
                                (\s|-)                              # Delimiter
                                (?P<min>[0-5]\d)                    # Minutes
                                (\s|-)                              # Delimiter
                                (?P<sec>[0-5]\d\.\d+|[0-5]\d)       # Seconds and decimal seconds
                                $''', re.VERBOSE)
                                
def lat_DMS_shdp2DD(lat):
    """ Converts coordinate givien in DMS space or hyphen delimited format, prefix with hemisphere indicator (NSWE) to decimal degrees
    :param dms: string, coordinate in DMS format
    :return result: float or constant NOT_VALID,  converted coordinates in decimal degrees format or NOT_VALID if format is not valid
    """
    if REGEX_LAT_DMS_shdp.match(lat):
        dms_group = REGEX_LAT_DMS_shdp.search(lat)
        h = dms_group.group('hem')        # Hemisphere
        d = int(dms_group.group('deg'))   # Degrees
        m = int(dms_group.group('min'))   # Minutes
        s = float(dms_group.group('sec')) # Seconds
        if d == 90 and (m > 0 or s > 0):  # Check if does not exceed 90 00 00.00
            result = NOT_VALID
        else:   # correct format - convert from DMS to DD
            result = ((s / 60) + m) / 60 + d
            if h in ['S', 's'] and result != 0:   # If hemisphere is south coordinate is negative 
                result = -result
    else:
        result = NOT_VALID
    return result
    
def lon_DMS_shdp2DD(lon):
    """ Converts coordinate givien in DMS space or hyphen delimited format, prefix with hemisphere indicator (NSWE) to decimal degrees
    :param dms: string, coordinate in DMS format
    :return result: float or constant NOT_VALID, converted coordinates in decimal degrees format or NOT_VALID if longitude is inavlid
    """
    if REGEX_LON_DMS_shdp.match(lon):
        dms_group = REGEX_LON_DMS_shdp.search(lon)
        h = dms_group.group('hem')        # Hemisphere
        d = int(dms_group.group('deg'))   # Degrees
        m = int(dms_group.group('min'))   # Minutes
        s = float(dms_group.group('sec')) # Seconds
        if d == 180 and (m > 0 or s > 0):   # Check if does not exceed 180 00 00.00
            result = NOT_VALID
        else: # correct format - convert from DMS to DD
            result = ((s / 60) + m) / 60 + d
            if h in ['W', 'w'] and result != 0 :   # if hemisphere is west coordinate is negative 
                result = -result
    else:
        result = NOT_VALID
    return result
    
def dd2dms_shdp(dd, c_type):
    """ Converts coordinate in DD (decimal degrees format) to DMS format space or hyphen delimited with hemisphere prefix
    :param dd: float, latitude or longitude in decimal degrees format
    :param c_type: coordinate type constant, 'LAT' for latitude, 'LON' for longitude
    Retrun:
        dms(string): latitude or longitude in DMS format
    """
    # if dd is < 0 remove sign '-'
    s_dd = str(dd)
    if s_dd[0] == '-':
        s_dd = s_dd[1:]
    
    d = int(math.floor(float(s_dd)))
    m = int(math.floor((float(s_dd) - d) * 60))
    s = (((float(s_dd) - d) * 60) - m) * 60
    
    if c_type == C_LAT:
        if d < 10:
            d = '0' + str(d)
        if m < 10:
            m = '0' + str(m)
        if s < 10:
            s = '0' + format(s, '.8f') 
 
        if dd >= 0:
            dms = 'N' + str(d) + ' ' + str(m) + ' ' + str(s)[0:5]
        else:
            dms = 'S' + str(d) + ' ' + str(m) + ' ' + str(s)[0:5]
    
    if c_type == C_LON:
        if d < 10:
            d = '00' + str(d)
        elif d < 100:
            d = '0' + str(d)
            
        if m < 10:
            m = '0' + str(m)
        if s < 10:
            s = '0' + format(s, '.8f') 
            
        if dd >= 0:
            dms = 'E' + str(d) + ' ' + str(m) + ' ' + str(s)[0:5]
        else:
            dms = 'W' + str(d) + ' ' + str(m) + ' ' + str(s)[0:5]
    return dms
    
""" Latitude, longitude computation on ellipsoid """

def vincenty_direct_solution(begin_lat, begin_lon, begin_azimuth, distance, a, b, f): 
    """ Computes the latitude and longitude of the second point based on latitude, longitude,
    of the first point and distance and azimuth from first point to second point.
    Uses the algorithm by Thaddeus Vincenty for direct geodetic problem.
    For more information refer to: http://www.ngs.noaa.gov/PUBS_LIB/inverse.pdf
    
    :param begin_lat: float, latitude of the first point; decimal degrees
    :param begin_lon: float, longitude of the first point; decimal degrees
    :param begin_azimuth: float, azimuth from first point to second point; decimal degrees
    :param distance: float, distance from first point to second point; meters
    :param a: float, semi-major axis of ellispoid; meters
    :param b: float, semi-minor axis of ellipsoid; meters
    :param f: float, flatttening of ellipsoid
    :return lat2_dd, lon2_dd: float, float latitude and longitude of the secon point, decimal degrees
    """
    # Convert latitude, longitude, azimuth of the begining point to radians
    lat1 = math.radians(begin_lat)
    lon1 = math.radians(begin_lon)
    alfa1 = math.radians(begin_azimuth)

    sinAlfa1 = math.sin(alfa1)
    cosAlfa1 = math.cos(alfa1)
    
    # U1 - reduced latitude
    tanU1 = (1 - f) * math.tan(lat1)
    cosU1 = 1 / math.sqrt(1 + tanU1 * tanU1)
    sinU1 = tanU1 * cosU1
    
    # sigma1 - angular distance on the sphere from the equator to begining point
    sigma1 = math.atan2(tanU1, math.cos(alfa1))
    
    # sinAlfa - azimuth of the geodesic at the equator
    sinAlfa = cosU1 * sinAlfa1
    cosSqAlfa = 1 - sinAlfa * sinAlfa
    uSq = cosSqAlfa * (a * a - b * b) / (b * b)
    A = 1 + uSq/16384 * (4096 + uSq * (-768 + uSq * (320 - 175 * uSq)))
    B = uSq/1024 * (256 + uSq * (-128 + uSq * (74 - 47 * uSq)))
    
    sigma = distance / (b * A)
    sigmap = 1
    
    while (math.fabs(sigma - sigmap) > 1e-12):
        cos2sigmaM = math.cos(2 * sigma1 + sigma)
        sinSigma = math.sin(sigma)
        cosSigma = math.cos(sigma)
        dSigma = B*sinSigma*(cos2sigmaM+B/4*(cosSigma*(-1+2*cos2sigmaM*cos2sigmaM)-B/6*cos2sigmaM*(-3+4*sinSigma*sinSigma)*(-3+4*cos2sigmaM*cos2sigmaM)))        
        sigmap = sigma
        sigma = distance / (b * A) + dSigma
    
    var_aux = sinU1 * sinSigma - cosU1 * cosSigma * cosAlfa1
    
    # Latitude of the end point in radians
    lat2 = math.atan2(sinU1 * cosSigma + cosU1 * sinSigma*cosAlfa1, (1 - f)*math.sqrt(sinAlfa * sinAlfa + var_aux*var_aux))
    
    lamb = math.atan2 (sinSigma * sinAlfa1, cosU1 * cosSigma - sinU1 * sinSigma * cosAlfa1)
    C = f / 16 * cosSqAlfa * (4 + f * (4 - 3 * cosSqAlfa))
    L = lamb - (1 - C) * f * sinAlfa *(sigma + C * sinSigma * (cos2sigmaM + C * cosSigma * (-1 + 2 * cos2sigmaM * cos2sigmaM)))
    # Longitude of the second point in radians
    lon2 = (lon1 + L +3*math.pi)%(2*math.pi) - math.pi
    
    # Convert to decimal degrees
    lat2_dd = math.degrees(lat2)  
    lon2_dd = math.degrees(lon2)
    
    return lat2_dd, lon2_dd
    
def dist_azm_orth_offset(ref_lat, ref_lon, ref_azm, dist, offset, offset_side):
    """ Calculates latitude and longitude of the second point base don latitude, longitude of the firts point, azimuth, distacne and offset
    Example: distance 1500 m, azimuth 45 degress and offset 500 meter left
    :param ref_lat: float, reference point latitude
    :param ref_lon: float, reference poitn longitude
    :param ref_azm: float, azimuth from reference point to intermediate point
    :param dist: float, distance in meters
    :param offset: float, offset distance in meteres
    :param offset_side: indicate offset side, 'LEFT' for left, 'RIGHT' for right
    :return lat2_dd, lon2_dd: float, second point latitude, longitude
    """
    # Calculate azimuth from intermediate point to second point
    if offset_side == 'LEFT':
        offset_azm = ref_azm - 90
    elif offset_side == 'RIGHT':
        offset_azm = ref_azm + 90
    # Normalize azm to [0,360] degrees
    if offset_azm < 0:
        offset_azm += 360
    elif offset_azm > 360:
        offset_azm -= 360
    
    # Calculate intermediate point latitude, longitude
    inter_lat_dd, inter_lon_dd = vincenty_direct_solution(ref_lat, ref_lon, ref_azm, dist, WGS84_A, WGS84_B, WGS84_F)
            
    # Calculate second point latitude, longitude, as referenc point use intermediate point
    lat2_dd, lon2_dd = vincenty_direct_solution(inter_lat_dd, inter_lon_dd, offset_azm, offset, WGS84_A, WGS84_B, WGS84_F)
    
    return lat2_dd, lon2_dd

class InputDataSet:
    """ Simple class for storing input data"""
    def __init__(self):
        self.r_lat = None
        self.r_lon = None
        self.r_mag = None
        self.o_lyr = ''
        self.ep_name = ''
        self.ep_azm = None
        self.ep_dist = None
        self.ep_offset = None
#        self.ep_offset_unit = ''
        self.ep_offset_side = ''
    def assign_values(self,r_lat, r_lon, r_mag, o_lyr, ep_name, ep_azm, ep_dist, ep_offset, ep_offset_side):
        self.r_lat = r_lat
        self.r_lon = r_lon
        self.r_mag = r_mag
        self.o_lyr = o_lyr
        self.ep_name = ep_name
        self.ep_azm = ep_azm
        self.ep_dist = ep_dist
        self.ep_offset = ep_offset
        self.ep_offset_side = ep_offset_side

# Initialize InputDataSet variables
input_data = InputDataSet()    
    
    
    
w = QWidget()    
    
class qgsAzmDistOffset2LatLon:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgisInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'qgsAzmDistOffset2LatLon_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)


        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&AzmDistOffset2LatLon')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'qgsAzmDistOffset2LatLon')
        self.toolbar.setObjectName(u'qgsAzmDistOffset2LatLon')

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('qgsAzmDistOffset2LatLon', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        # Create the dialog (after translation) and keep reference
        self.dlg = qgsAzmDistOffset2LatLonDialog()

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/qgsAzmDistOffset2LatLon/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'AzmDistOffset2LatLon'),
            callback=self.run,
            parent=self.iface.mainWindow())

        self.dlg.pbAddPoint.clicked.connect(self.add_point)
        
    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&AzmDistOffset2LatLon'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def get_dist_unit(self):
        """ Check which radio button is checked to get distance unit"""
        
        if self.dlg.rbDistM.isChecked():
            dist_unit = UOM_M
        elif self.dlg.rbDistKM.isChecked():
            dist_unit = UOM_KM
        elif self.dlg.rbDistFeet.isChecked():
            dist_unit = UOM_F
        elif self.dlg.rbDistNM.isChecked():
            dist_unit = UOM_NM
        elif self.dlg.rbDistSM.isChecked():
            dist_unit = UOM_SM
        
        return dist_unit
        
    def get_offest_unit(self):
        """ Check which radio button is checked to get offset unit"""
        if self.dlg.rbOffsetM.isChecked():
            offset_unit = UOM_M
        elif self.dlg.rbOffsetKM.isChecked():
            offset_unit = UOM_KM
        elif self.dlg.rbOffsetFeet.isChecked():
            offset_unit = UOM_F
        elif self.dlg.rbOffsetNM.isChecked():
            offset_unit = UOM_NM
        elif self.dlg.rbOffsetSM.isChecked():
            offset_unit = UOM_SM
        return offset_unit
        
    def get_offest_side(self):
        """ Check which radio button is checked to get offset side"""
        if self.dlg.rbSideLeft.isChecked():
            offset_side = 'LEFT'
        elif self.dlg.rbSideRight.isChecked():
            offset_side = 'RIGHT'
        return offset_side   
        
        
    def validate_input(self):
        """ Gets and validates if input data is correct"""
        global input_data
        val_result = True
        err_msg = ''
        # Assign input to variables
        rp_lat_dms = self.dlg.leRefLat.text()    # Latitude of the reference point
        rp_lon_dms = self.dlg.leRefLon.text()    # Longitude of the reference point
        rp_mv  = self.dlg.leRefMagVar.text()     # Magnetic variation of the reference point
        lyr_out = self.dlg.leLyrOut.text()       # Output layer
        ep_name = self.dlg.leEndPointName.text() # End (second) point name
        ep_azm  = self.dlg.leEndPointAzm.text()  # Azimuth to end (second) point
        ep_dist = self.dlg.leEndPointDist.text() # Distance to end (second) point
        ep_offset = self.dlg.leEndPointOffset.text() # Distance to end (second) point
        
        
        r_lat = lat_DMS_shdp2DD(rp_lat_dms)
        r_lon = lon_DMS_shdp2DD(rp_lon_dms)
        
        if r_lat == NOT_VALID:  
            err_msg += 'Enter latitude of reference point in correct format\n'
            val_result = False
 
        if r_lon == NOT_VALID:
            err_msg += 'Enter longitude of reference point in correct format\n'
            val_result = False
        
        if lyr_out == '':
            err_msg += 'Enter output layer name\n'
            val_result = False
        
        if ep_name == '':
            err_msg += 'Enter second point name\n'
            val_result = False
        
        if rp_mv == '': # Magnetic Variation not enetered - assume magnetic variation as 0.0, 
            r_mag = 0.0
        else:
            if validate_magvar(rp_mv) == NOT_VALID:
                err_msg += 'Enter magntic variation at the reference point in correct format, or leave blank if it is 0\n'
                val_result = False
            else: 
                r_mag = validate_magvar(rp_mv)

        if validate_azm_dd(ep_azm) == NOT_VALID:
            err_msg += 'Enter azimuth from reference point to end point in correct format\n'
            val_result = False
            
        if validate_distance(ep_dist) == NOT_VALID:
            err_msg += 'Enter distance from reference point to end point in correct format\n'
            val_result = False
        if validate_distance(ep_offset) == NOT_VALID:
            err_msg += 'Enter offset to end point in correct format\n'
            val_result = False
            
        if val_result == True:
            ep_azm = float(ep_azm) + r_mag # Correct by magnetic variation
            if ep_azm < 0: # Normalize azm to [0,360] Degrees
                ep_azm += 360
            # Check distance and offset unit, offset side
            ep_dist_unit = self.get_dist_unit()
            ep_offset_unit = self.get_offest_unit()
            ep_offset_side = self.get_offest_side()
            # Convert distance, offset to meters
            ep_dist_m = distance2m(float(ep_dist), ep_dist_unit)
            ep_offset_m = distance2m(float(ep_offset), ep_offset_unit)
            
            input_data.assign_values(r_lat, r_lon, r_mag, lyr_out, ep_name, ep_azm, ep_dist_m, ep_offset_m,  ep_offset_side)
        else:
            QMessageBox.critical(w, "Message", err_msg)
            
        return val_result
        
    def create_tmp_layer(self, l_name):
        """ Create temporary 'memory' layer to store results of calculations
        :param l_name: string, layer_name
        """
        l_name = l_name + '_tmp_memory'
        output_lyr = QgsVectorLayer('Point?crs=epsg:4326', l_name, 'memory')
        prov = output_lyr.dataProvider()
        output_lyr.startEditing()
        prov.addAttributes([QgsField("ID", QVariant.Int),
                            QgsField("NAME", QVariant.String),
                            QgsField("LAT_DMS", QVariant.String),
                            QgsField("LON_DMS", QVariant.String)])
        output_lyr.commitChanges()
        QgsMapLayerRegistry.instance().addMapLayers([output_lyr])
        return
    
    def add_point(self):
        global in_data
        if self.validate_input(): # If input data is correct
            ep_lat_dd, ep_lon_dd = dist_azm_orth_offset(input_data.r_lat, input_data.r_lon, input_data.ep_azm, input_data.ep_dist, 
                                                        input_data.ep_offset, input_data.ep_offset_side)
            ep_lat_dms = dd2dms_shdp(ep_lat_dd, C_LAT)
            ep_lon_dms = dd2dms_shdp(ep_lon_dd, C_LON)
            layers = self.iface.legendInterface().layers()
            layer_list = []   # List of layers in current (opened) QGIS project
            for layer in layers:
                layer_list.append(layer.name())
            if (input_data.o_lyr + '_tmp_memory') not in layer_list:
                self.create_tmp_layer(input_data.o_lyr)
                v_lyr = QgsVectorLayer('Point?crs=epsg:4326', input_data.o_lyr, 'memory')
                v_lyr = self.iface.activeLayer()
                v_lyr.startEditing()
                v_prov = v_lyr.dataProvider()
                feat = QgsFeature()
                # Add reference point to layer
                feat.setGeometry(QgsGeometry.fromPoint(QgsPoint(input_data.r_lon, input_data.r_lat)))      
                feat.setAttributes([0, 'REF_POINT', self.dlg.leRefLat.text(), self.dlg.leRefLon.text()])
                v_prov.addFeatures([feat])
                v_lyr.commitChanges()
                # Add calculated point to layer
                feat.setGeometry(QgsGeometry.fromPoint(QgsPoint(ep_lon_dd, ep_lat_dd)))      
                feat.setAttributes([0, input_data.ep_name, ep_lat_dms, ep_lon_dms])
                v_prov.addFeatures([feat])
                v_lyr.commitChanges()
                v_lyr.updateExtents() 
            elif (input_data.o_lyr + '_tmp_memory') in layer_list:
                v_lyr = QgsVectorLayer('Point?crs=epsg:4326', input_data.o_lyr, 'memory')
                v_lyr = self.iface.activeLayer()
                v_lyr.startEditing()
                v_prov = v_lyr.dataProvider()
                feat = QgsFeature()
                feat.setGeometry(QgsGeometry.fromPoint(QgsPoint(ep_lon_dd, ep_lat_dd)))      
                feat.setAttributes([0, input_data.ep_name, ep_lat_dms, ep_lon_dms])
                v_prov.addFeatures([feat])
                v_lyr.commitChanges()
                v_lyr.updateExtents() 
        return
        
    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass
