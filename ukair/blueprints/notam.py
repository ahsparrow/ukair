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

import os
import os.path
import time

from flask import Blueprint, make_response, render_template, current_app

bp = Blueprint('notam', __name__)

# NOTAMS for today and tomorrow
NOTAMS = ["today_south", "today_north", "tomorrow_south", "tomorrow_north"]

@bp.route("/notam", methods=['GET'])
def notam():
    notam_path = current_app.config['NOTAM_DIR']

    updates = {}
    for n in NOTAMS:
        try:
            notam_filename = n + ".pdf"
            stat = os.stat(os.path.join(notam_path, notam_filename))
            updates[n] = time.strftime("%H:%M %a %d/%m/%y",
                                       time.localtime(stat.st_mtime))
        except FileNotFoundError:
            updates[n] = "unavailable"

    resp = make_response(render_template("notam.html", updates=updates))
    return resp
