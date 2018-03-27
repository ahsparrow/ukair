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

CONFIG = {
    'deploy': {
        'base_dir': "/srv/www/asselect.uk",
        'var_dir': "/var/ukair",
        'service': "ukair_wsgi.service",
        'site': "asselect.uk"
    },
    'staging': {
        'base_dir': "/srv/www/staging.asselect.uk",
        'var_dir': "/var/ukair_staging",
        'service': "ukair_staging_wsgi.service",
        'site':  "staging.asselect.uk"
    }
}

def init_deploy(config):
    base_dir = config['base_dir']
    code_dir = os.path.join(base_dir, "ukair")
    if exists(code_dir):
        return

    # Create program directory
    sudo("install --directory --owner={} --group={} {}".format(env.user, env.user, base_dir))

    # Create directory for log files
    sudo("install --directory --owner=ukair --group=www-data --mode=774 {var_dir}".format(**config))

    # Create directory for NOTAM files
    sudo("install --directory --owner=ukair --group=www-data --mode=774 {var_dir}/media/notam".format(**config))

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
        sudo("cp deploy/{service} /etc/systemd/system".format(**config))
        sudo("cp deploy/{site} /etc/nginx/sites-available".format(**config))

    # Create uWSGI service
    sudo("systemctl enable {service}".format(**config))
    sudo("systemctl start {service}".format(**config))

    # Add to web server
    sudo("ln -sf /etc/nginx/sites-available/{site} /etc/nginx/sites-enabled".format(**config))
    sudo("nginx -s reload")

@task
def deploy(config='deploy'):
    cfg = CONFIG[config]
    init_deploy(cfg)

    code_dir = os.path.join(cfg['base_dir'], "ukair")
    with cd(code_dir):
        with prefix("source venv/bin/activate"):
            run("pip install git+https://github.com/ahsparrow/yaixm.git --upgrade --upgrade-strategy only-if-needed")

        run("git pull")

    sudo("systemctl restart {service}".format(**cfg))

@task
def upload(filename, config='deploy'):
    cfg = CONFIG[config]
    put(filename, os.path.join(cfg['var_dir'], "yaixm.json"))
    sudo("systemctl restart {service}".format(**cfg))
