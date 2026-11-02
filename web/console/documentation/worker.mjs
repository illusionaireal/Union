import html from './index.html';
import css from './document.css';
import script from './document.js';
import icon from './favicon.svg';

// Fixed, read-only resources. No bindings, upstream requests, credentials or logs.
const files = new Map([
  ['/', [html, 'text/html; charset=utf-8']],
  ['/document.css', [css, 'text/css; charset=utf-8']],
  ['/document.js', [script, 'application/javascript; charset=utf-8']],
  ['/favicon.svg', [icon, 'image/svg+xml']],
  ['/robots.txt', ['User-agent: *\nDisallow: /\n', 'text/plain; charset=utf-8']],
]);
const headers = {
  'Content-Security-Policy': "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'",
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'Referrer-Policy': 'no-referrer',
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
  'Cache-Control': 'public, max-age=0, must-revalidate',
  'X-Robots-Tag': 'noindex, nofollow',
};
export default {
  fetch(request) {
    if (!['GET', 'HEAD'].includes(request.method)) return new Response('Method not allowed', { status: 405, headers: { ...headers, Allow: 'GET, HEAD' } });
    const file = files.get(new URL(request.url).pathname);
    if (!file) return new Response(request.method === 'HEAD' ? null : 'Not found', { status: 404, headers });
    return new Response(request.method === 'HEAD' ? null : file[0], { headers: { ...headers, 'Content-Type': file[1] } });
  },
};
