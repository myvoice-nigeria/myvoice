{% import 'project/_vars.sls' as vars with context %}

include:
  - postgresql
  - ufw

user-{{ pillar['project_name'] }}:
  postgres_user.present:
    - name: {{ pillar['project_name'] }}_{{ pillar['environment'] }}
    - createdb: False
    - createuser: False
    - superuser: False
    - password: {{ pillar['secrets']['DB_PASSWORD'] }}
    - encrypted: True
    - require:
      - service: postgresql

user-{{ pillar['project_name'] }}-readonly:
  postgres_user.present:
    - name: {{ pillar['project_name'] }}_{{ pillar['environment'] }}_readonly
    - createdb: False
    - createuser: False
    - superuser: False
    - password: {{ pillar['secrets']['DB_READONLY_PASSWORD'] }}
    - encrypted: True
    - require:
      - service: postgresql

grant-user-{{ pillar['project_name'] }}-readonly:
  cmd.wait:
    - name: sudo -u postgres psql {{ pillar['project_name'] }}_{{ pillar['environment'] }} -c "GRANT SELECT ON ALL TABLES IN SCHEMA public TO {{ pillar['project_name'] }}_{{ pillar['environment'] }}_readonly; ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {{ pillar['project_name'] }}_{{ pillar['environment'] }}_readonly;"
    - watch:
      - postgres_user: user-{{ pillar['project_name'] }}-readonly

database-{{ pillar['project_name'] }}:
  postgres_database.present:
    - name: {{ pillar['project_name'] }}_{{ pillar['environment'] }}
    - owner: {{ pillar['project_name'] }}_{{ pillar['environment'] }}
    - template: template0
    - encoding: UTF8
    - locale: en_US.UTF-8
    - lc_collate: en_US.UTF-8
    - lc_ctype: en_US.UTF-8
    - require:
      - postgres_user: user-{{ pillar['project_name'] }}
      - file: hba_conf
      - file: postgresql_conf

hba_conf:
  file.managed:
    - name: /etc/postgresql/9.1/main/pg_hba.conf
    - source: salt://project/db/pg_hba.conf
    - user: postgres
    - group: postgres
    - mode: 0640
    - template: jinja
    - context:
        servers:
{%- for host, ifaces in salt['mine.get']('roles:web|worker', 'network.interfaces', expr_form='grain_pcre').items() %}
{% set host_addr = vars.get_primary_ip(ifaces) %}
          - {{ host_addr }}
{% endfor %}
    - require:
      - pkg: postgresql
      - cmd: /var/lib/postgresql/configure_utf-8.sh
    - watch_in:
      - service: postgresql

postgresql_conf:
  file.managed:
    - name: /etc/postgresql/9.1/main/postgresql.conf
    - source: salt://project/db/postgresql.conf
    - user: postgres
    - group: postgres
    - mode: 0644
    - template: jinja
    - require:
      - pkg: postgresql
      - cmd: /var/lib/postgresql/configure_utf-8.sh
    - watch_in:
      - service: postgresql

{% for host, ifaces in salt['mine.get']('roles:web|worker', 'network.interfaces', expr_form='grain_pcre').items() %}
{% set host_addr = vars.get_primary_ip(ifaces) %}
db_allow-{{ host_addr }}:
  ufw.allow:
    - name: '5432'
    - enabled: true
    - from: {{ host_addr }}
    - require:
      - pkg: ufw
{% endfor %}

{% if 'postgis' in pillar['postgres_extensions'] %}
ubuntugis:
  pkgrepo.managed:
    - humanname: UbuntuGIS PPA
    - ppa: ubuntugis/ppa

postgis-packages:
  pkg:
    - installed
    - names:
      - postgresql-9.1-postgis-2.0
    - require:
      - pkgrepo: ubuntugis
      - pkg: db-packages
    - require_in:
      - virtualenv: venv
{% endif %}

{% for extension in pillar['postgres_extensions'] %}
create-{{ extension }}-extension:
  cmd.run:
    - name: psql -U postgres {{ pillar['project_name'] }}_{{ pillar['environment'] }} -c "CREATE EXTENSION postgis;"
    - unless: psql -U postgres {{ pillar['project_name'] }}_{{ pillar['environment'] }} -c "\dx+" | grep postgis
    - user: postgres
    - require:
      - pkg: postgis-packages
      - postgres_database: database-{{ pillar['project_name'] }}
    - require_in:
      - virtualenv: venv
{% endfor %}
