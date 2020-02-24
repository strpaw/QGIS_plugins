import re
""" Constants """

# Units of measure
UOM_M = 'M'  # meters
UOM_KM = 'KM'  # kilometers
UOM_NM = 'NM'  # nautical miles
UOM_FEET = 'FEET'  # feet
UOM_SM = 'SM'  # statue miles

# Geometry types

GEOM_POINT = 'POINT'
GEOM_LINE = 'LINE'
GEOM_POLYGON = 'POLYGON'

# Angle types
C_LAT = 'C_LAT'
C_LON = 'C_LON'
A_BRNG = 'BRNG'
A_MAGVAR = 'MAGVAR'


ANGLE_PREFIX = ['-', '+', 'N', 'S', 'E', 'W']
ANGLE_SUFFIX = ['N', 'S', 'E', 'W']
ANGLE_POSITIVE_SIGN = ['+', 'N', 'E']
ANGLE_NEGATIVE_SIGN = ['-', 'S', 'W']

ANGLE_POSITIVE = 'COORD_POSITIVE'
ANGLE_NEGATIVE = 'COORD_NEGATIVE'


S_SPACE = ' '
S_HYPHEN = '-'
S_DEG_WORD = 'DEG'
S_DEG_LETTER = 'D'
S_MIN_WORD = 'MIN'
S_MIN_LETTER = 'M'
S_SEC_WORD = 'SEC'
S_ALL = [S_SPACE, S_HYPHEN, S_DEG_WORD, S_DEG_LETTER, S_MIN_WORD, S_MIN_LETTER, S_SEC_WORD]


# DMS, DM compacted constant formats
F_DMS_COMP = 'F_DMS_COMP'  # DMS compacted
F_DM_COMP = 'F_DM_COMP'  # DM compacted


""" Base class """


class AviationBaseClass:
    """ Aviation base class for storing and manipulating data with aviation content """

    def __init__(self):
        self._is_valid = None
        self._err_msg = ''

    @staticmethod
    def normalize_src_input(src_input):
        """ Normalizes source (input)  value for further processing
        :param src_input: str, input angle string to normalize
        :return: norm_angle: str, normalized angle string
        """
        norm_input = str(src_input).strip()
        norm_input = norm_input.replace(',', '.')
        norm_input = norm_input.upper()
        return norm_input

    @property
    def is_valid(self):
        return self._is_valid

    @is_valid.setter
    def is_valid(self, value):
        self._is_valid = value

    @property
    def err_msg(self):
        return self._err_msg

    @err_msg.setter
    def err_msg(self, value):
        self._err_msg = value


""" Distance """


