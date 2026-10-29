"""Render draft full-text PeaceRep news compendia from the frozen local snapshot."""

import argparse
from collections import defaultdict
import base64
from io import BytesIO
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import urlparse

import fitz
from PIL import Image, ImageOps
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
DATA = json.loads((ROOT / "data/news.json").read_text(encoding="utf-8"))
POSTS = DATA["posts"]
TYPES = DATA["story_types"]
HIGHLIGHTS = json.loads((ROOT / "editorial/compendium-highlights.json").read_text(encoding="utf-8"))
PREPARED = {}


def prepared_image(path):
    """Make a compact PDF copy without changing the archived image."""
    if path in PREPARED:
        return PREPARED[path]
    source = ROOT / path
    if not source.is_file():
        return None
    destination = OUTPUT / "images" / f"{source.stem}.jpg"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as original:
        resized = ImageOps.exif_transpose(original)
        resized.thumbnail((1000, 1000), Image.Resampling.LANCZOS)
        if resized.mode != "RGB":
            background = Image.new("RGB", resized.size, "white")
            if "A" in resized.getbands():
                background.paste(resized, mask=resized.getchannel("A"))
            else:
                background.paste(resized.convert("RGB"))
            resized = background
        resized.save(destination, "JPEG", quality=78, optimize=True, progressive=True)
    PREPARED[path] = "images/" + destination.name
    return PREPARED[path]


