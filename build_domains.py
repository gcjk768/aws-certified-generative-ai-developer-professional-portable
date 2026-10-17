"""Tag every question in data/questions.csv with its real exam domain.

Usage: python build_domains.py <path to exam-portal/study/<exam>.json> [--workers N]

Classifies with Claude Haiku through the local `claude` CLI in batches of ~40
(question + options only). Writes data/domains.json = {"<id>": "<domain>"}.
Resumable: ids already in domains.json are skipped; the file is rewritten
after every batch. Prints the summed total_cost_usd at the end.
"""
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "data", "questions.csv")
OUT_PATH = os.path.join(HERE, "data", "domains.json")
BATCH = 40

# Exam-specific tie-break hints, keyed by the study JSON's "exam" value.
TIEBREAK = {
    "SAP-C03": [
        "Nearly every question says 'least operational overhead' or 'cost-effective'; that wording alone does not decide the domain.",
        "Cost-optimized design ONLY when cost/pricing is the deciding criterion (Savings Plans, Spot, storage class, data transfer cost, rightsizing, billing/cost visibility). 'Cheapest DR option' -> cost only if cost is what separates the answers; a DR strategy choice driven by RTO/RPO -> resilience.",
        "Resilience, migration & business continuity: DR, RTO/RPO, backups, multi-AZ/multi-Region failover, high availability, migration strategy or tools (MGN, DMS, DataSync, Snowball, 7 Rs, migration planning/discovery).",
        "Security, compliance & governance: multi-account governance (Organizations, SCPs, Control Tower), IAM/access control, encryption/KMS, findings/compliance, data protection, auditing.",
        "Operational excellence & automation: CI/CD and deployment strategies, IaC/StackSets, monitoring/observability/logging, automated remediation, patching, Systems Manager, data-lake governance with Lake Formation.",
        "Cloud-native design & implementation: choosing the architecture/services for a new or modernised workload (compute, containers, serverless, databases, caching, messaging, networking/hybrid connectivity, performance, GenAI/agents).",
    ],
    "AIP-C01": [
        "FM integration, data management and compliance: choosing/configuring FMs, RAG vs fine-tuning, data preparation pipelines, vector stores, chunking/embeddings/retrieval design, prompt engineering and prompt management.",
        "Implementation and integration: building agents and tool use (Bedrock Agents, AgentCore, MCP, Strands, Step Functions orchestration), FM API integration (streaming, retries, fallbacks), wiring GenAI into enterprise systems and apps.",
        "AI safety, security and governance: guardrails, prompt injection, hallucination/grounding controls, PII protection, IAM/VPC endpoints/KMS, auditing, compliance, responsible AI.",
        "Operational efficiency and optimization: cost and latency/throughput choices (batch, provisioned throughput, cross-Region inference, caching, token reduction), scaling, and monitoring with CloudWatch.",
        "Testing, validation and troubleshooting: evaluating model/RAG/agent quality (LLM-as-a-judge, metrics, golden datasets), regression tests, and diagnosing failures.",
        "Pick by what is being DECIDED: a question about reducing token cost -> optimization even if it involves RAG; a question about why answers are wrong and how to measure it -> testing; a question about blocking unsafe content -> safety.",
    ],
}

lock = threading.Lock()
cost = [0.0]


def load_domains(study_path):
    d = json.load(open(study_path, encoding="utf-8"))
    domains = []
    for dm in d["domains"]:
        titles = "; ".join(n["title"] for n in dm.get("notes", []))
        domains.append((dm["domain"], f'{dm["summary"]["tests"]} Topics: {titles}.'))
    return d.get("exam", ""), domains


def build_prompt(exam, domains, rows):
    lines = [
        f"You classify {exam} exam questions into exactly one exam domain.",
        "Domains (use the exact name):",
    ]
    lines += [f'- "{name}": {scope}' for name, scope in domains]
    lines.append("Tie-break rules: pick the domain the question's DECISION is about (what distinguishes the right answer), not every service it mentions.")
    lines += [f"- {t}" for t in TIEBREAK.get(exam, [])]
    lines.append('Reply with ONLY a JSON object {"<id>": "<exact domain name>", ...} covering every id below. No prose, no code fences.')
    lines.append("")
    for r in rows:
        lines.append(f'### {r["id"]}\n{r["question"].strip()}\n{r["options"].strip()}\n')
    return "\n".join(lines)


def call_claude(prompt):
    exe = shutil.which("claude") or "claude"
    with tempfile.TemporaryDirectory() as cwd:
        p = subprocess.run(
            # The last three flags drop the default system prompt, CLAUDE.md/settings/hooks and MCP
            # servers: without them every call re-sends ~146k tokens (~$0.14) of agent context.
            [exe, "-p", "--model", "haiku", "--output-format", "json", "--tools", "",
             "--system-prompt", "You are an exam question classifier. Output strict JSON only.",
             "--setting-sources", "", "--strict-mcp-config"],
            input=prompt, capture_output=True, text=True, encoding="utf-8", cwd=cwd, timeout=600,
        )
    out = json.loads(p.stdout)
    with lock:
        cost[0] += float(out.get("total_cost_usd") or 0)
    text = out.get("result", "")
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else {}


def classify(exam, domains, rows):
    valid = {n for n, _ in domains}
    want = {r["id"] for r in rows}
    got = {}
    for attempt in (1, 2):  # one retry on bad output
        try:
            res = call_claude(build_prompt(exam, domains, [r for r in rows if r["id"] not in got]))
        except Exception as e:  # bad JSON, CLI failure, timeout
            print(f"  attempt {attempt} failed: {e!r}", flush=True)
            continue
        got.update({k: v for k, v in res.items() if k in want and v in valid})
        if want <= got.keys():
            break
        print(f"  attempt {attempt}: {len(want - got.keys())} ids missing/invalid", flush=True)
    return got


def main():
    study = sys.argv[1]
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 4
    exam, domains = load_domains(study)
    rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))
    done = json.load(open(OUT_PATH, encoding="utf-8")) if os.path.exists(OUT_PATH) else {}
    valid = {n for n, _ in domains}
    done = {k: v for k, v in done.items() if v in valid}
    todo = [r for r in rows if r["id"] not in done]
    batches = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
    print(f"{exam}: {len(rows)} questions, {len(done)} done, {len(batches)} batches to run", flush=True)

    def run(batch):
        got = classify(exam, domains, batch)
        with lock:
            done.update(got)
            tmp = OUT_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({r["id"]: done[r["id"]] for r in rows if r["id"] in done}, f, ensure_ascii=False, indent=0)
            os.replace(tmp, OUT_PATH)
            print(f"  batch {batch[0]['id']}: {len(got)}/{len(batch)} ok, total {len(done)}/{len(rows)}, cost ${cost[0]:.3f}", flush=True)

    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(run, batches))
    missing = [r["id"] for r in rows if r["id"] not in done]
    print(f"done: {len(done)}/{len(rows)}, missing {len(missing)} {missing[:10]}, cost this run ${cost[0]:.3f}")


if __name__ == "__main__":
    main()
