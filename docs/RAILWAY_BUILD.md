# Railway build context checklist
#
# If build fails with:
#   "/web/package-lock.json": not found
# then either:
#   1) Root Directory is wrongly set to "web" (must be EMPTY), or
#   2) an old Dockerfile without package-lock.json* wildcard is deployed.
#
# Required Dashboard settings:
#   Root Directory  = (blank)
#   Dockerfile Path = Dockerfile
#   Config file     = /railway.toml

Required files in git (repo root context):
  - Dockerfile
  - web/package.json
  - web/package-lock.json  (tracked; optional for build thanks to wildcard COPY)
  - wpaipublish.py
  - scripts/
  - tests/
  - requirements.txt
