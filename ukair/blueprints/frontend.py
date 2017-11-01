import logging
import json

from flask import Blueprint, make_response, render_template, request, current_app
import yaixm

logger = logging.getLogger('ukair')

bp = Blueprint('ukair', __name__)

def get_yaixm(app):
    return app.config['YAIXM_DATA']

def get_loa_names(app):
    return app.config['LOA_NAMES']

def get_wave_names(app):
    return app.config['WAVE_NAMES']

def get_airac_date(app):
    return app.config['AIRAC_DATE']

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

@bp.route("/", methods=['POST'])
def download():
    values = request.form.to_dict()
    logger.info("POST %s %s" % (request.remote_addr, str(values)))

    # Merge LoA
    yaixm_data = get_yaixm(current_app)
    loa_names = [v[4:] for v in values if v.startswith("loa-")]
    loa = [loa for loa in yaixm_data.get('loa', [])
           if loa['name'] in loa_names]
    airspace = yaixm.merge_loa(yaixm_data['airspace'], loa)

    # Get wave areas to be excluded
    wave = get_wave_names(current_app)
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
        filename = "uk%s.sua" % get_airac_date(current_app)
    else:
        atz = "CTR" if values['atz'] == "ctr" else "D"
        type_func = yaixm.make_openair_type(atz = atz,
                ils = atz if values['ils'] == "atz" else "G")
        converter = yaixm.Openair(filter_func=airfilter, type_func=type_func)
        filename = "uk%s.txt" % get_airac_date(current_app)

    data = converter.convert(airspace, obstacles)

    # Convert to DOS format
    dos_data = data.replace("\n", "\r\n") + "\r\n"

    resp  = make_response(dos_data.encode(encoding="ascii"))
    resp.headers['Content-Type'] = "text/plain"
    resp.headers['Content-Disposition'] = "attachment; filename=%s" % filename
    resp.set_cookie('values', json.dumps(values))

    return resp

@bp.route("/", methods=['GET'])
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

    release= "AIRAC: %s" % get_airac_date(current_app)

    resp  = make_response(
        render_template("main.html",
                        values=values,
                        release=release,
                        choices=choices,
                        formats=formats,
                        wave=get_wave_names(current_app),
                        loa=get_loa_names(current_app)))
    return resp
