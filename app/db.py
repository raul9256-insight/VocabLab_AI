from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from economist_vocab import DEFAULT_DB_PATH, connect


WEB_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS word_enrichment (
    word_id INTEGER PRIMARY KEY REFERENCES words(id) ON DELETE CASCADE,
    english_definition TEXT NOT NULL DEFAULT '',
    pronunciation TEXT NOT NULL DEFAULT '',
    synonyms_json TEXT NOT NULL DEFAULT '[]',
    example_sentence TEXT NOT NULL DEFAULT '',
    sentence_distractors_json TEXT NOT NULL DEFAULT '[]',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS assessment_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'active',
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    current_index INTEGER NOT NULL DEFAULT 0,
    score INTEGER NOT NULL DEFAULT 0,
    estimated_band_rank INTEGER,
    estimated_band_label TEXT
);

CREATE TABLE IF NOT EXISTS assessment_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES assessment_sessions(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    word_id INTEGER NOT NULL REFERENCES words(id) ON DELETE CASCADE,
    band_rank INTEGER NOT NULL,
    band_label TEXT NOT NULL,
    question_type TEXT NOT NULL,
    prompt_text TEXT NOT NULL,
    correct_option TEXT NOT NULL,
    options_json TEXT NOT NULL,
    explanation TEXT NOT NULL DEFAULT '',
    user_answer TEXT,
    is_correct INTEGER,
    answered_at TEXT
);

CREATE TABLE IF NOT EXISTS learning_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'active',
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    current_index INTEGER NOT NULL DEFAULT 0,
    score INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS learning_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES learning_sessions(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    word_id INTEGER NOT NULL REFERENCES words(id) ON DELETE CASCADE,
    question_type TEXT NOT NULL,
    prompt_text TEXT NOT NULL,
    correct_option TEXT NOT NULL,
    options_json TEXT NOT NULL,
    explanation TEXT NOT NULL DEFAULT '',
    user_answer TEXT,
    is_correct INTEGER,
    answered_at TEXT
);

