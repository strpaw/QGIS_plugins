# -*- coding: utf-8 -*-
"""
/***************************************************************************
 qgsCsvAzmDist2LatLon
                                 A QGIS plugin
 Calculates latitude, longitude based on reference point latitude, longitude
    and azimuth and distance stored in csv file
                             -------------------
        begin                : 2018-04-29
        copyright            : (C) 2018 by Paweł Strzelewicz
        email                : Q
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
    """Load qgsCsvAzmDist2LatLon class from file qgsCsvAzmDist2LatLon.

    :param iface: A QGIS interface instance.
    :type iface: QgisInterface
    """
    #
    from .qgs_csv_azm_dist2lat_lon import qgsCsvAzmDist2LatLon
    return qgsCsvAzmDist2LatLon(iface)
