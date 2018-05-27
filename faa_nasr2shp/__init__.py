# -*- coding: utf-8 -*-
"""
/***************************************************************************
 faa_nasr2shp
                                 A QGIS plugin
 Converts FAA NASR data to shapefile
                             -------------------
        begin                : 2018-05-27
        copyright            : (C) 2018 by Pawel Strzelewicz
        email                : @
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
    """Load faa_nasr2shp class from file faa_nasr2shp.

    :param iface: A QGIS interface instance.
    :type iface: QgisInterface
    """
    #
    from .faa_nasr2shp import faa_nasr2shp
    return faa_nasr2shp(iface)
