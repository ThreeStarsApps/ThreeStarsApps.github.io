"""Render src/ into the static files served by GitHub Pages.

Run normally to update the committed pages, or use --output .qa/preview to
build a separate, self-contained copy. Only changed files are rewritten.
"""
import argparse
from datetime import date
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
from urllib.parse import quote

try:
    from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
except ModuleNotFoundError:
    raise SystemExit("Install build dependencies first: python -m pip install -r requirements.txt")

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "src/content"


def read_json(name):
    return json.loads((CONTENT / name).read_text(encoding="utf-8"))


class GuideSections(HTMLParser):
    """Derive the table of contents from the guide's own section headings."""

    def __init__(self, html):
        super().__init__()
        self.sections = []
        self.section_id = None
        self.heading = None
        self.feed(html)

    def handle_starttag(self, tag, attributes):
        if tag == "section":
            self.section_id = dict(attributes).get("id")
        elif tag == "h2" and self.section_id:
            self.heading = ""

    def handle_data(self, data):
        if self.heading is not None:
            self.heading += data

    def handle_endtag(self, tag):
        if tag == "h2" and self.heading is not None:
            self.sections.append({"id": self.section_id, "title": self.heading})
            self.heading = None
        elif tag == "section":
            self.section_id = None


def load_content():
    apps = read_json("apps.json")
    for app in apps.values():
        app["playUrl"] = "https://play.google.com/store/apps/details?id=" + app["package"]
        app["downloadUrl"] = "/assets/apks/" + quote(app["apk"])
    guides = read_json("guides.json")
    for guide in guides:
        guide["body"] = (CONTENT / "guides" / (guide["slug"] + ".html")).read_text(encoding="utf-8")
        guide["sections"] = GuideSections(guide["body"]).sections
        for key in ("published", "modified"):
            date.fromisoformat(guide[key])
    return apps, guides


def display_date(value):
    parsed = date.fromisoformat(value)
    return f"{parsed.day} {parsed:%B %Y}"


def structured_data(site, page, app=None, guide=None):
    base = site["url"]
    publisher = {"@id": base + "/#organization"}
    graph = [{
        "@type": "Organization", "@id": publisher["@id"],
        "name": site["name"], "url": base + "/",
        "logo": base + "/assets/images/brand-mark.svg", "email": site["email"],
        "founder": {"@type": "Person", "name": site["developer"]},
    }]
    if page.get("schema") == "website":
        graph.append({
            "@type": "WebSite", "@id": base + "/#website", "name": site["name"],
            "url": base + "/", "publisher": publisher,
        })
    elif page.get("schema") == "app":
        graph.append({
            "@type": "SoftwareApplication", "@id": base + page["url"] + "#app",
            "name": app["name"], "url": base + page["url"], "description": app["description"],
            "operatingSystem": app["os"], "softwareVersion": app["version"],
            "applicationCategory": "UtilitiesApplication",
            "image": base + f'/assets/images/{page["app"]}_icon.png',
            "installUrl": app["playUrl"], "downloadUrl": base + app["downloadUrl"],
            "sameAs": app["playUrl"], "publisher": publisher,
            "offers": {
                "@type": "Offer", "price": "0", "priceCurrency": "EUR",
                "description": "Free download with an optional one-time lifetime licence. " + app["paid"] + ".",
                "url": app["playUrl"],
            },
            "featureList": [title for title, _ in app["features"]],
        })
    elif page.get("schema") == "article":
        graph.append({
            "@type": "TechArticle", "headline": guide["title"], "description": guide["summary"],
            "url": base + page["url"], "mainEntityOfPage": base + page["url"],
            "datePublished": guide["published"], "dateModified": guide["modified"],
            "author": {"@type": "Person", "name": site["developer"], "url": base + "/about/"},
            "publisher": publisher, "image": base + site["socialImage"],
            "about": [{"@id": base + f"/{slug}/#app"} for slug in guide["apps"]],
        })
    if page["breadcrumbs"]:
        crumbs = [{"title": "Home", "url": "/"}] + page["breadcrumbs"]
        graph.append({
            "@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": index, "name": crumb["title"],
                 "item": base + (crumb["url"] or page["url"])}
                for index, crumb in enumerate(crumbs, 1)
            ],
        })
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False).replace("<", "\\u003c")


def destination(url):
    """Map registered public URLs to files; reject non-local paths."""
    if not url.startswith("/") or ".." in url.split("/") or "\\" in url:
        raise ValueError(f"Invalid route: {url}")
    return url.lstrip("/") + ("index.html" if url.endswith("/") else "")


def render_site():
    site = read_json("site.json")
    registry = read_json("pages.json")
    apps, guides = load_content()
    guide_by_slug = {guide["slug"]: guide for guide in guides}
    environment = Environment(
        loader=FileSystemLoader(ROOT / "src/templates"),
        autoescape=select_autoescape(["html"]), undefined=StrictUndefined,
        trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True,
    )
    environment.filters["display_date"] = display_date
    defaults = {"active": "", "noindex": False, "article": False, "breadcrumbs": []}
    output = {}
    sitemap = []
    for entry in registry["pages"]:
        page = defaults | entry
        app = apps.get(page.get("app"))
        guide = guide_by_slug.get(page.get("guide"))
        context = {"site": site, "apps": apps, "guides": guides, "page": page, "app": app, "guide": guide}
        if page["template"] == "support":
            context["faqs"] = read_json(f'support/{page["app"]}.json')
            context["other_app"] = next(slug for slug in apps if slug != page["app"])
        elif page["template"] == "privacy":
            context["policy"] = (CONTENT / f'legal/{page["app"]}.html').read_text(encoding="utf-8")
        context["structured_data"] = structured_data(site, page, app, guide)
        filename = destination(page["url"])
        if filename in output:
            raise ValueError(f'Duplicate route: {page["url"]}')
        output[filename] = environment.get_template(f'pages/{page["template"]}.html').render(context)
        if not page["noindex"]:
            modified = guide["modified"] if guide else page["modified"]
            date.fromisoformat(modified)
            sitemap.append(f'  <url><loc>{escape(site["url"] + page["url"])}</loc><lastmod>{modified}</lastmod></url>\n')
    for redirect in registry["redirects"]:
        filename = destination(redirect["from"])
        if filename in output or destination(redirect["to"]) not in output:
            raise ValueError(f"Invalid redirect: {redirect}")
        output[filename] = environment.get_template("layouts/redirect.html").render(site=site, redirect=redirect)
    output["sitemap.xml"] = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(sitemap) + '</urlset>\n'
    return output, len(sitemap)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT, help="Output directory (default: repository root)")
    args = parser.parse_args()
    output = args.output.resolve()
    if any(output == ROOT / name or output.is_relative_to(ROOT / name) for name in ("assets", "src", "scripts", ".git")):
        parser.error("Output must be separate from source, assets, scripts, and Git metadata.")
    # Render everything first: a template or data error cannot leave half-built pages.
    files, page_count = render_site()
    changed = 0
    for name, content in files.items():
        target = output / name
        encoded = content.encode("utf-8")
        if not target.is_file() or target.read_bytes() != encoded:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(encoded)
            changed += 1
    if output != ROOT:
        shutil.copytree(ROOT / "assets", output / "assets", dirs_exist_ok=True)
        for name in ("CNAME", ".nojekyll", "robots.txt"):
            shutil.copy2(ROOT / name, output / name)
    print(f"Built {page_count} indexable pages, the 404 page, and {len(read_json('pages.json')['redirects'])} redirects; {changed} generated files updated.")


if __name__ == "__main__":
    main()
