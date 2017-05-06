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
    for lt, v in [("NOATZ2", 'nonatz'), ("UL", 'microlight'),
                  ("HIRTA", 'hirta'), ("GVS", 'gvs'), ("RTM", 'obstacle')]:
      if localtype == lt and values[v] == "exclude":
       return False

    if localtype == "GLIDER" and not feature.get('rules') and \
       values['glider'] == "exclude":
      return False

    # Wave and LoA
    if localtype == "GLIDER" and\
       {"LOA", "NOSSR", "TRA"} & set(feature.get('rules')):

      if "id-" + feature['name'] not in values:
        return False

    # Above FL105
    if 'fl105' in values and volume['lower'].startswith("FL")\
      and int(volume['lower'][2:]) >= 105:

      return False

    # Min/max latitude
    min_lat, max_lat = minmax_lat(volume)
    if min_lat > int(values['north']):
      return False

    if max_lat < int(values['south']):
      return False

    return True

  return filter_f
