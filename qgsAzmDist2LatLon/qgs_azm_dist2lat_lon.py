# -*- coding: utf-8 -*-
"""
/***************************************************************************
 qgsAzmDist2LatLon
                                 A QGIS plugin
 Calculates second point latitude, longitude based on first point latitude, longitude and azimuth and distance from first point to second point
                              -------------------
        begin                : 2018-04-28
        git sha              : $Format:%H$
        copyright            : (C) 2018 by Pawel Strzelewicz
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
from qgs_azm_dist2lat_lon_dialog import qgsAzmDist2LatLonDialog
import os.path

import re
import math

""" This section contains general constants, function to perform validation of input data and calculations
"""
# Parameters of WGS84 ellipsoid
WGS84_A = 6378137.0         # semi-major axis of the WGS84 ellipsoid in m
WGS84_B = 6356752.314245    # semi-minor axis of the WGS84 ellipsoid in m
WGS84_F = 1 / 298.257223563 # flatttening of the WGS84 ellipsoid

# Latitude, longitude format
F_DMS_shdp  = 'DMS_shdp' # DMS, space or hyphen delimited with prefix, N52 13 56.00, N52-13-56.00

# Patterns for regular expressions
REGEX_DIST        = re.compile(r'^\d+(\.\d+)?$')
REGEX_AZM_DD      = re.compile(r'^360(\.[0]+)?$|^3[0-5][0-9](\.\d+)?$|^[1-2][0-9]{2}(\.\d+)?$|^[1-9][0-9](\.\d+)?$|^\d(\.\d+)?$')
REGEX_MAGVAR_DD   = re.compile(r'^[EW]360(\.[0]+)?$|^[EW]3[0-5][0-9](\.\d+)?$|^[EW][1-2][0-9]{2}(\.\d+)?$|^[EW][1-9][0-9](\.\d+)?$|^[EW][1-9](\.\d+)?$|^[EW]0\.d+$|^0(\.0+)?$')
REGEX_LAT_DMS_shdp = re.compile(r'''^
                                (?P<hem>[NSns])               # Hemisphere indicator
                                (?P<deg>[0-8]\d|90)           # Degreess
                                (\s|-)                        # Delimiter
                                (?P<min>[0-5]\d)              # Minutes
                                (\s|-)                        # Delimiter
                                (?P<sec>[0-5]\d\.\d+|[0-5]\d) # Seconds and decimal seconds
                                $''', re.VERBOSE)
REGEX_LON_DMS_shdp = re.compile(r'''^
                                (?P<hem>[EeWw])               # Hemisphere indicator
                                (?P<deg>[0-1][0-7]\d|180)     # Degreess
                                (\s|-)                        # Delimiter
                                (?P<min>[0-5]\d)              # Minutes
                                (\s|-)                        # Delimiter
                                (?P<sec>[0-5]\d\.\d+|[0-5]\d) # Seconds and decimal seconds
                                $''', re.VERBOSE)

def validate_distance(d):
    """ Distance validation.
    Arg:
        d(float): distance to validate
   
    Returns:
        is_valid(bool): True if distance is valid, False if distance is not valid (e.g distance is less than 0)
    """
    if REGEX_DIST.match(d):
        is_valid = True
    else:
        is_valid = False
    return is_valid
    
def validate_azm_dd(a):
    """ Azimuth in DD (decimal degrees) format validation.
    Args:
        a(float):   azimuth to validate
    Return:
        is_valid(bool): True if azimuth is valid value (e. g. 355.47), False if azimuth is invalid
    """
    if REGEX_AZM_DD.match(a):
        is_valid = True
    else:
        is_valid = False
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
        result = 'NOT_VALID'
    return result
    
def lat_DMS_shdp2DD(lat):
    """ Converts coordinate givien in DMS space or hyphen delimited format to decimal degrees.
    If input parameter is not in DMS_shdp format, returns False
  
    indicator as prefix, e. g. N52 13 56.00, N52-13-56.00
    Args:
        lat(string): string to validation
    Return:
        decimal degress of the latitud or False if input parameter has wrong format
    """
    if REGEX_LAT_DMS_shdp.match(lat):
        dms_group = REGEX_LAT_DMS_shdp.search(lat)
        d = int(dms_group.group('deg'))   # Degrees
        m = int(dms_group.group('min'))   # Minutes
        s = float(dms_group.group('sec')) # Seconds
        if d == 90 and (m > 0 or s > 0):  # Check if does not exceed 90 00 00.00
            result = False
        else:   # correct format - convert from DMS to DD
            h = lat[0]  # get hemispehere prefix
            result = ((s / 60) + m) / 60 + d
            if h in ['S', 's']:   # if hemisphere is south coordinate is negative 
                result = -result
    else:
        result = False
    return result
 
def lon_DMS_shdp2DD(lon):
    """ Validates if latitude is in DMS format, space or hyphen separated, with hemisphere 
    indicator as prefix, e. g. N52 13 56.00, N52-13-56.00
    Args:
        lat(string): string to validation
    Return:
        is_valid(bool): True if (lon) string is valid longitude, False if (lat) string is not valid
    """
    if REGEX_LON_DMS_shdp.match(lon):
        dms_group = REGEX_LON_DMS_shdp.search(lon)
        d = int(dms_group.group('deg'))   # Degrees
        m = int(dms_group.group('min'))   # Minutes
        s = float(dms_group.group('sec')) # Seconds
        if d == 180 and (m > 0 or s > 0):   # Check if does not exceed 180 00 00.00
            result = False
        else: # correct format - convert from DMS to DD
            h = lon[0]  # get hemispehere prefix
            result = ((s / 60) + m) / 60 + d
            if h in ['W', 'w']:   # if hemisphere is west coordinate is negative 
                result = -result
    else:
        result = False
    return result

def dd2dms_sd_prefix(dd, c_type):
    """ Converts coordinate in DD (decimal degrees format) to DMS format space delimited
    Args:
        dd(float): latitude or longitude in decimal degrees format
        c_type(string): cooridnate type, 'LAT' for latitude, 'LON' for longitude
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
    
    if c_type == 'LAT':
        if d < 10:
            d = '0' + str(d)
        if m < 10:
            m = '0' + str(m)
        if s < 10:
            s = '0' + str(s) 
 
        if dd >= 0:
            dms = 'N' + str(d) + ' ' + str(m) + ' ' + str(s)[0:5]
        else:
            dms = 'S' + str(d) + ' ' + str(m) + ' ' + str(s)[0:5]
    
    if c_type == 'LON':
        if d < 10:
            d = '00' + str(d)
        elif d < 100:
            d = '0' + str(d)
            
        if m < 10:
            m = '0' + str(m)
        if s < 10:
            s = '0' + str(s)
            
        if dd >= 0:
            dms = 'E' + str(d) + ' ' + str(m) + ' ' + str(s)[0:5]
        else:
            dms = 'W' + str(d) + ' ' + str(m) + ' ' + str(s)[0:5]
    return dms

