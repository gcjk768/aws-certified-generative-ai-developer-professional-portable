"""Build the AIP-C01 practice question CSVs from private sources + authored banks.
Usage: python -I build_csv.py          (reads ./sources and ./banks, writes AIP-C01_practice_questions_2026.csv + data/questions.csv)
Sources (gitignored, personal use): sources/genai/AIP-C01.docx (25 vendor sample questions, no explanations),
sources/genai/skillbuilder.docx (Skill Builder questions with per-option explanations), sources/skillbuilder/*.md
(transcribed Skill Builder screenshots, bank format). Public banks: banks/*.md (format in AGENT.md).
Exits non-zero if any row is malformed.
"""
import csv, glob, html, os, re, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "sources")
OUT = os.path.join(HERE, "AIP-C01_practice_questions_2026.csv")
LET = "ABCDEFGH"
rows = []


def add(source, url, version, q, opts, ans, expl, topic=""):
    r = {"id": len(rows) + 1, "source": source, "source_url": url, "exam_version": version, "topic": topic,
         "select_count": len(ans.split(",")), "question": " ".join(q.split())}
    for L in LET:
        r["option_" + L] = " ".join(opts.get(L, "").split())
    r["correct_answer"] = ans
    r["explanation"] = " ".join(expl.split()) or "(no explanation in source)"
    rows.append(r)


def split_opts(block, pat):
    """block -> (question_text, {letter: text}) using regex pat that captures the letter."""
    parts = re.split(pat, block, flags=re.M)
    q, opts = parts[0], {}
    for i in range(1, len(parts), 2):
        opts[parts[i]] = parts[i + 1]
    return q, opts


