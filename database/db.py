"""SQLite persistence and indicative eligibility checks."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from config import get_settings


@contextmanager
def connect(database_path: Path | str | None = None) -> Iterator[sqlite3.Connection]:
    path = Path(database_path) if database_path else get_settings().database_path
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database(database_path: Path | str | None = None) -> Path:
    settings = get_settings()
    path = Path(database_path) if database_path else settings.database_path
    with connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schemes (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                name_ta TEXT NOT NULL,
                department TEXT NOT NULL,
                summary TEXT NOT NULL,
                summary_ta TEXT NOT NULL,
                benefit TEXT NOT NULL,
                eligibility_json TEXT NOT NULL,
                documents_json TEXT NOT NULL,
                application_url TEXT NOT NULL,
                source_url TEXT NOT NULL,
                tags_json TEXT NOT NULL
            )
            """
        )
        seed_path = settings.base_dir / "data" / "schemes_seed.json"
        schemes = json.loads(seed_path.read_text(encoding="utf-8"))
        connection.executemany(
            """
            INSERT OR IGNORE INTO schemes (
                id, name, name_ta, department, summary, summary_ta, benefit,
                eligibility_json, documents_json, application_url, source_url, tags_json
            ) VALUES (
                :id, :name, :name_ta, :department, :summary, :summary_ta, :benefit,
                :eligibility_json, :documents_json, :application_url, :source_url, :tags_json
            )
            """,
            [
                {
                    **scheme,
                    "eligibility_json": json.dumps(scheme["eligibility"], ensure_ascii=False),
                    "documents_json": json.dumps(scheme["documents"], ensure_ascii=False),
                    "tags_json": json.dumps(scheme["tags"], ensure_ascii=False),
                }
                for scheme in schemes
            ],
        )
    return path


