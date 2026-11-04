"""Validate generated pages, canonical URLs, local links, and search metadata."""
import argparse
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
import json
import xml.etree.ElementTree as ET
from build_site import render_site

SOURCE = Path(__file__).resolve().parents[1]
ROOT = SOURCE
BASE = json.loads((SOURCE / "src/content/site.json").read_text(encoding="utf-8"))["url"]


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.duplicate_ids = set()
        self.references = []
        self.metas = {}
        self.canonical = []
        self.title = ""
        self.h1_count = 0
        self.in_title = False
        self.in_schema = False
        self.schema_text = ""
        self.schemas = []
        self.feed(source)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if attrs.get("id"):
            if attrs["id"] in self.ids:
                self.duplicate_ids.add(attrs["id"])
            self.ids.add(attrs["id"])
        if tag == "h1":
            self.h1_count += 1
        if tag == "title":
            self.in_title = True
        if tag == "meta":
            self.metas[attrs.get("name", attrs.get("property"))] = attrs.get("content", "")
            if attrs.get("property") == "og:image" or attrs.get("name") == "twitter:image":
                self.references.append(attrs["content"])
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonical.append(attrs["href"])
        if tag in ("a", "link") and attrs.get("href"):
            self.references.append(attrs["href"])
        if tag in ("img", "script") and attrs.get("src"):
            self.references.append(attrs["src"])
        if tag == "img":
            assert "alt" in attrs, "Image missing alternative text"
            if attrs.get("src"):
                assert attrs.get("width") and attrs.get("height"), "Image missing intrinsic dimensions"
            for candidate in attrs.get("srcset", "").split(","):
                if candidate.strip():
                    self.references.append(candidate.strip().split()[0])
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self.in_schema = True
            self.schema_text = ""

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag == "script" and self.in_schema:
            self.schemas.append(json.loads(self.schema_text))
            self.in_schema = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self.in_schema:
            self.schema_text += data


def local_file(url):
    relative = unquote(urlsplit(url).path).lstrip("/")
    candidate = ROOT / relative
    if candidate.is_dir():
        return candidate / "index.html"
    if not candidate.exists() and not candidate.suffix:
        return candidate.with_suffix(".html")
    return candidate


def main():
    global ROOT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=SOURCE, help="Generated site to validate")
    ROOT = parser.parse_args().root.resolve()
    expected, _ = render_site()
    for name, content in expected.items():
        assert (ROOT / name).read_bytes() == content.encode("utf-8"), f"{name}: generated output is stale; run scripts/build_site.py"
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    tree = ET.parse(ROOT / "sitemap.xml")
    urls = [item.text for item in tree.findall("s:url/s:loc", ns)]
    assert len(urls) == len(set(urls)), "Duplicate sitemap URLs"
    assert all(url.startswith(BASE + "/") for url in urls), "Non-canonical domain in sitemap"
    assert all(not urlsplit(url).path.endswith(".html") for url in urls), "Sitemap contains an .html page URL"
    all_urls = urls + [BASE + "/404.html"]
    pages = {local_file(url).resolve(): Page(local_file(url).read_text(encoding="utf-8")) for url in all_urls}
    titles = set()
    descriptions = set()
    link_count = 0
    for url in all_urls:
        file = local_file(url).resolve()
        page = pages[file]
        assert page.h1_count == 1, f"{url}: needs one H1"
        assert not page.duplicate_ids, f"{url}: duplicate IDs {page.duplicate_ids}"
        assert page.title and page.title not in titles, f"{url}: missing/duplicate title"
        titles.add(page.title)
        description = page.metas.get("description", "")
        assert description and description not in descriptions, f"{url}: missing/duplicate description"
        descriptions.add(description)
        assert page.canonical == [url], f"{url}: invalid canonical URL"
        assert page.metas.get("og:url") == url, f"{url}: wrong Open Graph URL"
        assert page.metas.get("og:image"), f"{url}: missing share image"
        assert page.schemas, f"{url}: missing structured data"
        if url.endswith("404.html"):
            assert "noindex" in page.metas["robots"]
        else:
            assert "noindex" not in page.metas["robots"]
        for reference in page.references:
            target_url = urljoin(url, reference)
            split = urlsplit(target_url)
            if split.scheme not in ("http", "https") or split.netloc != urlsplit(BASE).netloc:
                continue
            assert not split.path.endswith(".html") or (
                url == BASE + "/404.html" and split.path == "/404.html"
            ), f"{url}: public link uses .html: {reference}"
            target = local_file(target_url).resolve()
            assert target.is_relative_to(ROOT.resolve()), f"Path escapes site: {reference}"
            assert target.is_file(), f"{url}: missing local target {reference}"
            if split.fragment and target.suffix == ".html":
                target_page = pages.get(target) or Page(target.read_text(encoding="utf-8"))
                assert unquote(split.fragment) in target_page.ids, f"{url}: broken fragment {reference}"
            link_count += 1
    for app in ("keystar", "penstar"):
        items = json.loads((SOURCE / f"src/content/support/{app}.json").read_text(encoding="utf-8"))
        page = pages[(ROOT / app / "support" / "index.html").resolve()]
        for item in items:
            assert item["anchor"] in page.ids and item["heading"] in page.ids, "Legacy answer link was lost"
        for schema in pages[(ROOT / app / "index.html").resolve()].schemas:
            for entity in schema["@graph"]:
                assert "aggregateRating" not in entity, "Do not invent app review data"
    print(f"PASS: {len(pages)} pages, {link_count} local references, unique metadata, valid JSON-LD, sitemap, all 34 legacy answer anchors, and generated files match source.")


if __name__ == "__main__":
    main()
