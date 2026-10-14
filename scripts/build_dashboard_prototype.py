"""Build the design-only Dashboard prototype from public website data."""
import base64
import hashlib
import json
from pathlib import Path

from build_single_html import Dependencies, csp_hash, replace_once

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "design/dashboard"
OUTPUT = ROOT / "ai-union-dashboard-prototype.html"


def main():
    public = json.loads((ROOT / "site/data/progress.json").read_text(encoding="utf-8"))
    if public["metrics"]["real_model_calls"] != 0 or public["verification"]["real_agent_verified"]:
        raise ValueError("Prototype requires explicitly simulated public evidence")
    for item in public["artifacts"]:
        if hashlib.sha256(item["content"].encode("utf-8")).hexdigest() != item["sha256"]:
            raise ValueError("Public fixture artifact integrity mismatch")
    data = {key: public[key] for key in ("work", "artifacts", "steps")}
    snapshot = "window.UNION_PROTOTYPE_DATA = " + json.dumps(data, ensure_ascii=False).replace("<", "\\u003c") + ";"
    css = (SOURCE / "styles.css").read_text(encoding="utf-8")
    app = (SOURCE / "app.js").read_text(encoding="utf-8")
    console = (SOURCE / "console.js").read_text(encoding="utf-8")
    if "</script" in (app + console).lower() or "</style" in css.lower():
        raise ValueError("Unexpected HTML closing tag in inline source")
    document = (SOURCE / "index.html").read_text(encoding="utf-8")
    icon = base64.b64encode((ROOT / "site/favicon.svg").read_bytes()).decode("ascii")
    document = replace_once(document, 'href="favicon.svg"', 'href="data:image/svg+xml;base64,' + icon + '"')
    document = replace_once(document, '<link rel="stylesheet" href="styles.css">', "<style>" + css + "</style>")
    document = replace_once(document, '<script src="prototype-data.js"></script>', "<script>" + snapshot + "</script>")
    document = replace_once(document, '<script src="app.js"></script>', "<script>" + app + "</script>")
    document = replace_once(document, '<script src="console.js"></script>', "<script>" + console + "</script>")
    policy = ("default-src 'none'; script-src " + csp_hash(snapshot) + " " + csp_hash(app) + " " + csp_hash(console)
              + "; style-src " + csp_hash(css)
              + "; img-src data:; connect-src 'none'; base-uri 'none'; form-action 'none'")
    document = replace_once(document, '<meta charset="utf-8">', '<meta charset="utf-8">\n  <meta http-equiv="Content-Security-Policy" content="' + policy + '">')
    Dependencies().feed(document)
    OUTPUT.write_text(document, encoding="utf-8")
    print(f"Design prototype: {OUTPUT.name} ({OUTPUT.stat().st_size:,} bytes), standalone, no network or runtime access")


if __name__ == "__main__":
    main()
