# -*- coding: utf-8 -*-
"""
/***************************************************************************
 faa_nasr2shp
                                 A QGIS plugin
 Converts FAA NASR data to shapefile
                              -------------------
        begin                : 2018-05-27
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
from PyQt4.QtCore import *
from PyQt4.QtGui import QAction, QIcon, QFileDialog
from qgis.core import *
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from faa_nasr2shp_dialog import faa_nasr2shpDialog
import os.path
import re


VALID     = 'VALID'
NOT_VALID = 'NOT_VALID'



H_LAT = ['N', 'S']
H_LON = ['E', 'W']
H_MINUS = ['S', 'W']

def dms_dshl2dd_s(dms):
    """ Convert latitude, longitude given in DMS delimited suffix hemisphere letter
    (32-44-52.77N, 134-55-21.619W) to decimal degress signed format (32.33457, -134.4475885)
    :param dms: string, dms value to cnvert to dd format
    :return dd: float if dms is valid return decimal degress of dms, if dms is not valid returns constant NOT_VALID
    """
    try:
        h = dms[len(dms) - 1]      # Get hemisphere letter, 
        dms_m = dms[:len(dms) - 1] # Trim hemisphere letter
        dms_m = dms_m.replace("-", " ")    # Replace hyphen to space
        dms_m = re.sub(r'\s+', ' ', dms_m) # # Replace multiple spaces to single space
        dms_t = dms_m.split(' ')      # Splits dms by spaces and return as tuple
        if len(dms_t) == 3:
            try:
                d = float(dms_t[0])
                m = float(dms_t[1])
                s = float(dms_t[2])
                if ((d < 0) or (m < 0) or (m >= 60) or (s < 0) or (s >= 60)):
                    dd = NOT_VALID
                else:
                    dd = d + m/60 + s/3600
                    if (h in H_MINUS):
                        dd = -dd
            except:

                dd = NOT_VALID
        else:
            dd = NOT_VALID
    except:
        dd = NOT_VALID
    return

NATFIX_NAVAID = ['NDB', 'NDB/DME', 'TACAN', 'UHF/NDB', 'VOR', 'VOR/DME', 'VORTAC']

def decode_natfix_wpt_type(code):
    """ Decode NATFIX wyapoint types
    :param code: string, code waypoint in NATFIX file
    :return wpt_type: string, waypoint type
    """
    if code == 'ARPT':
        wpt_type = 'ARPT'
    elif code in NATFIX_NAVAID:
        wpt_type = 'NAVAID'
    else:
        wpt_type = 'UNKNOWN'
    return wpt_type
    
def natfix2shp(in_file, out_file):
    """ Converts NASR FAA NATFIX file to shapefile
    :param in_file: string, input file
    :param out_file: string, output file
    """
    crs = QgsCoordinateReferenceSystem()
    crs.createFromId(4326) # TODO - check refernce system of NATFIX file
    nfix_fields = QgsFields()
    nfix_fields.append(QgsField("NFIX_ID", QVariant.String))      # FIX/NAVAID/AIRPORT ID
    nfix_fields.append(QgsField("NFIX_LAT_DMS", QVariant.String)) # FIX/NAVAID/AIRPORT LATITUDE
    nfix_fields.append(QgsField("NFIX_LON_DMS", QVariant.String)) # FIX/NAVAID/AIRPORT LONGITUDE
    nfix_fields.append(QgsField("NFIX_R_COD", QVariant.String))   # ICAO REGION CODE
    nfix_fields.append(QgsField("NFIX_TYPE", QVariant.String))    # FIX/NAVAID TYPE OR STRING "ARPT"
    nfix_fields.append(QgsField("WPT_TYPE", QVariant.String))     # FIX/NAVAID TYPE OR STRING "ARPT"
    nfix_fields.append(QgsField("NFIX_CYCLE", QVariant.String))   # Cycle
    
    writer = QgsVectorFileWriter(out_file, "CP1250", nfix_fields, QGis.WKBPoint, crs, "ESRI Shapefile")
        
    feat = QgsFeature()
    
    with open(in_file, 'r') as NFIX_file:
            line_nr = -1
            for line in NFIX_file:
                try:
                    line_nr += 1
                    if line_nr < 2:   # Skip first 2 lines
                        continue
                    else:
                        id = line[2:8].rstrip()
                        lat_dms = line[8:16]
                        
                        lat_d = lat_dms[0:2]
                        lat_m = lat_dms[2:4]
                        lat_s = lat_dms[4:6]
                        lat_h = lat_dms[6]
                            
                        lat_dd = float(lat_d) + float(lat_m)/60 + float(lat_s)/3600
                        if lat_h == 'S':
                            lat_dd = -lat_dd
                            
                        lon_dms = line[16:24]
                        lon_d = lon_dms[0:3]
                        lon_m = lon_dms[3:5]
                        lon_s = lon_dms[5:7]
                        lon_h = lon_dms[7]
                        
                        lon_dd = float(lon_d) + float(lon_m)/60 + float(lon_s)/3600
                        if lon_h == 'W':
                            lon_dd = -lon_dd

                        reg_cod = line[34:36]
                        nfix_type = line[37:45].rstrip()
                        wpt_type = decode_natfix_wpt_type(nfix_type)
                            

                        feat.setGeometry(QgsGeometry.fromPoint(QgsPoint(lon_dd, lat_dd)))
                        feat.setAttributes([id,
                                            lat_dms,
                                            lon_dms,
                                            reg_cod,
                                            nfix_type,
                                            wpt_type,
                                            ""]) # TO DO: reading cycle date from NATFIX file

                        writer.addFeature(feat)
                except:
                    pass

    del writer
    return

def regulatory_awy2awy_shp(in_file, out_file):
    """ Converts FAA NASR Regulatory AWY file to shapefile, exctracts only whole awy as poluline with awy_id as attribute
    :param in_file: string, input file
    :param out_file: string, output file
    """
    crs = QgsCoordinateReferenceSystem()
    crs.createFromId(4326) # TODO - check refernce system of AWY file
    awy_pline_fields = QgsFields()
    awy_pline_fields.append(QgsField("AWY_ID", QVariant.String))      # AWY Identifier
    
    writer = QgsVectorFileWriter(out_file, "CP1250", awy_pline_fields, QGis.WKBLineString, crs, "ESRI Shapefile")
    # Set initial values
    feat = QgsFeature()

    current_awy_id = ''    # Current awy identifier
    points = []            # List of fixes
    
    with open(in_file, 'r') as in_file:
        with open(out_file, 'w') as out_file:
            # Get first awy_id and assign its value to current_awy_id varaiable
            line = in_file.readline()
            awy_id = line[4:9].rstrip()
            current_awy_id = awy_id
            in_file.seek(0)
            
            while True:
                try:
                    line = next(in_file)
                    rec_type = line[0:4]
                    if rec_type == 'AWY2': # Read fix points for each awy
                        awy_id = line[4:9].rstrip()
                        fix_lat = line[83:97].rstrip()  # Read fix latitude
                        fix_lon = line[97:111].rstrip() # Read fix longitude
                        # Convert DMS format to DD format
                        lat_d = fix_lat[0:2]
                        lat_m = fix_lat[3:5]
                        lat_s = fix_lat[6:len(fix_lat) - 1]
                                
                        lon_d = fix_lon[0:3]
                        lon_m = fix_lon[4:6]
                        lon_s = fix_lon[7:len(fix_lon) - 1]
                        try: # Try to create QgsPoint() 
                            lat_dd = float(lat_d) + float(lat_m)/60 + float(lat_s)/3600
                            lon_dd = float(lon_d) + float(lon_m)/60 + float(lon_s)/3600
                            point = QgsPoint(-lon_dd, lat_dd)
                        except:
                            continue # TO DO - error message, log
                        if awy_id == current_awy_id:
                            try:
                                points.append(point) 
                            except:
                                continue # TO DO - error message, log
                        elif awy_id != current_awy_id:
                            try:
                                feat.setGeometry(QgsGeometry.fromPolyline(points))
                                feat.setAttributes([current_awy_id])
                                writer.addFeature(feat)
                                
                                current_awy_id = awy_id
                                points = []
                                points.append(point)
                            except:
                                continue # TO DO - error message, log
                except StopIteration: # Loop reaches end of file
                    try: # Try to create polyline shape from collected data
                        feat.setGeometry(QgsGeometry.fromPolyline(points))
                        feat.setAttributes([current_awy_id])
                        writer.addFeature(feat)
                    except:
                        continue # TO DO - error message, log
                    break   
    del writer
    return
    
def regulatory_awy2awy_segment_shp(in_file, out_file):
    current_awy_id = ''
    next_awy_id = ''
    current_seg = ''
    next_seg = ''
    wpt_start = ''
    wpt_end = ''
    crs = QgsCoordinateReferenceSystem()
    crs.createFromId(4326) # TODO - check refernce system of AWY file
    awy_pline_fields = QgsFields()
    awy_pline_fields.append(QgsField("AWY_ID", QVariant.String))      # AWY Identifier
    awy_pline_fields.append(QgsField("SEG_ID", QVariant.String))      # AWY Identifier
    awy_pline_fields.append(QgsField("WPT_START_ID", QVariant.String))      # AWY Identifier
    awy_pline_fields.append(QgsField("WPT_END_ID", QVariant.String))      # AWY Identifier
    writer = QgsVectorFileWriter(out_file, "CP1250", awy_pline_fields, QGis.WKBLineString, crs, "ESRI Shapefile")
    feat = QgsFeature()
    
    """
    jeśli typ rekodu = AWYw i nr segmentu = biezacy nr segmentu - > wpt start, biezacy segment
    jeśli typ rekordu = AWY1 i nr segmentu sgement +10 - nnastepny segment
    jesli typ rekordu AWY2 i nr segmentu + 10 - konices bizeacego segmetnu
    
    """
    points = []
    with open(in_file, 'r') as in_file:
        with open(out_file, 'w') as out_file:
            """
            # Get first awy_id and assign its value to current_awy_id varaiable
            line = in_file.readline()
            awy_id = line[4:9].rstrip()
            current_awy_id = awy_id
            in_file.seek(0)
            
            
            while True:
                try:
                except StopIteration: # Loop reaches end of file
                    try:
                        
                    except:
                        pass
                
            """
            line = in_file.readline()      # Read first line of AWY file
            awy_id = line[4:9].rstrip()    # Get awy identifier from first record
            seg_nr = int(line[10:15].lstrip())
            #current_awy_id = awy_id        # Set awy identifier from first record as current_awy_id
            current_seg_nr = seg_nr
            in_file.seek(0)                # Go back to begin of AWY file
            for line in in_file:
                rec_type = line[0:4] 
                seg_nr = int(line[10:15].lstrip())
                next_seg_nr = seg_nr
                if next_seg == current_seg_nr and rec_type == 'AWY2':  # Start point biezacego segmentu
                    wpt1_lat = line[83:97].rstrip()  # Read waypoint latitude
                    wpt1_lon = line[97:113].rstrip() # Read waypoint longitude

                    lat1_d = wpt1_lat[0:2]
                    lat1_m = wpt1_lat[3:5]
                    lat1_s = wpt1_lat[6:len(wpt1_lat) - 1]
                            
                    lon1_d = wpt1_lon[0:3]
                    lon1_m = wpt1_lon[4:6]
                    lon1_s = wpt1_lon[6:len(wpt1_lon) - 1]

                    lat1_dd = float(lat1_d) + float(lat1_m)/60 + float(lat1_s)/3600
                    lon1_dd = float(lon1_d) + float(lon1_m)/60 + float(lon1_s)/3600
                    wpt_start = QgsPoint(-lon1_dd, lat1_dd)
                    points.append(wpt_start)
                
                if next_seg_nr == (current_seg_nr + 10) and rec_type == 'AWY2' :#koniec punkt ubiezacego
                    wpt2_lat = line[83:97].rstrip()  # Read waypoint latitude
                    wpt2_lon = line[97:113].rstrip() # Read waypoint longitude

                    lat2_d = wpt2_lat[0:2]
                    lat2_m = wpt2_lat[3:5]
                    lat2_s = wpt2_lat[6:len(wpt2_lat) - 1]
                            
                    lon2_d = wpt2_lon[0:3]
                    lon2_m = wpt2_lon[4:6]
                    lon2_s = wpt2_lon[6:len(wpt2_lon) - 1]

                    lat2_dd = float(lat2_d) + float(lat2_m)/60 + float(lat2_s)/3600
                    lon2_dd = float(lon2_d) + float(lon2_m)/60 + float(lon2_s)/3600
                    wpt_end = QgsPoint(-lon2_dd, lat2_dd)
                    points.append(wpt_end)
                    #wpt_end = QgsPoint(-lon2_dd, lat2_dd)
                    feat.setGeometry(QgsGeometry.fromPolyline(points))
                    feat.setAttributes([awy_id,
                                        current_seg_nr,
                                        wpt_start, 
                                        wpt_end])
                    writer.addFeature(feat)
                    wpt_start      = wpt_end
                    points = []
                    current_seg_nr = next_seg_nr
                

    return

def regulatory_awy2wpt_shp(in_file, out_file):
    
    return
    
class faa_nasr2shp:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgisInterface
        """
        self.input_file = ''     # Input file path + file name
        self.output_file = ''    # Output file path + file name
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'faa_nasr2shp_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)


        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&FAA_NASR2shp')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'faa_nasr2shp')
        self.toolbar.setObjectName(u'faa_nasr2shp')

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
        return QCoreApplication.translate('faa_nasr2shp', message)


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
        self.dlg = faa_nasr2shpDialog()

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

        icon_path = ':/plugins/faa_nasr2shp/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'FAA_NASR2shp'),
            callback=self.run,
            parent=self.iface.mainWindow())

        self.dlg.pbInputFile.clicked.connect(self.select_input_file)
        self.dlg.pbOutputFile.clicked.connect(self.select_output_file)
        self.dlg.pbConvert2shp.clicked.connect(self.faa_nasr2shp)
        
    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&FAA_NASR2shp'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def select_input_file(self):
        """ Select input file with FAA NASR data """
        if self.dlg.cbeNasrFile.currentIndex() == 0:
            self.input_file = QFileDialog.getOpenFileName(self.dlg, "Select input file ", "", '*.txt')
            self.dlg.leInputFile.setText(self.input_file)
        elif self.dlg.cbeNasrFile.currentIndex() == 1:
            self.input_file = QFileDialog.getOpenFileName(self.dlg, "Select input file ", "", '*.txt')
            self.dlg.leInputFile.setText(self.input_file)
        elif self.dlg.cbeNasrFile.currentIndex() == 2:
            self.input_file = QFileDialog.getOpenFileName(self.dlg, "Select input file ", "", '*.txt')
            self.dlg.leInputFile.setText(self.input_file)
        # TODO - other types of NASR data files
        return
    
    def select_output_file(self):
        """ Select output shp file """
        self.output_file = QFileDialog.getSaveFileName(self.dlg, "Select output shp file ", "", '*.shp')
        self.dlg.leOutputFile.setText(self.output_file)
        return
        
    def faa_nasr2shp(self):
        # TO DO: input validation
        if self.dlg.cbeNasrFile.currentIndex() == 0: # NATIFX file
            natfix2shp(self.input_file, self.output_file)
        elif self.dlg.cbeNasrFile.currentIndex() == 1: # AWY file - awys
            regulatory_awy2awy_shp(self.input_file, self.output_file)
        elif self.dlg.cbeNasrFile.currentIndex() == 2: # seg
            regulatory_awy2awy_segment_shp(self.input_file, self.output_file)
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