{% import 'project/_vars.sls' as vars with context %}

include:
  - project.user

{% set nr_app_name = pillar['project_name'] ~ ' ' ~ pillar['environment'] %}

newrelic_celery_ini:
  file.managed:
    - name: /etc/newrelic-{{ pillar['project_name'] }}-celery.ini
    - source: salt://project/newrelic/newrelic.ini
    - user: {{ pillar['project_name'] }}
    - group: {{ pillar['project_name'] }}
    - mode: 600
    - template: jinja
    - context:
        license_key: {{ pillar['secrets']['NEWRELIC_LICENSE_KEY'] }}
        app_name: {{ nr_app_name }} (celery);{{ nr_app_name }}
    - require:
        - user: project_user
    - watch_in:
      - cmd: supervisor_update

newrelic_gunicorn_ini:
  file.managed:
    - name: /etc/newrelic-{{ pillar['project_name'] }}-gunicorn.ini
    - source: salt://project/newrelic/newrelic.ini
    - user: {{ pillar['project_name'] }}
    - group: {{ pillar['project_name'] }}
    - mode: 600
    - template: jinja
    - context:
        license_key: {{ pillar['secrets']['NEWRELIC_LICENSE_KEY'] }}
        app_name: {{ nr_app_name }} (gunicorn);{{ nr_app_name }}
    - require:
        - user: project_user
    - watch_in:
      - cmd: supervisor_update
