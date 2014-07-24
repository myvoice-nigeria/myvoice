{% import 'project/_vars.sls' as vars with context %}

include:
  - supervisor.pip
  - project.dirs
  - project.venv
  - postfix

importer_conf:
  file.managed:
    - name: /etc/supervisor/conf.d/{{ pillar['project_name'] }}-celery-importer.conf
    - source: salt://project/worker/celery.conf
    - user: root
    - group: root
    - mode: 600
    - template: jinja
    - context:
        log_dir: "{{ vars.log_dir }}"
        settings: "{{ pillar['project_name'] }}.settings.{{ pillar['environment'] }}"
        virtualenv_root: "{{ vars.venv_dir }}"
        directory: "{{ vars.source_dir }}"
        name: "celery-importer"
        command: "worker"
        flags: "-n importer@%%n --loglevel=INFO --concurrency=1 -Q importer"
    - require:
      - pip: supervisor
      - file: log_dir
      - pip: pip_requirements
    - watch_in:
      - cmd: supervisor_update

importer_process:
  supervisord.running:
    - name: {{ pillar['project_name'] }}-celery-importer
    - restart: True
    - require:
      - file: importer_conf
