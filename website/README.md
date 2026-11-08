# AI-UNION public homepage

Public URL: https://union.zengbo.site/

## Scope and source

This is the public project introduction based on `docs/UNION_CHARTER_v1.0.md` at `b2a30f3af4ad69a679c4860468d744dd285a0098`. It presents the seven defining characteristics, a four-step conceptual organization explorer, core/platform boundaries, and links to the charter, repository, issues and implementation status. Concepts are explicitly distinguished from verified product capabilities. No signup, model execution, customer data, credentials or analytics are involved.

The source is dependency-free HTML/CSS/JavaScript in `public/`. The responsive menu and tabs support keyboard navigation; motion respects the operating system preference. Fonts and assets are local/system-provided, with no third-party asset dependencies.

## Build and preview

```sh
node website/build.mjs
```

The build emits `website/dist/worker.mjs`, a deterministic module containing the six public assets and `handler.mjs`. For static local preview, serve `website/public` with any static HTTP server. The `/charter` redirect is handled by the Worker, so it is available in the deployed site or when previewing the Worker.

## Deployment

Host: Cloudflare Worker `ai-union-home`, custom domain `union.zengbo.site` in the existing `zengbo.site` zone. This project uses the Cloudflare REST API via the connected Cloudflare integration; it does not introduce a new CLI dependency or credentials in source.

Upload `dist/worker.mjs` to the Worker script endpoint as a multipart `application/javascript+module` part named `worker.mjs`, with metadata `{"main_module":"worker.mjs","compatibility_date":"2026-11-05"}`. Attach `union.zengbo.site` through the Workers custom domains API. Cloudflare manages the associated DNS and certificate. Rebuild and upload the same Worker on subsequent changes; do not recreate the domain or modify unrelated resources.

Keep the source commit and returned deployment/version IDs in the release record. To roll back, rebuild the previously deployed source commit and upload it to the same Worker. No database migration is needed.

The Worker serves GET/HEAD, redirects HTTP to HTTPS, links `/charter` to the fixed charter commit, returns a genuine 404 for unknown paths, and includes a restrictive Content Security Policy and ETags. No private services or runtime secrets are required.
