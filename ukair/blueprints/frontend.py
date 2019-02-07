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

from copy import copy
from datetime import datetime
import logging
import json
from pprint import pformat
import os
from textwrap import TextWrapper
import time

from flask import Blueprint, make_response, render_template, request
from flask import current_app, abort
import yaixm

logger = logging.getLogger('ukair')

bp = Blueprint('ukair', __name__)

def get_yaixm(app):
    return app.config['YAIXM_DATA']

def get_loa_names(app):
    return app.config['LOA_NAMES']

def get_wave_names(app):
    return app.config['WAVE_NAMES']

def get_rat_names(app):
    return app.config['RAT_NAMES']

def get_gliding_sites(app):
    return app.config['GLIDING_SITES']

def get_airac_date(app):
    return app.config['AIRAC_DATE']

def get_release_header(app):
    return app.config['YAIXM_DATA']['release'].get('note', "")

def get_commit(app):
    return app.config['YAIXM_DATA']['release'].get('commit')

def get_services(app):
    return app.config['SERVICES']

# Permanently enabled LoA
SPECIAL_LOA = ["CAMBRIDGE RAZ"]

# Default UI settings
DEFAULT_VALUES = {'noatz': "classg",
                  'microlight': "exclude",
                  'hgl': "exclude",
                  'obstacle': "exclude",
                  'glider': "exclude",
                  'atz': "ctr",
                  'ils': "atz",
                  'format': "openair",
                  'maxlevel': "66000",
                  'north': "59",
                  'south': "50",
                  'homesite': "None",
                  'radiofreq': "exclude"}

# NOTAMS for today and tomorrow
NOTAMS = ["today_south", "today_north", "tomorrow_south", "tomorrow_north"]

# Get NOTAM update times
def get_notams(app):
    notam_path = current_app.config['NOTAM_DIR']

    notams = {}
    for n in NOTAMS:
        try:
            notam_filename = n + ".pdf"
            stat = os.stat(os.path.join(notam_path, notam_filename))
            notams[n] = time.strftime("%H:%M %a %d/%m/%y",
                                       time.localtime(stat.st_mtime))
        except FileNotFoundError:
            notams[n] = "unavailable"

    return notams

def get_value(values, item):
    return values.get(item, DEFAULT_VALUES[item])

