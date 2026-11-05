# Homepage release · 2026-11-05

- Public URL: https://union.zengbo.site/
- Charter source: `docs/UNION_CHARTER_v1.0.md` at `b2a30f3af4ad69a679c4860468d744dd285a0098`.
- Cloudflare Worker: `ai-union-home`.
- Cloudflare deployment ID: `425af14b7cd24f8894ab635ccf48ddfe`.
- Domain attachment: `union.zengbo.site`, enabled; Cloudflare returned an associated TLS certificate ID.
- Publication observed: 2026-11-05 17:20 (Asia/Singapore).

## Verification

- `npm run check` passed on Node.js 24.22.1: baseline integrity (82 tasks, 181 dependencies, 5 snapshots) and 9 existing offline action-safety tests. These checks concern existing repository assets, not AU runtime acceptance.
- `node website/build.mjs` and JavaScript syntax checks passed; the final bundle contains exactly six public assets. The temporary responsive QA harness is excluded.
- Invoked the bundled Worker handler with native Request/Response: home and asset GETs, HEAD bodies, matching ETag / 304, missing route / 404, POST / 405, HTTP / 308 and fixed charter redirect / 302 passed.
- Browser inspection: desktop layout and 390px iframe mobile layout; mobile document scroll width equalled client width (375px excluding scrollbar), with no horizontal overflow.
- Browser interaction: four-step explorer, arrow-key navigation, mobile navigation open/close and section navigation passed.
- The public HTTPS domain loaded the complete styled homepage; the deployed explorer changed its selected panel successfully.

This release is a public introduction to the project. It does not establish that the organization runtime, model access, self-improvement or commercial platform has completed implementation or acceptance. The page marks conceptual illustrations and links to implementation status.
