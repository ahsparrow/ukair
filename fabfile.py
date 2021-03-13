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

from fabric import task

CONFIG = {
    'deploy': {
        'base_dir': "/var/www/asselect.uk",
        'var_dir': "/var/ukair",
        'service': "ukair_wsgi.service",
        'site': "asselect.uk"
    },
    'staging': {
        'base_dir': "/var/www/staging.asselect.uk",
        'var_dir': "/var/ukair_staging",
        'service': "ukair_staging_wsgi.service",
        'site':  "staging.asselect.uk"
    }
}

def init_deploy(c, config):
    base_dir = config['base_dir']
    code_dir = os.path.join(base_dir, "ukair")
    if c.run('test -d {}'.format(code_dir)):
        return

    # Create program directory
    c.sudo("install --directory --owner={} --group={} {}".format(env.user, env.user, base_dir))

    # Create directory for log files
    c.sudo("install --directory --owner=ukair --group=www-data --mode=774 {var_dir}".format(**config))

    # Create directory for NOTAM files
    c.sudo("install --directory --owner=ukair --group=www-data --mode=774 {var_dir}/media/notam".format(**config))

    # Create directory for static files
    static_dir = os.path.join(base_dir, "static")
    c.run("mkdir -p %s" % static_dir)

    # Check-out application and create virtual environment
    with c.cd(base_dir):
        c.run("git clone https://gitlab.com/ahsparrow/ukair.git")

    with c.cd(code_dir):
        c.run("virtualenv -p python3 venv")
        with c.prefix("source venv/bin/activate"):
            c.run("pip install -r deploy/requirements.txt")

        # Create web service files
        c.sudo("cp deploy/{service} /etc/systemd/system".format(**config))
        c.sudo("cp deploy/{site} /etc/nginx/sites-available".format(**config))

    # Create uWSGI service
    c.sudo("systemctl enable {service}".format(**config))
    c.sudo("systemctl start {service}".format(**config))

    # Add to web server
    c.sudo("ln -sf /etc/nginx/sites-available/{site} /etc/nginx/sites-enabled".format(**config))
    c.sudo("nginx -s reload")

@task
def deploy(c, config='deploy'):
    cfg = CONFIG[config]
    init_deploy(c, cfg)

    code_dir = os.path.join(cfg['base_dir'], "ukair")
    with c.cd(code_dir):
        with c.prefix("source venv/bin/activate"):
            c.run("pip install git+https://gitlab.com/ahsparrow/yaixm.git --upgrade --upgrade-strategy only-if-needed")

        c.run("git pull")

        # Copy web service files
        # FIXME Doesn't work with Fabric v2
        #c.sudo("cp deploy/{service} /etc/systemd/system".format(**cfg))
        #c.sudo("cp deploy/{site} /etc/nginx/sites-available".format(**cfg))

    c.sudo("systemctl daemon-reload")
    c.sudo("systemctl restart {service}".format(**cfg))
    c.sudo("nginx -s reload")

@task()
def upload(c, filename, config='deploy'):
    cfg = CONFIG[config]
    c.put(filename, os.path.join(cfg['var_dir'], "yaixm.json"))
    c.sudo("systemctl restart {service}".format(**cfg))
