

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


Development Process
------------------------

We use the `GitHub Flow development <http://scottchacon.com/2011/08/31/github-flow.html>`_
process, so all new work is done in independent feature branches (off of
develop). Pull requests are then used to solicit feedback from another developer.
Only upon receiving a "ship it" from another developer is that code merged to
develop. The develop branch can then been deployed to the staging server, and
once it's been QA'ed by the client, it can be merged to master and deployed
to production.

Unit Testing and Code Format
+++++++++++++++++++++++++++

Unit tests should be written for all new code, and we strive to achieve 100%
test coverage for all new code. We use flake8 to check for proper code formatting.
There is a Travis CI server set up to warn developers if unit tests or code
formatting is broken, and new developers can be added to this list in the
``.travis.yml`` file in the repo.

Static Media
++++++++++++++++++++++++

Static media should be hosted in the repo (rather than using a CDN) to aid with
running the dev server in absence of an internet connection (which may occur
while traveling or if a developer ends up writing code in rural Nigeria).

Data Input
++++++++++++++++++++++++

If you have static data that will never change, you can use an ``initial_data.json``
fixture in Django. If you have some initial data that you want to add, but it
might change later, e.g., via the admin, you can use a fixture and just run the
``loaddata`` management command to add it. If the data source itself will be updated
from time to time and re-imported, you could also write a management command to
parse the source data directly and add it to the Django models. In any of these
cases, the data should most likely be checked in to the repo.

Migrations
++++++++++++++++++++++++

The project uses South for migrations. In case any new migrations get added to
develop before your branch is merged, you will need to (a) roll back your local
database to a state before your migrations, (b) delete your new migrations, (c)
merge develop into your branch, and (d) recreate your migrations based on the
new schema. Only once the migrations are updated should the branch be merged,
and migrations that have landed on develop should never be renumbered or changed
(as they may have been deployed to a server).

Getting a Copy of Production Data
+++++++++++++++++++++++++++++++++

You can download a SQL file of production data by running the following fab
command::

    fab download_prod_db:myvoice_prod.sql

You can then drop and recreate your local database with this data, e.g.::

    dropdb myvoice
    createdb -E UTF8 myvoice
    psql myvoice < myvoice_prod.sql

Copying Production Data to Staging
++++++++++++++++++++++++++++++++++

You can also copy production data to the staging server like so::

    fab copy_prod_db_to_staging

This will completely replace the staging database with the current database
from production.

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

Release and Deploy to Production
++++++++++++++++++++++++++++++++

Once the client has quality assured the ``develop`` branch by reviewing the staging
server, the code should be merge dto the ``master`` branch and deployed to production.
The steps for releasing are:

1. Merge ``develop`` to ``master``, e.g.::

    git pull
    git checkout master
    git update
    git merge develop
    git push

2. Tag the release with today's date and a sequential number indicating the release
   number for the day, e.g.:

    git tag -a vYYYY-MM-DD.N -m "Released vYYYY-MM-DD.N"
    git push origin --tags

3. Run the deployment::

    fab production deploy

