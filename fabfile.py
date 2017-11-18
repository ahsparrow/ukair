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

from __future__ import with_statement

import os.path

from fabric.api import cd, env, local, prefix, put, run, sudo, task
from fabric.contrib.files import exists

def init_deploy(base_dir):
    code_dir = os.path.join(base_dir, "ukair")
    if exists(code_dir):
        return

    # Create program directory
    sudo("install --directory --owner=%s --group=%s %s" % (env.user, env.user, base_dir))

    # Create directory for log files
    sudo("install --directory --owner=ukair --group=www-data --mode=774 /var/ukair")

    # Create directory for static files
    static_dir = os.path.join(base_dir, "static")
    run("mkdir -p %s" % static_dir)

    # Check-out application and create virtual environment
    with cd(base_dir):
        run("git clone https://github.com/ahsparrow/ukair.git")

    with cd(code_dir):
        run("virtualenv -p python3 venv")
        with prefix("source venv/bin/activate"):
            run("pip install -r deploy/requirements.txt")

        # Create web service files
        sudo("cp deploy/ukair_wsgi.service /etc/systemd/system")
        sudo("cp deploy/asselect.uk /etc/nginx/sites-available")

    # Create uWSGI service
    sudo("systemctl enable ukair_wsgi.service")
    sudo("systemctl start ukair_wsgi.service")

    # Add to web server
    sudo("ln -sf /etc/nginx/sites-available/asselect.uk /etc/nginx/sites-enabled")
    sudo("nginx -s reload")

@task
def deploy():
    base_dir = "/srv/www/asselect.uk"
    init_deploy(base_dir)

    code_dir = os.path.join(base_dir, "ukair")
    with cd(code_dir):
        run("git pull")

    sudo("systemctl restart ukair_wsgi.service")

@task
def upload(filename):
    put(filename, "/var/ukair/yaixm.json")
    sudo("systemctl restart ukair_wsgi.service")
