# -*- coding: utf-8 -*-
"""
/***************************************************************************
 FAA_DOF2shp
                                 A QGIS plugin
 Converts Federal Aviation Administration DOF (Digital Obstacle File) to shapefile format (shp)
                             -------------------
        begin                : 2018-05-22
        copyright            : (C) 2018 by Pawel Strzelewicz
        email                : pawel.strzelewicz@wp.pl
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load FAA_DOF2shp class from file FAA_DOF2shp.

    :param iface: A QGIS interface instance.
    :type iface: QgisInterface
    """
    #
    from .faa_dof2shp import FAA_DOF2shp
    return FAA_DOF2shp(iface)