def docx_paras(path):
    x = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
    paras = ["".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", p, re.S)) for p in re.findall(r"<w:p[ >].*?</w:p>", x, re.S)]
    return [html.unescape(p).replace("\xa0", " ") for p in paras if p.strip()]


# 1. AIP-C01.docx: "Question # n" / stem / options glued in one or two paragraphs ("A. ...B. ...") / "Answer: B[,C]"
f = os.path.join(SRC, "genai", "AIP-C01.docx")
if os.path.exists(f):
    paras = docx_paras(f)
    for i, p in enumerate(paras):
        if not p.startswith("Question #"):
            continue
        j = i + 1
        q = paras[j]; j += 1
        optline = ""
        while j < len(paras) and not paras[j].startswith("Answer:"):
            optline += paras[j].strip() + " "; j += 1
        m = re.match(r"Answer:\s*([A-F](?:\s*,\s*[A-F])*)", paras[j])
        pos, opts, L = 0, {}, "A"
        while True:  # next marker = "<letter>. <Uppercase>" after the current option start
            nxt = chr(ord(L) + 1)
            mm = re.compile(nxt + r"\.\s+(?=[A-Z])").search(optline, pos + 3) if nxt <= "F" else None
            opts[L] = optline[pos + 3: mm.start() if mm else len(optline)]
            if not mm:
                break
            pos, L = mm.start(), nxt
        add("Vendor sample questions (AIP-C01.docx)", "sources/genai/AIP-C01.docx", "AIP-C01", q, opts, m.group(1).replace(" ", ""), "")
else:
    print("skip (missing)", f)

# 2. skillbuilder.docx: "n. stem" [extra stem paragraphs] / "A" / option text / "Correct./Incorrect. why" / "Learn more about ..."
#    Each question runs until the next numbered stem; ordering questions ("Select and order each step") have no lettered options and are skipped.
f = os.path.join(SRC, "genai", "skillbuilder.docx")
if os.path.exists(f):
    paras = [p.strip() for p in docx_paras(f)]
    idx = [i for i, p in enumerate(paras) if re.match(r"^\d+\.\s", p)] + [len(paras)]
    for a, b in zip(idx, idx[1:]):
        block = paras[a:b]
        stem_end = next((k for k, p in enumerate(block) if re.fullmatch(r"[A-F]\.?", p)), None)
        if stem_end is None:
            print("skip (ordering question)", block[0][:60]); continue
        stem = re.sub(r"^\d+\.\s+", "", " ".join(block[:stem_end]))
        opts, why, ans, k = {}, [], [], stem_end
        while k < len(block):
            if re.fullmatch(r"[A-F]\.?", block[k]) and k + 1 < len(block):
                L, text = block[k][0], block[k + 1]; k += 2
                opts[L] = text
                if k < len(block) and block[k].startswith(("Correct", "Incorrect")):
                    if block[k].startswith("Correct"):
                        ans.append(L)
                    why.append(f"{L}: {block[k]}"); k += 1
            else:
                k += 1
        if ans:
            add("AWS Skill Builder official practice questions (skillbuilder.docx)", "https://skillbuilder.aws/", "AIP-C01",
                stem, opts, ",".join(ans), " ".join(why))
else:
    print("skip (missing)", f)

# 3. Bank files: sources/skillbuilder/*.md (private transcriptions) + banks/*.md (public, see AGENT.md)
for _f in sorted(glob.glob(os.path.join(SRC, "skillbuilder", "*.md"))) + sorted(glob.glob(os.path.join(HERE, "banks", "*.md"))):
    t = open(_f, encoding="utf-8").read()
    hdr = dict(re.findall(r"^(source|url|version): (.*)$", t.split("\n## ", 1)[0], flags=re.M))
    qpart, apart = t.split("## Answers")
    key = {n: (x, why) for n, x, why in re.findall(r"^\| (\d+) \| ([A-F](?:,[A-F])*) \| (.*?) \|$", apart, flags=re.M)}
    section = ""
    for chunk in re.split(r"^(## .*)$", qpart, flags=re.M)[1:]:
        if chunk.startswith("## "):
            section = chunk[3:].strip(); continue
        qs = re.split(r"^(\d+)\. ", chunk, flags=re.M)[1:]
        for k in range(0, len(qs), 2):
            n, body = qs[k], qs[k + 1]
            q, opts = split_opts(body, r"^\s+([A-F])\. ")
            assert n in key, f"{_f}: question {n} has no answer row"
            add(hdr.get("source", os.path.basename(_f)), hdr.get("url", os.path.basename(_f)), hdr.get("version", "AIP-C01"),
                q, opts, key[n][0], key[n][1], section)

# 4. Online sources downloaded by fetch_sources.py into sources/online/ (gitignored; each missing file is skipped)
ON = os.path.join(SRC, "online")
import json, hashlib

def _hash_pos(text, n):
    return int(hashlib.md5(text.encode()).hexdigest(), 16) % n

# 4a. JeremyEngineer/aws-aip-c01-practice-exam (MIT): {questions:[{id,task,type,question,options:[{text,correct,explanation}],source?}]}
for _lvl in ("easy", "hard", "veryhard"):
    _f = os.path.join(ON, f"jeremy_{_lvl}.json")
    if not os.path.exists(_f):
        print("skip (missing)", _f); continue
    for q in json.load(open(_f, encoding="utf-8"))["questions"]:
        if q.get("source") == "BenchPrep":          # re-typed official items: not ours to use
            continue
        opts = {LET[k]: o["text"] for k, o in enumerate(q["options"])}
        ans = ",".join(LET[k] for k, o in enumerate(q["options"]) if o.get("correct"))
        why = " ".join(f"{LET[k]}: {o.get('explanation', '')}" for k, o in enumerate(q["options"]) if o.get("explanation"))
        add(f"JeremyEngineer practice exam, {_lvl} (GitHub, MIT)", "https://github.com/JeremyEngineer/aws-aip-c01-practice-exam",
            "AIP-C01", q["question"], opts, ans, why, f"task {q.get('task', '')}")

# 4b. open-exam-prep.com: Next.js RSC payload, "initialQuestions":[{id,question,options,correctAnswer,explanation,category,examTip}]
_f = os.path.join(ON, "oep.html")
if os.path.exists(_f):
    _h = open(_f, encoding="utf-8", errors="replace").read()
    _chunks = re.findall(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)', _h)
    _txt = json.loads('"' + "".join(_chunks) + '"')
    _i = _txt.find('"initialQuestions":')
    if _i >= 0:
        for q in json.JSONDecoder().raw_decode(_txt, _i + len('"initialQuestions":'))[0]:
            ca = q["correctAnswer"]
            ans = ",".join(LET[i] for i in (ca if isinstance(ca, list) else [ca]))
            opts = {LET[k]: o for k, o in enumerate(q["options"])}
            why = q.get("explanation", "") + (" Exam tip: " + q["examTip"] if q.get("examTip") else "")
            add("open-exam-prep.com free practice", "https://open-exam-prep.com/practice/aws-genai-developer-pro", "AIP-C01",
                q["question"], opts, ans, why, q.get("category", ""))
    else:
        print("open-exam-prep: initialQuestions not found; page layout changed?")
else:
    print("skip (missing)", _f)

# 4c. certsafari.com: schema.org Quiz JSON-LD; acceptedAnswer is always listed first, so place it by a stable hash
_f = os.path.join(ON, "certsafari.html")
if os.path.exists(_f):
    _h = open(_f, encoding="utf-8", errors="replace").read()
    for blob in re.findall(r"<script[^>]*ld\+json[^>]*>(.*?)</script>", _h, re.S):
        for node in json.loads(blob).get("@graph", []):
            for q in node.get("hasPart", []) if node.get("@type") == "Quiz" else []:
                acc = q["acceptedAnswer"]
                accs = acc if isinstance(acc, list) else [acc]          # multi-response questions list several
                sug = q.get("suggestedAnswer", [])
                texts = [s["text"] for s in sug]
                for a in accs:                                          # correct ones are listed first: spread them by a stable hash
                    texts.insert(_hash_pos(q["text"] + a["text"], len(texts) + 1), a["text"])
                right = {a["text"] for a in accs}
                opts = {LET[k]: t for k, t in enumerate(texts)}
                ans = ",".join(LET[k] for k, t in enumerate(texts) if t in right)
                comment = {x["text"]: x.get("comment", {}).get("text", "") for x in accs + sug}
                why = " ".join(f"{LET[k]}: {comment[t]}" for k, t in enumerate(texts) if comment.get(t))
                add("certsafari.com free sample questions", "https://certsafari.com/aws/gen-ai-developer-professional/practice-questions",
                    "AIP-C01", q["text"], opts, ans, why)
else:
    print("skip (missing)", _f)

# 4d. certland.net: <article> blocks with "Qn." heading, <li> options (the ✓ one is correct), an Explanation paragraph
_f = os.path.join(ON, "certland.html")
if os.path.exists(_f):
    _h = open(_f, encoding="utf-8", errors="replace").read()
    for art in re.findall(r"<article.*?</article>", _h, re.S):
        m = re.search(r"<h2[^>]*>.*?Q\d+\.</span>(.*?)</h2>", art, re.S)
        if not m:
            continue
        stem = html.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))
        items = re.findall(r"<li[^>]*>(.*?)</li>", art, re.S)
        opts, ans = {}, []
        for k, li in enumerate(items):
            spans = re.findall(r"<span[^>]*>(.*?)</span>", li, re.S)
            if len(spans) < 2:
                continue
            opts[LET[k]] = html.unescape(re.sub(r"<[^>]+>", " ", spans[-1]))
            if "✓" in spans[0]:
                ans.append(LET[k])
        ex = re.search(r"Explanation</p>\s*<p[^>]*>(.*?)</p>", art, re.S)
        why = html.unescape(re.sub(r"<[^>]+>", " ", ex.group(1))).replace("**", "") if ex else ""
        if opts and ans:
            add("certland.net free practice questions", "https://certland.net/exams/aws-certified-generative-ai-developer-professional-aip-c01/practice-questions/",
                "AIP-C01", stem, opts, ",".join(ans), why)
