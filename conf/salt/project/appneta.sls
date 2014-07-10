add-appneta-source:
  cmd.run:
    - name: echo "deb http://apt.appneta.com/{{ pillar['secrets']['APPNETA_TOKEN'] }} precise main" > appneta.list
    - cwd: /etc/apt/sources.list.d/
    - unless: sh -c "[ -f appneta.list ]"

add-appneta-key:
  cmd.run:
    - name: echo "tracelyzer.access_key={{ pillar['secrets']['APPNETA_TOKEN'] }}" > /etc/tracelytics.conf
    - unless: which tracelyzer

install-appneta:
  pkg.installed:
    - pkgs:
        - curl
        - ca-certificates
        - liboboe0
        - liboboe-dev
        - tracelyzer
    - require:
        - cmd: add-appneta-key
        - cmd: add-appneta-source

update-nginx:
  pkg.latest:
    - pkgs:
        - nginx-full
    - require:
        - pkg: install-appneta
