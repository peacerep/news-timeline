"""Create the version 5 editorial proposal for research responses to current events."""

import csv
import shutil
from collections import Counter
from pathlib import Path


SOURCE = Path("/classification/proposals_20261028T165947Z_v4.csv")
DESTINATION = Path("/classification/proposals_20261028T165947Z_v5.csv")
SITE_COPY = Path("/work/editorial/classification.csv")
LABEL = "Research responses to current events"
REASONS = {
    "26138": "The fall of El Fasher leads the story; PeaceRep explains the Sudan conflict using existing research and links to relevant reports and tools. Media interviews are part of the response, not the sole focus.",
    "25699": "Renewed fighting in Gedo leads the story; the post uses a new blog and an existing PeaceRep report to explain political and clan tensions. The event-led research response is primary.",
    "25229": "Escalating violence in South Sudan leads the story; existing PeaceRep surveys, analysis and the PA-X Tracker are presented as context for the crisis.",
    "22238": "The COP28 relief, recovery and peace declaration leads the story; the post interprets that development using existing PeaceRep climate and conflict research.",
    "20289": "The outbreak of fighting in Sudan leads the story; the post directs readers to existing PeaceRep research, PA-X agreements and expert analysis.",
    "19862": "The Turkey-Syria earthquakes lead the story; existing Syria research is applied to recovery, aid and conflict dynamics, alongside plans for future work.",
    "11687": "The UN Security Council's Covid-19 ceasefire resolution leads the story; PSRP connects it to its ongoing ceasefire tracking and conflict research.",
    "10424": "The Covid-19 crisis leads the story; Christine Bell applies PSRP expertise to conflict-sensitive health responses in a topical authored article.",
}
FLAGS = {
    "26138": "Review boundary with Media engagements: two interviews accompany the research roundup",
    "25699": "Review boundary with New research, data & tools: a new blog is linked alongside existing research",
    "22238": "Review whether the COP28 declaration belongs with crisis-led responses",
    "10424": "Review boundary with New research, data & tools: the response is an authored article",
}


def main():
    with SOURCE.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        rows = list(reader)
    assert fields and len(rows) == 172
    original = [row.copy() for row in rows]
    by_id = {row["post_id"]: row for row in rows}
    assert len(by_id) == 172 and set(REASONS) <= set(by_id)
    assert all(by_id[post_id]["story_type"] == "Other programme news" for post_id in REASONS)
    for post_id, reason in REASONS.items():
        row = by_id[post_id]
        row["story_type"] = LABEL
        row["classification_reason"] = reason
        if post_id in FLAGS:
            row["confidence"] = "medium"
            row["review_flag"] = FLAGS[post_id]
    assert Counter(row["story_type"] for row in rows)[LABEL] == 8
    assert Counter(row["story_type"] for row in rows)["Other programme news"] == 19
    allowed_edits = {"story_type", "classification_reason", "confidence", "review_flag"}
    assert all({key for key in row if row[key] != before[key]} <= allowed_edits for row, before in zip(rows, original))
    assert sum(row["story_type"] != before["story_type"] for row, before in zip(rows, original)) == 8
    assert all(row["review_status"] == "unreviewed" and row["evidence_status"] == "not_assessed" for row in rows)
    assert all(not row[field] for row in rows for field in ("impact_area", "theme", "country", "impact_story_id", "reviewer", "reviewed_at", "review_notes"))
    for path in (DESTINATION, SITE_COPY):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    shutil.copyfile("/input/guide.md", "/work/editorial/classification-guide.md")
    shutil.copyfile("/classification/classification_report_20261028T165947Z_v5.md", "/work/editorial/classification-report.md")
    shutil.copyfile("/input/impact-crosswalk.md", "/work/editorial/impact-news-crosswalk.md")
    print(f"Wrote {len(rows)} rows; {len(REASONS)} moved to {LABEL}; 19 remain Other")


if __name__ == "__main__":
    main()
