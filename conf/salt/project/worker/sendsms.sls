{% import 'project/_vars.sls' as vars with context %}

include:
  - supervisor.pip
  - project.dirs
  - project.venv
  - postfix

sendsms_conf:
  file.managed:
    - name: /etc/supervisor/conf.d/{{ pillar['project_name'] }}-celery-sendsms.conf
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
        name: "celery-sendsms"
        command: "worker"
        flags: "-n sendsms@%%n --loglevel=INFO --concurrency=5 -Q sendsms"
    - require:
      - pip: supervisor
      - file: log_dir
      - pip: pip_requirements
    - watch_in:
      - cmd: supervisor_update

sendsms_process:
  supervisord.running:
    - name: {{ pillar['project_name'] }}-celery-sendsms
    - restart: True
    - require:
      - file: sendsms_conf
