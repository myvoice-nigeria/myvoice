

Myvoice
========================

Below you will find basic setup and deployment instructions for the myvoice
project. To begin you should have the following applications installed on your
local development system::

- Python >= 2.6 (2.7 recommended)
- `pip >= 1.1 <http://www.pip-installer.org/>`_
- `virtualenv >= 1.7 <http://www.virtualenv.org/>`_
- `virtualenvwrapper >= 3.0 <http://pypi.python.org/pypi/virtualenvwrapper>`_
- Postgres >= 8.4 (9.1 recommended)
- git >= 1.7

The deployment uses SSH with agent forwarding so you'll need to enable agent
forwarding if it is not already by adding ``ForwardAgent yes`` to your SSH config.


Getting Started
------------------------

MyVoice uses PostGIS, so first install the necessary PostgreSQL extensions,
adjusting the Ubuntu release (precise) PostgreSQL version (9.1) if needed::

    wget -O - http://apt.postgresql.org/pub/repos/apt/ACCC4CF8.asc | sudo apt-key add -
    sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt/ precise-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
    sudo apt-get update
    sudo apt-get install pgdg-keyring postgresql-9.1-postgis-2.1

To setup your local environment you should create a virtualenv and install the
necessary requirements::

    mkvirtualenv myvoice
    $VIRTUAL_ENV/bin/pip install -r $PWD/requirements/dev.txt

Then create a local settings file and set your ``DJANGO_SETTINGS_MODULE`` to use it::

    cp myvoice/settings/local.example.py myvoice/settings/local.py
    echo "export DJANGO_SETTINGS_MODULE=myvoice.settings.local" >> $VIRTUAL_ENV/bin/postactivate
    echo "unset DJANGO_SETTINGS_MODULE" >> $VIRTUAL_ENV/bin/postdeactivate

Exit the virtualenv and reactivate it to activate the settings just changed::

    deactivate
    workon myvoice

Create the Postgres database and run the initial syncdb/migrate::

    createdb -E UTF-8 myvoice
    psql myvoice -c "CREATE EXTENSION postgis;"
    python manage.py syncdb --migrate

You should now be able to run the development server::

    python manage.py runserver

To import the default data, run::

    python manage.py import_regions


Deployment
------------------------

You can deploy changes to a particular environment with
the ``deploy`` command. This takes an optional branch name to deploy. If the branch
is not given, it will use the default branch defined for this environment in
``env.branch``::

    fab staging deploy
    fab staging deploy:new-feature

New requirements or South migrations are detected by parsing the VCS changes and
will be installed/run automatically.
