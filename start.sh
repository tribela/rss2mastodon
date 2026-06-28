#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

docker stop newsbot && docker rm newsbot || true

docker run -d --name newsbot \
  --restart=unless-stopped \
  --env-file $PWD/.env \
  -v $PWD/saved:/app/saved \
  rss2mastodon
