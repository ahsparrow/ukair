import json
import os

from flask import Flask, g, make_response, render_template, request

from . import airfilter
from . import openair

app = Flask(__name__)

def get_airspace():
  if not hasattr(g, 'airspace'):
    with open(os.path.join(app.root_path, "data/airspace.json")) as js:
      g.airspace = json.load(js)

  return g.airspace

def get_loas():
  if not hasattr(g, 'loas'):
    airspace = get_airspace()
    g.loas = [a['name'] for a in airspace['airspace']
              if "LOA" in a.get('rules', [])]
    g.loas.sort()

  return g.loas

def get_wave():
  if not hasattr(g, 'wave'):
    airspace = get_airspace()
    g.wave = [a['name'] for a in airspace['airspace']
              if "TRA" in a.get('rules', []) or "NOSSR" in a.get('rules', [])]
    g.wave.sort()

  return g.wave

def get_airac():
  if not hasattr(g, 'airac'):
    airspace = get_airspace()
    g.airac = airspace['header']['airac_date']

  return g.airac

@app.route("/", methods=['POST'])
def download():
  values = request.form.to_dict()
  print(values)

  str = openair.convert(get_airspace()['airspace'],
                        ffunc=airfilter.filter_factory(values))
  filename = "uk%s.txt" % get_airac()

  resp  = make_response(str.encode(encoding="ascii"))
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
        'nonatz': "include",
        'microlight': "exclude",
        'hirta': "exclude",
        'gvs': "exclude",
        'obstacle': "exclude",
        'glider': "exclude",
        'atz': "classd",
        'ils': "classd",
        'format': "seeyou",
        'north': "59",
        'south': "50"
    }

  choices = [
      {'name': "nonatz", 'label': "Non-ATZ Airfield",
       'value1': "include", 'option1': "Include",
       'value2': "exclude", 'option2': "Exclude"
      },
      {'name': "microlight", 'label': "Microlight Strip",
       'value1': "include", 'option1': "Include",
       'value2': "exclude", 'option2': "Exclude"
      },
      {'name': "hirta", 'label': "HIRTA",
       'value1': "include", 'option1': "Include",
       'value2': "exclude", 'option2': "Exclude"
      },
      {'name': "gvs", 'label': "GVS",
       'value1': "include", 'option1': "Include",
       'value2': "exclude", 'option2': "Exclude"
      },
      {'name': "obstacle", 'label': "Obstacle",
       'value1': "include", 'option1': "Include",
       'value2': "exclude", 'option2': "Exclude"
      },
      {'name': "glider", 'label': "Gliding Site",
       'value1': "include", 'option1': "Include",
       'value2': "exclude", 'option2': "Exclude"
      },
      {'name': "atz", 'label': "ATZ",
       'value1': "classd", 'option1': "Class D",
       'value2': "classg", 'option2': "Class G"
      },
      {'name': "ils", 'label': "ILS Feather",
       'value1': "classd", 'option1': "Class D",
       'value2': "classg", 'option2': "Class G"
      }
  ]

  formats = [
      {'name': "xcsoar", 'label': "XCSoar"},
      {'name': "seeyou", 'label': "SeeYou"}
  ]

  release= "AIRAC: %s" % get_airac()

  resp  = make_response(
     render_template("main.html",
                     values=values,
                     release=release,
                     choices=choices,
                     formats=formats,
                     wave=get_wave(),
                     loas=get_loas()))
  return resp