else:
    print("skip (missing)", _f)

# 5. Second batch of online sources (2026-10-16 research): see online_parsers.py
sys.path.insert(0, HERE)          # python -I drops the script dir from sys.path
import online_parsers
online_parsers.parse_all(ON, add)

# dedupe by first 80 chars of the stem
seen, uniq = set(), []
for r in rows:
    k = r["question"][:80].lower()
    if k in seen:
        continue
    seen.add(k); uniq.append(r)
print("duplicates dropped:", len(rows) - len(uniq)); rows = uniq
for k, r in enumerate(rows, 1):
    r["id"] = k

cols = ["id", "source", "source_url", "exam_version", "topic", "select_count", "question"] + \
       ["option_" + L for L in LET] + ["correct_answer", "explanation"]
with open(OUT, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)

from collections import Counter
print(Counter(r["source"] for r in rows))
bad = [r["id"] for r in rows if not r["option_A"] or not r["option_B"] or not r["correct_answer"] or not r["question"]]
assert not bad, f"incomplete rows: {bad}"
for r in rows:
    assert all(r["option_" + L] for L in r["correct_answer"].split(",")), (r["id"], r["correct_answer"])
print("rows:", len(rows), "->", OUT)

# Bot-schema copy (same columns as the CCAR-P / SAP-C03 quiz bots); domain = short source name for now.
SHORT = {"Vendor sample questions (AIP-C01.docx)": "Vendor samples",
         "AWS Skill Builder official practice questions (skillbuilder.docx)": "Skill Builder official set",
         "AWS Skill Builder Trivia (GenAI for Developers)": "Skill Builder trivia",
         "open-exam-prep.com free practice": "open-exam-prep", "certsafari.com free sample questions": "CertSafari samples",
         "certland.net free practice questions": "Certland samples",
         **{f"JeremyEngineer practice exam, {l} (GitHub, MIT)": f"JeremyEngineer {l}" for l in ("easy", "hard", "veryhard")},
         "himanshu-nakrani/aws-ai-dev-prof original questions (GitHub)": "himanshu-nakrani bank",
         "jrajath94/aws-aip-c01-study-guide question bank (GitHub)": "jrajath94 bank",
         "michaelgarcia/educational-aws-gen-ai-certification-prep (GitHub, MIT)": "michaelgarcia prep exam",
         "tunglt-0058/aip-c01-lesson-learned practice questions (GitHub, CC BY 4.0)": "tunglt practice",
         "KodeKloud free AIP-C01 practice test": "KodeKloud free test",
         "mankale/aipc01-exam-skill sample questions (GitHub)": "mankale samples",
         **{f"AWS Skill Builder practice set {n}": f"Skill Builder set {n}" for n in range(1, 10)}}
bot_path = os.path.join(HERE, "data", "questions.csv")
os.makedirs(os.path.dirname(bot_path), exist_ok=True)
with open(bot_path, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["id", "domain", "question", "options", "correct", "explanation"]); w.writeheader()
    for r in rows:
        opts = "\n".join(f"{L}. {r['option_' + L]}" for L in LET if r["option_" + L])
        # ponytail: domain = source bank; swap for the official AIP-C01 domains once questions are tagged
        w.writerow({"id": f"AIP-{r['id']:04d}", "domain": SHORT.get(r["source"], r["source"][:40]), "question": r["question"],
                    "options": opts, "correct": r["correct_answer"], "explanation": r["explanation"]})
print("bot rows:", len(rows), "->", bot_path)
