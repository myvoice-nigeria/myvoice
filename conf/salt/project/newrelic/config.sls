{% import 'project/_vars.sls' as vars with context %}

newrelic_celery_ini:
  file.managed:
    - name: /etc/newrelic-{{ pillar['project_name'] }}-celery.ini
    - source: salt://project/newrelic/newrelic.ini
    - user: root
    - group: root
    - mode: 600
    - template: jinja
    - context:
        license_key: {{ pillar['secrets']['NEWRELIC_LICENSE_KEY'] }}
        app_name: {{ pillar['project_name'] }} (celery);{{ pillar['project_name'] }}

newrelic_gunicorn_ini:
  file.managed:
    - name: /etc/newrelic-{{ pillar['project_name'] }}-gunicorn.ini
    - source: salt://project/newrelic/newrelic.ini
    - user: root
    - group: root
    - mode: 600
    - template: jinja
    - context:
        license_key: {{ pillar['secrets']['NEWRELIC_LICENSE_KEY'] }}
        app_name: {{ pillar['project_name'] }} (gunicorn);{{ pillar['project_name'] }}

