# Copyright 2017 Alan Sparrow
#
# This file is part of ukair
#
# Airplot is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Airplot is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Airplot.  If not, see <http://www.gnu.org/licenses/>.

def parse_radius(rstr):
    r = rstr.split()
    if r[1] == "nm":
        radius = float(r[0])
    elif r[1] == "km":
        radius = float(r[0]) / 1.852

    return radius

def parse_lat(cstr):
    lat = int(cstr[:2]) + int(cstr[2:4]) / 60.0 + int(cstr[4:6]) / 3600.0
    return lat

def minmax_lat(volume):
    max_arr = []
    min_arr = []
    for seg in volume['boundary']:
        if 'line' in seg:
            lat = [parse_lat(x) for x in seg['line']]
            max_arr.append(max(lat))
            min_arr.append(min(lat))

        if 'circle' in seg:
            lat = parse_lat(seg['circle']['centre'])
            radius = parse_radius(seg['circle']['radius'])
            max_arr.append(lat + radius / 60)
            min_arr.append(lat - radius / 60)

        if 'arc' in seg:
            # This is an approximation
            lat = parse_lat(seg['arc']['to'])
            max_arr.append(lat)
            min_arr.append(lat)

    return min(min_arr), max(max_arr)

def filter_factory(values):
    def filter_f(feature, volume):
        # Local type
        localtype = feature.get('localtype')
        for lt, v in [("NOATZ", 'nonatz'), ("UL", 'microlight'),
                                    ("HIRTA", 'hirta'), ("GVS", 'gvs'), ("RTM", 'obstacle')]:
            if localtype == lt and values.get(v) == "exclude":
              return False

        if localtype == "GLIDER" and not feature.get('rules') and \
              values.get('glider') == "exclude":
            return False

        # Wave and LoA
        if localtype == "GLIDER" and\
              {"LOA", "NOSSR", "TRA"} & set(feature.get('rules', [])):

            if "id-" + feature['name'] not in values:
                return False

        # Above FL105
        if 'fl105' in values and volume['lower'].startswith("FL")\
            and int(volume['lower'][2:]) >= 105:

            return False

        # Min/max latitude
        min_lat, max_lat = minmax_lat(volume)
        if min_lat > int(values.get('north', 60)):
            return False

        if max_lat < int(values.get('south', 50)):
            return False

        return True

    return filter_f

def class_factory(values):
    def class_f(feature, volume):
        # Class A-D
        cls = volume.get('class') or feature.get('class')
        if cls and cls in "ABCD":
            return cls

        # Danger, prohibited and restricted
        typ  = feature['type']
        if typ == "D":
            return "Q"

        if typ in "RP":
            return typ

        # Drop zone -> Danger
        localtype = feature.get('localtype')
        if localtype == "DZ":
            return "Q"

        # MATZ
        if localtype == "MATZ":
            if values.get('format') == "seeyou":
                return "CTR"
            else:
                return "MATZ"

        # TMZ
        rules = set(feature.get('rules', [])) | set(volume.get('rules', []))
        if localtype == "TMZ" or "TMZ" in rules:
            return "TMZ"

        # RMZ
        if localtype == "RMZ" or "RMZ" in rules:
            return "RMZ"

        # ATZ
        if typ == "ATZ":
            if values.get('atz') == "classd":
                return "D"

        # ILS Feather
        if localtype == "ILS":
            if values.get('ils') == "classd":
                return "D"

        # Radio advisory LoA
        if "RAZ" in rules or "RAA" in rules:
            return "F"

        # LoA and wave boxes
        if set(["LOA", "NOSSR", "TRA"]) & rules:
            return "W"

        # Class E and F
        if cls and cls in "EF":
            return cls

        # Everything else defaults to class C
        return "G"

    return class_f