class Distance(AviationBaseClass):
    def __init__(self, dist_src, dist_uom, allow_negative=False):
        AviationBaseClass.__init__(self)
        self.dist_src = dist_src  # Source distance
        self.dist_uom = dist_uom  # Unit of measure in distance is expressed which
        self.allow_negative = allow_negative  # Indicates if negative values are allowed (e. g. Cartesian)
        self._dist_float = None  # Distance float value
        self.check_distance()

    @staticmethod
    def to_meters(d, from_unit):
        """ Converts distance given in specified unit to distance in meters
        :param d: float, distance in unit specified by parameter from_unit
        :param from_unit: constant unit of measure, unit of measure parameter d_unit
        :return float, distance in unit specified by parameter to_unit
        """
        if from_unit == UOM_M:
            return d
        elif from_unit == UOM_KM:
            return d * 1000
        elif from_unit == UOM_NM:
            return d * 1852
        elif from_unit == UOM_FEET:
            return d * 0.3048
        elif from_unit == UOM_SM:
            return d * 1609.344
        else:
            return None

    @staticmethod
    def from_meters(d, to_unit):
        """ Converts distance given in meters to distance in specified unit
        :param d: float, distance in meters
        :param to_unit: constant unit of measurement
        :return float, distance in unit specified by parameter to_unit
        """
        if to_unit == UOM_M:
            return d
        elif to_unit == UOM_KM:
            return d / 1000
        elif to_unit == UOM_NM:
            return d / 1852
        elif to_unit == UOM_FEET:
            return d / 0.3048
        elif to_unit == UOM_SM:
            return d / 1609.344
        else:
            return None

    def convert_distance(self, d, from_unit, to_unit):
        """ Convert distance between various units
        :param d: float, distance in units specified by parameter from_unit
        :param from_unit: constant measure of units
        :param to_unit: constant measure of unit
        :return float, distance in units specified by parameter to_unit
        """
        if from_unit == to_unit:
            return d
        else:
            d_m = self.to_meters(d, from_unit)  # Convert to meters
            return self.from_meters(d_m, to_unit)  # Convert from meters

    def get_meters(self):
        """ Returns source distance in meters """
        if self.is_valid is True:
            return self.to_meters(self.dist_float, self.dist_uom)

    def to_unit(self, to_unit):
        """ Returns source distance in UOM given in to_unit """
        if self.is_valid is True:
            return self.convert_distance(self.dist_float, self.dist_uom, to_unit)

    def check_distance(self):
        """ Distance validation. Uses float() function to check if distance value is a number """
        if self.dist_src == '':
            self.is_valid = False
            self.err_msg = 'Enter distance\n'
        else:
            try:
                dist_norm = float(self.normalize_src_input(self.dist_src))
                if self.allow_negative is False:
                    if dist_norm < 0:  # Check if distance is less than 0
                        self.is_valid = False
                        self.err_msg = 'Distance error.\n'

                    else:
                        self.is_valid = True
                        self.dist_float = dist_norm
                else:
                    self.is_valid = True
            except ValueError:
                self.is_valid = False
                self.err_msg = 'Distance error.\n'

    def get_distance_str_info_data(self):
        """ Returns string with information: distance string value and UOM
        Useful when we want to add source information in output """
        dist_str = '{} {}'.format(self.dist_src, self.dist_uom)
        return dist_str

    @property
    def dist_float(self):
        return self._dist_float

    @dist_float.setter
    def dist_float(self, value):
        self._dist_float = value


""" Angles """

# Regular expression patterns for DMS and DM formats
coord_lat_comp_regex = {F_DMS_COMP: re.compile(r'''(?P<deg>^\d{2})  # Degrees
                                                   (?P<min>\d{2})  # Minutes
                                                   (?P<sec>\d{2}(\.\d+)?$)  # Seconds 
                                                ''', re.VERBOSE),
                        F_DM_COMP: re.compile(r'''(?P<deg>^\d{2})  # Degrees
                                                  (?P<min>\d{2}(\.\d+)?$)   # Minutes    
                                              ''', re.VERBOSE)}

coord_lon_comp_regex = {F_DMS_COMP: re.compile(r'''(?P<deg>^\d{3})  # Degrees
                                                   (?P<min>\d{2})  # Minutes
                                                   (?P<sec>\d{2}\.\d+$|\d{2}$)  # Seconds 
                                                ''', re.VERBOSE),
                        F_DM_COMP: re.compile(r'''(?P<deg>^\d{3})  # Degrees
                                                  (?P<min>\d{2}\.\d+$|\d{2}$)   # Minutes    
                                              ''', re.VERBOSE)}

coord_symbol_sep_regex = re.compile(r'''(?P<deg>^\d{1,3})  # Degrees
                                        (\W)
                                        (?P<min>\d{1,2})  # Degrees
                                        (\W)
                                        (?P<sec>\d{1,2}\.\d+|\d{1,2})  # Degrees
                                        (\W{1,2}$)
                                    ''', re.VERBOSE)

