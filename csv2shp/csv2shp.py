# -*- coding: utf-8 -*-
"""
/***************************************************************************
 csv2shp
                                 A QGIS plugin
 csv2shp
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2019-05-16
        git sha              : $Format:%H$
        copyright            : (C) 2019 by csv2shp
        email                : csv2shp
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
from PyQt5.QtCore import *
from PyQt5.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QMessageBox, QWidget, QFileDialog
from qgis.core import *
from osgeo import ogr, osr

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .csv2shp_dialog import csv2shpDialog
import os.path
import csv


w = QWidget()

def dms2dd(dms):
    h =  dms[-1]
    dms_mod = dms[:-1]
    dms_parts = dms_mod.split(' ')

    d = float(dms_parts[0])
    m = float(dms_parts[1])
    s = float(dms_parts[2][:-1])

    dd = d + m / 60 + s / 3600
    if h in ['S', 'W']:
        dd = -dd
    return dd

class csv2shp:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """

        self.input_file = ''
        self.output_file = ''

        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'csv2shp_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = csv2shpDialog()
        self.dlg.pushButtonSelectInput.clicked.connect(self.select_input_file)
        self.dlg.pushButtonSelectOutput.clicked.connect(self.select_output_file)
        self.dlg.pushButtonGenerateSHP.clicked.connect(self.generate_shp)


        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&csv2shp')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'csv2shp')
        self.toolbar.setObjectName(u'csv2shp')

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
        return QCoreApplication.translate('csv2shp', message)


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

        icon_path = ':/plugins/csv2shp/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'csv2shp'),
            callback=self.run,
            parent=self.iface.mainWindow())




    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&csv2shp'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def select_input_file(self):
        """ Opens open file dialog window to select input FAA DOF file """
        input_file = QFileDialog.getOpenFileName(self.dlg, "Select input file ", "", '*.csv')
        self.dlg.lineEditInputCSV.setText(input_file[0])
        self.input_file = input_file[0]
        return input_file

    def select_output_file(self):
        """ Opens save file dialog window to select output file """
        output_file = QFileDialog.getSaveFileName(self.dlg, "Select output CSV file ", "", '*.shp')
        self.dlg.lineEditOutputSHP.setText(output_file[0])
        self.output_file = output_file[0]
        return output_file

    def generate_shp(self):
        crs = QgsCoordinateReferenceSystem()
        crs.createFromId(4326)
        # Defining fields for feature attributes
        out_fields = QgsFields()
        out_fields.append(QgsField("NAME", QVariant.String))
        out_fields.append(QgsField("LAT_DMS", QVariant.String))
        out_fields.append(QgsField("LON_DMS", QVariant.String))
        out_fields.append(QgsField("ELEV", QVariant.Double))
        out_fields.append(QgsField("HGT", QVariant.Double))

        writer = QgsVectorFileWriter(self.output_file, "CP1250", out_fields, QgsWkbTypes.Point, crs,
                                     "ESRI Shapefile")

        # csv_data = 0
        # with open(self.input_file, 'r') as DOF_file:
        #     line_nr = 0
        #     for line in DOF_file:
        #         line_nr += 1
        #         if line_nr < 5:  # Skip first 4 lines
        #             continue
        #         else:
        #             obstacle.parse_dof_line(line, coordinates_dd=True, decode_values=True)
        #
        #             feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(float(obstacle.lon_dd),
        #                                                                 float(obstacle.lat_dd))))
        #             feat.setAttributes([row['NAME'],
        #                                 row['LAT_DMS'],
        #                                 row['LON_DMS']])
        #
        #                     writer.addFeature(feat)
        #                     progress = (line_nr / lines_count) * 100
        #                     self.dlg.progressBar.setValue(progress)
        #
        #         del writer
        #     if self.dlg.checkBoxAddOutputToMap.isChecked():
        #         self.iface.addVectorLayer(self.output_file, '', "ogr")

        with open(self.input_file, 'r') as csv_data:
            line_nr = 0
            for line in csv_data:
                line_nr += 1
            lines_count = line_nr

        feat = QgsFeature()

        with open(self.input_file, 'r') as csv_data:

            line_nr = 0

            reader = csv.DictReader(csv_data, delimiter=';')
            header = reader.fieldnames
            if 2 < 1:
                pass
            # if header != ['NAME', 'X', 'X_UOM', 'Y', 'Y_UOM']:
            #         QMessageBox.critical(w, "Message", '''Wrong CSV file format.
            # Different then: NAME;X;X_UOM;Y;Y_UOM''')

            else:
                for row in reader:
                    line_nr += 1
                    #obstacle.parse_dof_line(line, coordinates_dd=True, decode_values=True)

                    feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(float(dms2dd(row['LAT_DMS'])),
                                                                        float(dms2dd(row['LON_DMS'])))))
                    feat.setAttributes([row['NAME'],
                                        row['LAT_DMS'],
                                        row['LON_DMS']])

                    writer.addFeature(feat)
                    progress = (line_nr / lines_count) * 100
                    self.dlg.progressBar.setValue(progress)
        del writer

        if self.dlg.checkBoxAddToMap.isChecked():
            self.iface.addVectorLayer(self.output_file, '', "ogr")

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