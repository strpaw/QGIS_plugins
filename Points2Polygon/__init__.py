# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Points2Polygon
                                 A QGIS plugin
 Creates polugon from points stored in different formats (DMS delimited, DMS compacted, DD etc.)
                             -------------------
        begin                : 2018-06-02
        copyright            : (C) 2018 by Pawel Strzelewicz
        email                : pawel.strzelewicz83@gmail.com
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
    """Load Points2Polygon class from file Points2Polygon.

    :param iface: A QGIS interface instance.
    :type iface: QgisInterface
    """
    #
    from .points2polygon import Points2Polygon
    return Points2Polygon(iface)