@bp.route("/download", methods=['GET'])
def download():
    values = request.args.to_dict()
    logger.info("GET %s %s" % (request.remote_addr, str(values)))

    # Check request looks at least approximately correct
    if 'format' not in values:
        logger.info("BAD_REQUEST")
        abort(400)

    yaixm_data = get_yaixm(current_app)

    # Get obstacles
    if get_value(values, 'obstacle') == "include":
        obstacles = yaixm_data.get('obstacle', [])
    else:
        obstacles = []

    # Merge LoA
    loa_names = [v[4:] for v in values if v.startswith("loa-")]
    loa_names.extend(SPECIAL_LOA)
    loa = [loa for loa in yaixm_data.get('loa', [])
           if loa['name'] in loa_names]
    airspace = yaixm.merge_loa(yaixm_data['airspace'], loa)

    # RA(T)s
    rat_names = [v[4:] for v in values if v.startswith("rat-")]
    rats = [rat for rat in yaixm_data.get('rat', [])
            if rat['name'] in rat_names]

    if get_value(values, 'format') == "ratonly":
        # Replace airspace with RA(T)s, remove obstacles
        airspace = rats
        obstacles = []
    else:
        # Add RA(T)s to airspace
        airspace.extend(rats)

    # Radio frequencies
    if get_value(values, 'radiofreq') == "include":
        airspace = yaixm.merge_service(airspace, get_services(current_app))

    # Get wave areas to be excluded
    wave = copy(get_wave_names(current_app))
    include_wave = [v[5:] for v in values if v.startswith("wave-")]
    for w in include_wave:
        if w in wave:
            wave.remove(w)
    exclude = [{'name': w, 'type': "D_OTHER"} for w in wave]

    # Exclude home gliding site
    exclude.append({'name': get_value(values, 'homesite'),
                    'type': "OTHER",
                    'localtype': "GLIDER"})

    # Define filter function
    try:
        north = float(get_value(values, 'north'))
        south = float(get_value(values, 'south'))
        max_level = int(get_value(values, 'maxlevel'))
    except ValueError:
        logging.info("BAD_REQUEST")
        abort(400)

    airfilter = yaixm.make_filter(
        noatz=get_value(values, 'noatz') != 'exclude',
        microlight=get_value(values, 'microlight') != 'exclude',
        hgl=get_value(values, 'hgl') != 'exclude',
        gliding_site=get_value(values, 'glider') != 'exclude',
        north=north,
        south=south,
        max_level=max_level,
        exclude=exclude)

    # File header
    header = current_app.config.get('HEADER', "")

    # Release header
    header += "\n"
    header += get_release_header(current_app)

    # Diagnostic header
    header += "\nAIRAC: {}\n".format(get_airac_date(current_app))
    header += "Produced by asselect.uk: {}\n".format(
            datetime.utcnow().isoformat())

    commit = get_commit(current_app)
    if commit:
        header += "Commit: {}\n".format(commit)

    wrapper = TextWrapper(width=70, subsequent_indent="           ")
    header += wrapper.fill(
            "Settings: {}".format(pformat(values, width=9999, compact=True)))

    # Airspace convert
    if get_value(values, 'format') == "tnp":
        # TNP class
        atz = "D" if get_value(values, 'atz') == "classd" else None
        ils = {'classf': "F",
               'classg': "G",
               'atz': atz}.get(get_value(values, 'ils'))
        glider = {'classf': "F",
                  'classg': "G",
                  'gsec': None}.get(get_value(values, 'glider'))
        noatz = "F" if get_value(values, 'noatz') == "classf" else "G"
        ul = "F" if get_value(values, 'microlight') == "classf" else "G"
        class_func = yaixm.make_tnp_class(atz=atz, ils=ils, glider=glider,
                                          noatz=noatz, ul=ul)

        # TNP type
        ils = "CTA/CTR" if get_value(values, 'ils') == "atz" else "OTHER"
        glider = "GSEC" if get_value(values, 'glider') == "gsec" else "OTHER"
        type_func = yaixm.make_tnp_type(ils=ils, glider=glider)

        converter = yaixm.Tnp(filter_func=airfilter, header=header,
                              class_func=class_func, type_func=type_func)
        filename = "uk%s.sua" % get_airac_date(current_app)
    else:
        # Openair type
        atz = "CTR" if get_value(values, 'atz') == "ctr" else "D"
        noatz = "F" if get_value(values, 'noatz') == "classf" else "G"
        ul = "F" if get_value(values, 'microlight') == "classf" else "G"

        ils = {'classf': "F",
               'classg': "G",
               'atz': atz}.get(get_value(values, 'ils'))

        glider = {'classf': "F",
                  'classg': "G",
                  'gsec': "W"}.get(get_value(values, 'glider'))

        type_func = yaixm.make_openair_type(atz=atz, ils=ils, glider=glider,
                                            noatz=noatz, ul=ul)

        converter = yaixm.Openair(filter_func=airfilter, type_func=type_func,
                                  header=header)
        filename = "uk%s.txt" % get_airac_date(current_app)

    data = converter.convert(airspace, obstacles)

    # Convert to DOS format
    dos_data = data.replace("\n", "\r\n") + "\r\n"

    resp  = make_response(dos_data.encode(encoding="ascii"))
    resp.headers['Content-Type'] = "text/plain"
    resp.headers['Content-Disposition'] = "attachment; filename=%s" % filename
    resp.set_cookie('values', value=json.dumps(values), max_age=63072000)

    return resp

