# gdebi resolves dependencies when installing .debs. the -core version doesn't
# require installing lots of gtk deps
gdebi-core:
  pkg.installed

{% if grains.get('cpuarch') == 'x86_64' %}
/tmp/wkhtmltox-0.12.1_linux-precise-amd64.deb:
  file.managed:
    - source: http://superb-dca3.dl.sourceforge.net/project/wkhtmltopdf/0.12.1/wkhtmltox-0.12.1_linux-precise-amd64.deb
    - source_hash: md5=7d5e71726df33f733d67e281f2178c6e
{% else %}
/tmp/wkhtmltox-0.12.1_linux-precise-i386.deb:
  file.managed:
    - source: http://superb-dca3.dl.sourceforge.net/project/wkhtmltopdf/0.12.1/wkhtmltox-0.12.1_linux-precise-i386.deb
    - source_hash: md5=bf972bc1a0f948cc283f9e030f248929
{% endif %}

wkhtmltopdf:
  cmd.run: 
    - name: gdebi /tmp/wkhtmltox-0.12.1_linux-precise-i386.deb
    - require:
      - file: /tmp/wkhtmltox-0.12.1_linux-precise-i386.deb
    - unless: dpkg --list|grep wkhtmltox
