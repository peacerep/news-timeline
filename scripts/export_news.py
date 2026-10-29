"""Export a portable news snapshot from the frozen capture and proposal."""

import argparse
import csv
import json
import hashlib
import shutil
from pathlib import Path


TYPES = (
    "Events held",
    "High-level visits",
    "Research cited or used",
    "Partnerships & process support",
    "Recognition",
    "New research, data & tools",
    "Training & fellowships",
    "Media engagements",
    "Research responses to current events",
    "Other programme news",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "data/news.json")
    parser.add_argument("--image-output", type=Path, default=Path(__file__).resolve().parents[1] / "assets/images")
    args = parser.parse_args()

    records = json.loads(args.records.read_text(encoding="utf-8"))
    with args.proposal.open(encoding="utf-8-sig", newline="") as handle:
        sheet = list(csv.DictReader(handle))
    by_id = {str(row["post_id"]): row for row in sheet}
    assert len(records) == len(sheet) == len(by_id) == 172, "Expected 172 unique source and proposal posts"
    assert {str(row["id"]) for row in records} == set(by_id), "Capture and proposal IDs differ"

    posts = []
    copied = set()
    def copy_saved_image(image):
        source = (args.records.parent / image["file"]).resolve()
        assert source.is_relative_to(args.records.parent.resolve()), "Image path leaves capture folder"
        assert source.is_file(), f"Missing saved image: {source}"
        filename = Path(image["file"]).name
        target = args.image_output / filename
        if filename not in copied:
            assert hashlib.sha256(source.read_bytes()).hexdigest() == image["sha256"], f"Image checksum changed: {source}"
            args.image_output.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied.add(filename)
        return f"assets/images/{filename}"

    for record in records:
        row = by_id[str(record["id"])]
        assert row["title"] == record["title"] and row["url"] == record["url"]
        assert row["published_date"] == record["date"][:10]
        assert row["story_type"] in TYPES
        assert row["evidence_status"] == "not_assessed" and row["review_status"] == "unreviewed"
        assert all(not row[field] for field in ("impact_area", "impact_story_id", "theme", "country", "reviewer", "reviewed_at"))
        image = next((item for item in record.get("images", []) if item.get("role") == "featured" and item.get("capture_status") == "saved" and item.get("file")), None)
        image_data = None
        if image:
            image_data = {
                "path": copy_saved_image(image),
                "alt": image.get("alt") or "",
                "caption": image.get("caption") or "",
                "credit": image.get("credit") or "",
            }
        inline_images = [copy_saved_image(item) for item in record.get("images", []) if item.get("role") == "inline" and item.get("capture_status") == "saved" and item.get("file")]
        posts.append({
            "id": record["id"],
            "published_date": row["published_date"],
            "title": record["title"],
            "excerpt": record["excerpt"],
            "full_text": record["full_text"],
            "content_html": record["content_html"],
            "inline_images": inline_images,
            "url": record["url"],
            "story_type": row["story_type"],
            "secondary_type": row["secondary_types"] or None,
            "image": image_data,
        })
    payload = {
        "source_capture": "20261028T165947Z",
        "classification_status": "editorial_proposal_unreviewed",
        "story_types": TYPES,
        "posts": posts,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    args.output.write_text(serialized + "\n", encoding="utf-8")
    print(f"Wrote {len(posts)} posts and {len(copied)} images to {args.output}")


if __name__ == "__main__":
    main()
