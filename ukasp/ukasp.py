import json
import os

from flask import Flask, g, make_response, render_template, request

app = Flask(__name__)

def get_airspace():
  if not hasattr(g, 'airspace'):
    with open(os.path.join(app.root_path, "data/airspace.json")) as js:
      g.airspace = json.load(js)

  return g.airspace

def get_loas():
  if not hasattr(g, 'loas'):
    airspace = get_airspace()
    g.loas = [a['name'] for a in airspace if a.get('localtype') == "LOA"]
    g.loas.sort()

  return g.loas

def get_wave():
  if not hasattr(g, 'wave'):
    airspace = get_airspace()
    g.wave = [a['name'] for a in airspace
              if a.get('localtype') == "TRAG" or a.get('localtype') == "NSGA"]
    g.wave.sort()

  return g.wave

@app.route("/", methods=['POST', 'GET'])
def home():
  if request.method == 'POST':
    values = request.form.to_dict()
    print(values)
  else:
    try:
      values = json.loads(request.cookies.get('values'))
    except TypeError:
      values = {}

  choices = [{'name': "nonatz", 'label': "Non-ATZs",
              'value1': "include", 'option1': "Include",
              'value2': "exclude", 'option2': "Exclude"
             },
             {'name': "microlight", 'label': "Microlight",
              'value1': "include", 'option1': "Include",
              'value2': "exclude", 'option2': "Exclude"
             },
             {'name': "hirta", 'label': "HIRTAs",
              'value1': "include", 'option1': "Include",
              'value2': "exclude", 'option2': "Exclude"
             },
             {'name': "gvs", 'label': "GVSs",
              'value1': "include", 'option1': "Include",
              'value2': "exclude", 'option2': "Exclude"
             },
             {'name': "glider", 'label': "Gliding Sites",
              'value1': "include", 'option1': "Include",
              'value2': "exclude", 'option2': "Exclude"
             },
             {'name': "atz", 'label': "ATZs",
              'value1': "classd", 'option1': "Class D",
              'value2': "classg", 'option2': "Class G"
             },
             {'name': "ils", 'label': "ILS Feathers",
              'value1': "classd", 'option1': "Class D",
              'value2': "classg", 'option2': "Class G"
             }]

  resp  = make_response(
     render_template("main.html", choices=choices, values=values, wave=get_wave(), loas=get_loas()))
  resp.set_cookie('values', json.dumps(values))
  return resp
