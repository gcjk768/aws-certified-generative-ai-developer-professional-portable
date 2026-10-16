"""Parsers for the second batch of online AIP-C01 sources (downloaded into sources/online/ by a research agent,
2026-10-16). Each parser reads one file layout and calls add(source, url, version, q, opts, ans, expl, topic).
Missing files are skipped. Personal use: nothing here is redistributed."""
import glob, html, os, re

LET = "ABCDEFGH"


def _clean(s):
    return html.unescape(re.sub(r"<[^>]+>", " ", s)).replace("**", "").strip()


def parse_all(ON, add):
    # himanshu-nakrani/aws-ai-dev-prof: "### d1-002 *(hard)*" / stem / "- [x] **B.** text" / "**Why**" paragraph / table
    for f in sorted(glob.glob(os.path.join(ON, "himanshu_*.md"))):
        t = open(f, encoding="utf-8").read()
        for m in re.finditer(r"^### ([a-z]\d-\d+)[^\n]*\n(.*?)(?=^### [a-z]\d-\d+|\Z)", t, re.M | re.S):
            qid, body = m.groups()
            opts, ans = {}, []
            for chk, L, text in re.findall(r"^- \[([ x])\] \*\*([A-H])\.\*\* (.*)$", body, re.M):
                opts[L] = text.strip()
                if chk == "x":
                    ans.append(L)
            stem = body.split("\n- [", 1)[0].strip()
            why = re.search(r"\*\*Why\*\*\s*\n+(.*?)(?=\n\| Option|\n\*See|\n---|\Z)", body, re.S)
            if opts and ans:
                add("himanshu-nakrani/aws-ai-dev-prof original questions (GitHub)", "https://github.com/himanshu-nakrani/aws-ai-dev-prof",
                    "AIP-C01", stem, opts, ",".join(ans), _clean(why.group(1)) if why else "", qid.split("-")[0])

    # jrajath94/aws-aip-c01-study-guide volume-question-bank.html: <section id="q-d1-001"> with pq-option correct|wrong + pq-note, pq-answer
    f = os.path.join(ON, "jrajath94_volume_question_bank.html")
    if os.path.exists(f):
        h = open(f, encoding="utf-8", errors="replace").read()
        for sec in re.split(r'<div class="pq" id="q-d\d-\d+"', h)[1:]:     # one chunk per question block
            qm = re.search(r'<p class="pq-question"[^>]*>(.*?)</p>', sec, re.S)
            if not qm:
                continue
            stem = _clean(re.sub(r"^.*?<strong>Q\d+\.</strong>", "", qm.group(1), flags=re.S))
            dom = re.search(r"<em>(D\d)", qm.group(1))
            opts, ans, notes = {}, [], []
            for cls, letter, rest in re.findall(r'<li class="pq-option (correct|wrong)"><strong>([A-H])\) </strong>(.*?)</li>', sec, re.S):
                note = re.search(r'<span class="pq-note">(.*?)</span>', rest, re.S)
                opts[letter] = _clean(re.sub(r'<span class="pq-note">.*?</span>', "", rest, flags=re.S))
                if cls == "correct":
                    ans.append(letter)
                if note:
                    notes.append(f"{letter}: {_clean(note.group(1))}")
            why = re.search(r'<div class="pq-answer".*?</div>', sec, re.S)
            expl = (_clean(why.group(0)) + " " + " ".join(notes)) if why else " ".join(notes)
            if opts and ans:
                add("jrajath94/aws-aip-c01-study-guide question bank (GitHub)", "https://github.com/jrajath94/aws-aip-c01-study-guide",
                    "AIP-C01", stem, opts, ",".join(ans), expl, dom.group(1) if dom else "")

    # michaelgarcia/educational-aws-gen-ai-certification-prep (MIT): <div class="question" data-correct="B,C"> with option divs + justification
    f = os.path.join(ON, "michaelgarcia_prep_exam.html")
    if os.path.exists(f):
        h = open(f, encoding="utf-8", errors="replace").read()
        blocks = re.split(r'(?=<div class="question" data-question=")', h)[1:]
        for b in blocks:
            head = re.match(r'<div class="question" data-question="(\d+)" data-type="(\w+)" data-correct="([A-H,]+)"', b)
            if not head:
                continue
            topic = re.search(r'<span class="question-topic">(.*?)</span>', b)
            qt = re.search(r'<div class="question-text">(.*?)</div>\s*<div class="options">', b, re.S)
            opts, just = {}, []
            for L, inner in re.findall(r'<div class="option" data-option="([A-H])"[^>]*>(.*?)(?=<div class="option" data-option=|<div class="question-footer|</div>\s*</div>\s*</div>)', b, re.S):
                txt = re.search(r'<span class="option-text">(.*?)</span>', inner, re.S)
                jm = re.search(r'<div class="justification[^"]*">(.*?)</div>', inner, re.S)
                if txt:
                    opts[L] = _clean(txt.group(1))
                if jm:
                    just.append(f"{L}: {_clean(jm.group(1))}")
            if qt and opts:
                add("michaelgarcia/educational-aws-gen-ai-certification-prep (GitHub, MIT)", "https://github.com/michaelgarcia/educational-aws-gen-ai-certification-prep",
                    "AIP-C01", _clean(qt.group(1)), opts, head.group(3).replace(" ", ""), " ".join(just), topic.group(1).strip() if topic else "")

    # tunglt-0058/aip-c01-lesson-learned (CC BY 4.0): "## Question N — title (Select TWO)" / stem / "- **A.** text" / details with "- **A — CORRECT.**"
    f = os.path.join(ON, "tunglt_practice_questions_en.md")
    if os.path.exists(f):
        t = open(f, encoding="utf-8").read()
        for m in re.finditer(r"^## Question (\d+) — (.*?)\n(.*?)(?=^## Question \d+|\Z)", t, re.M | re.S):
            n, title, body = m.groups()
            qpart, _, apart = body.partition("<details>")
            opts = {L: _clean(x) for L, x in re.findall(r"^- \*\*([A-H])\.\*\* (.*)$", qpart, re.M)}
            ans = sorted(set(re.findall(r"\*\*([A-H]) — CORRECT", apart)))
            stem = re.sub(r"^> .*$", "", qpart.split("\n- **", 1)[0], flags=re.M).replace("**", "").strip()
            core = re.search(r"### 🔍 Core analysis[^\n]*\n(.*?)(?=\n### )", apart, re.S)
            expl = _clean(core.group(1))[:900] if core else ""
            if opts and ans:
                add("tunglt-0058/aip-c01-lesson-learned practice questions (GitHub, CC BY 4.0)", "https://github.com/tunglt-0058/aip-c01-lesson-learned",
                    "AIP-C01", stem, opts, ",".join(ans), expl, title.strip())

    # KodeKloud free practice test page: Webflow CMS items with data-field attributes
    f = os.path.join(ON, "kodekloud_practice_test_page.html")
    if os.path.exists(f):
        h = open(f, encoding="utf-8", errors="replace").read()
        for item in re.findall(r'data-quiz-item="true"[^>]*>(.*?)(?=data-quiz-item="true"|</div></div></div>\s*$)', h, re.S):
            fields = {k: _clean(v) for k, v in re.findall(r'data-field="([a-z0-9-]+)">(.*?)</div>', item, re.S)}
            opts = {L: fields[f"option-{L.lower()}"] for L in "ABCD" if fields.get(f"option-{L.lower()}")}
            ans = [fields.get("correct", "").strip()[:1]]
            if fields.get("correct-option-2", "").strip():
                ans.append(fields["correct-option-2"].strip()[:1])
            ans = sorted(a for a in ans if a in opts)
            if fields.get("question") and opts and ans:
                add("KodeKloud free AIP-C01 practice test", "https://kodekloud.com/practice-test/aws-certified-generative-ai-developer-professional-aip-c01",
                    "AIP-C01", fields["question"], opts, ",".join(ans), fields.get("explanation", ""), fields.get("domain", ""))

    # mankale/aipc01-exam-skill SAMPLE_QUESTIONS.md: "### Q1 (Multiple Choice)" / "- A. text" / details "**Correct: C**" + per-option lines
    f = os.path.join(ON, "mankale_sample_questions.md")
    if os.path.exists(f):
        t = open(f, encoding="utf-8").read()
        for m in re.finditer(r"^### Q(\d+)[^\n]*\n(.*?)(?=^### Q\d+|\Z)", t, re.M | re.S):
            body = m.group(2)
            qpart, _, apart = body.partition("<details>")
            opts = {L: x.strip() for L, x in re.findall(r"^- ([A-H])\. (.*)$", qpart, re.M)}
            am = re.search(r"\*\*Correct: ([A-H](?:,\s*[A-H])*)\*\*", apart)
            stem = qpart.split("\n- A.", 1)[0].strip()
            expl = " ".join(_clean(l) for l in re.findall(r"^- [✅❌] \*\*[A-H]:\*\* .*$", apart, re.M))
            if opts and am:
                add("mankale/aipc01-exam-skill sample questions (GitHub)", "https://github.com/mankale/aipc01-exam-skill",
                    "AIP-C01", stem, opts, am.group(1).replace(" ", ""), expl)