class AngleBase(AviationBaseClass):
    def __init__(self):
        AviationBaseClass.__init__(self)

    @staticmethod
    def get_angle_parts(angle_norm):
        """
        :param angle_norm: str, normalized angle
        :return: tuple:
        """
        # TODO - if contains string-> norm input will be empty string!
        hem_char = angle_norm[0]
        if hem_char in ANGLE_PREFIX:
            if hem_char in ANGLE_POSITIVE_SIGN:
                return ANGLE_POSITIVE, angle_norm[1:].strip(), hem_char
            elif hem_char in ANGLE_NEGATIVE_SIGN:
                return ANGLE_NEGATIVE, angle_norm[1:].strip(), hem_char
        else:
            hem_char = angle_norm[-1]
            if hem_char in ANGLE_SUFFIX:
                if hem_char in ANGLE_POSITIVE_SIGN:
                    return ANGLE_POSITIVE, angle_norm[:-1].strip(), hem_char
                elif hem_char in ANGLE_NEGATIVE_SIGN:
                    return ANGLE_NEGATIVE, angle_norm[:-1].strip(), hem_char
            else:
                # Begins with digit -> positive sign
                return ANGLE_POSITIVE, angle_norm.strip(), hem_char

    @staticmethod
    def check_angle_range(angle_dd, min_value, max_value):
        """ Checks if angle is within closed interval <min_value, max_value>
        :param angle_dd: float, angle value to check
        :param min_value: float, minimum value
        :param max_value: float, maximum value
        :return: tuple (bool, float) if angle is within the range
                 tuple (bool, None) if angle is out of range
        """
        if min_value <= angle_dd <= max_value:
            return True, angle_dd
        else:
            return False, None

    @staticmethod
    def check_angle_dd(angle_norm):
        """ Checks if angle is in DD format.
        :param angle_norm: float: angle to check
        :return: float, vale of angle if angle is integer of float, const NOT_VALID otherwise
        """
        try:
            dd = float(angle_norm)
            return True, dd
        except ValueError:
            return False, None

    @staticmethod
    def parse_compacted_formats(regex_patterns, coord_part):
        """ Converts latitude or longitude in DMSH format into DD format.
        :param regex_patterns: dictionary of regex object, patterns of DMS formats
        :param coord_part: str, angle to check
        :return: flag, bool,
        :return: dd:, float if DMS is valid format, None otherwise
        :return: coord_format: DMS format constant in which input is if input is valid, None otherwise
        """
        result = False
        dd = None
        for pattern in regex_patterns:  # Check if input matches any pattern
            if regex_patterns.get(pattern).match(coord_part):
                if pattern == F_DMS_COMP:
                    groups = regex_patterns.get(pattern).search(coord_part)
                    d = float(groups.group('deg'))
                    m = float(groups.group('min'))
                    s = float(groups.group('sec'))

                    if m < 60 and s < 60:
                        result = True
                        dd = d + m / 60 + s / 3600

                if pattern == F_DM_COMP:
                    groups = regex_patterns.get(pattern).search(coord_part)
                    d = float(groups.group('deg'))
                    m = float(groups.group('min'))

                    if m < 60:
                        result = True
                        dd = d + m / 60

        return result, dd

    @staticmethod
    def parse_separated_formats(coord):
        # Replace separators (delimiters) with blank (space)
        for sep in S_ALL:
            coord = re.sub(sep, ' ', coord)
        # Replace multiple spaces into single spaces
        coord_mod = re.sub('\s+', ' ', coord)
        c_parts = coord_mod.split(' ')
        if len(c_parts) == 3:  # Assume format DMS separated

            if len(c_parts[0]) > 2 or len(c_parts[1]) > 2:
                return False, None
            else:
                try:
                    d = int(c_parts[0])
                    if d < 0:
                        return False, None
                except ValueError:
                    return False, None

                try:
                    m = int(c_parts[1])
                    if m < 0 or m >= 60:
                        return False, None
                except ValueError:
                    return False, None

                try:
                    s = float(c_parts[2])
                    if s < 0 or s >= 60:
                        return False, None
                except ValueError:
                    return False, None

                try:
                    dd = float(d) + float(m) / 60 + s / 3600
                    return True, dd
                except ValueError:
                    return False, None
        elif len(c_parts) == 2:  # Assume format DM separated

            try:
                d = int(c_parts[0])
                if d < 0:
                    return False, None
            except ValueError:
                return False, None

            try:
                m = int(c_parts[1])
                if m < 0 or m >= 60:
                    return False, None
            except ValueError:
                return False, None

            try:
                dd = float(d) + float(m) / 60
                return True, dd
            except ValueError:
                return False, None

        elif len(c_parts) == 1:  # Assume format DD separated
            try:
                d = float(c_parts[0])
                if d < 0:
                    return False, None
                else:
                    return True, d
            except ValueError:
                return False, None

        else:
            return False, None



    @staticmethod
    def parse_symbols_separated(coord):
        """ Parse coordinates that is separated by degree, minutes, and second symbols"""

        if coord_symbol_sep_regex.match(coord):
            groups = coord_symbol_sep_regex.search(coord)
            d = float(groups.group('deg'))
            m = float(groups.group('min'))
            s = float(groups.group('sec'))

            if m >= 60 or s >= 60:
                return False, None
            else:
                dd = d + m / 60 + s / 3600

                return True, dd
        else:
            return False, None


