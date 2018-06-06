# -*- coding: utf-8 -*-
"""
/***************************************************************************
 PointByLatLon
                                 A QGIS plugin
 Adds point by latitude, longitude 
                              -------------------
        begin                : 2018-06-06
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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon, QMessageBox, QWidget
# Initialize Qt resources from file resources.py
from qgis.core import *
import resources
# Import the code for the dialog
from point_by_latlon_dialog import PointByLatLonDialog
import os.path
import re


# Special constant to use instead of False, to avoid ambigous where result of function might equal 0 and 
# and result of fucntion will be used in if statements etc.
VALID = 'VALID'
NOT_VALID = 'NOT_VALID'

# DMS, DM format separators, e.g. N32-44-55.21, N32 44 55.21, N32DEG 44 55.21
S_SPACE      = ' '
S_HYPHEN     = ' ' # TO DO: hyphen separator
S_SYMBOL_DEG = '°'
S_SYMBOL_MIN_1 = "'"
S_SYMBOL_MIN_2 = "’"
S_SYMBOL_SEC_1 = '"'
S_SYMBOL_SEC_2 = "’’"
S_WORD_DEG   = 'DEG'
S_WORD_MIN   = 'MIN'
S_WORD_SEC   = 'SEC'

S_LIST = [S_SPACE, S_HYPHEN, S_SYMBOL_DEG, S_SYMBOL_MIN_1, S_SYMBOL_MIN_2, S_SYMBOL_SEC_1, S_SYMBOL_SEC_2,
          S_WORD_DEG, S_WORD_MIN, S_WORD_SEC]
          
# Hemisphere letters
H_ALL = ['N', 'S', 'E', 'W']
H_LAT = ['N', 'S']
H_LON = ['E', 'W']
H_MINUS = ['S', 'W']

# Coordinate types
C_LAT = 'LAT'
C_LON = 'LON'

# DMS, DM coordinate formats
F_DMS_shdp  = 'DMS_shdp' # DMS, space or hyphen delimited with prefix, N52 13 56.00, N52-13-56.00
F_DMS_shds  = 'DMS_shds' # DMS, space or hyphen delimited with suffix  021 00 30.00E, 021-00-30.00E
F_DMS_cp    = 'DMS_cp'   # DMS, compacted (no delimited) with prefix   N521356.00, E0210030.00
F_DMS_cs    = 'DMS_cs'   # DMS, compactet (no delimited) with suffix   5221356.00N, 0210030.00E

""" Latitude, longitude validation and conversion functions """

def check_latlon_range(dd, c_type):
    """ Check if latitude is with range <-90, 90> or longitude with range <-180, 180>
    :param dd  : float, coordinate in decimal degress
    :param c_type: constant C_LAT or C_LON, coordinate type,
    :return result: float dd if param dd is in range, constant NOT_VALID otherwise
    """
    result = dd

    if c_type == C_LAT:
        if (dd < -90) or (dd > 90):
            result = NOT_VALID
    elif c_type == C_LON:
        if (dd < -180) or (dd > 180):
            result = NOT_VALID

    return result
    
def if_signed_DD(dms, c_type):
    """ Checks if input parameter is float number, dosen't check latitude, longitude limiest (-90 +90, -180 +180)
    :param dms: string, 
    return dd: float - decimal degress if is float value, NOT_VALID constant if is not valid float value
    """
    try:
        dd = float(dms)
        dd = check_latlon_range(dd, c_type)    
    except:
        dd = NOT_VALID
    return dd
    
def if_hletter_DD(dms, c_type):
    """ Checks if input parameter decimal degress with hemisphere letter prefix or suffix, 
    dosen't check latitude, longitude limiest (-90 +90, -180 +180)
    :param dms: string, 
    return dd: float - decimal degress if is valid dms, NOT_VALID constant if is not valid float value
    """
    h = dms[0]  
    if h in H_ALL: # If hemisphere letter is as prefix - normalize dms - hemisphere suffix
        dms_n = dms[1:] + h
    else:
        dms_n = dms
    h = dms_n[len(dms_n) - 1]
    # Check if it is not a compacted dms
    dms_l = dms_n.split('.')
    if len(dms_l[0]) > 3:
        dd = NOT_VALID
    else:
        dms_n = dms_n[0:len(dms_n) - 1] # Trim hemisphere letter
        try:
            dd = float(dms_n)
            dd = check_latlon_range(dd, c_type) 
            if (h in H_MINUS) and (dd != NOT_VALID):
                dd = -dd
        except:
            dd = NOT_VALID
    return dd
    
def if_signed_DMS_DM(dms, c_type):
    """ Checks if input parameter is signed DMS or DM format, without hemisphere letter prefix or suffix, 
    dosen't check latitude, longitude limiest (-90 +90, -180 +180)
    :param dms: string, 
    return dd: float - decimal degress if is valid dms, NOT_VALID constant if is not valid float value
    """
    for sep in S_LIST:            # Replace any separator to space separator
        dms = dms.replace(sep, ' ')
    dms = re.sub(r'\s+', ' ', dms)  # Replace multiple spaces to single space
    dms_t = dms.split(' ')      # Splits dms by spaces and return as tuple
    if len(dms_t) == 3:   # 3 elments in tuple - assumes it is DMS format (DD MM SS.sss)
        try:
            d = float(dms_t[0])
            m = float(dms_t[1])
            s = float(dms_t[2])
            if ((d < 0) or (m < 0) or (m >= 60) or (s < 0) or (s >= 60)):
                dd = NOT_VALID
            else:
                if  d >= 0:
                    dd = d + m/60 + s/3600
                    dd = check_latlon_range(dd, c_type)  
                elif d < 0:
                    dd = -(math.fabs(d) + m/60 + s/3600)
                    dd = check_latlon_range(dd, c_type) 
        except:
            dd = NOT_VALID
    elif len(dms_t) == 2: # 2 elemnts in tuple - assumes it is in DM (DD MM.mmmm)
        try:
            d = float(dms_t[0])
            m = float(dms_t[1])
            if ((d < 0) or (m < 0) or (m >= 60)):
                dd = 'DMS_ERROR'
            else:
                if  d >= 0:
                    dd = d + m/60
                    dd = check_latlon_range(dd, c_type) 
                elif d < 0:
                    dd = -(math.fabs(d) + m/60)
                    dd = check_latlon_range(dd, c_type) 
        except:
            dd = NOT_VALID
    else:
        dd = NOT_VALID
    return dd
    
def if_hletter_DMS_DM(dms, c_type):
    """ Checks if input parameter DMS or DM format with hemisphere letter prefix or suffix, 
    dosen't check latitude, longitude limiest (-90 +90, -180 +180)
    :param dms: string, 
    return dd: float - decimal degress if is valid dms, NOT_VALID constant if is not valid float value
    """
    h = dms[0]  
    if h in H_ALL: # If hemisphere letter is as prefix - normalize dms - hemisphere suffix
        dms_n = dms[1:] + h
    else:
        dms_n = dms
    h = dms_n[len(dms_n) - 1]
    dms_n = dms_n[0:len(dms_n) - 1] # Trim hemisphere letter
    
    for sep in S_LIST:            # Replace any separator to space separator
         dms_n = dms_n.replace(sep, ' ')
    dms_n = dms_n.rstrip() # Trim trailing spaces - when sconds sign ('') replaced by space at the end of the string
    dms_n = re.sub(r'\s+', ' ', dms_n)  # Replace multiple spaces to single space
    dms_t = dms_n.split(' ')      # Splits dms by spaces and return as tuple
    
    if len(dms_t) == 3:   # 3 elments in tuple - assumes it is DMS format (DD MM SS.sss)
        try:
            d = float(dms_t[0])
            m = float(dms_t[1])
            s = float(dms_t[2])
            if ((d < 0) or (m < 0) or (m >= 60) or (s < 0) or (s >= 60)):
                dd = NOT_VALID
            else:
                dd = d + m/60 + s/3600
                dd = check_latlon_range(dd, c_type) 
                if (h in H_MINUS) and (dd != NOT_VALID):
                    dd = -dd
        except:
            dd = NOT_VALID
    elif len(dms_t) == 2:   # 2 elments in tuple - assumes it is DM format (DD MM.mmmm)
        try:
            d = float(dms_t[0])
            m = float(dms_t[1])
            if (d < 0) or (m < 0) or (m >= 60):
                dd = NOT_VALID
            else:
                dd = d + m/60
                dd = check_latlon_range(dd, c_type) 
                if (h in H_MINUS) and (dd != NOT_VALID):
                    dd = -dd
        except:
            dd = NOT_VALID
    else:
        dd = NOT_VALID
    return dd

def if_compact_dms2dd(dms, c_type):
    h = dms[0]  
    if h in H_ALL: # If hemisphere letter is as prefix - normalize dms - hemisphere suffix
        dms_n = dms[1:] + h
    else:
        dms_n = dms
    h = dms_n[len(dms_n) - 1]
    dms_n = dms_n[0:len(dms_n) - 1] # Trim hemisphere letter
    if h in H_LAT:
        try:
            d = float(dms_n[0:2])
            m = float(dms_n[2:4])
            s = float(dms_n[4:])
            if ((d < 0) or (m < 0) or (m >= 60) or (s < 0) or (s >= 60)):
                dd = NOT_VALID
            else:
                dd = d + m/60 + s/3600
                dd = check_latlon_range(dd, c_type)
                if (h in H_MINUS) and (dd != NOT_VALID):
                    dd = -dd                    
        except:
            dd = NOT_VALID
    elif h in H_LON:
        try:
            d = float(dms_n[0:3])
            m = float(dms_n[3:5])
            s = float(dms_n[5:])
            if ((d < 0) or (m < 0) or (m >= 60) or (s < 0) or (s >= 60)):
                dd = NOT_VALID 
            else:
                dd = d + m/60 + s/3600
                dd = check_latlon_range(dd, c_type)
                if (h in H_MINUS) and (dd != NOT_VALID):
                    dd = -dd
        except:
            dd = NOT_VALID
    else:
        dd = NOT_VALID
    return dd
    
def parse_dms2dd(dms, c_type):
    """ Checks if input parameter is float number, dosen't check latitude, longitude limiest (-90 +90, -180 +180)
    :param dms: string, 
    return dd: decimal degrees or NOT_VALID constant if input is not valid coordinate, 
    """
    dms = str(dms)  # Ensure that dms in string variable to perform some string built-in functions
    dms = dms.replace(',','.') # Replace comma decimal separator to period decimal separator
    dms = dms.lstrip(' ')  # Remove leading blanks
    dms = dms.rstrip(' ')  # Remove trailing blanks
    dms = dms.upper()    # Ensure that all charatcers are in upper case, e.g N, E instead of n, e
    
    dd = if_signed_DD(dms, c_type)
    if dd == NOT_VALID:
        dd = if_hletter_DD(dms, c_type)
        if dd == NOT_VALID:
            dd = if_signed_DMS_DM(dms, c_type)
            if dd == NOT_VALID:
                dd = if_hletter_DMS_DM(dms, c_type)
                if dd == NOT_VALID:
                    dd = if_compact_dms2dd(dms, c_type)  

    return dd

w = QWidget()    

class PointByLatLon:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgisInterface
        """
        self.lat_dd = None
        self.lon_dd = None
        
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'PointByLatLon_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)


        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&PointByLatLon')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'PointByLatLon')
        self.toolbar.setObjectName(u'PointByLatLon')

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
        return QCoreApplication.translate('PointByLatLon', message)


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
        self.dlg = PointByLatLonDialog()

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

        icon_path = ':/plugins/PointByLatLon/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'PointByLatLon'),
            callback=self.run,
            parent=self.iface.mainWindow())
        
        self.dlg.pbAddPoint.clicked.connect(self.add_point)
        
        return
    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&PointByLatLon'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar
    
    def if_latlon_empty(self):
        return result
    def get_latlon(self):
        """ Gets input latidue, longitude and conevrt the into decimal degrees format"""
        result = True
        msg_info = ''
        mgs_error = 'Input error!'
        lat_dms = self.dlg.leLat.text()
        lon_dms = self.dlg.leLon.text()
        
        if lat_dms == '':
            msg_info += 'Enter latitude\n'
            result = False
        if lon_dms == '':
            msg_info += 'Enter longitude\n'
            result = False
            
        if result == False:
            QMessageBox.information(w, "Message", msg_info)
        else:
            lat_dd = parse_dms2dd(lat_dms, C_LAT)
            lon_dd = parse_dms2dd(lon_dms, C_LON)
            if lat_dd != NOT_VALID and lon_dd != NOT_VALID:
                self.lat_dd = lat_dd
                self.lon_dd = lon_dd
            else:
                QMessageBox.critical(w, "Message", 'Input error!')
                result = False
        return result
    def add_point(self):
        if self.get_latlon() == True:
            layer = self.iface.activeLayer()
            feat = QgsFeature()
            point = QgsPoint(self.lon_dd, self.lat_dd)
            feat.setGeometry(QgsGeometry.fromPoint(point))
            layer.dataProvider().addFeatures([feat])
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
