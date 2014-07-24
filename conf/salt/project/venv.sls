{% import 'project/_vars.sls' as vars with context %}

include:
  - project.dirs
  - project.repo
  {% if pillar['python_version'] > 3 %}
  - python.33
  {% else %}
  - python.27
  {% endif %}

venv:
  virtualenv.managed:
    - name: {{ vars.venv_dir }}
    - python: {{ '/usr/bin/python' ~ pillar['python_version'] }}
    - user: {{ pillar['project_name'] }}
    - require:
      - pip: virtualenv
      - file: root_dir
      - git: project_repo
      - pkg: python-pkgs
      - pkg: python-headers

pip_requirements:
  pip.installed:
    - bin_env: {{ vars.venv_dir }}
    - requirements: {{ vars.build_path(vars.source_dir, 'requirements/production.txt') }}
    - upgrade: true
    - extra_index_url: https://pypi.tracelytics.com
    - require:
      - virtualenv: venv
      - pkg: install-liboboe

project_path:
  file.managed:
    - contents: "{{ vars.source_dir }}"
    - name: {{ vars.build_path(vars.venv_dir, 'lib/python' ~ pillar['python_version'] ~ '/site-packages/project.pth') }}
    - user: {{ pillar['project_name'] }}
    - group: {{ pillar['project_name'] }}
    - require:
      - pip: pip_requirements
