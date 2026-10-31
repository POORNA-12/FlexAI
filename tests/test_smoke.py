"""Smoke tests that must pass with MySQL stopped.

Purpose (ADR-0001 D6): prove the environment — interpreter, imports, configuration
validation, ID shapes and business-rule arithmetic — without any database.

Anything requiring a database belongs in tests/test_project.py (marked ``db``).
"""

from __future__ import annotations

import re
from datetime import date

import pytest

from backend.business_rules import (
    calculate_delivery_delay,
    calculate_price_variance,
    calculate_quantity_variance,
    calculate_schedule_impact,
    is_supplier_silent,
)
from backend.config import Settings, get_settings
from backend.generator import BASE_SEED, SyntheticDataGenerator
from backend.validation import DataValidator

ID_PATTERNS = {
    "po": re.compile(r"^PO-2026-\d{6}$"),
    "po_line": re.compile(r"^PO-2026-\d{6}-L\d{2}$"),
    "ack": re.compile(r"^ACK-PO-2026-\d{6}-\d{2}$"),
    "change": re.compile(r"^CHG-PO-2026-\d{6}-\d{6}$"),
    "promise": re.compile(r"^PRM-ACK-PO-2026-\d{6}-\d{2}-\d{2}$"),
    "plan": re.compile(r"^PLAN-PO-2026-\d{6}-L\d{2}$"),
}


@pytest.fixture(scope="module")
def dev_tables() -> dict:
    """Deterministic development-scale dataset, generated once."""
    return SyntheticDataGenerator(seed=BASE_SEED, scale="dev").generate_all()


def test_config_is_validated() -> None:
    """Settings load from backend/.env and expose a usable DSN."""
    settings = get_settings()
    assert settings.db_password, "DB_PASSWORD must be present (no default allowed)"
    assert settings.db_port == 3306
    dsn = settings.sqlalchemy_url()
    assert dsn.startswith("mysql+pymysql://")
    assert settings.cors_origin_list, "CORS origin list must not be empty"


def test_config_rejects_missing_password(monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing password must be a hard error, never a silent default."""
    monkeypatch.delenv("DB_PASSWORD", raising=False)
    monkeypatch.setenv("DB_PASSWORD", "")
    with pytest.raises(Exception):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_generated_ids_follow_conventions(dev_tables: dict) -> None:
    """Every id shape documented in docs/02-architecture/ID-CONVENTIONS.md holds."""
    checks = {
        "po": dev_tables["purchase_orders"][0]["po_id"],
        "po_line": dev_tables["po_lines"][0]["po_line_id"],
        "ack": dev_tables["acknowledgements"][0]["ack_id"],
        "change": dev_tables["change_requests"][0]["change_id"],
        "promise": dev_tables["promise_dates"][0]["promise_id"],
        "plan": dev_tables["inventory_plans"][0]["plan_id"],
    }
    for key, value in checks.items():
        assert ID_PATTERNS[key].match(value), f"{key} id '{value}' violates the convention"


def test_variance_math() -> None:
    """Derived values are computed, not invented."""
    assert calculate_quantity_variance(100, 90) == -10.0
    assert calculate_price_variance(100.0, 110.0) == 10.0
    assert calculate_delivery_delay(date(2026, 4, 1), date(2026, 4, 6)) == 5


def test_schedule_impact_math() -> None:
    """Shortage = required - (available + usable supply)."""
    delay, shortage, status = calculate_schedule_impact(
        required_qty=100,
        available_inventory=20,
        projected_supply=60,
        requested_delivery_date=date(2026, 4, 15),
        current_promised_date=date(2026, 4, 15),
        production_required_date=date(2026, 4, 20),
    )
    assert (delay, shortage, status) == (0, 20, "CONFIRMED_SHORTAGE")


def test_silence_threshold() -> None:
    """Silence is a date comparison, not a random flag."""
    assert is_supplier_silent(date(2026, 4, 1), None, date(2026, 4, 8)) is True
    assert is_supplier_silent(date(2026, 4, 1), date(2026, 4, 3), date(2026, 4, 8)) is False


def test_generator_is_deterministic() -> None:
    """Same seed -> same rows (in-memory reproducibility)."""
    first = SyntheticDataGenerator(seed=BASE_SEED, scale="dev").generate_all()
    second = SyntheticDataGenerator(seed=BASE_SEED, scale="dev").generate_all()
    for table in ("purchase_orders", "acknowledgements", "change_requests", "inventory_plans"):
        assert first[table] == second[table], f"{table} is not reproducible"


def test_pending_changes_never_touch_supply(dev_tables: dict) -> None:
    """Core invariant (INV-1), checked without a database."""
    plans = {p["po_line_id"]: p for p in dev_tables["inventory_plans"]}
    lines = {l["po_line_id"]: l for l in dev_tables["po_lines"]}
    injected = {
        gt["record_id"]
        for gt in dev_tables["ground_truth_records"]
        if gt["issue_type"] == "unapproved_change_updates_plan"
    }
    for change in dev_tables["change_requests"]:
        if change["status"] != "PENDING_APPROVAL" or change["change_type"] != "QUANTITY":
            continue
        plan = plans.get(change["po_line_id"])
        line = lines.get(change["po_line_id"])
        if not plan or not line or plan["plan_id"] in injected:
            continue
        assert plan["projected_supply"] == line["ordered_qty"]


def test_validation_summary_is_well_formed(dev_tables: dict) -> None:
    """Validator returns the documented contract (counts + metrics)."""
    summary = DataValidator(dev_tables).run_all_validations()
    assert summary["passed_checks"] > 0
    assert summary["failed_checks"] == 0
    metrics = summary["metrics"]
    for key in ("true_positives", "false_positives", "precision", "recall", "f1_score"):
        assert key in metrics
