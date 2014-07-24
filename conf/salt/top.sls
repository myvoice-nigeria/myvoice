base:
  '*':
    - base
    - sudo
    - sshd
    - sshd.github
    - locale.utf8
    - project.devs
    - salt.minion
    - project.appneta
  'precise32':
    - vagrant.user
  'roles:salt-master':
    - match: grain
    - salt.master
  'roles:web':
    - match: grain
    - project.web.app
  'roles:worker':
    - match: grain
    - project.worker.wkhtmltox
    - project.worker.default
    - project.worker.sendsms
    - project.worker.importer
    - project.worker.beat
  'roles:balancer':
    - match: grain
    - project.web.balancer
  'roles:db-master':
    - match: grain
    - project.db
  'roles:queue':
    - match: grain
    - project.queue
  'roles:cache':
    - match: grain
    - project.cache
  'roles:sms-gateway':
    - match: grain
    - project.kannel