CREATE TABLE IF NOT EXISTS briefing_sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    accent_color TEXT NOT NULL DEFAULT '#d71920',
    display_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS briefing_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id INTEGER NOT NULL REFERENCES briefing_sections(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    strapline TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL DEFAULT '',
    summary_points_json TEXT NOT NULL DEFAULT '[]',
    published_on TEXT NOT NULL,
    reading_time_minutes INTEGER NOT NULL DEFAULT 4,
    economist_note TEXT NOT NULL DEFAULT '',
    display_order INTEGER NOT NULL DEFAULT 0
);
"""


DEFAULT_BRIEFING_SEED = [
    {
        "slug": "leaders",
        "name": "Leaders",
        "description": "Arguments and editorials.",
        "accent_color": "#d71920",
        "articles": [
            {
                "title": "Central banks are winning inflation's second round",
                "strapline": "Policy",
                "summary": "Disinflation is broadening, but policymakers are still balancing fragile growth against sticky service prices.",
                "summary_points": [],
                "published_on": "Apr 19, 2026 09:00 AM",
                "reading_time_minutes": 4,
                "economist_note": "Patience still matters more than celebration.",
            }
        ],
    },
    {
        "slug": "united-states",
        "name": "US",
        "description": "Politics, policy and society in America.",
        "accent_color": "#275d9a",
        "articles": [
            {
                "title": "America's housing shortage is starting to reshape migration",
                "strapline": "Property",
                "summary": "High rents and mortgage costs are pushing households to rethink where they can live and work.",
                "summary_points": [],
                "published_on": "Apr 19, 2026 10:15 AM",
                "reading_time_minutes": 4,
                "economist_note": "Housing is becoming a growth constraint as much as a social one.",
            }
        ],
    },
    {
        "slug": "china",
        "name": "China",
        "description": "Power, markets and policy in China.",
        "accent_color": "#a61e22",
        "articles": [
            {
                "title": "China's local-government repair job is only beginning",
                "strapline": "Debt and growth",
                "summary": "Beijing is trying to stabilise provincial balance-sheets without reviving the old investment model.",
                "summary_points": [],
                "published_on": "Apr 17, 2026 09:10 AM",
                "reading_time_minutes": 4,
                "economist_note": "Intervention is easier than lasting reform.",
            }
        ],
    },
    {
        "slug": "business",
        "name": "Business",
        "description": "Companies, industries and competition.",
        "accent_color": "#2d6a4f",
        "articles": [
            {
                "title": "Consultancies are quietly becoming AI integrators",
                "strapline": "Services",
                "summary": "The real prize in corporate AI may lie less in models themselves than in stitching them into messy workflows.",
                "summary_points": [],
                "published_on": "Apr 19, 2026 11:40 AM",
                "reading_time_minutes": 5,
                "economist_note": "Integration is starting to matter as much as invention.",
            }
        ],
    },
    {
        "slug": "europe",
        "name": "Europe",
        "description": "Politics and power across Europe.",
        "accent_color": "#1f4f8a",
        "articles": [
            {
                "title": "Hungary's elections",
                "strapline": "Democracy in Europe",
                "summary": "Peter Magyar's victory will keep Hungary in the spotlight",
                "summary_points": [],
                "published_on": "Apr 16, 2026 03:44 PM",
                "reading_time_minutes": 4,
                "economist_note": "The country will become a test case for reversing democratic decay",
            }
        ],
    },
]


def ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    conn = connect(db_path or DEFAULT_DB_PATH)
    conn.executescript(WEB_SCHEMA)
    ensure_column(conn, "word_enrichment", "english_definition", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "word_enrichment", "pronunciation", "TEXT NOT NULL DEFAULT ''")
    conn.execute(
        """
        INSERT INTO users (id, username)
        VALUES (1, 'lawrence')
        ON CONFLICT(id) DO NOTHING
        """
    )
    ensure_briefing_seed(conn)
    conn.commit()
    return conn


def ensure_briefing_seed(conn: sqlite3.Connection) -> None:
    for section_index, section in enumerate(DEFAULT_BRIEFING_SEED, start=1):
        conn.execute(
            """
            INSERT INTO briefing_sections (slug, name, description, accent_color, display_order)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
                name = excluded.name,
                description = excluded.description,
                accent_color = excluded.accent_color,
                display_order = excluded.display_order
            """,
            (
                section["slug"],
                section["name"],
                section["description"],
                section["accent_color"],
                section_index,
            ),
        )
        section_id = conn.execute(
            "SELECT id FROM briefing_sections WHERE slug = ?",
            (section["slug"],),
        ).fetchone()[0]
        for article_index, article in enumerate(section["articles"], start=1):
            existing_article = conn.execute(
                """
                SELECT id
                FROM briefing_articles
                WHERE section_id = ? AND title = ?
                """,
                (section_id, article["title"]),
            ).fetchone()
            if existing_article is None:
                conn.execute(
                    """
                    INSERT INTO briefing_articles (
                        section_id, title, strapline, summary, summary_points_json,
                        published_on, reading_time_minutes, economist_note, display_order
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        section_id,
                        article["title"],
                        article["strapline"],
                        article["summary"],
                        json.dumps(article["summary_points"]),
                        article["published_on"],
                        article["reading_time_minutes"],
                        article["economist_note"],
                        article_index,
                    ),
                )
                continue
            conn.execute(
                """
                UPDATE briefing_articles
                SET strapline = ?,
                    summary = ?,
                    summary_points_json = ?,
                    published_on = ?,
                    reading_time_minutes = ?,
                    economist_note = ?,
                    display_order = ?
                WHERE id = ?
                """,
                (
                    article["strapline"],
                    article["summary"],
                    json.dumps(article["summary_points"]),
                    article["published_on"],
                    article["reading_time_minutes"],
                    article["economist_note"],
                    article_index,
                    existing_article["id"],
                ),
            )


