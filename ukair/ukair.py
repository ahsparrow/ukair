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
import logging
import sys

from flask import Flask
from werkzeug.utils import find_modules, import_string
import yaixm

logger = logging.getLogger('ukair')

# Logging setup
def init_logging(app):
    loglevel = app.config.get('APPLICATION_LOG_LEVEL', logging.INFO)
    logger.setLevel(loglevel)

    logfile = app.config.get('APPLICATION_LOG_FILE', None)
    if logfile:
        ch = logging.FileHandler(logfile)
    else:
        ch = logging.StreamHandler(sys.stderr)

    formatter = logging.Formatter("%(levelname)s [%(asctime)s] %(message)s")
    ch.setFormatter(formatter)

    logger.addHandler(ch)

# Get page definition blueprints
def register_blueprints(app):
    for name in find_modules('ukair.blueprints'):
        mod = import_string(name)
        if hasattr(mod, 'bp'):
            app.register_blueprint(mod.bp)

# Flask application factory
def create_app(config_env):
    app = Flask('ukair')
    app.config.from_envvar(config_env, silent=True)

    init_logging(app)

    with open(app.config['YAIXM_FILE']) as f:
        yaixm_data = yaixm.load(f)

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

    register_blueprints(app)

    return app
