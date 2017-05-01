import json

from flask import Flask, make_response, render_template, request

app = Flask(__name__)

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

  loas = ["MADLEY", "RAGLAN", "BRIZE", "COMPTON BOX", "BRISTOL", "CAMPHILL"]

  resp  = make_response(
     render_template("main.html", choices=choices, values=values, loas=loas))
  resp.set_cookie('values', json.dumps(values))
  return resp
