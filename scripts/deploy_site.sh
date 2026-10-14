#!/usr/bin/env bash
set -euo pipefail

union_repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$union_repo_dir"
: "${CLOUDFLARE_API_TOKEN:?Configure Cloudflare Pages credentials securely in environment settings}"
: "${CLOUDFLARE_ACCOUNT_ID:?Configure the intended Cloudflare account ID in environment settings}"
union_project_name="${UNION_CF_PROJECT:-ai-union-progress}"
if [[ ! "$union_project_name" =~ ^[a-z0-9][a-z0-9-]{0,56}[a-z0-9]$ ]]; then
  printf '%s\n' 'Use a valid, new Cloudflare Pages project name.' >&2
  exit 2
fi
export WRANGLER_SEND_METRICS=false
python3 scripts/build_site_data.py

# Create a new project first. A name collision stops the script rather than overwriting an existing site.
# Pinned CLI; no token values in arguments, files or output.
if [[ -n "${UNION_WRANGLER_COMMAND:-}" ]]; then
  "$UNION_WRANGLER_COMMAND" pages project create "$union_project_name" --production-branch main
  "$UNION_WRANGLER_COMMAND" pages deploy site --project-name "$union_project_name" --branch main --commit-dirty=true
else
  npx --yes --cache /tmp/union-site-npm-cache wrangler@4.149.0 pages project create "$union_project_name" --production-branch main
  npx --yes --cache /tmp/union-site-npm-cache wrangler@4.149.0 pages deploy site --project-name "$union_project_name" --branch main --commit-dirty=true
fi
