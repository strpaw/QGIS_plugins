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
import copy
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



def regulatory_awy2awy_shp(in_file, out_file):
    """ Converts FAA NASR Regulatory AWY file to shapefile, exctracts only whole awy as polyline with awy_id as attribute
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
    
def regulatory_awy2awy_segment_shp(input_file, output_file):
    """ Converts FAA NASR Regulatory AWY file to shapefile, exctracts only segments of awy  - each record is one segment
    :param in_file: string, input file
    :param out_file: string, output file
    """
    crs = QgsCoordinateReferenceSystem()
    crs.createFromId(4326) # TODO - check refernce system of AWY file
    awy_segment_fields = QgsFields()
    awy_segment_fields.append(QgsField("AWY_ID", QVariant.String))      # AWY Identifier
    awy_segment_fields.append(QgsField("SEG_NR", QVariant.String))      # Segment number
    awy_segment_fields.append(QgsField("FIX_START", QVariant.String))   # Fix - start of segment
    awy_segment_fields.append(QgsField("FIX_END", QVariant.String))     # Fix - end of segment
    awy_segment_fields.append(QgsField("EFF_DATE", QVariant.String))    # Effective date of segment
    awy_segment_fields.append(QgsField("MEA", QVariant.Int))            # Minimum en route altitude of segment, feet
    
    writer = QgsVectorFileWriter(output_file, "CP1250", awy_segment_fields, QGis.WKBLineString, crs, "ESRI Shapefile")
    # Set initial values
    feat = QgsFeature()
    
    
    with open(input_file, 'r') as in_file:
        line = in_file.readline()
        awy_id = line[4:9].rstrip()
        seg_nr = int(line[10:15].lstrip())
        in_file.seek(0)
        
        current_awy_id = awy_id
        current_seg_nr = seg_nr
        
        prev_awy_id = ''
        prev_seg_nr = ''
        full_data = False
        
        for line in in_file:
            # Read record type, AWY identifier, segment number of the AWY
            rec_type = line[0:4]
            awy_id = line[4:9].rstrip()
            seg_nr = int(line[10:15].lstrip())
            
            if awy_id == current_awy_id:
                if rec_type == 'AWY1':  # Data releted to AWY segment
                    if seg_nr == current_seg_nr:
                        seg_prev_eff_date = line[15:25].rstrip()
                        seg_prev_MEA = line[74:79].lstrip('0')
                if rec_type == 'AWY2': # Data related to fixes of AWY
                    if seg_nr == prev_seg_nr: # Start fix of segment
                        fix_from_name = line[15:45].rstrip()
                        from_lat = line[83:97].rstrip()  # Read fix latitude
                        from_lon = line[97:111].rstrip() # Read fix longitude

                        from_lat_d = from_lat[0:2]
                        from_lat_m = from_lat[3:5]
                        from_lat_s = from_lat[6:len(from_lat) - 1]
                                        
                        from_lon_d = from_lon[0:3]
                        from_lon_m = from_lon[4:6]
                        from_lon_s = from_lon[7:len(from_lon) - 1]
                        
                        

                        try:
                            from_lat_dd = float(from_lat_d) + float(from_lat_m)/60 + float(from_lat_s)/3600
                            from_lon_dd = float(from_lon_d) + float(from_lon_m)/60 + float(from_lon_s)/3600
                            from_fix = QgsPoint(-from_lon_dd, from_lat_dd)
                        except:
                            continue
                      
                    elif ((seg_nr - prev_seg_nr) == 10): # End fix of segment
                        fix_to_name = line[15:45].rstrip()
                        to_lat = line[83:97].rstrip()  # Read fix latitude
                        to_lon = line[97:111].rstrip() # Read fix longitude
                            
                        to_lat_d = to_lat[0:2]
                        to_lat_m = to_lat[3:5]
                        to_lat_s = to_lat[6:len(to_lat) - 1]
                                        
                        to_lon_d = to_lon[0:3]
                        to_lon_m = to_lon[4:6]
                        to_lon_s = to_lon[7:len(to_lon) - 1]
                                                
                        try:
                            to_lat_dd = float(to_lat_d) + float(to_lat_m)/60 + float(to_lat_s)/3600
                            to_lon_dd = float(to_lon_d) + float(to_lon_m)/60 + float(to_lon_s)/3600
                            to_fix = QgsPoint(-to_lon_dd, to_lat_dd)
                        except:
                            continue
                        
                        full_data = True
            
                if full_data == True:
                    try:
                        feat.setGeometry(QgsGeometry.fromPolyline([from_fix, to_fix]))
                        feat.setAttributes([awy_id,
                                                prev_seg_nr,
                                                fix_from_name,
                                                fix_to_name,
                                                seg_prev_eff_date,
                                                seg_prev_MEA])
                        writer.addFeature(feat)
                    except:
                        continue
                        
                    #from_fix = copy.deepcopy(to_fix)
                    from_fix = to_fix
                    to_fix = QgsPoint()
                    fix_from_name = fix_to_name
                    fix_to_name = ''
                    full_data = False
                
                prev_seg_nr = current_seg_nr
                prev_awy_id = current_awy_id
                current_seg_nr = seg_nr

            else: # Awy is not equal current_awy_id ->  record related to new AWY starts
                full_data = False 
                fix_from_name = ''
                fix_to_name = ''
                prev_seg_nr = 10
                if rec_type == 'AWY1':  # Data releted to AWY segment
                    seg_prev_eff_date = line[15:25].rstrip()
                    seg_prev_MEA = line[74:79].lstrip('0')
                prev_awy_id = current_awy_id
                current_seg_nr = seg_nr
            # After taking proper action depending record type, segment number assign awy_ud read ath the begining of the
            # loop to variable current_awy_id
            current_awy_id = awy_id

    return

def regulatory_awy2wpt_shp(in_file, out_file):
    line = in_file.readline()
    awy_id = line[4:9].rstrip()
    current_awy_id = awy_id
    seg_nr = int(line[10:15].lstrip())
    current_seg_nr = seg_nr
    
    for line in in_file:
        rec_type = line[0:4]
        awy_id = line[4:9].rstrip()
        seg_nr = int(line[10:15].lstrip())
        
        if rec_type == 'AWY1' and seg_nr == current_seg_nr:
            seg_c_eff_date = line[15:25].rstrip()
            seg_c_MEA = line[74:79].lstrip('0')
        if rec_type == 'AWY2' and awy_id == current_awy_id and seg_nr == prev_seg:
                fix_lat1 = line[83:97].rstrip()  # Read fix latitude
                fix_lon1 = line[97:111].rstrip() # Read fix longitude
                fix_latlon_start = fix_lat1 + '_' + fix_lon1
    
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
        # TODO - other types of NASR data files
        return
    
    def select_output_file(self):
        """ Select output shp file """
        self.output_file = QFileDialog.getSaveFileName(self.dlg, "Select output shp file ", "", '*.shp')
        self.dlg.leOutputFile.setText(self.output_file)
        return
        
    def faa_nasr2shp(self):
        # TO DO: input validation
        if self.dlg.cbeNasrFile.currentIndex() == 0: # AWY file - awys
            regulatory_awy2awy_shp(self.input_file, self.output_file)
        elif self.dlg.cbeNasrFile.currentIndex() == 1: # seg
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