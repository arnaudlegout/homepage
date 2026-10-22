"""Shared helpers for the migration checks: paths, local server, HTML parsing."""
import csv
import json
import functools
import subprocess
import sys
import threading
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

HERE = Path(__file__).resolve().parent
HOME = HERE.parent
WEB = HOME.parent
TAG = "pre-subdir-migration-2026-10"
APEX = "https://arnaudlegout.fr"
OLD_REPOS = {"formation": WEB / "formation-consulting", "consulting": WEB / "consulting"}
COURSES = {"python-niveau-1.html", "python-avance.html", "python-data-science-niveau-1.html",
           "python-data-science-niveau-2.html", "python-machine-learning.html"}
NOINDEX_OK = {"mentions-legales.html", "404.html", "formation/articles.html",
              "formation/articles/_template-article.html"}
TEMPLATE = "formation/articles/_template-article.html"
sys.stdout.reconfigure(encoding="utf-8")


def url_map():
    with open(HERE / "url-map.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def pages():
    """Every HTML file of the new site, as paths relative to HOME (posix)."""
    return sorted(p.relative_to(HOME).as_posix() for p in HOME.rglob("*.html")
                  if not p.relative_to(HOME).parts[0].startswith(("_", ".")))


def new_url(rel):
    """Public URL of a page of the new site."""
    if rel == "index.html":
        return APEX + "/"
    if rel.endswith("/index.html"):
        return f"{APEX}/{rel[:-len('index.html')]}"
    return f"{APEX}/{rel}"


def old_source(rel):
    """(repo, path in repo) of the page a new page was built from."""
    sec, _, rest = rel.partition("/")
    if sec in OLD_REPOS and rest:
        return OLD_REPOS[sec], (f"formations/{rest}" if rest in COURSES else rest)
    return HOME, rel


def old_html(rel):
    repo, path = old_source(rel)
    if repo == HOME:  # homepage pages changed in place: take them from the tag
        return subprocess.run(["git", "-C", str(HOME), "show", f"{TAG}:{path}"],
                              capture_output=True, check=True).stdout.decode("utf-8")
    return (repo / path).read_text(encoding="utf-8")


def read(rel):
    return (HOME / rel).read_text(encoding="utf-8")


class Links(HTMLParser):
    """Collects href/src of tags (comments and script bodies are skipped by HTMLParser),
    element ids, and visible text outside head/header/nav/footer/script/style."""
    SKIP = {"head", "script", "style", "header", "nav", "footer", "noscript", "template"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs, self.ids, self.text, self.depth = [], set(), [], []
        self.title, self.h1, self.meta, self.links, self._grab = None, [], {}, [], None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "a" and "name" in a:
            self.ids.add(a["name"])
        for k in ("href", "src"):
            if a.get(k) is not None:
                self.refs.append((tag, k, a[k], a))
        if tag == "meta":
            key = a.get("name") or a.get("property")
            if key:
                self.meta.setdefault(key, []).append(a.get("content"))
        if tag == "link":
            self.links.append(a)
        if tag in self.SKIP:
            self.depth.append(tag)
        if tag in ("title", "h1"):
            self._grab = [tag, []]

    def handle_endtag(self, tag):
        if self.depth and self.depth[-1] == tag:
            self.depth.pop()
        if self._grab and self._grab[0] == tag:
            s = " ".join("".join(self._grab[1]).split())
            if tag == "title":
                self.title = s
            else:
                self.h1.append(s)
            self._grab = None

    def handle_data(self, data):
        if self._grab:
            self._grab[1].append(data)
        if not self.depth and data.strip():
            self.text.append(" ".join(data.split()))


def parse(html):
    p = Links()
    p.feed(html)
    p.close()
    return p


# --- local server -----------------------------------------------------------------

SHOT = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;padding:0;background:#fff;overflow:hidden}iframe{border:0;display:block}
</style></head><body><iframe id="f" src="%s" width="%d" height="%d" scrolling="no"></iframe>
<script>
document.getElementById('f').addEventListener('load', function () {
  if (%s) {  /* open the burger menu of the sections */
    var m = this.contentDocument.querySelector('.nav__menu');
    if (m) m.classList.add('is-open');
  }
  var foc = %s;  /* focus an element, e.g. to open a dropdown via :focus-within */
  if (foc) { var e = this.contentDocument.querySelector(foc); if (e) e.focus(); }
  var d = this.contentDocument.documentElement;
  document.title = 'H=' + Math.max(d.scrollHeight, this.contentDocument.body.scrollHeight);
});
</script></body></html>"""


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        u = urlsplit(self.path)
        if u.path == "/__shot__":  # iframe wrapper used by screenshots.py
            q = parse_qs(u.query)
            body = (SHOT % (q["src"][0], int(q["w"][0]), int(q["h"][0]),
                           "true" if q.get("open") == ["1"] else "false",
                           json.dumps(q.get("focus", [""])[0]))).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()


def serve(directory):
    """Start a quiet static server on a free port; return its base URL."""
    srv = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(directory)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{srv.server_address[1]}"
