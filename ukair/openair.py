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

import sys

# Default airspace filter, filters nothing
def default_filter(feature, volume):
  return True

# Default airspace class, returns A-G
def default_class(feature, volume):
  if volume.get('class'):
    return volume['class']
  elif feature.get('class'):
    return feature['class']
  else:
    return "G"

# Default airspace name
def default_name(feature, volume):
  name = []
  if feature.get('localtype') in ("GVS", "HIRTA"):
    name.append(feature['localtype'])
  else:
    name.append(feature['name'])

  if feature['type'] in ("CTA", "CTR", "TMA"):
    name.append(feature['type'])

  if feature.get('localtype') in ("DZ", "LASER", "RMZ", "TMZ"):
    name.append(feature['localtype'])

  if 'suffix' in volume:
    name.append(volume['suffix'])

  if 'seqnum' in volume:
    name.append(str(volume['seqnum']))

  return " ".join(name)

def format_latlon(latlon):
  return "%s:%s:%s %s %s:%s:%s %s" % (
      latlon[:2], latlon[2:4], latlon[4:6], latlon[6:7],
      latlon[8:11], latlon[11:13], latlon[13:15], latlon[15:16])

# Airspace class/type
def do_class(openair, cls):
  openair.append("AC %s" % cls)

# Airspace name
def do_name(openair, name):
  openair.append("AN %s" % name)

# Upper and lower levels
def do_levels(openair, volume):
  openair.append("AH %s" % volume['upper'])
  if volume['lower'] == "GND":
    openair.append("AL SFC")
  else:
    openair.append("AL %s" % volume['lower'])

# Centre of arc or circle
def do_centre(openair, latlon):
  openair.append("V X=%s" % format_latlon(latlon))

# Airspace circle boundary
def do_circle(openair, circle):
  do_centre(openair, circle['centre'])
  openair.append("DC %s" % circle['radius'].split()[0])

# Airspace boundary point
def do_point(openair, point):
  openair.append("DP %s" % format_latlon(point))

# Airspace boundary line
def do_line(openair, line):
  for point in line:
    do_point(openair, point)

# Airspace arc direction
def do_dir(openair, dir):
  if dir == "cw":
    openair.append("V D=+")
  else:
    openair.append("V D=-")

# Airspace arc from/to points
def do_fromto(openair, from_point, to_point):
  openair.append("DB %s, %s" % (format_latlon(from_point),
                                format_latlon(to_point)))

# Airspace arc
def do_arc(openair, arc, from_point):
  do_dir(openair, arc['dir'])
  do_centre(openair, arc['centre'])
  do_fromto(openair, from_point, arc['to'])

# Airspace boundary
def do_boundary(openair, boundary):
  for segment in boundary:
    segtype = list(segment.keys())[0]
    if segtype == 'circle':
      do_circle(openair, segment['circle'])
    elif segtype == 'line':
      do_line(openair, segment['line'])
      point = segment['line'][-1]
    elif segtype == 'arc':
      do_arc(openair, segment['arc'], point)
      point = segment['arc']['to']

  # Close the polygon
  if 'line' in boundary[0] and 'line' in boundary[-1]:
    do_point(openair, boundary[0]['line'][0])

# Convert to openair format
def convert(airspace,
            ffunc=default_filter, nfunc=default_name, cfunc=default_class):
  openair = []
  for feature in airspace:
    for volume in feature['shape']:
      if ffunc(feature, volume):
        do_class(openair, cfunc(feature, volume))
        do_name(openair, nfunc(feature, volume))
        do_levels(openair, volume)
        do_boundary(openair, volume['boundary'])

  return "\n".join(openair) + "\n"

if __name__ == "__main__":
  import argparse
  import json

  parser = argparse.ArgumentParser()
  parser.add_argument("airspace_file", type=argparse.FileType("r"))
  parser.add_argument("openair_file", nargs="?", type=argparse.FileType("w"),
                      default=sys.stdout)
  args = parser.parse_args()

  airspace = json.load(args.airspace_file)

  openair = convert(airspace['airspace'])

  args.openair_file.write(openair)
