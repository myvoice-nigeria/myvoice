/tmp/tracelytics-apt-key.pub:
  file.managed:
    - source: https://apt.tracelytics.com/tracelytics-apt-key.pub
    - source_hash: md5=8ca581adfeab7cb10cd19d95e4fdd8d4

add-apt-key:
  cmd.run:
    - name: apt-key add /tmp/tracelytics-apt-key.pub
    - unless: apt-key list | grep 03311F21

add-appneta-source:
  cmd.run:
    - name: echo "deb http://apt.appneta.com/{{ pillar['secrets']['APPNETA_TOKEN'] }} precise main" > appneta.list
    - cwd: /etc/apt/sources.list.d/
    - unless: grep {{ pillar['secrets']['APPNETA_TOKEN'] }} appneta.list
    - require:
        - cmd: add-apt-key

add-appneta-key:
  cmd.run:
    - name: echo "tracelyzer.access_key={{ pillar['secrets']['APPNETA_TOKEN'] }}" > /etc/tracelytics.conf
    - unless: grep {{ pillar['secrets']['APPNETA_TOKEN'] }} /etc/tracelytics.conf

install-liboboe:
  pkg.installed:
    - pkgs:
        - liboboe0
        - liboboe-dev
    - refresh: true
    - require:
        - cmd: add-appneta-key
        - cmd: add-appneta-source

install-tracelyzer:
  pkg.installed:
    - pkgs:
        - tracelyzer
    - require:
        - pkg: install-liboboe

update-nginx:
  pkg.latest:
    - pkgs:
        - nginx-full
    - require:
        - pkg: install-tracelyzer
