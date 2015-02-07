# gdebi resolves dependencies when installing .debs. the -core version doesn't
# require installing lots of gtk deps
gdebi-core:
  pkg.installed

{% set wk_version = '0.12.1' %}

{% if grains.get('cpuarch') == 'x86_64' %}
    {% set wk_arch = 'amd64' %}
    {% set wk_md5sum = '7d5e71726df33f733d67e281f2178c6e' %}
{% else %}
    {% set wk_arch = 'i386' %}
    {% set wk_md5sum = 'bf972bc1a0f948cc283f9e030f248929' %}
{% endif %}

/tmp/wkhtmltox-{{ wk_version }}_linux-precise-{{ wk_arch }}.deb:
  file.managed:
    - source: http://liquidtelecom.dl.sourceforge.net/project/wkhtmltopdf/archive/{{ wk_version }}/wkhtmltox-{{ wk_version }}_linux-precise-{{ wk_arch }}.deb
    - source_hash: md5={{ wk_md5sum }}

wkhtmltopdf:
  cmd.run: 
    - name: gdebi --non-interactive /tmp/wkhtmltox-{{ wk_version }}_linux-precise-{{ wk_arch }}.deb
    - require:
      - file: /tmp/wkhtmltox-{{ wk_version }}_linux-precise-{{ wk_arch }}.deb
    - unless: which wkhtmltopdf
