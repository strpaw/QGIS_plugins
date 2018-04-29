# -*- coding: utf-8 -*-
"""
/***************************************************************************
 qgsAzmDist2LatLon
                                 A QGIS plugin
 Calculates second point latitude, longitude based on first point latitude, longitude and azimuth and distance to from first point to second point
                             -------------------
        begin                : 2018-04-28
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
    """Load qgsAzmDist2LatLon class from file qgsAzmDist2LatLon.

    :param iface: A QGIS interface instance.
    :type iface: QgisInterface
    """
    #
    from .qgs_azm_dist2lat_lon import qgsAzmDist2LatLon
    return qgsAzmDist2LatLon(iface)
