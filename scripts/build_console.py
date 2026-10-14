"""Reproduce the archived 004 single HTML. The current app uses npm run build:console."""
import base64
from pathlib import Path
from build_single_html import csp_hash, replace_once

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = ROOT / "design/console-legacy"
    css = (ROOT / "design/dashboard/styles.css").read_text(encoding="utf-8") + "\n" + (source / "styles.css").read_text(encoding="utf-8")
    app = (source / "app.js").read_text(encoding="utf-8")
    if "</script" in app.lower() or "</style" in css.lower():
        raise ValueError("Unexpected closing tag")
    html = (source / "index.html").read_text(encoding="utf-8")
    icon = base64.b64encode((ROOT / "site/favicon.svg").read_bytes()).decode("ascii")
    html = replace_once(html, 'href="favicon.svg"', 'href="data:image/svg+xml;base64,' + icon + '"')
    html = replace_once(html, '<link rel="stylesheet" href="styles.css">', "<style>" + css + "</style>")
    html = replace_once(html, '<script src="app.js"></script>', "<script>" + app + "</script>")
    policy = "default-src 'none'; script-src " + csp_hash(app) + "; style-src " + csp_hash(css) + "; img-src data:; connect-src 'self'; base-uri 'none'; form-action 'none'"
    html = replace_once(html, '<meta charset="utf-8">', '<meta charset="utf-8">\n<meta http-equiv="Content-Security-Policy" content="' + policy + '">')
    (ROOT / "ai-union-console.html").write_text(html, encoding="utf-8")
    print("Built ai-union-console.html; same-origin service required, no embedded runtime data")


if __name__ == "__main__":
    main()