class CoordinatesPair(AngleBase):
    def __init__(self, lat_src, lon_src):
        AngleBase.__init__(self)
        self.lat_src = lat_src
        self.lon_src = lon_src
        self._lat_dd = None
        self._lon_dd = None
        self.parse_coordinates2dd()

    def parse_coordinates2dd(self):
        lat_valid, lon_valid = False, False

        if self.lat_src == '':  # Blank input
            self.err_msg += 'Enter latitude value!\n'
        else:
            lat_src_norm = self.normalize_src_input(self.lat_src)
            # Get parts of the latitude
            lat_sign, lat_deg_part, lat_hem = self.get_angle_parts(lat_src_norm)
            if lat_hem in ['W', 'E']:
                lat_valid = False
            else:
                # Check DMS, DM compacted formats
                lat_valid, lat_dd = self.parse_compacted_formats(coord_lat_comp_regex, lat_deg_part)
                if lat_valid is False:
                    # Check separated formats
                    lat_valid, lat_dd = self.parse_separated_formats(lat_deg_part)
                    if lat_valid is False:
                        # Check symbol separated
                        lat_valid, lat_dd = self.parse_symbols_separated(lat_deg_part)

                if lat_valid is True:
                    if lat_sign is ANGLE_NEGATIVE:
                        lat_dd = -1 * lat_dd
                    lat_valid, self.lat_dd = self.check_angle_range(lat_dd, -90, 90)

            if lat_valid is False:
                self.err_msg += 'Latitude error!\n'

        if self.lon_src == '':  # Blank input
            self.err_msg += 'Enter longitude value!\n'
        else:
            lon_src_norm = self.normalize_src_input(self.lon_src)
            # Get parts of the latitude
            lon_sign, lon_deg_part, lon_hem = self.get_angle_parts(lon_src_norm)
            if lon_hem in ['N', 'S']:
                lon_valid = False
            else:
                # Check DMS, DM compacted formats
                lon_valid, lon_dd = self.parse_compacted_formats(coord_lon_comp_regex, lon_deg_part)
                if lon_valid is False:
                    # Check separated formats
                    lon_valid, lon_dd = self.parse_separated_formats(lon_deg_part)
                    if lon_valid is False:
                        # Check symbol separated
                        lon_valid, lon_dd = self.parse_symbols_separated(lon_deg_part)

                if lon_valid is True:
                    if lon_sign is ANGLE_NEGATIVE:
                        lon_dd = -1 * lon_dd
                    lon_valid, self.lon_dd = self.check_angle_range(lon_dd, -180, 180)

            if lon_valid is False:
                self.err_msg += 'Longitude error!\n'

        if lat_valid is False or lon_valid is False:
            self.is_valid = False
        else:
            self.is_valid = True

        #
        # lat_valid, lon_valid = False, False
        #
        # if self.lat_src == '':  # Blank input
        #     self.err_msg += 'Enter latitude value!\n'
        # else:
        #     lat_src_norm = self.normalize_src_input(self.lat_src)
        #     # Check if angle is in DD format without hemisphere prefix, suffix
        #     lat_valid, lat_dd = self.check_angle_dd(lat_src_norm)
        #     if lat_valid is True and (lat_dd < -90 or lat_dd > 90):
        #         # Get hemisphere sign na degrees part
        #         lat_sign, lat_deg_part = self.get_angle_parts(lat_src_norm)
        #         lat_valid, lat_dd = self.parse_compacted_formats(coord_lat_comp_regex, lat_deg_part)
        #         if lat_valid is True:
        #             if lat_sign is ANGLE_NEGATIVE:
        #                 lat_dd = -1 * lat_dd
        #         else:
        #             self.err_msg += 'Latitude error!\n'
        #
        #     if lat_valid is True:
        #         lat_valid, self.lat_dd = self.check_angle_range(lat_dd, -90, 90)
        #         if lat_valid is False:
        #             self.err_msg += 'Latitude error!\n'
        #     else:
        #         self.err_msg += 'Latitude error!\n'
        #
        # if self.lon_src == '':  # Blank input
        #     self.err_msg += 'Enter longitude value!\n'
        # else:
        #     lon_src_norm = self.normalize_src_input(self.lon_src)
        #     # Check if angle is in DD format without hemisphere prefix, suffix
        #     lon_valid, lon_dd = self.check_angle_dd(lon_src_norm)
        #     if lon_valid is False or lon_dd < -90 or lon_dd > 90:
        #         # Get hemisphere sign na degrees part
        #         lon_sign, lon_deg_part = self.get_angle_parts(lon_src_norm)
        #         lon_valid, lon_dd = self.parse_compacted_formats(coord_lon_comp_regex, lon_deg_part)
        #         if lon_valid is True:
        #             if lon_sign is ANGLE_NEGATIVE:
        #                 lon_dd = -1 * lon_dd
        #         else:
        #             self.err_msg += 'Latitude error!\n'
        #
        #     if lon_valid is True:
        #         lon_valid, self.lon_dd = self.check_angle_range(lon_dd, -180, 180)
        #         if lon_valid is False:
        #             self.err_msg += 'Longitude error!\n'
        #     else:
        #         self.err_msg += 'Longitude error!\n'
        #
        # if lat_valid is False or lon_valid is False:
        #     self.is_valid = False
        # else:
        #     self.is_valid = True



    @property
    def lat_dd(self):
        return self._lat_dd

    @lat_dd.setter
    def lat_dd(self, value):
        self._lat_dd = value

    @property
    def lon_dd(self):
        return self._lon_dd

    @lon_dd.setter
    def lon_dd(self, value):
        self._lon_dd = value


