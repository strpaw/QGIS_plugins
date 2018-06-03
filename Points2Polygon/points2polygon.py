# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Points2Polygon
                                 A QGIS plugin
 Creates polugon from points stored in different formats (DMS delimited, DMS compacted, DD etc.)
                              -------------------
        begin                : 2018-06-02
        git sha              : $Format:%H$
        copyright            : (C) 2018 by Pawel Strzelewicz
        email                : pawel.strzelewicz83@gmail.com
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
from PyQt4.QtCore import *
from PyQt4.QtGui import QAction, QIcon, QFileDialog
from qgis.core import *
from osgeo import ogr, osr
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from points2polygon_dialog import Points2PolygonDialog
import os.path
import re
import csv
import decimal

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
H_ALL = ['N', 'S', 'E', 'W']
H_LAT = ['N', 'S']
H_LON = ['E', 'W']
H_MINUS = ['S', 'W']
NOT_VALID = 'NOT_VALID'

C_LAT = 'LAT'
C_LON = 'LON'


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
            d = int(dms_t[0])
            m = int(dms_t[1])
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
            d = int(dms_t[0])
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
            d = int(dms_t[0])
            m = int(dms_t[1])
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
            d = int(dms_t[0])
            m = float(dms_t[1])
            if ((d < 0) or (m < 0) or (m >= 60)):
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

class Points2Polygon:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgisInterface
        """
        self.input_file = ''     # Input file, path + file name
        self.output_file = ''    # Output file, path + file name
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'Points2Polygon_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)


        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Points2Polygon')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'Points2Polygon')
        self.toolbar.setObjectName(u'Points2Polygon')

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
        return QCoreApplication.translate('Points2Polygon', message)


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
        self.dlg = Points2PolygonDialog()

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

        icon_path = ':/plugins/Points2Polygon/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Points2Polygon'),
            callback=self.run,
            parent=self.iface.mainWindow())
            
        self.dlg.pbInputFile.clicked.connect(self.select_input_file)
        self.dlg.pbOutputFile.clicked.connect(self.select_output_file)
        self.dlg.pbConvert2shp.clicked.connect(self.points2polygon)

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Points2Polygon'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar
    
    def select_input_file(self):
        """ Select input file with Electronic Obstacle Data """
        self.input_file = QFileDialog.getOpenFileName(self.dlg, "Select input file ", "", '*.csv')
        self.dlg.leInputFile.setText(self.input_file)
        return
    
    def select_output_file(self):
        """ Select output shp file """
        self.output_file = QFileDialog.getSaveFileName(self.dlg, "Select output shp file ", "", '*.shp')
        self.dlg.leOutputFile.setText(self.output_file)
        return
    
    def points2polygon(self):
        """ Converts input csv file with list of points to polygon features """
        # Set referefnce system
        crs = QgsCoordinateReferenceSystem()
        crs.createFromId(4326)
        # Defining fileds for feature attributes
        fields = QgsFields()
        fields.append(QgsField("POL_ID", QVariant.String))  # Polygon Identifier

        writer = QgsVectorFileWriter(self.output_file, "CP1250", fields, QGis.WKBPolygon, crs, "ESRI Shapefile")

        feat = QgsFeature()

        points = [] # List of points for polygon feature
        current_pol_id = '' #TO DO - get current_pol_id from input file - POL_ID from firest line data
        vertex_nr = 0  # Number of vertices in polygon feature
        
        with open(self.input_file, 'r') as in_file:
            reader = csv.DictReader(in_file, delimiter = ';')
            while True:
                try:
                    row = next(reader)
                    pol_id = row['POL_ID']
                    lat_dd = parse_dms2dd(row['LAT'], C_LAT)
                    lon_dd = parse_dms2dd(row['LON'], C_LON)             
                    point = str(lat_dd) + '_' + str(lon_dd)
                    point = QgsPoint(lon_dd, lat_dd)    # Create QgsPoint object from longitude and latitude in decimal degrees format
                    if pol_id == current_pol_id:
                        vertex_nr += 1              # Count vertices
                        points.append(point)        # Add point to point list
                    elif pol_id != current_pol_id:
                        if vertex_nr < 3:  # We need at least 3 vertexes to create polygon shape
                            pass   # TO DO: error message
                        else: 
                            try: # Try to create polygon 
                                feat.setGeometry(QgsGeometry.fromPolygon([points]))
                                feat.setAttributes([current_pol_id])
                                writer.addFeature(feat) 
                            except:
                                pass # TO DO: error message if fail to cerate polygon
                        vertex_nr = 0
                        current_pol_id = pol_id
                        points = []
                        points.append(point)
                except StopIteration: # End of file - try to create polygon from data
                    if vertex_nr < 3:  # We need at least 3 vertexes to create polygon shape
                        pass   # TO DO: error message
                    else:          
                        try: # Try to create polygon 
                            feat.setGeometry(QgsGeometry.fromPolygon([points]))
                            feat.setAttributes([current_pol_id])
                            writer.addFeature(feat) 
                        except:
                            pass # TO DO: error message if fail to cerate polygon
                    break # Stop iteration
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
