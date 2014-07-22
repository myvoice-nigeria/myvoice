base:
  "*":
    - project
    - devs
  'environment:local_vagrant':
    - match: grain
    - local
  'environment:staging':
    - match: grain
    - staging.env
    - staging.secrets
  'environment:production':
    - match: grain
    - production.env
    - production.secrets
