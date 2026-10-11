"""Package the public progress site into one offline HTML document."""
import base64
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
OUTPUT = ROOT / "ai-union-progress.html"


class Dependencies(HTMLParser):
    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in ("src", "href", "srcset") and value:
                if not value.startswith(("#", "data:")):
                    raise ValueError(f"Single HTML has an external dependency: {tag} {name}")


def replace_once(document, source, replacement):
    if document.count(source) != 1:
        raise ValueError("Site template changed; review the single-file packaging")
    return document.replace(source, replacement, 1)


def csp_hash(content):
    digest = hashlib.sha256(content.encode("utf-8")).digest()
    return "'sha256-" + base64.b64encode(digest).decode("ascii") + "'"


def main():
    document = (SITE / "index.html").read_text(encoding="utf-8")
    css = (SITE / "styles.css").read_text(encoding="utf-8")
    app = (SITE / "app.js").read_text(encoding="utf-8")
    data = json.loads((SITE / "data/progress.json").read_text(encoding="utf-8"))
    # HTML parsing precedes JS parsing; escape '<' inside embedded data strings.
    snapshot = "window.UNION_DATA = " + json.dumps(data, ensure_ascii=False).replace("<", "\\u003c") + ";"
    if "</script" in app.lower() or "</style" in css.lower():
        raise ValueError("Unexpected HTML closing tag in inline source")
    icon = base64.b64encode((SITE / "favicon.svg").read_bytes()).decode("ascii")
    document = replace_once(document, 'href="favicon.svg"', 'href="data:image/svg+xml;base64,' + icon + '"')
    document = replace_once(document, '<link rel="stylesheet" href="styles.css">', "<style>" + css + "</style>")
    document = replace_once(document, '  <script src="data/progress.js" defer></script>\n', "")
    document = replace_once(document, '  <script src="app.js" defer></script>\n', "")
    document = replace_once(document, "</body>", "<script>" + snapshot + "</script>\n<script>" + app + "</script>\n</body>")
    policy = ("default-src 'none'; script-src " + csp_hash(snapshot) + " " + csp_hash(app)
              + "; style-src " + csp_hash(css)
              + "; img-src data:; connect-src 'none'; base-uri 'none'; form-action 'none'")
    document = replace_once(document, '<meta charset="utf-8">', '<meta charset="utf-8">\n  <meta http-equiv="Content-Security-Policy" content="' + policy + '">')
    Dependencies().feed(document)
    OUTPUT.write_text(document, encoding="utf-8")
    print(f"Single HTML: {OUTPUT.name} ({OUTPUT.stat().st_size:,} bytes), no external dependencies")


if __name__ == "__main__":
    main()