def vincenty_direct_solution(begin_lat, begin_lon, begin_azimuth, distance, a, b, f): 
    """ Computes the latitude and longitude of the second point based on latitude, longitude,
    of the first point and distance and azimuth from first point to second point.
    Uses the algorithm by Thaddeus Vincenty for direct geodetic problem.
    For more information refer to: http://www.ngs.noaa.gov/PUBS_LIB/inverse.pdf
    
    Args:
        begin_lat (float)   : latitude of the first point; decimal degrees
        begin_lon (float)   : longitude of the first point; decimal degrees
        begin_azimuth(float): azimuth from first point to second point; decimal degrees
        distance(float)     :  distance from first point to second point; meters
        a (float) : semi-major axis of ellispoid; meters
        b (float) : semi-minor axis of ellipsoid; meters
        f (float) : flatttening of ellipsoid
    
    Returns:
        lat2_dd (float): latitude of the second point; decimal degrees
        lon2_dd (float): longitude of the second point; decimal degrees
    """
    # Convert latitude, longitude, azimuth of the begining point to radians
    lat1 = math.radians(begin_lat)
    lon1 = math.radians(begin_lon)
    alfa1 = math.radians(begin_azimuth)

    # U1 - reduced latitude
    tanU1 = (1 - f) * math.tan(lat1)
    cosU1 = 1 / math.sqrt(1 + tanU1 * tanU1)
    sinU1 = tanU1 * cosU1
    
    # sigma1 - angular distance on the sphere from the equator to begining point
    sigma1 = math.atan2(tanU1, math.cos(alfa1))
    
    # sinAlfa - azimuth of the geodesic at the equator
    sinAlfa = cosU1 * math.sin(alfa1)
    cosSqAlfa = 1 - sinAlfa * sinAlfa
    uSq = cosSqAlfa * (a * a - b * b) / (b * b)
    
    A = 1 + (uSq * (4096 + uSq * (-768 + uSq * (320 - 175 * uSq)))) / 16384
    B = (uSq * (256 + uSq * (-128 + uSq * (74 - 47 * uSq)))) / 1024
    
    sigma = distance / (b * A)
    sigmap = 1
    
    while (math.fabs(sigma - sigmap) > 1e-13):
        cos2sigmaM = math.cos(2 * sigma1 + sigma)
        dsigma = B * math.sin(sigma)*(cos2sigmaM + B*(cos2sigmaM*(-1 + 2 * cos2sigmaM * cos2sigmaM)-B*(cos2sigmaM*(-3 + 4 * math.sin(sigma) * math.sin(sigma))*(-3 + 4 *cos2sigmaM*cos2sigmaM))/6)/4)
        sigmap = sigma
        sigma = distance / (b * A) + dsigma
    
    var_aux = (sinU1 * math.sin(sigma) - cosU1 * math.cos(sigma) * math.cos(alfa1)) * (sinU1 * math.sin(sigma) - cosU1 * math.cos(sigma) * math.cos(alfa1))
    
    # Latitude of the end point in radians
    lat2 = math.atan2(sinU1 * math.cos(sigma) + cosU1 * math.sin(sigma)*math.cos(alfa1), (1 - f)*math.sqrt(sinAlfa * sinAlfa + var_aux))
    
    lamb = math.atan2 (math.sin(sigma) * math.sin(alfa1), cosU1 * math.cos(sigma) - sinU1 * math.sin(sigma) * math.cos(alfa1))
    C = f / (16 * cosSqAlfa * (4 + f * (4 - 3 * cosSqAlfa)))
    L = lamb - (1 - C) * f * sinAlfa *(sigma + C *math.sin(sigma) * (cos2sigmaM + C * math.cos(sigma) * (-1 + 2 * cos2sigmaM * cos2sigmaM)))
    # Longitude of the second point in radians
    lon2 = lon1 + L
    
    # Convert to decimal degrees
    lat2_dd = math.degrees(lat2)  
    lon2_dd = math.degrees(lon2)
    
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
    def assign_values(self,r_lat, r_lon, r_mag, o_lyr, ep_name, ep_azm, ep_dist):
        self.r_lat = r_lat
        self.r_lon = r_lon
        self.r_mag = r_mag
        self.o_lyr = o_lyr
        self.ep_name = ep_name
        self.ep_azm = ep_azm
        self.ep_dist = ep_dist