class ArticleHTML(HTMLParser):
    """Keep readable source formatting and safe links to locally captured images."""

    TAGS = {"p", "h2", "h3", "h4", "strong", "b", "em", "i", "ul", "ol", "li", "blockquote", "br", "a", "img", "figure", "figcaption", "table", "thead", "tbody", "tr", "th", "td"}
    VOID = {"br", "img"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.stack = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if self.hidden:
            if tag in {"script", "style", "iframe", "svg"}:
                self.hidden += 1
            return
        if tag in {"script", "style", "iframe", "svg"}:
            self.hidden = 1
            return
        if tag not in self.TAGS:
            return
        attrs = dict(attrs)
        extra = ""
        if tag == "a":
            href = attrs.get("href", "")
            if urlparse(href).scheme in {"https", "http", "mailto"}:
                extra = f' href="{escape(href, quote=True)}"'
        elif tag == "img":
            source = attrs.get("src", "")
            if source.startswith("images/"):
                image = prepared_image("assets/" + source)
                if image:
                    extra = f' src="{escape(image, quote=True)}" alt="{escape(attrs.get("alt", ""), quote=True)}"'
            if not extra:
                return
        self.parts.append(f"<{tag}{extra}>")
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if self.hidden:
            if tag in {"script", "style", "iframe", "svg"}:
                self.hidden -= 1
            return
        if tag in self.stack:
            while self.stack:
                current = self.stack.pop()
                self.parts.append(f"</{current}>")
                if current == tag:
                    break

    def handle_data(self, value):
        if not self.hidden:
            self.parts.append(escape(value))

    def html(self, source):
        self.feed(source)
        while self.stack:
            self.parts.append(f"</{self.stack.pop()}>")
        return "".join(self.parts)


def article(post, prefix):
    image = post.get("image")
    image_html = ""
    if image and (path := prepared_image(image["path"])):
        caption = image.get("caption") or image.get("credit") or ""
        image_html = f'<figure class="feature"><img src="{escape(path, quote=True)}" alt="{escape(image.get("alt") or "", quote=True)}">'
        if caption:
            image_html += f"<figcaption>{escape(caption)}</figcaption>"
        image_html += "</figure>"
    body = ArticleHTML().html(post["content_html"])
    if not body.strip():
        body = f"<p>{escape(post['full_text'])}</p>"
    secondary = f' · {escape(post["secondary_type"])}' if post.get("secondary_type") else ""
    return (
        f'<article id="{prefix}-{post["id"]}" class="story">'
        f'<div class="story-meta">{escape(post["published_date"])} &nbsp; / &nbsp; {escape(post["story_type"])}{secondary}</div>'
        f'<h3>{escape(post["title"])}</h3>{image_html}'
        f'<div class="article-body">{body}</div>'
        f'<p class="source">Original News post: <a href="{escape(post["url"], quote=True)}">{escape(post["url"])}</a></p>'
        "</article>"
    )


def highlights():
    by_id = {post["id"]: post for post in POSTS}
    assert len(set(HIGHLIGHTS["post_ids"])) == len(HIGHLIGHTS["post_ids"])
    assert all(post_id in by_id for post_id in HIGHLIGHTS["post_ids"])
    cards = []
    for post_id in HIGHLIGHTS["post_ids"]:
        post = by_id[post_id]
        cards.append(
            f'<div class="highlight"><p class="story-meta">{escape(post["published_date"])} / {escape(post["story_type"])}</p>'
            f'<h3><a href="#year-{post_id}">{escape(post["title"])}</a></h3>'
            f'<p>{escape(post["excerpt"])}</p></div>'
        )
    return '<section class="highlights"><h2>Selected stories for editorial review</h2><p>These posts are possible starting points for impact stories. Their selection and any claims about outcomes require evidence and editorial approval.</p>' + "".join(cards) + "</section>"


STYLE = """
@font-face{font-family:Montserrat;src:url('../assets/fonts/Montserrat-Variable.ttf') format('truetype');font-weight:100 900}
@page{size:A4 portrait;margin:25mm 17mm 18mm}
*{box-sizing:border-box}html{font-family:Montserrat,Arial,sans-serif;color:#091f40}body{margin:0;font-size:10pt;line-height:1.48}
.cover{break-after:page;min-height:210mm;display:flex;flex-direction:column;justify-content:center;padding-top:15mm}
.cover img{width:76mm;height:auto}.kicker{text-transform:uppercase;letter-spacing:.16em;font-size:9pt;font-weight:750;color:#016099;margin:14mm 0 4mm}
h1{font-size:34pt;line-height:1.08;letter-spacing:-.04em;margin:0 0 7mm}h1 em{font-style:normal;color:#456b7d}.deck{font-size:13pt;line-height:1.4;max-width:135mm;color:#456b7d}
.cover-note{margin-top:18mm;padding:5mm 6mm;background:#f0f4f6;border-left:2mm solid #016099;font-size:9pt}
.cover-bottom{margin-top:auto;border-top:1px solid #d5deea;padding:5mm 0;font-size:9pt;color:#456b7d}
.contents{break-after:page}.contents h2,.highlights h2{font-size:20pt;margin:4mm 0 6mm}.contents ul{list-style:none;padding:0;columns:2;column-gap:15mm}.contents li{margin:0 0 3mm;break-inside:avoid}.contents a{color:#091f40;text-decoration:none;border-bottom:1px solid #d5deea}
.highlights{break-after:page}.highlights>p{max-width:150mm;color:#456b7d}.highlight{break-inside:avoid;border-top:1px solid #d5deea;padding:3mm 0}.highlight h3{font-size:12pt;margin:1mm 0}.highlight h3 a{color:#091f40;text-decoration:none}.highlight p{margin:1mm 0;font-size:9pt}
.section{break-before:page}.section-title{background:#091f40;color:#fff;padding:6mm 7mm;margin:0 0 7mm}.section-title h2{font-size:22pt;line-height:1.15;margin:0}.section-title p{font-size:9pt;margin:2mm 0 0;color:#e1eaf1}
.story{border-top:1px solid #d5deea;padding:5mm 0 7mm;break-inside:auto}.story-meta{font-size:8pt;line-height:1.4;font-weight:700;letter-spacing:.02em;color:#016099;text-transform:uppercase;margin:0 0 2mm}
.story h3{font-size:16pt;line-height:1.2;letter-spacing:-.02em;margin:0 0 4mm;break-after:avoid}.feature{float:right;width:58mm;margin:0 0 4mm 6mm;break-inside:avoid}.feature img{width:100%;max-height:55mm;object-fit:cover}.feature figcaption,.article-body figcaption{font-size:7pt;color:#456b7d;margin-top:1mm}
.article-body{overflow-wrap:anywhere}.article-body p{margin:0 0 3mm}.article-body h2,.article-body h3,.article-body h4{font-size:11pt;break-after:avoid;margin:5mm 0 2mm}.article-body img{display:block;max-width:100%;max-height:100mm;width:auto;height:auto;margin:3mm auto;break-inside:avoid}.article-body figure{margin:4mm 0;break-inside:avoid}.article-body ul,.article-body ol{padding-left:6mm}.article-body li{margin-bottom:1mm}.article-body blockquote{margin:3mm 0;padding:2mm 4mm;border-left:1mm solid #016099;background:#f0f4f6}.article-body table{border-collapse:collapse;font-size:8pt;max-width:100%}.article-body th,.article-body td{border:1px solid #d5deea;padding:1mm}
.source{clear:both;border-top:1px solid #d5deea;padding-top:2mm;font-size:7pt;color:#456b7d;overflow-wrap:anywhere}.source a{color:#016099}
"""


def document(title, deck, sections, include_highlights=False):
    logo = "../assets/brand/peacerep-logo.png"
    cover = (
        f'<section class="cover"><img src="{logo}" alt="PeaceRep"><p class="kicker">News and impact / draft compendium</p>'
        f'<h1>{title}</h1><p class="deck">{deck}</p>'
        '<div class="cover-note"><strong>Editorial draft.</strong> Story types are proposed classifications. Highlight choices, impact claims, image rights and credits need review before this document is shared with funders.</div>'
        f'<p class="cover-bottom">Saved News archive: 28 October 2026 · {len(POSTS)} full-text posts · 2018–2026</p></section>'
    )
    contents = '<section class="contents"><h2>Contents</h2><ul>' + "".join(f'<li><a href="#{escape(anchor)}">{escape(label)}</a></li>' for anchor, label, _ in sections) + '</ul></section>'
    body = ""
    for anchor, label, posts in sections:
        body += f'<section id="{escape(anchor)}" class="section"><div class="section-title"><h2>{escape(label)}</h2><p>{len(posts)} stories · Full original text</p></div>'
        body += "".join(article(post, "year" if include_highlights else "type") for post in posts)
        body += "</section>"
    return f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{escape(title)}</title><style>{STYLE}</style></head><body>{cover}{contents}{highlights() if include_highlights else ""}{body}</body></html>'


SUMMARY_STYLE = """
.summary-story{display:grid;grid-template-columns:38mm minmax(0,1fr);gap:4mm;break-inside:avoid;padding:4mm 0}
.summary-story .feature{grid-column:1;grid-row:1;float:none;width:38mm;margin:0}
.summary-story .feature img{width:38mm;height:28mm;max-height:none;object-fit:cover}
.summary-story .summary-copy{grid-column:2;grid-row:1;min-width:0}
.summary-story.no-image .summary-copy{grid-column:1/-1}
.summary-story h3{font-size:11.5pt;margin:0 0 1mm}.summary-story .excerpt{font-size:9pt;margin:0 0 1mm}
.summary-story .source{border:0;padding:0;margin:1mm 0 0;font-size:7pt}
"""


def summary_document(years):
    logo = "../assets/brand/peacerep-logo.png"
    cover = (
        f'<section class="cover"><img src="{logo}" alt="PeaceRep"><p class="kicker">News and impact / draft summary</p>'
        '<h1>News <em>at a glance</em></h1><p class="deck">A concise, chronological guide to the saved PeaceRep News archive.</p>'
        '<div class="cover-note"><strong>Editorial draft.</strong> Story types, impact claims, image rights and credits need review before this document is shared with funders.</div>'
        f'<p class="cover-bottom">Saved News archive: 28 October 2026 · {len(POSTS)} posts · 2018–2026</p></section>'
    )
    years = sorted(years.items(), reverse=True)
    contents = '<section class="contents"><h2>Contents</h2><ul>' + "".join(f'<li><a href="#summary-{year}">{year}</a></li>' for year, _ in years) + '</ul></section>'
    sections = []
    for year, posts in years:
        cards = []
        for post in sorted(posts, key=lambda item: item["published_date"], reverse=True):
            prepared = prepared_image(post["image"]["path"]) if post.get("image") else None
            figure = f'<figure class="feature"><img src="{escape(prepared, quote=True)}" alt="{escape(post["image"].get("alt") or "", quote=True)}"></figure>' if prepared else ""
            cards.append(
                f'<article class="story summary-story{"" if prepared else " no-image"}">{figure}<div class="summary-copy">'
                f'<p class="story-meta">{escape(post["published_date"])} / {escape(post["story_type"])}</p><h3>{escape(post["title"])}</h3>'
                f'<p class="excerpt">{escape(post["excerpt"])}</p><p class="source"><a href="{escape(post["url"], quote=True)}">Original News post</a></p></div></article>'
            )
        sections.append(f'<section id="summary-{year}" class="section"><div class="section-title"><h2>{year}</h2><p>{len(posts)} stories · Short summaries</p></div>{"".join(cards)}</section>')
    return f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>PeaceRep news summary</title><style>{STYLE}{SUMMARY_STYLE}</style></head><body>{cover}{contents}{"".join(sections)}</body></html>'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary-only", action="store_true", help="Regenerate only the short news summary PDF")
    args = parser.parse_args()
    assert len(POSTS) == len({post["id"] for post in POSTS}) == 172
    assert set(post["story_type"] for post in POSTS) == set(TYPES)
    assert all(post["full_text"].strip() for post in POSTS)
    OUTPUT.mkdir(exist_ok=True)
    years = defaultdict(list)
    types = defaultdict(list)
    for post in POSTS:
        years[post["published_date"][:4]].append(post)
        types[post["story_type"]].append(post)
    editions = [
        ("peacerep-news-summary", summary_document(years)),
        ("peacerep-news-by-year", document("News <em>through the years</em>", "A full-text chronological record, with selected stories for editorial review.", [(f"year-{year}", year, sorted(posts, key=lambda item: item["published_date"], reverse=True)) for year, posts in sorted(years.items(), reverse=True)], True)),
        ("peacerep-news-by-story-type", document("News <em>by story type</em>", "A full-text thematic record of research, events, partnerships and other PeaceRep news.", [(f"type-{index}", label, sorted(types[label], key=lambda item: item["published_date"], reverse=True)) for index, label in enumerate(TYPES, 1)])),
    ]
    if args.summary_only:
        editions = editions[:1]
    with Image.open(ROOT / "assets/brand/peacerep-logo.png") as source_logo:
        small_logo = Image.new("RGB", source_logo.size, "white")
        small_logo.paste(source_logo, mask=source_logo.getchannel("A") if "A" in source_logo.getbands() else None)
        small_logo.thumbnail((460, 150), Image.Resampling.LANCZOS)
        logo_buffer = BytesIO()
        small_logo.save(logo_buffer, "JPEG", quality=78, optimize=True)
    logo_data = base64.b64encode(logo_buffer.getvalue()).decode("ascii")
    header = f'<div style="width:100%;height:16mm;margin:0 17mm;display:flex;align-items:center;justify-content:space-between;border-bottom:2.5mm solid #091f40"><img src="data:image/jpeg;base64,{logo_data}" style="width:37mm;height:12mm;object-fit:contain"><span style="font:700 8pt Arial;color:#456b7d;letter-spacing:.1em;text-transform:uppercase">PeaceRep news and impact</span></div>'
    footer = '<div style="width:100%;margin:0 17mm;text-align:right;font:9pt Arial;color:#456b7d"><span class="pageNumber"></span></div>'
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        for name, markup in editions:
            html_path = OUTPUT / f"{name}.html"
            pdf_path = OUTPUT / f"{name}.pdf"
            html_path.write_text(markup, encoding="utf-8")
            page = browser.new_page(viewport={"width": 1100, "height": 800})
            page.goto(html_path.as_uri(), wait_until="load")
            page.evaluate("document.fonts.ready")
            assert page.locator("article.story").count() == 172
            assert page.locator(".feature img").evaluate_all("images => images.every(image => image.complete && image.naturalWidth > 0)")
            page.pdf(path=str(pdf_path), format="A4", print_background=True, prefer_css_page_size=True, display_header_footer=True, header_template=header, footer_template=footer)
            assert pdf_path.read_bytes()[:5] == b"%PDF-" and pdf_path.stat().st_size > 100_000
            with fitz.open(pdf_path) as pdf:
                assert len(pdf) > 20
                assert "Editorial draft" in pdf[0].get_text()
                assert len(pdf[1].get_links()) >= 8, "Contents links missing from PDF"
                print(f"{pdf_path.name}: {len(pdf)} A4 pages, {pdf_path.stat().st_size:,} bytes, 172 posts")
            page.close()
        browser.close()


if __name__ == "__main__":
    main()
