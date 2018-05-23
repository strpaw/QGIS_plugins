# -*- coding: utf-8 -*-
"""
/***************************************************************************
 FAA_DOF2shp
                                 A QGIS plugin
 Converts Federal Aviation Administration DOF (Digital Obstacle File) to shapefile format (shp)
                              -------------------
        begin                : 2018-05-22
        git sha              : $Format:%H$
        copyright            : (C) 2018 by Pawel Strzelewicz
        email                : pawel.strzelewicz@wp.pl
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
from faa_dof2shp_dialog import FAA_DOF2shpDialog
import os.path


def decode_FAA_DOF_verif_status(code):
    """ Decode verification status
    :param code: string
    :return verfif_status: string
    """
    if code == 'O':
        verif_status = 'VERIFIED'
    elif code == 'U':
        verif_status = 'UNVERIFIED'
    else: 
        verif_status = 'NO_DATA'
    return verif_status

def decode_FAA_DOF_lighting(code):
    """ Decode lighting information
    :param code: string
    :return lighting: string
    """
    if code in ['R', 'D', 'H', 'M','S', 'F', 'C', 'L']:
        lighting = 'LIGHTED'
    elif code == 'N':
        lighting = 'NONE'
    elif code == 'U':
        lighting = 'UNKNOWN'
    else:
        lighting = 'NO_DATA'
    return lighting

def decode_FAA_DOF_h_acc(code):
    """ Decode horizonat accuracy information
    :param code: string
    :return h_acc_value: int
    :return h_acc_uom: string
    """
    if code == '1':
        h_acc_value = 20
        h_acc_uom = 'FEET'
    elif code == '2':
        h_acc_value = 50
        h_acc_uom = 'FEET'
    elif code == '3':
        h_acc_value = 100
        h_acc_uom = 'FEET'
    elif code == '4':
        h_acc_value = 250
        h_acc_uom = 'FEET'
    elif code == '5':
        h_acc_value = 500
        h_acc_uom = 'FEET'
    elif code == 6:
        h_acc_value = 1000
        h_acc_uom = 'FEET'
    elif code == 7:
        h_acc_value = 0.5
        h_acc_uom = 'NM'
    elif code == 8:
        h_acc_value = 1
        h_acc_uom = 'NM'
    elif code == 9:
        h_acc_value = -1 # indicates unknown
        h_acc_uom = 'UNKNOWN'
    else:
        h_acc_value = -1 # indicates unknown
        h_acc_uom = 'UNKNOWN'
    return h_acc_value, h_acc_uom    
    
def decode_FAA_DOF_v_acc(code):
    """ Decode vertical accuracy information
    :param code: string
    :return v_acc_value: int
    """
    if code == 'A':
        v_acc_value = 3
    elif code == 'B':
        v_acc_value = 10
    elif code == 'C':
        v_acc_value = 20
    elif code == 'D':
        v_acc_value = 50
    elif code == 'E':
        v_acc_value = 125
    elif code == 'F':
        v_acc_value = 250
    elif code == 'G':
        v_acc_value = 500
    elif code == 'H':
        v_acc_value = 1000
    elif code == 'I':
        v_acc_value = -1 # indicates unknown
    else:
        v_acc_value = -1
    return v_acc_value
    
def decode_FAA_DOF_marking(code):
    """ Decode marking information
    :param code: string
    :return marking: string
    """
    if code in ['P', 'W', 'M', 'F', 'S']:
        marking = 'MARKER'
    elif code == 'N':
        marking = 'NONE'
    elif code == 'U':
        marking = 'UNKNOWN'
    else:
        marking = 'NO_DATA'
    return marking    
    
class FAA_DOF2shp:
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
            'FAA_DOF2shp_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)


        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&FAA_DOF2shp')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'FAA_DOF2shp')
        self.toolbar.setObjectName(u'FAA_DOF2shp')

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
        return QCoreApplication.translate('FAA_DOF2shp', message)


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
        self.dlg = FAA_DOF2shpDialog()

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

        icon_path = ':/plugins/FAA_DOF2shp/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'FAA_DOF2shp'),
            callback=self.run,
            parent=self.iface.mainWindow())

        self.dlg.pbInputFile.clicked.connect(self.select_input_file)
        self.dlg.pbOutputFile.clicked.connect(self.select_output_file)
        self.dlg.pbConvert2shp.clicked.connect(self.convert_FAA_DOF2shp)
        
    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&FAA_DOF2shp'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar
    
    def select_input_file(self):
        """ Select input file with Electronic Obstacle Data """
        self.input_file = QFileDialog.getOpenFileName(self.dlg, "Select input file ", "", '*.dat')
        self.dlg.leInputFile.setText(self.input_file)
        return
    
    def select_output_file(self):
        """ Select output shp file """
        self.output_file = QFileDialog.getSaveFileName(self.dlg, "Select output shp file ", "", '*.shp')
        self.dlg.leOutputFile.setText(self.output_file)
        return
        
    def convert_FAA_DOF2shp(self):
        # Set referefnce system
        crs = QgsCoordinateReferenceSystem()
        crs.createFromId(4326)
        # Defining fileds for feature attributes
        obs_fields = QgsFields()
        obs_fields.append(QgsField("OAS_NUMBER", QVariant.String))  # Obstacle OAS number
        obs_fields.append(QgsField("VERIF_STAT", QVariant.String))  # Verification status
        obs_fields.append(QgsField("CTRY_IDENT", QVariant.String))  # Country identifier
        obs_fields.append(QgsField("ST_IDENT", QVariant.String))    # State identifier
        obs_fields.append(QgsField("LAT_DMS", QVariant.String))     # Obstacle latitude, DMS format
        obs_fields.append(QgsField("LON_DMS", QVariant.String))     # Obstacle longitude, DMS format
        obs_fields.append(QgsField("TYPE", QVariant.String))        # Obstacle type
        obs_fields.append(QgsField("AGL_FEET", QVariant.Int))       # Above ground level height, feet
        obs_fields.append(QgsField("AMSL_FEET", QVariant.Int))      # Above mean sea level height, feet
        obs_fields.append(QgsField("H_ACC", QVariant.Int))          # Horizontal accuracy
        obs_fields.append(QgsField("H_ACC_UOM", QVariant.String))   # Horizontal accuracy - unit of measurement
        obs_fields.append(QgsField("V_ACC", QVariant.Int))          # Vertical accuuracy
        obs_fields.append(QgsField("V_ACC_UOM", QVariant.String))   # Vertical accuuracy - unit of measurement
        obs_fields.append(QgsField("LIGHTING", QVariant.String))    # Information related to lighting: LIGHTED, NONE, UNKNOWN, NO_DATA
        obs_fields.append(QgsField("MARK_IND", QVariant.String))    # Information related to marking: MARKED, NONE, UNKNOWN, NO_DATA

        writer = QgsVectorFileWriter(self.output_file, "CP1250", obs_fields, QGis.WKBPoint, crs, "ESRI Shapefile")
        
        feat = QgsFeature()

        with open (self.input_file, 'r') as DOF_file:
            line_nr = -1
            for line in DOF_file:
                try:
                    line_nr += 1  # TO DO: if line_nr is > than max 'int value'
                    if line_nr < 4:   # Skip first 4 lines
                        continue
                    else:
                        oas_nr = line[0:9]
                        verif_st = decode_FAA_DOF_verif_status(line[10])
                        ctry_id = line[12:14]
                        if ctry_id == '  ':
                            ctry_id = 'NO_DATA'
                            
                        st_id = line[15:17]
                        if st_id == '  ':
                           st_id = 'NO_DATA'
                        
                        lat_dms = line[35:47]
                        lat_d = line[35:37]
                        lat_m = line[38:40]
                        lat_s = line[41:46]
                        lat_h = line[46]
                        lat_dd = float(lat_d) + float(lat_m)/60 + float(lat_s)/3600
                        if lat_h == 'S':
                            lat_dd = -lat_dd
                        
                        lon_dms = line[48:61]
                        lon_d = line[48:51]
                        lon_m = line[52:54]
                        lon_s = line[55:60]
                        lon_h = line[60]
                        lon_dd = float(lon_d) + float(lon_m)/60 + float(lon_s)/3600
                        if lon_h == 'W':
                            lon_dd = -lon_dd
                            
                        o_type = line[62:80].rstrip()
                        agl_feet = int(line[83:88])
                        amsl_feet = int(line[89:95])
                        lighting = decode_FAA_DOF_lighting(line[95])
                        h_acc_value, h_acc_uom = decode_FAA_DOF_h_acc(line[97])
                        v_acc_value = decode_FAA_DOF_v_acc(line[99])
                        v_acc_uom = 'FEET'
                        marking = decode_FAA_DOF_marking(line[101])
                        
                        feat.setGeometry(QgsGeometry.fromPoint(QgsPoint(lon_dd, lat_dd)))
                        feat.setAttributes([oas_nr,
                                            verif_st,
                                            ctry_id,
                                            st_id,
                                            lat_dms,
                                            lon_dms,
                                            o_type,
                                            agl_feet,
                                            amsl_feet,
                                            h_acc_value,
                                            h_acc_uom,
                                            v_acc_value,
                                            v_acc_uom,
                                            lighting,
                                            marking])
                      
                        writer.addFeature(feat)

                except:
                    pass #TO DO - information if DOF line is not in correct format

        del writer

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
