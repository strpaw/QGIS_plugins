# -*- coding: utf-8 -*-
"""
/***************************************************************************
 qgsCsvAzmDist2LatLon
                                 A QGIS plugin
 Calculates latitude, longitude based on reference point latitude, longitude
    and azimuth and distance stored in csv file
                              -------------------
        begin                : 2018-04-29
        git sha              : $Format:%H$
        copyright            : (C) 2018 by Paweł Strzelewicz
        email                : Q
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
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QMessageBox, QWidget
from qgis.core import *
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from qgs_csv_azm_dist2lat_lon_dialog import qgsCsvAzmDist2LatLonDialog
import os.path

import re
import math
import csv
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
REGEX_MAGVAR_DD      = re.compile(r'^\d+(\.d+)?$')

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
    result = VALID
    mag_var = None
    try:
        mag_var = float(mv)
        if (mag_var > 360) or (mag_var < -360):
            result = NOT_VALID
    except ValueError:
        try:
            prefix = mv[0]
            if REGEX_MAGVAR_DD.match(mv[1:]): # Check if there are only numbers > 0, eg. 1.5, not -1.5
                mag_var = float(mv[1:])
                if prefix == 'W':
                    result = -mag_var
                elif prefix == 'E':
                    result = mag_var
                else:
                    result = NOT_VALID
            else:
                result = NOT_VALID

            if (mag_var != None) and ((mag_var > 360) or (mag_var < -360)):
                result = NOT_VALID    
            
        except ValueError:
            result = NOT_VALID
            mag_var = None

    return result, mag_var

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

""" Validate azimuth or bearning and distacne """

def validate_azm_dist(azm, dist):
    is_valid = True
    err_msg = ''
    if validate_azm_dd(azm) == NOT_VALID:
        is_valid = False
        err_msg += '*Azimuth value error*'
    if validate_distance(dist) == NOT_VALID:
        is_valid = False
        err_msg += '*Distance value error*'
    return is_valid, err_msg

def check_csv_header(csv_f, header_to_check):
    """
    :param csv_f: csv file to check
    :param header_to_check: string, header to check
    :retun result: validation status, VALID if header_to_check parameter match to header in csv file, NOT_VALID otherwise
    """
    with open(csv_f, 'r') as csv_file:
        header_line = csv_file.readline()
        header_line = header_line.rstrip('\n')
        
    if header_line == header_to_check:
        result = VALID
    else:
        result = NOT_VALID
    return result
    
def tmp_layer_name():
    """ Creates temprary layer name, from current datie
    Temporary layer name format: YYYYMMDD_HHMMSS_tmp_memory 
    """
    curr_time = datetime.datetime.now()
    tmp_lyr_name = str(curr_time).replace('-', '')
    tmp_lyr_name = tmp_lyr_name.replace(':','')
    tmp_lyr_name = tmp_lyr_name.replace(' ', '_')
    tmp_lyr_name = tmp_lyr_name[:15]
    return tmp_lyr_name + '_tmp_memory'
    
class InputDataSet:
    """ Simple class for storing input data"""
    def __init__(self):
        self.r_lat = None
        self.r_lon = None
        self.r_mag = None
        self.f_in = ''
        self.f_out = ''
    def assign_values(self ,r_lat, r_lon, r_mag, f_in, f_out):
        self.r_lat = r_lat
        self.r_lon = r_lon
        self.r_mag = r_mag
        self.f_in = f_in
        self.f_out = f_out

# Initialize InputDataSet variables
input_data = InputDataSet()
     
w = QWidget()

class qgsCsvAzmDist2LatLon:
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
            'qgsCsvAzmDist2LatLon_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)


        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&csvAzmDist2LatLon')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'qgsCsvAzmDist2LatLon')
        self.toolbar.setObjectName(u'qgsCsvAzmDist2LatLon')

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
        return QCoreApplication.translate('qgsCsvAzmDist2LatLon', message)


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
        self.dlg = qgsCsvAzmDist2LatLonDialog()

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

        icon_path = ':/plugins/qgsCsvAzmDist2LatLon/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'csvAzmDist2LatLon'),
            callback=self.run,
            parent=self.iface.mainWindow())
        
        self.dlg.pbInCsv.clicked.connect(self.select_input_file)
        self.dlg.pbOutCsv.clicked.connect(self.select_output_file)
        self.dlg.pbCalc.clicked.connect(self.calculations)
    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&csvAzmDist2LatLon'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar
    
    
    def select_input_file(self):
        """ Select input csv file with data: ID of the point, azimuth, distance from refernce point to the current point """
        input_file = QFileDialog.getOpenFileName(self.dlg, "Select input file ", "", '*.csv')
        self.dlg.leInCsv.setText(input_file)
    
    def select_output_file(self):
        """ Select output csv file """
        output_file = QFileDialog.getSaveFileName(self.dlg, "Select output file ", "", '*.csv')
        self.dlg.leOutCsv.setText(output_file)
    
    def val_input(self):
        """ Gets and validates if input data is correct"""
        global in_data
        val_result = True
        err_msg = ''
        h_to_check = 'P_NAME;AZM_BRNG;DIST'
        # Assign input to variables
        rp_lat_dms = self.dlg.leRefLat.text()        # Latitude of the reference point
        rp_lon_dms = self.dlg.leRefLon.text()        # Longitude of the reference point
        rp_mv  = self.dlg.leRefMagVar.text()         # Magnetic variation of the reference point
        in_csv = self.dlg.leInCsv.text()             # Input csv file
        out_csv = self.dlg.leOutCsv.text()           # Output csv file
        
        r_lat = lat_DMS_shdp2DD(rp_lat_dms)
        r_lon = lon_DMS_shdp2DD(rp_lon_dms)
        
        if r_lat == NOT_VALID:  
            err_msg += 'Enter latitude of reference point in correct format\n'
            val_result = False
 
        if r_lon == NOT_VALID:
            err_msg += 'Enter longitude of reference point in correct format\n'
            val_result = False
            
        if rp_mv == '': # Magnetic Variation not enetered - assume magnetic variation as 0.0, 
            r_mag = 0.0
        else:
            if validate_magvar(rp_mv)[0] == NOT_VALID:
                err_msg = err_msg + 'Enter magntic variation at the reference point in correct format, or leave blank if it is 0\n'
                val_result = False
            else: 
                r_mag = float(validate_magvar(rp_mv)[1])
                
        if in_csv == '':
            err_msg += 'Choose input file\n'
            val_result = False
        else:
            if check_csv_header(in_csv, h_to_check) == NOT_VALID:
                err_msg += 'Inpute csv file header is not P_NAME;AZM_BRNG;DIST\n'
                val_result = False
                
        if out_csv == '':
            err_msg += 'Choose output file\n'
            val_result = False
        
            
        if val_result == True:
            input_data.assign_values(r_lat, r_lon, r_mag, in_csv, out_csv)
        else:
            QMessageBox.critical(w, "Message", err_msg)   
         
        return val_result
    
        
    def create_tmp_layer(self, l_name):
        """ Create temporary 'memory' layer to store results of calculations
        Args:
            l_name(string): layer name
        """
        output_lyr = QgsVectorLayer('Point?crs=epsg:4326', l_name, 'memory')
        prov = output_lyr.dataProvider()
        output_lyr.startEditing()
        prov.addAttributes([QgsField("ID", QVariant.Int),
                            QgsField("P_NAME", QVariant.String),
                            QgsField("LAT_DMS", QVariant.String),
                            QgsField("LON_DMS", QVariant.String)])
        output_lyr.commitChanges()
        QgsMapLayerRegistry.instance().addMapLayers([output_lyr])
    def csv_azmdist2latlon(self):
        """ Reads input file, calcutes, saves to output file"""
        global input_data
        err_msg = ''
        # Create temporary vector layer to store oytput points
        v_lyr_name = tmp_layer_name()       # Get layer name
        self.create_tmp_layer(v_lyr_name)
        # Set layer to active
        v_lyr = QgsVectorLayer('Point?crs=epsg:4326', v_lyr_name, 'memory')
        v_lyr = self.iface.activeLayer()
        # Enabale edititing
        v_lyr.startEditing()
        v_prov = v_lyr.dataProvider()
        feat = QgsFeature()
        
        out_csv_field_names = ['P_NAME', 'AZM_BRNG', 'DIST', 'LAT_DMS', 'LON_DMS', 'NOTES']
        with open(input_data.f_in, 'r') as in_csv:
            with open(input_data.f_out, 'w') as out_csv:
                reader = csv.DictReader(in_csv, delimiter = ';')
                writer = csv.DictWriter(out_csv, fieldnames = out_csv_field_names, delimiter = ';')
                for row in reader:
                    try: # Try to read line according to field names
                        azm_dist_valid, err_msg = validate_azm_dist(row['AZM_BRNG'], row['DIST'])
                        if azm_dist_valid: # azimuth or brng and distance are valid
                            # Correct azimuth by magnetic variation
                            azm = float(row['AZM_BRNG']) + input_data.r_mag
                            if azm < 0:
                                azm += 360
                            elif azm > 360:
                                azm -= 360
                            # Calculate second point latitude and longitude in decimal degress 
                            ep_lat_dd, ep_lon_dd = vincenty_direct_solution(input_data.r_lat, input_data.r_lon, azm, float(row['DIST']), WGS84_A, WGS84_B, WGS84_F)
                            # Convert to DMS format with hemisphere indicator as prefix
                            ep_lat_dms = dd2dms_shdp(ep_lat_dd, C_LAT)
                            ep_lon_dms = dd2dms_shdp(ep_lon_dd, C_LON)
                            # Write result to output file
                            writer.writerow({'P_NAME': row['P_NAME'],
                                        'AZM_BRNG': row['AZM_BRNG'],
                                        'DIST': row['DIST'],
                                        'LAT_DMS' : ep_lat_dms,
                                        'LON_DMS' : ep_lon_dms,
                                        'NOTES' : ''})
                            # Write result to temporary layer
                            end_point = QgsPoint(ep_lon_dd, ep_lat_dd)
                            feat.setGeometry(QgsGeometry.fromPoint(end_point))
                            feat.setAttributes([0, row['P_NAME'], ep_lat_dms, ep_lon_dms])
                            v_prov.addFeatures([feat])
                            v_lyr.commitChanges()
                        else: # azimuth or brng or distance is not valid write err_msg to NOTES
                            writer.writerow({'P_NAME': row['P_NAME'],
                                        'AZM_BRNG': row['AZM_BRNG'],
                                        'DIST': row['DIST'],
                                        'LAT_DMS' : '',
                                        'LON_DMS' : '',
                                        'NOTES' : err_msg})
                    except: # Row of csv does not match to field names in header
                        writer.writerow({'P_NAME': row['P_NAME'],
                                        'AZM_BRNG': row['AZM_BRNG'],
                                        'DIST': row['DIST'],
                                        'LAT_DMS' : '',
                                        'LON_DMS' : '',
                                        'NOTES' : 'Wrong CSV line'})
                        
        v_lyr.updateExtents()              
        return
    def calculations(self):
        if self.val_input():
            self.csv_azmdist2latlon()
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
