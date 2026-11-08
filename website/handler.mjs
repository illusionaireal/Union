// Bundled after the immutable asset map by build.mjs. No secrets or runtime storage.
const charterUrl = 'https://github.com/illusionaireal/Union/blob/b2a30f3af4ad69a679c4860468d744dd285a0098/docs/UNION_CHARTER_v1.0.md';
const baseHeaders = {
  'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'strict-origin-when-cross-origin',
  'X-Frame-Options': 'DENY',
  'Content-Security-Policy': "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; font-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
};
export default {
  async fetch(request) {
    const url = new URL(request.url);
    if (url.protocol === 'http:') {
      url.protocol = 'https:';
      return new Response(null, { status: 308, headers: { ...baseHeaders, Location: url.href } });
    }
    if (!['GET', 'HEAD'].includes(request.method)) return new Response('Method not allowed', { status: 405, headers: { ...baseHeaders, Allow: 'GET, HEAD' } });
    if (url.pathname === '/charter' || url.pathname === '/charter/') return new Response(null, { status: 302, headers: { ...baseHeaders, Location: charterUrl, 'Cache-Control': 'public, max-age=300' } });
    const asset = assets[url.pathname === '/' ? '/index.html' : url.pathname];
    if (!asset) return new Response(request.method === 'HEAD' ? null : '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>页面未找到 · AI-UNION</title><h1>404 · 页面未找到</h1><p><a href="/">返回 AI-UNION 首页</a></p></html>', { status: 404, headers: { ...baseHeaders, 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' } });
    const headers = { ...baseHeaders, 'Content-Type': asset.type, ETag: asset.etag, 'Cache-Control': 'public, max-age=60, must-revalidate' };
    if (request.headers.get('If-None-Match') === asset.etag) return new Response(null, { status: 304, headers });
    return new Response(request.method === 'HEAD' ? null : asset.content, { headers });
  },
};