def fetch_stats(conn: sqlite3.Connection) -> dict:
    row = conn.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM words) AS total_words,
            (SELECT COUNT(*) FROM word_enrichment WHERE json_array_length(synonyms_json) > 0) AS words_with_synonyms,
            (SELECT COUNT(*) FROM word_enrichment WHERE example_sentence <> '') AS words_with_examples,
            (SELECT COUNT(*) FROM assessment_sessions) AS tests_taken,
            (SELECT COUNT(*) FROM learning_sessions) AS learning_runs
        """
    ).fetchone()
    return dict(row)


def band_summary(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT best_band_rank, best_band_label, COUNT(*) AS total
        FROM words
        GROUP BY best_band_rank, best_band_label
        ORDER BY best_band_rank
        """
    ).fetchall()


def letters_for_band(conn: sqlite3.Connection, band_rank: int) -> list[str]:
    rows = conn.execute(
        """
        SELECT DISTINCT UPPER(SUBSTR(lemma, 1, 1)) AS letter
        FROM words
        WHERE best_band_rank = ?
        ORDER BY letter
        """,
        (band_rank,),
    ).fetchall()
    return [row["letter"] for row in rows if row["letter"]]


def definitions_for_word(conn: sqlite3.Connection, word_id: int) -> list[str]:
    rows = conn.execute(
        """
        SELECT meanings_json
        FROM source_entries
        WHERE word_id = ?
        ORDER BY band_rank, workbook_name, row_number
        """,
        (word_id,),
    ).fetchall()
    seen: list[str] = []
    for row in rows:
        for meaning in json.loads(row["meanings_json"]):
            if meaning not in seen:
                seen.append(meaning)
    return seen


def parts_of_speech_for_word(conn: sqlite3.Connection, word_id: int) -> list[str]:
    rows = conn.execute(
        """
        SELECT DISTINCT pos
        FROM source_entries
        WHERE word_id = ? AND pos IS NOT NULL AND pos <> ''
        ORDER BY pos
        """,
        (word_id,),
    ).fetchall()
    return [row["pos"] for row in rows]


def briefing_sections(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            briefing_sections.id,
            briefing_sections.slug,
            briefing_sections.name,
            briefing_sections.description,
            briefing_sections.accent_color,
            briefing_sections.display_order,
            COUNT(briefing_articles.id) AS article_count
        FROM briefing_sections
        LEFT JOIN briefing_articles ON briefing_articles.section_id = briefing_sections.id
        GROUP BY briefing_sections.id
        ORDER BY briefing_sections.display_order, briefing_sections.name
        """
    ).fetchall()
    return [dict(row) for row in rows]


def briefing_section_by_slug(conn: sqlite3.Connection, slug: str | None = None) -> dict | None:
    sections = briefing_sections(conn)
    if not sections:
        return None
    if slug:
        for section in sections:
            if section["slug"] == slug:
                return section
    return sections[0]


def briefing_articles_for_section(conn: sqlite3.Connection, section_id: int) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            id,
            title,
            strapline,
            summary,
            summary_points_json,
            published_on,
            reading_time_minutes,
            economist_note
        FROM briefing_articles
        WHERE section_id = ?
        ORDER BY display_order, id
        """,
        (section_id,),
    ).fetchall()
    articles = []
    for row in rows:
        item = dict(row)
        item["summary_points"] = json.loads(item.pop("summary_points_json") or "[]")
        articles.append(item)
    return articles


def briefing_overview(conn: sqlite3.Connection) -> dict:
    row = conn.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM briefing_sections) AS total_sections,
            (SELECT COUNT(*) FROM briefing_articles) AS total_articles,
            (SELECT MAX(published_on) FROM briefing_articles) AS latest_issue_date
        """
    ).fetchone()
    return dict(row)
