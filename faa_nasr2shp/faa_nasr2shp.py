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
    """ Converts FAA NATFIX file to shapefile
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
