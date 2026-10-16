"""Build data/study_notes.csv from a slide-deck PDF (private: the PDF and the CSV are gitignored).
Usage: python build_notes.py "<slides.pdf>" [data/questions.csv]
One row per slide title (consecutive slides with the same title are merged): id, section, title, pages,
bullets (one per line), labels (diagram text on the slide), related (bank question ids by keyword overlap).
Needs pymupdf locally; the bot only reads the CSV.
"""
import csv, math, re, sys
from collections import Counter
from pathlib import Path
import pymupdf

PDF = sys.argv[1]
BANK = Path(sys.argv[2] if len(sys.argv) > 2 else "data/questions.csv")
OUT = Path("data/study_notes.csv")
TITLE_PT = 44                              # slide-title size in the Sundog deck; sections come from the "What We'll Cover:" slides
SKIP_TITLE = re.compile(r"^(Question \d+|Option |Table of Contents|Practice Exam|Let's|What We.ll Cover|Course|Quiz|Lab)")
STOP = set("aws amazon the and for with your you are can use using from into that this what how of to in on a an is be or by it its "
           "vs via not up what's overview basics deep dive".split())

def tokens(s):
    return [t for t in re.findall(r"[a-z0-9][a-z0-9@-]+", s.lower()) if t not in STOP and len(t) > 1]

def slide(page):
    """-> (section|None, title, bullets, labels) for one page."""
    section = title = None
    bullets, labels, cur = [], [], None
    for b in page.get_text("dict")["blocks"]:
        for line in b.get("lines", []):
            txt = "".join(s["text"] for s in line["spans"]).strip()
            size = round(max(s["size"] for s in line["spans"]))
            if not txt or "sundog-education.com" in txt or "datacumulus.com" in txt or "All Rights Reserved" in txt:
                continue
            if size >= TITLE_PT:
                title = f"{title} {txt}" if title else txt
            elif txt[0] in "•▪◦-" and len(txt) > 2:
                cur = txt.lstrip("•▪◦- ").strip(); bullets.append(cur)
            elif cur is not None and size >= 14:          # wrapped continuation of the bullet above
                bullets[-1] += " " + txt
            else:
                labels.append(txt)
        cur = None
    return section, title, bullets, labels

doc = pymupdf.open(PDF)
# Sections = the entries of the deck's Table of Contents (page 2); a slide whose title equals one of them opens that section.
TOC = {re.sub(r"\s+", " ", l).strip().rstrip(":").lower() for l in doc[1].get_text().splitlines()
       if l.strip() and not l.startswith(("sundog", "datacumulus", "©", "Table of"))}
notes, section = [], ""
for i, page in enumerate(doc):
    sec, title, bullets, labels = slide(page)
    if title:
        t = re.sub(r"^What We.ll Cover:?\s*", "", re.sub(r"\s+", " ", title)).strip().rstrip(":")
        if t.lower() in TOC and len(t) > 3:
            section = t; continue
    if i < 3 or not title or not section or SKIP_TITLE.search(title):
        continue
    title = re.sub(r"\s+", " ", title).strip(" –-")
    if notes and notes[-1]["title"] == title and notes[-1]["section"] == section:
        n = notes[-1]; n["pages"] += f",{i + 1}"; n["bullets"] += bullets; n["labels"] += labels
    else:
        notes.append({"section": section, "title": title, "pages": str(i + 1), "bullets": list(bullets), "labels": list(labels)})

# related bank questions: IDF-weighted overlap of the note's title (x3) + bullet tokens with question text
bank = list(csv.DictReader(BANK.open(encoding="utf-8"))) if BANK.exists() else []
qtok = {q["id"]: set(tokens(q["question"] + " " + q["options"])) for q in bank}
df = Counter(t for ts in qtok.values() for t in ts)
idf = lambda t: math.log((len(bank) + 1) / (df.get(t, 0) + 1))
for n in notes:
    tt, bt = set(tokens(n["title"])), set(tokens(" ".join(n["bullets"])))
    scored = sorted(((sum(idf(t) * (3 if t in tt else 1) for t in (tt | bt) & ts), qid) for qid, ts in qtok.items()), reverse=True)
    n["related"] = ",".join(qid for s, qid in scored[:3] if s >= 6)

OUT.parent.mkdir(exist_ok=True)
with OUT.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["id", "section", "title", "pages", "bullets", "labels", "related"])
    w.writeheader()
    for k, n in enumerate(notes, 1):
        w.writerow({"id": f"N-{k:04d}", "section": n["section"], "title": n["title"], "pages": n["pages"],
                    "bullets": "\n".join(n["bullets"]), "labels": " | ".join(n["labels"]), "related": n["related"]})
print(Counter(n["section"] for n in notes))
print("notes:", len(notes), "with bullets:", sum(bool(n["bullets"]) for n in notes),
      "with labels:", sum(bool(n["labels"]) for n in notes), "with related:", sum(bool(n["related"]) for n in notes), "->", OUT)
