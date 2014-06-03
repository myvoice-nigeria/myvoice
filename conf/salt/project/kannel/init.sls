{% import 'project/_vars.sls' as vars with context %}

kannel-extras:
  pkg:
    - installed

kannel:
  pkg:
    - installed
  service:
    - running
    - enable: True
    - watch:
      - file: /etc/kannel/kannel.conf
      - file: /etc/default/kannel
      - pkg: kannel

/etc/kannel/kannel.conf:
  file.managed:
    - source: salt://project/kannel/kannel.conf
    - user: root
    - mode: 644
    - template: jinja

/etc/default/kannel:
  file.managed:
    - source: salt://project/kannel/etc_default
    - user: root
    - mode: 644
    - template: jinja

allow_sendsms:
  ufw.allow:
    - name: '13013'
    - enabled: true
    - require:
      - pkg: ufw

