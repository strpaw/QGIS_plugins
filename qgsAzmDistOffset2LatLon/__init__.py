# -*- coding: utf-8 -*-
"""
/***************************************************************************
 qgsAzmDistOffset2LatLon
                                 A QGIS plugin
 Calculates lat, lon base on lat, lon reference pint and azimuth, distance and offset to second point
                             -------------------
        begin                : 2018-04-30
        copyright            : (C) 2018 by Paweł Strzelewicz
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
    """Load qgsAzmDistOffset2LatLon class from file qgsAzmDistOffset2LatLon.

    :param iface: A QGIS interface instance.
    :type iface: QgisInterface
    """
    #
    from .qga_azm_dist_offset2latlon import qgsAzmDistOffset2LatLon
    return qgsAzmDistOffset2LatLon(iface)
