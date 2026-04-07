from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from app.db import definitions_for_word, parts_of_speech_for_word


def load_env_file(dotenv_path: Path = Path(".env")) -> None:
    if not dotenv_path.exists():
        return
    for line in dotenv_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def openai_client():
    load_env_file()
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Add it to your environment or .env file.")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("The openai package is not installed. Run: python3 -m pip install openai") from exc
    return OpenAI(api_key=api_key)


def openai_model() -> str:
    load_env_file()
    return os.environ.get("OPENAI_MODEL", "gpt-5").strip() or "gpt-5"


def words_for_generation(conn: sqlite3.Connection, limit: int, band_rank: int | None = None) -> list[sqlite3.Row]:
    clauses = [
        "(word_enrichment.word_id IS NULL OR word_enrichment.english_definition = '' OR word_enrichment.example_sentence = '' OR word_enrichment.synonyms_json = '[]')"
    ]
    params: list[object] = []
    if band_rank is not None:
        clauses.append("words.best_band_rank = ?")
        params.append(band_rank)
    sql = f"""
        SELECT words.id, words.lemma, words.best_band_label, words.best_band_rank
        FROM words
        LEFT JOIN word_enrichment ON word_enrichment.word_id = words.id
        WHERE {' AND '.join(clauses)}
        ORDER BY words.best_band_rank, words.lemma
        LIMIT ?
    """
    params.append(limit)
    return conn.execute(sql, params).fetchall()


def prompt_payload(conn: sqlite3.Connection, rows: list[sqlite3.Row]) -> list[dict]:
    payload = []
    for row in rows:
        payload.append(
            {
                "lemma": row["lemma"],
                "band_label": row["best_band_label"],
                "parts_of_speech": parts_of_speech_for_word(conn, row["id"]),
                "chinese_definitions": definitions_for_word(conn, row["id"])[:5],
            }
        )
    return payload


RESPONSE_SCHEMA = {
    "type": "json_schema",
    "name": "vocab_enrichment_batch",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "lemma": {"type": "string"},
                        "english_definition": {"type": "string"},
                        "example_sentence": {"type": "string"},
                        "synonyms": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["lemma", "english_definition", "example_sentence", "synonyms"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["items"],
        "additionalProperties": False,
    },
}


SYSTEM_PROMPT = (
    "You are enriching an English vocabulary database for a learner. "
    "For each word, produce a concise learner-friendly English definition, one natural example sentence, "
    "and 2 to 4 clear synonyms. Keep the meaning aligned with the provided Chinese definitions and part of speech. "
    "Prefer contemporary, neutral English. The example sentence should use the target word naturally and clearly. "
    "Return structured JSON only."
)


def generate_enrichment_batch(conn: sqlite3.Connection, *, limit: int, band_rank: int | None = None) -> dict[str, int]:
    rows = words_for_generation(conn, limit=limit, band_rank=band_rank)
    if not rows:
        return {"selected": 0, "updated": 0}
    client = openai_client()
    payload = prompt_payload(conn, rows)
    response = client.responses.create(
        model=openai_model(),
        instructions=SYSTEM_PROMPT,
        input=json.dumps({"items": payload}, ensure_ascii=False),
        text={"format": RESPONSE_SCHEMA},
    )
    parsed = json.loads(response.output_text)
    by_lemma = {item["lemma"].strip().lower(): item for item in parsed.get("items", [])}
    updated = 0
    for row in rows:
        item = by_lemma.get(row["lemma"].strip().lower())
        if not item:
            continue
        synonyms = [syn.strip() for syn in item.get("synonyms", []) if syn.strip()]
        conn.execute(
            """
            INSERT INTO word_enrichment (
                word_id, english_definition, synonyms_json, example_sentence, sentence_distractors_json
            )
            VALUES (?, ?, ?, ?, '[]')
            ON CONFLICT(word_id) DO UPDATE SET
                english_definition = excluded.english_definition,
                synonyms_json = excluded.synonyms_json,
                example_sentence = excluded.example_sentence,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                row["id"],
                item.get("english_definition", "").strip(),
                json.dumps(synonyms, ensure_ascii=False),
                item.get("example_sentence", "").strip(),
            ),
        )
        updated += 1
    conn.commit()
    return {"selected": len(rows), "updated": updated}
