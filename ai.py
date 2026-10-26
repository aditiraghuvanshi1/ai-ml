"""Optional Ollama extension.

Safety design:
  * The model NEVER writes or runs SQL.
  * Backend code decides which records to fetch (simple, fixed rules) using parameterised queries.
  * Only id, name, date of birth and course are sent to the model (no email/phone/address).
  * The model is told to answer only from the supplied records.
"""
import json
import os
import re
import urllib.error
import urllib.request

import database as db

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:1b")
MAX_RECORDS = 50


class OllamaUnavailable(Exception):
    pass


def build_filters(question: str) -> dict:
    """Turn a question into safe filter values using fixed rules."""
    q = question.lower()
    filters = {}

    m = re.search(r"born\s+(after|before|in)\s+(\d{4})", q)
    if m:
        kind, year = m.group(1), int(m.group(2))
        if kind == "after":
            filters["born_after"] = f"{year + 1}-01-01"
        elif kind == "before":
            filters["born_before"] = f"{year - 1}-12-31"
        else:
            filters["born_after"] = f"{year}-01-01"
            filters["born_before"] = f"{year}-12-31"

    for course in db.distinct_courses():
        if course.lower() in q:
            filters["course"] = course
            break
    return filters


def build_context(question: str):
    filters = build_filters(question)
    total = db.count_students()
    matches = db.count_students(**filters)
    records = db.list_students(limit=MAX_RECORDS, **filters)

    lines = [
        f"Total students in database: {total}",
        f"Students matching the question's filters: {matches}",
        f"Records shown below: {len(records)}" + (" (list truncated)" if matches > len(records) else ""),
        "",
    ]
    for r in records:
        lines.append(f"- id {r['id']}: {r['name']}, born {r['date_of_birth']}, course: {r['course'] or 'n/a'}")
    return "\n".join(lines), len(records)


def ask_ollama(prompt: str) -> str:
    payload = json.dumps({"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate", data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode())["response"].strip()
    except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
        raise OllamaUnavailable(
            f"Could not get an answer from Ollama at {OLLAMA_URL} (model {OLLAMA_MODEL}). "
            f"Make sure Ollama is running and the model is pulled. Details: {exc}"
        )


def answer_question(question: str) -> dict:
    context, used = build_context(question)
    prompt = (
        "You answer questions about a student database.\n"
        "Use ONLY the data below. If the data does not contain the answer, say you cannot tell.\n"
        "Be brief and accurate. Do not invent students or numbers.\n\n"
        f"DATA:\n{context}\n\nQUESTION: {question}\nANSWER:"
    )
    return {
        "question": question,
        "answer": ask_ollama(prompt),
        "records_used": used,
        "model": OLLAMA_MODEL,
    }