def _decode(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["eligibility"] = json.loads(item.pop("eligibility_json"))
    item["documents"] = json.loads(item.pop("documents_json"))
    item["tags"] = json.loads(item.pop("tags_json"))
    return item


def list_schemes(database_path: Path | str | None = None) -> list[dict[str, Any]]:
    initialize_database(database_path)
    with connect(database_path) as connection:
        rows = connection.execute("SELECT * FROM schemes ORDER BY name").fetchall()
    return [_decode(row) for row in rows]


def get_scheme(scheme_id: str, database_path: Path | str | None = None) -> dict[str, Any] | None:
    initialize_database(database_path)
    with connect(database_path) as connection:
        row = connection.execute("SELECT * FROM schemes WHERE id = ?", (scheme_id,)).fetchone()
    return _decode(row) if row else None


def search_schemes(query: str, limit: int = 6, database_path: Path | str | None = None) -> list[dict[str, Any]]:
    terms = {term.casefold() for term in query.split() if len(term) > 1}
    schemes = list_schemes(database_path)
    scored: list[tuple[int, dict[str, Any]]] = []
    for scheme in schemes:
        text = " ".join(
            [scheme["name"], scheme["name_ta"], scheme["department"], scheme["summary"], *scheme["tags"]]
        ).casefold()
        score = sum(1 for term in terms if term in text)
        if score:
            scored.append((score, scheme))
    scored.sort(key=lambda item: (-item[0], item[1]["name"]))
    matches = [scheme for _, scheme in scored[:limit]]
    return matches if matches else schemes[:limit]


PROFILE_CRITERIA = (
    "age", "state", "gender", "occupation", "category", "is_student",
    "has_land", "is_rural", "education_after_matric",
    "government_school_background", "beneficiary_database_match",
    "meets_household_rules", "house_status",
)


def has_eligibility_details(profile: dict[str, Any]) -> bool:
    return any(profile.get(field) is not None and profile.get(field) != "" for field in PROFILE_CRITERIA)


def check_eligibility(scheme: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    """Compare only the supported demo rules; unknown criteria stay unknown."""
    prior = profile.get("previously_applied_scheme_ids", [])
    if not isinstance(prior, list) or not all(isinstance(item, str) for item in prior):
        raise ValueError("profile.previously_applied_scheme_ids must be a list of scheme IDs")
    if scheme["id"] in prior:
        return {
            "status": "already_applied",
            "reasons": [
                "You reported having already applied for this scheme. Check your existing application status with the official department before applying again; prior application alone does not establish official ineligibility."
            ],
            "missing_information": [],
        }
    rules = scheme["eligibility"]
    failures: list[str] = []
    missing: list[str] = []

    def required_value(key: str, label: str) -> Any:
        value = profile.get(key)
        if value is None or value == "":
            missing.append(label)
        return value

    def required_boolean(key: str, label: str) -> bool | None:
        value = required_value(key, label)
        if value is not None and not isinstance(value, bool):
            raise ValueError(f"profile.{key} must be a boolean")
        return value

    if "state" in rules:
        value = required_value("state", "state")
        state_aliases = {"தமிழ்நாடு": "tamil nadu", "tn": "tamil nadu"}
        normalized_value = state_aliases.get(str(value).casefold(), str(value).casefold()) if value else ""
        normalized_rule = str(rules["state"]).casefold()
        if value and normalized_value != normalized_rule:
            failures.append(f"State should be {rules['state']}")
    if "gender" in rules:
        value = required_value("gender", "gender")
        if value and str(value).casefold() not in {item.casefold() for item in rules["gender"]}:
            failures.append("Gender does not match this scheme's listed group")
    if "occupation" in rules:
        value = required_value("occupation", "occupation")
        if value and str(value).casefold() not in {item.casefold() for item in rules["occupation"]}:
            failures.append("Occupation does not match this scheme's listed group")
    if rules.get("student_required"):
        value = required_boolean("is_student", "student status")
        if value is not None and not value:
            failures.append("This scheme is intended for students")
    if rules.get("landholding_required"):
        value = required_boolean("has_land", "landholding status")
        if value is not None and not value:
            failures.append("Landholding is required by the demo rule")
    if rules.get("rural_resident_required"):
        value = required_boolean("is_rural", "rural residence")
        if value is not None and not value:
            failures.append("Rural residence is required by the demo rule")
    if rules.get("adult_required"):
        age = required_value("age", "age")
        if age is not None:
            try:
                numeric_age = int(age)
            except (TypeError, ValueError) as exc:
                raise ValueError("profile.age must be an integer") from exc
            if isinstance(age, bool) or str(numeric_age) != str(age).strip():
                raise ValueError("profile.age must be an integer")
            if numeric_age < 18:
                failures.append("Applicant must be an adult")
    if "category" in rules:
        value = required_value("category", "community category")
        if value and str(value).casefold() not in {item.casefold() for item in rules["category"]}:
            failures.append("Community category does not match this scheme's listed group")
    if rules.get("education_after_matric_required"):
        value = required_boolean("education_after_matric", "studying beyond matriculation")
        if value is not None and not value:
            failures.append("Study beyond matriculation is required by the demo rule")
    if rules.get("government_school_background_required"):
        value = required_boolean("government_school_background", "government school background")
        if value is not None and not value:
            failures.append("Government school background is required by the demo rule")
    if rules.get("database_match_required"):
        value = required_boolean("beneficiary_database_match", "beneficiary database match")
        if value is not None and not value:
            failures.append("A beneficiary database match is required")
    if rules.get("household_rules_apply"):
        value = required_boolean("meets_household_rules", "household eligibility criteria")
        if value is not None and not value:
            failures.append("Household criteria do not match the supplied information")
    if "house_status" in rules:
        value = required_value("house_status", "household housing status")
        allowed = {item.casefold() for item in rules["house_status"]}
        if value and str(value).casefold() not in allowed:
            failures.append("Household housing status does not match this scheme's listed group")

    if failures:
        status = "unlikely_eligible"
    elif missing:
        status = "needs_more_information"
    else:
        status = "possibly_eligible"
    return {"status": status, "reasons": failures, "missing_information": missing}