@bp.route("/", methods=['GET'])
def home():
    if current_app.config['YAIXM_DATA'] is None:
        resp = make_response(render_template("error.html", error="Bad YAIXM data!"))
        return resp

    try:
        values = json.loads(request.cookies.get('values'))
        for v in DEFAULT_VALUES:
            if v not in values:
                values[v] = DEFAULT_VALUES[v]
    except TypeError:
        values = DEFAULT_VALUES

    choices = [
        {'name': "noatz",
         'label': "Training A/F",
         'options': [{'value': "exclude", 'option': "Exclude"},
                     {'value': "classf", 'option': "Class F"},
                     {'value': "classg", 'option': "Class G"}]
        },
        {'name': "glider",
         'label': "Gliding A/F",
         'options': [{'value': "exclude", 'option': "Exclude"},
                     {'value': "gsec", 'option': "Gliding Sector"},
                     {'value': "classf", 'option': "Class F"},
                     {'value': "classg", 'option': "Glass G"}]
        },
        {'name': "microlight",
         'label': "Microlight A/F",
         'options': [{'value': "exclude", 'option': "Exclude"},
                     {'value': "classf", 'option': "Class F"},
                     {'value': "classg", 'option': "Class G"}]
        },
        {'name': "obstacle",
         'label': "Obstacle",
         'options': [{'value': "exclude", 'option': "Exclude"},
                     {'value': "include", 'option': "Include"}]
        },
        {'name': "hgl",
         'label': "HIRTA/GVS",
         'options': [{'value': "exclude", 'option': "Exclude"},
                     {'value': "include", 'option': "Include"}]
        },
        {'name': "atz",
         'label': "ATZ",
         'options': [{'value': "classd", 'option': "Class D"},
                     {'value': "ctr", 'option': "Control Zone"}]
        },
        {'name': "ils",
         'label': "ILS Feather",
         'options': [{'value': "atz", 'option': "As ATZ"},
                     {'value': "classf", 'option': "Class F"},
                     {'value': "classg", 'option': "Class G"}]
        }
    ]

    formats = [{'name': "openair", 'label': "OpenAir (recommended)"},
               {'name': "tnp", 'label': "TNP"},
               {'name': "ratonly", 'label': "OpenAir, RA(T) only"}] 

    maxlevels = [{'value': "66000", 'label': "Unlimited"},
                 {'value': "19500", 'label': "FL195"},
                 {'value': "12500", 'label': "FL125"},
                 {'value': "10500", 'label': "FL105"},
                 {'value': "6500", 'label': "FL65"}]

    norths = [{'value': "59", 'label': "None"},
              {'value': "54.9", 'label': "Carlisle"},
              {'value': "53.7", 'label': "Hull"},
              {'value': "52.9", 'label': "Nottingham"}]

    souths = [{'value': "49", 'label': "None"},
              {'value': "51.8", 'label': "Oxford"},
              {'value': "52.9", 'label': "Nottingham"},
              {'value': "53.7", 'label': "Hull"},
              {'value': "54.9", 'label': "Carlisle"}]

    gliding_sites = get_gliding_sites(current_app)

    radiofreq = [{'value': 'exclude', 'label': "Exclude"},
                 {'value': 'include', 'label': "Append to name"}]

    release = "AIRAC: %s" % get_airac_date(current_app)

    loa = [loa for loa in get_loa_names(current_app) if loa not in SPECIAL_LOA]

    resp  = make_response(
        render_template("main.html",
                        values=values,
                        release=release,
                        choices=choices,
                        formats=formats,
                        wave=get_wave_names(current_app),
                        loa=loa,
                        rat=get_rat_names(current_app),
                        maxlevels=maxlevels,
                        norths=norths,
                        souths=souths,
                        glidingsites=gliding_sites,
                        radiofreq=radiofreq,
                        notams=get_notams(current_app)))
    return resp

@bp.route("/release", methods=['GET'])
def release():
    resp = make_response(
        render_template("release.html",
                        release_text=get_release_header(current_app))
    )
    return resp
