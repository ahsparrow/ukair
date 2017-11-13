from __future__ import with_statement

import os.path

from fabric.api import cd, env, prefix, run, sudo, task
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

    #sudo("systemctl restart ukair_uwsgi.service")