class MagVar(AngleBase):
    def __init__(self, mag_var_src):
        AngleBase.__init__(self)
        self.mag_var_src = mag_var_src
        self._mag_var_dd = None

    @property
    def mag_var_dd(self):
        return self._mag_var_dd

    @mag_var_dd.setter
    def mag_var_dd(self, value):
        self._mag_var_dd = value


class Bearing(AngleBase):
    def __init__(self, brng_src):
        AngleBase.__init__(self)
        self.brng_src = brng_src
        self._brng_dd = None
        self.parse_brng2dd()

    def parse_brng2dd(self):
        """ Parse source value to convert it into decimal degrees value"""
        if self.brng_src == '':  # No value
            self.is_valid = False
            self.err_msg = 'Enter bearing!\n'
        else:
            brng_norm = self.normalize_src_input(self.brng_src)
            # Check if angle is in DD format without hemisphere prefix, suffix
            self.is_valid, brng_dd = self.check_angle_dd(brng_norm)
            if brng_dd is None:
                self.is_valid, brng_dd = self.parse_compacted_formats(coord_lat_comp_regex, brng_norm)
                # Check separated format
                if brng_dd is None:
                    self.is_valid, brng_dd = self.parse_separated_formats(brng_norm)

            if brng_dd is not None:
                # Check baring range
                self.is_valid, self.brng_dd = self.check_angle_range(brng_dd, 0, 360)

            if self.is_valid is False:
                self.err_msg = 'Bearing error\n'

    def calc_tbrng(self, mag_var_dd):
        """ Calculates true bearing.
        :param: dd_mag_var: float, magnetic variation value
        """
        if mag_var_dd == 0:
            return self.brng_dd
        else:
            tbrng = self.brng_dd + mag_var_dd
            if tbrng > 360:
                tbrng -= 360
            elif tbrng < 360:
                tbrng += 360
            return tbrng

    @property
    def brng_dd(self):
        return self._brng_dd

    @brng_dd.setter
    def brng_dd(self, value):
        self._brng_dd = value