# Initialize InputDataSet variables
in_data = InputDataSet()
     
w = QWidget()

class qgsAzmDist2LatLon:
    """QGIS Plugin Implementation."""
    r_lat = None
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
            'qgsAzmDist2LatLon_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)


        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&AzmDist2LatLon')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'qgsAzmDist2LatLon')
        self.toolbar.setObjectName(u'qgsAzmDist2LatLon')
        
        #self.dlg.pbAddPoint.clicked.connect(self.add_point)
        
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
        return QCoreApplication.translate('qgsAzmDist2LatLon', message)


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
        self.dlg = qgsAzmDist2LatLonDialog()

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

        icon_path = ':/plugins/qgsAzmDist2LatLon/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'AzmDist2LatLon'),
            callback=self.run,
            parent=self.iface.mainWindow())
            
        
        self.dlg.pbAddPoint.clicked.connect(self.add_point)

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&AzmDist2LatLon'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar
    
    def select_input_file(self):
        input_file = QFileDialog.getOpenFileName(self.dlg, "Select input file ", "", '*.csv')
        self.dlg.leInputFile.setText(input_file)
        
    def val_input(self):
        """ Gets and validates if input data is correct"""
        global in_data
        val_result = True              # If input data is correct val_result will be set to False
        err_msg = ''
        # Assign input to variables
        rp_lat_dms = self.dlg.leRefLat.text()        # Latitude of the reference point
        rp_lon_dms = self.dlg.leRefLon.text()        # Longitude of the reference point
        rp_mv  = self.dlg.leRefMagVar.text()     # Magnetic variation of the reference point
        lyr_out = self.dlg.leLyrOut.text()       # Output layer
        ep_name = self.dlg.leEndPointName.text() # End (second) point name
        ep_azm  = self.dlg.leEndPointAzm.text()  # Azimuth to end (second) point
        ep_dist = self.dlg.leEndPointDist.text() # Distance to end (second) point
        
        r_lat = lat_DMS_shdp2DD(rp_lat_dms)
        r_lon = lon_DMS_shdp2DD(rp_lon_dms)
        # Check if input data is correct
        if not r_lat:  
            err_msg = err_msg + 'Enter latitude of reference point in correct format\n'
            val_result = False
 
        if not r_lon:
            err_msg = err_msg + 'Enter longitude of reference point in correct format\n'
            val_result = False
        
        if lyr_out == '':
            err_msg = err_msg + 'Enter output layer name\n'
            val_result = False
        
        if ep_name == '':
            err_msg = err_msg + 'Enter second point name\n'
            val_result = False
        
        if rp_mv == '': # Magnetic Variation not enetered - assume magnetic variation as 0.0, 
            r_mag = 0.0
            #val_result = True
        else:
            if validate_magvar(rp_mv) == 'NOT_VALID':
                err_msg = err_msg + 'Enter magntic variation at the reference point in correct format, or leave blank if it is 0\n'
                val_result = False
            else: 
                r_mag = validate_magvar(rp_mv)

        if not validate_azm_dd(ep_azm):
            err_msg = err_msg + 'Enter azimuth from reference point to end point in correct format\n'
            val_result = False
            
        if not validate_distance(ep_dist):
            err_msg = err_msg + 'Enter distance from reference point to end point in correct format\n'
            val_result = False
        
        if val_result == True:
            ep_azm = float(ep_azm) + r_mag # Correct by magnetic variation
            if ep_azm < 0:
                ep_azm += 360
            in_data.assign_values(r_lat, r_lon, r_mag, lyr_out, ep_name, ep_azm, float(ep_dist))
        else:
            QMessageBox.critical(w, "Message", err_msg)
            
        return val_result
    def create_tmp_layer(self, l_name):
        """ Create temporary 'memory' layer to store results of calculations
        Args:
            l_name(string): layer name
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
        
    def add_point(self):
        """ Performs calculations and adds new point to the temporary (memory) layer
        """
        global in_data
        # If input is valid perform calculations and add point to layer
        if self.val_input(): # If input data is correct
            """ Check if output_layer is on the layer list, if not - create layer and add rrefernce point and calculated point
            """
            
            ep_lat_dd, ep_lon_dd = vincenty_direct_solution(in_data.r_lat, in_data.r_lon, in_data.ep_azm, in_data.ep_dist, WGS84_A, WGS84_B, WGS84_F)
            ep_lat_dms = dd2dms_sd_prefix(ep_lat_dd, 'LAT')
            ep_lon_dms = dd2dms_sd_prefix(ep_lon_dd, 'LON')
            #ep_lat_dd = vincenty_direct_solution(in_data.r_lat, in_data.r_lon, in_data.ep_azm, in_data.ep_dist, WGS84_A, WGS84_B, WGS84_F)[0]
            #ep_lon_dd = vincenty_direct_solution(in_data.r_lat, in_data.r_lon, in_data.ep_azm, in_data.ep_dist, WGS84_A, WGS84_B, WGS84_F)[1]
            layers = self.iface.legendInterface().layers()
            layer_list = []   # List of layers in current (opened) QGIS project
            for layer in layers:
                layer_list.append(layer.name())
            if (in_data.o_lyr + '_tmp_memory') not in layer_list:
                self.create_tmp_layer(in_data.o_lyr)
                v_lyr = QgsVectorLayer('Point?crs=epsg:4326', in_data.o_lyr, 'memory')
                v_lyr = self.iface.activeLayer()
                v_lyr.startEditing()
                v_prov = v_lyr.dataProvider()
                feat = QgsFeature()
                # Add reference point to layer
                feat.setGeometry(QgsGeometry.fromPoint(QgsPoint(in_data.r_lon, in_data.r_lat)))      
                feat.setAttributes([0, 'REF_POINT', self.dlg.leRefLat.text(), self.dlg.leRefLon.text()])
                v_prov.addFeatures([feat])
                v_lyr.commitChanges()
                # Add calculated point to layer
                feat.setGeometry(QgsGeometry.fromPoint(QgsPoint(ep_lon_dd, ep_lat_dd)))      
                feat.setAttributes([0, in_data.ep_name, ep_lat_dms, ep_lon_dms])
                v_prov.addFeatures([feat])
                v_lyr.commitChanges()
                v_lyr.updateExtents() 
            elif (in_data.o_lyr + '_tmp_memory') in layer_list:
                v_lyr = QgsVectorLayer('Point?crs=epsg:4326', in_data.o_lyr, 'memory')
                v_lyr = self.iface.activeLayer()
                v_lyr.startEditing()
                v_prov = v_lyr.dataProvider()
                feat = QgsFeature()
                feat.setGeometry(QgsGeometry.fromPoint(QgsPoint(ep_lon_dd, ep_lat_dd)))      
                feat.setAttributes([0, in_data.ep_name, ep_lat_dms, ep_lon_dms])
                v_prov.addFeatures([feat])
                v_lyr.commitChanges()
                v_lyr.updateExtents() 
        return
    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        #self.dlg.pbAddPoint.clicked.connect(self.add_point)
        self.dlg.show()
        # initialize input data set
        
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass
