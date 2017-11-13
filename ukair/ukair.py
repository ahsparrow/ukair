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
import logging, logging.config
import os

from flask import Flask
from werkzeug.utils import find_modules, import_string
import yaixm
import yaml

logger = logging.getLogger('ukair')

# Get page definition blueprints
def register_blueprints(app):
    for name in find_modules('ukair.blueprints'):
        mod = import_string(name)
        if hasattr(mod, 'bp'):
            app.register_blueprint(mod.bp)

def load_yaixm(app):
    # Load airspace data from YAML/JSON file
    yaixm_file = app.config['YAIXM_FILE']
    try:
        with open(yaixm_file) as f:
            try:
                yaixm_data = yaixm.load(f)
            except yaml.YAMLError:
                logger.error("Can't parse YAIXM file %s" % yaixm_file)
                app.config['YAIXM_DATA'] = None
                return
    except FileNotFoundError:
        logger.error("YAIXM file %s doesn't exist" % yaixm_file)
        app.config['YAIXM_DATA'] = None
        return

    loa_names = [a['name'] for a in yaixm_data.get('loa', [])]
    loa_names.sort()

    wave_names = [a['name'] for a in yaixm_data['airspace']
            if "TRA" in a.get('rules', []) or "NOSSR" in a.get('rules', [])]
    wave_names.sort()

    airac_date = yaixm_data['release']['airac_date'][:10]
    logger.info("AIRAC %s" % airac_date)

    app.config['YAIXM_DATA'] = yaixm_data
    app.config['LOA_NAMES'] = loa_names
    app.config['WAVE_NAMES'] = wave_names
    app.config['AIRAC_DATE'] = airac_date

# Flask application factory. config argument is either a dictionary of
# config values, or the name of the environment variable that points to
# a YAML config file.
def create_app(config):
    app = Flask('ukair')

    # Load config from YAML file
    if isinstance(config, str):
        with open(os.getenv(config)) as cf:
            config = yaml.load(cf)

    # Configure app and logging
    config_dict = config['flask']
    app.config.from_mapping(config_dict)

    logging.config.dictConfig(config_dict.get('logging', {'version': 1}))

    # Set URL handlers
    register_blueprints(app)

    # Load YAIXM airspace, etc. data
    load_yaixm(app)

    return app
