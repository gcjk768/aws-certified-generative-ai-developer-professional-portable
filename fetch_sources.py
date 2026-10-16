"""Download the online AIP-C01 question sources into sources/online/ (gitignored). python fetch_sources.py [--force]
One GET per file, cached; build_csv.py parses whatever is present. Sources (checked 2026-10-16):
  JeremyEngineer/aws-aip-c01-practice-exam (GitHub, MIT): questions_easy/hard/veryhard.json, per-option explanations
  open-exam-prep.com/practice/aws-genai-developer-pro: 100 questions embedded in the Next.js payload (robots allow)
  certsafari.com free sample questions: 35 questions as schema.org Quiz JSON-LD (robots allow)
  certland.net free practice questions: 8 questions in plain HTML (robots allow)
"""
import os, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "sources", "online")
UA = {"User-Agent": "Mozilla/5.0 (aipc01-quiz-bot; personal study use)"}
FILES = {
    "jeremy_easy.json": "https://raw.githubusercontent.com/JeremyEngineer/aws-aip-c01-practice-exam/main/questions/questions_easy.json",
    "jeremy_hard.json": "https://raw.githubusercontent.com/JeremyEngineer/aws-aip-c01-practice-exam/main/questions/questions_hard.json",
    "jeremy_veryhard.json": "https://raw.githubusercontent.com/JeremyEngineer/aws-aip-c01-practice-exam/main/questions/questions_veryhard.json",
    "oep.html": "https://open-exam-prep.com/practice/aws-genai-developer-pro",
    "certsafari.html": "https://certsafari.com/aws/gen-ai-developer-professional/practice-questions",
    "certland.html": "https://certland.net/exams/aws-certified-generative-ai-developer-professional-aip-c01/practice-questions/",
}

os.makedirs(OUT, exist_ok=True)
for name, url in FILES.items():
    path = os.path.join(OUT, name)
    if os.path.exists(path) and "--force" not in sys.argv:
        print("cached", name); continue
    try:
        data = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
        open(path, "wb").write(data)
        print("fetched", name, len(data), "bytes")
    except Exception as exc:   # a failed source is skipped by the builder, never fatal
        print("FAILED", name, exc)
    time.sleep(3)              # low volume: a few seconds apart
