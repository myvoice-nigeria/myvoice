install-appneta:
  cmd.run:
    - name: cd /tmp && wget https://files.appneta.com/install_appneta.sh && sudo sh ./install_appneta.sh {{ pillar['secrets']['APPNETA_TOKEN'] }}
    - unless: dpkg --list|grep tracelyzer

reinstall-nginx:
  cmd.wait:
    - name: apt-get install nginx-full
    - watch:
        - cmd: install-appneta
