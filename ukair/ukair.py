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

from flask import Flask, make_response, render_template, request, current_app
import yaixm

# Default UI settings
DEFAULT_VALUES = {'noatz': "include",
                  'microlight': "exclude",
                  'hgl': "exclude",
                  'obstacle': "exclude",
                  'glider': "exclude",
                  'atz': "classd",
                  'ils': "atz",
                  'format': "seeyou",
                  'north': "59",
                  'south': "50"}

# Create Flask application
application = Flask(__name__)
application.config.from_envvar("UKAIR_SETTINGS", silent=True)

def init(app):
    with open(app.config['YAIXM_FILE']) as f:
        yaixm_data = yaixm.load(f)

    loa_names = [a['name'] for a in yaixm_data.get('loa', [])]
    loa_names.sort()

    wave_names = [a['name'] for a in yaixm_data['airspace']
            if "TRA" in a.get('rules', []) or "NOSSR" in a.get('rules', [])]
    wave_names.sort()

    airac_date = yaixm_data['release']['airac_date'][:10]

    app.config['YAIXM_DATA'] = yaixm_data
    app.config['LOA_NAMES'] = loa_names
    app.config['WAVE_NAMES'] = wave_names
    app.config['AIRAC_DATE'] = airac_date

# Initialise the application
init(application)

# Data access functions
def get_yaixm():
    return current_app.config['YAIXM_DATA']

def get_loa_names():
    return current_app.config['LOA_NAMES']

def get_wave_names():
    return current_app.config['WAVE_NAMES']

def get_airac_date():
    return current_app.config['AIRAC_DATE']

# Download response
@application.route("/", methods=['POST'])
def download():
    values = request.form.to_dict()

    # Merge LoA
    yaixm_data = get_yaixm()
    loa_names = [v[4:] for v in values if v.startswith("loa-")]
    loa = [loa for loa in yaixm_data.get('loa', [])
           if loa['name'] in loa_names]
    airspace = yaixm.merge_loa(yaixm_data['airspace'], loa)

    # Get wave areas to be excluded
    wave = get_wave_names()
    include_wave = [v[5:] for v in values if v.startswith("wave-")]
    for w in include_wave:
        wave.remove(w)
    exclude = [{'name': w, 'type': "D_OTHER"} for w in wave]

    # Define filter function
    airfilter = yaixm.make_filter(
        noatz = values['noatz'] == 'include',
        microlight = values['microlight']=='include',
        hgl = values['hgl']=='include',
        gliding_site = values['glider']=='include',
        north = int(values['north']),
        south = int(values['south']),
        max_level = 10500 if 'fl105' in values else None,
        exclude=exclude)

    # Get obstacles
    if values['obstacle'] == "include":
        obstacles = yaixm_data.get('obstacle', [])
    else:
        obstacles = []

    # Convert to Openair/TNP
    if values['format'] == "tnp":
        converter = yaixm.Tnp(filter_func=airfilter)
        filename = "uk%s.sua" % get_airac_date()
    else:
        atz = "CTR" if values['atz'] == "ctr" else "D"
        type_func = yaixm.make_openair_type(atz = atz,
                ils = atz if values['ils'] == "atz" else "G")
        converter = yaixm.Openair(filter_func=airfilter, type_func=type_func)
        filename = "uk%s.txt" % get_airac_date()

    data = converter.convert(airspace, obstacles)

    # Convert to DOS format
    dos_data = data.replace("\n", "\r\n") + "\r\n"

    resp  = make_response(dos_data.encode(encoding="ascii"))
    resp.headers['Content-Type'] = "text/plain"
    resp.headers['Content-Disposition'] = "attachment; filename=%s" % filename
    resp.set_cookie('values', json.dumps(values))

    return resp

# Main web page response
@application.route("/", methods=['GET'])
def home():
    try:
        values = json.loads(request.cookies.get('values'))
        for v in DEFAULT_VALUES:
            if v not in values:
                values[v] = DEFAULT_VALUES[v]
    except TypeError:
        values = DEFAULT_VALUES

    choices = [
        {'name': "noatz", 'label': "No-ATZ Airfield",
         'value1': "exclude", 'option1': "Exclude",
         'value2': "include", 'option2': "Include"
        },
        {'name': "glider", 'label': "Gliding Site",
         'value1': "exclude", 'option1': "Exclude",
         'value2': "include", 'option2': "Include"
        },
        {'name': "microlight", 'label': "Microlight Strip",
         'value1': "exclude", 'option1': "Exclude",
         'value2': "include", 'option2': "Include"
        },
        {'name': "hgl", 'label': "HIRTA/GVS/LASER",
         'value1': "exclude", 'option1': "Exclude",
         'value2': "include", 'option2': "Include"
        },
        {'name': "obstacle", 'label': "Obstacle",
         'value1': "exclude", 'option1': "Exclude",
         'value2': "include", 'option2': "Include"
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

    release= "AIRAC: %s" % get_airac_date()

    resp  = make_response(
        render_template("main.html",
                        values=values,
                        release=release,
                        choices=choices,
                        formats=formats,
                        wave=get_wave_names(),
                        loa=get_loa_names()))
    return resp
