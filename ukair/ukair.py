# Copyright 2017 Alan Sparrow
#
# This file is part of ukair
#
# ukair is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ukair is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ukair.  If not, see <http://www.gnu.org/licenses/>.

import json
import os

from flask import Flask, g, make_response, render_template, request
import yaixm

app = Flask(__name__)
app.config.update(dict(
    YAIXM_FILE=os.path.join(app.root_path, "data/airspace.json")
))
app.config.from_envvar("UKAIR_SETTINGS", silent=True)

# Load YAIXM data from file
def get_yaixm():
    if not hasattr(g, 'yaixm'):
        with open(app.config['YAIXM_FILE']) as f:
            g.yaixm = yaixm.load(f)

    return g.yaixm

def get_loa():
    if not hasattr(g, 'loas'):
        yaixm_data = get_yaixm()
        g.loa = [a['name'] for a in yaixm_data['loa']]
        g.loa.sort()

    return g.loa

def get_wave():
    if not hasattr(g, 'wave'):
        yaixm_data = get_yaixm()
        g.wave = [a['name'] for a in yaixm_data['airspace']
                  if "TRA" in a.get('rules', []) or "NOSSR" in a.get('rules', [])]
        g.wave.sort()

    return g.wave

def get_airac():
    if not hasattr(g, 'airac'):
        yaixm_data = get_yaixm()
        g.airac = yaixm_data['release']['airac_date'][:10]

    return g.airac

@app.route("/", methods=['POST'])
def download():
    values = request.form.to_dict()

    # Merge LoA
    yaixm_data = get_yaixm()
    loa_names = [v[4:] for v in values if v.startswith("loa-")]
    loa = [loa for loa in yaixm_data['loa'] if loa['name'] in loa_names]
    airspace = yaixm.merge_loa(yaixm_data['airspace'], loa)

    # Get wave areas to be excluded
    wave = get_wave()
    include_wave = [v[5:] for v in values if v.startswith("wave-")]
    for w in include_wave:
        wave.remove(w)
    exclude = [{'name': w, 'type': "D_OTHER"} for w in wave]

    airfilter = yaixm.make_filter(
        noatz = values['noatz'] == 'include',
        microlight = values['microlight']=='include',
        hgl = values['hgl']=='include',
        gliding_site = values['glider']=='include',
        north = int(values['north']),
        south = int(values['south']),
        max_level = 10500 if 'fl105' in values else None,
        exclude=exclude)

    if values['format'] == "tnp":
        converter = yaixm.Tnp(filter_func=airfilter)
        filename = "uk%s.sua" % get_airac()
    else:
        atz = "CTR" if values['atz'] == "ctr" else "D"
        type_func = yaixm.make_openair_type(atz = atz,
                ils = atz if values['ils'] == "atz" else "G")
        converter = yaixm.Openair(filter_func=airfilter, type_func=type_func)
        filename = "uk%s.txt" % get_airac()

    data = converter.convert(airspace)

    # Convert to DOS format
    dos_data = data.replace("\n", "\r\n") + "\r\n"

    resp  = make_response(dos_data.encode(encoding="ascii"))
    resp.headers['Content-Type'] = "text/plain"
    resp.headers['Content-Disposition'] = "attachment; filename=%s" % filename
    resp.set_cookie('values', json.dumps(values))

    return resp

@app.route("/", methods=['GET'])
def home():
    try:
        values = json.loads(request.cookies.get('values'))
    except TypeError:
        values = {
            'noatz': "include",
            'microlight': "exclude",
            'hgl': "exclude",
            'obstacle': "exclude",
            'glider': "exclude",
            'atz': "classd",
            'ils': "classd",
            'format': "seeyou",
            'north': "59",
            'south': "50"
        }

    choices = [
        {'name': "glider", 'label': "Gliding Site",
         'value1': "include", 'option1': "Include",
         'value2': "exclude", 'option2': "Exclude"
        },
        {'name': "noatz", 'label': "No-ATZ Airfield",
         'value1': "include", 'option1': "Include",
         'value2': "exclude", 'option2': "Exclude"
        },
        {'name': "microlight", 'label': "Microlight Strip",
         'value1': "include", 'option1': "Include",
         'value2': "exclude", 'option2': "Exclude"
        },
        {'name': "hgl", 'label': "HIRTA/GVS/LASER",
         'value1': "include", 'option1': "Include",
         'value2': "exclude", 'option2': "Exclude"
        },
        {'name': "obstacle", 'label': "Obstacle",
         'value1': "include", 'option1': "Include",
         'value2': "exclude", 'option2': "Exclude"
        },
        {'name': "atz", 'label': "ATZ",
         'value1': "classd", 'option1': "Class D",
         'value2': "ctr", 'option2': "CTR"
        },
        {'name': "ils", 'label': "ILS Feather",
         'value1': "atz", 'option1': "As ATZ",
         'value2': "classg", 'option2': "Class G"
        }
    ]

    formats = [{'name': "openair", 'label': "OpenAir (recommended)"},
               {'name': "tnp", 'label': "TNP"}]

    release= "AIRAC: %s" % get_airac()

    resp  = make_response(
        render_template("main.html",
                        values=values,
                        release=release,
                        choices=choices,
                        formats=formats,
                        wave=get_wave(),
                        loa=get_loa()))
    return resp
