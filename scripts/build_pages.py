"""Assemble the static GitHub Pages payload from saved local files."""

import argparse
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PDFS = (
    "peacerep-news-summary.pdf",
    "peacerep-news-by-year.pdf",
    "peacerep-news-by-story-type.pdf",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "pages-dist")
    args = parser.parse_args()
    output = args.output.resolve()
    assert output.is_relative_to(ROOT.resolve()) and output != ROOT.resolve(), "Output must stay inside this standalone folder"
    source = json.loads((ROOT / "data/news.json").read_text(encoding="utf-8"))
    assert len(source["posts"]) == 172
    assert all(post["full_text"].strip() for post in source["posts"])
    assert all((ROOT / image["path"]).is_file() for post in source["posts"] if (image := post.get("image")))
    assert all((ROOT / path).is_file() for post in source["posts"] for path in post["inline_images"])
    assert all((ROOT / "output" / pdf).is_file() for pdf in PDFS)

    if output.exists():
        assert output.name == "pages-dist", "Refusing to replace an unexpected directory"
        shutil.rmtree(output)
    output.mkdir(parents=True)
    (output / ".nojekyll").touch()
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "News / timeline" in html and "</head>" in html
    html = html.replace("News / timeline", "News / editorial preview", 1)
    html = html.replace("</head>", '  <meta name="robots" content="noindex,nofollow">\n</head>', 1)
    (output / "index.html").write_text(html, encoding="utf-8")
    shutil.copytree(ROOT / "assets", output / "assets")
    shutil.copytree(ROOT / "data", output / "data")
    (output / "downloads").mkdir()
    for pdf in PDFS:
        shutil.copy2(ROOT / "output" / pdf, output / "downloads" / pdf)

    expected = {"index.html", ".nojekyll", "assets", "data", "downloads"}
    assert {path.name for path in output.iterdir()} == expected
    print(f"Pages package: {output} ({len(source['posts'])} posts, {len(PDFS)} PDFs)")


if __name__ == "__main__":
    main()
