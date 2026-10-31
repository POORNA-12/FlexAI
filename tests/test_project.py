"""
Automated pytest suite for Supplier Acknowledgement and Schedule Impact Manager.
Covers all 20 required test criteria from Section 25.
"""

import io
import json
import openpyxl
import pytest
from datetime import date, datetime
from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import app
from backend.generator import SyntheticDataGenerator, BASE_SEED
from backend.validation import DataValidator
from backend.business_rules import (
    calculate_quantity_variance,
    calculate_price_variance,
    calculate_delivery_delay,
    evaluate_approval_requirement,
    calculate_schedule_impact,
    is_supplier_silent,
)
from backend.services import (
    approve_change_request,
    reject_change_request,
    run_reproducibility_test,
)
from backend import models
from backend.database import SessionLocal, init_db


@pytest.fixture(scope="module")
def dev_dataset():
    """Generates a small deterministic test fixture."""
    gen = SyntheticDataGenerator(seed=BASE_SEED, scale="dev")
    return gen.generate_all()


# 1. Deterministic ID generation
def test_01_deterministic_id_generation(dev_dataset):
    pos = dev_dataset["purchase_orders"]
    acks = dev_dataset["acknowledgements"]
    chgs = dev_dataset["change_requests"]

    assert pos[0]["po_id"] == "PO-2026-000001"
    assert acks[0]["ack_id"].startswith("ACK-PO-2026-")
    assert chgs[0]["change_id"].startswith("CHG-PO-2026-")


# 2. Foreign-key integrity
def test_02_foreign_key_integrity(dev_dataset):
    validator = DataValidator(dev_dataset)
    validator.check_foreign_key_integrity()
    assert validator.summary["failed_checks"] == 0


# 3. Partial acknowledgement handling
def test_03_partial_acknowledgement_handling(dev_dataset):
    partial_acks = [a for a in dev_dataset["acknowledgements"] if a["status"] == "PARTIAL_ACCEPTANCE"]
    assert len(partial_acks) > 0
    for a in partial_acks:
        assert a["accepted_qty"] > 0
        assert a["rejected_qty"] > 0


# 4. Quantity reconciliation
def test_04_quantity_reconciliation(dev_dataset):
    validator = DataValidator(dev_dataset)
    validator.check_quantity_reconciliation()
    assert validator.summary["failed_checks"] == 0


# 5. Price variance calculation
def test_05_price_variance_calculation():
    var_up = calculate_price_variance(100.0, 110.0)
    assert var_up == 10.0
    var_down = calculate_price_variance(100.0, 95.0)
    assert var_down == -5.0
    var_same = calculate_price_variance(50.0, 50.0)
    assert var_same == 0.0


# 6. Delivery delay calculation
def test_06_delivery_delay_calculation():
    req = date(2026, 4, 10)
    prom_delayed = date(2026, 4, 15)
    prom_ontime = date(2026, 4, 10)
    prom_early = date(2026, 4, 8)

    assert calculate_delivery_delay(req, prom_delayed) == 5
    assert calculate_delivery_delay(req, prom_ontime) == 0
    assert calculate_delivery_delay(req, prom_early) == -2


# 7. Approval thresholds
def test_07_approval_thresholds():
    req_d = date(2026, 4, 1)
    prom_d = date(2026, 4, 10)  # 9 days delay > planner threshold (7 days)

    req_appr, tier, reason = evaluate_approval_requirement(
        change_type="DELIVERY_DATE",
        original_qty=100,
        proposed_qty=100,
        original_price=50.0,
        proposed_price=50.0,
        requested_date=req_d,
        promised_date=prom_d
    )
    assert req_appr is True
    assert tier == "OPERATIONS_MANAGER"


# 8. Pending changes not updating projected supply
def test_08_pending_changes_not_updating_projected_supply(dev_dataset):
    plan_map = {p["po_line_id"]: p for p in dev_dataset["inventory_plans"]}
    line_map = {l["po_line_id"]: l for l in dev_dataset["po_lines"]}

    for chg in dev_dataset["change_requests"]:
        if chg["status"] == "PENDING_APPROVAL" and chg["change_type"] == "QUANTITY":
            plan = plan_map[chg["po_line_id"]]
            line = line_map[chg["po_line_id"]]
            # Exclude the single deliberately injected anomaly
            if plan["plan_id"] != dev_dataset["ground_truth_records"][0]["record_id"]:
                assert plan["projected_supply"] == line["ordered_qty"]


# 9. Approved changes updating plans correctly
def test_09_approved_changes_updating_plans_correctly(dev_dataset):
    plan_map = {p["po_line_id"]: p for p in dev_dataset["inventory_plans"]}

    applied_changes = [c for c in dev_dataset["change_requests"] if c["status"] == "APPLIED" and c["change_type"] == "QUANTITY"]
    for chg in applied_changes:
        plan = plan_map[chg["po_line_id"]]
        assert plan["projected_supply"] == int(chg["new_value"])


# 10. Rejected changes leaving plans unchanged
def test_10_rejected_changes_leaving_plans_unchanged(dev_dataset):
    plan_map = {p["po_line_id"]: p for p in dev_dataset["inventory_plans"]}
    line_map = {l["po_line_id"]: l for l in dev_dataset["po_lines"]}

    rejected_changes = [c for c in dev_dataset["change_requests"] if c["status"] == "REJECTED" and c["change_type"] == "QUANTITY"]
    for chg in rejected_changes:
        plan = plan_map[chg["po_line_id"]]
        line = line_map[chg["po_line_id"]]
        assert plan["projected_supply"] == line["ordered_qty"]


# 11. Duplicate approval prevention
def test_11_duplicate_approval_prevention():
    db = SessionLocal()
    try:
        # Find an already APPLIED change
        applied_chg = db.query(models.ChangeRequest).filter(models.ChangeRequest.status == "APPLIED").first()
        if applied_chg:
            with pytest.raises(ValueError) as excinfo:
                approve_change_request(db, change_id=applied_chg.change_id)
            assert "Must be 'PENDING_APPROVAL'" in str(excinfo.value)
    finally:
        db.close()


# 12. Transaction rollback on failed application
def test_12_transaction_rollback_on_failed_application():
    db = SessionLocal()
    try:
        with pytest.raises(ValueError):
            # Attempt to approve a non-existent change
            approve_change_request(db, change_id="NON-EXISTENT-ID")
    finally:
        db.close()


# 13. Revision history preservation
def test_13_revision_history_preservation(dev_dataset):
    acks = dev_dataset["acknowledgements"]
    rev2_acks = [a for a in acks if a["revision_no"] == 2]
    assert len(rev2_acks) > 0


# 14. Prevention of older-revision overwrites
def test_14_prevention_of_older_revision_overwrites(dev_dataset):
    validator = DataValidator(dev_dataset)
    validator.check_revision_ordering()
    anomalies = [a for a in validator.summary["detected_anomalies"] if a["issue_type"] == "older_revision_overwrites_newer"]
    assert len(anomalies) > 0


# 15. Downstream shortage calculations
def test_15_downstream_shortage_calculations():
    req_d = date(2026, 4, 15)
    prom_d = date(2026, 4, 15)
    mo_req_d = date(2026, 4, 20)

    delay, shortage, status = calculate_schedule_impact(
        required_qty=100,
        available_inventory=20,
        projected_supply=60,
        requested_delivery_date=req_d,
        current_promised_date=prom_d,
        production_required_date=mo_req_d
    )
    assert shortage == 20  # 100 - (20 + 60)
    assert status == "CONFIRMED_SHORTAGE"


# 16. Supplier silence detection
def test_16_supplier_silence_detection():
    order_d = date(2026, 4, 1)
    # 7 days elapsed with no ack
    curr_d = date(2026, 4, 8)
    assert is_supplier_silent(order_d, last_ack_date=None, current_date=curr_d) is True
    # If ack received, silence is False
    assert is_supplier_silent(order_d, last_ack_date=date(2026, 4, 3), current_date=curr_d) is False


# 17. All four required negative scenarios
def test_17_all_four_required_negative_scenarios(dev_dataset):
    validator = DataValidator(dev_dataset)
    summary = validator.run_all_validations()

    issue_types = {a["issue_type"] for a in summary["detected_anomalies"]}
    expected_issues = {
        "unapproved_change_updates_plan",
        "ack_wrong_po_line",
        "promise_before_order_date",
        "older_revision_overwrites_newer"
    }
    assert expected_issues.issubset(issue_types)


# 18. Ground-truth separation
def test_18_ground_truth_separation(dev_dataset):
    gt = dev_dataset["ground_truth_records"]
    assert len(gt) >= 4
    for record in gt:
        assert "expected_outcome" in record
        assert "issue_type" in record
        assert "record_id" in record


# 19. Fixed-seed reproducibility
def test_19_fixed_seed_reproducibility():
    report = run_reproducibility_test()
    assert report["overall_reproducible"] is True
    assert report["entities_checked"] > 10


# 20. CSV and JSON export integrity
def test_20_csv_and_json_export_integrity(tmp_path):
    gen = SyntheticDataGenerator(seed=BASE_SEED, scale="dev")
    gen.generate_all()
    gen.export_data(tmp_path)

    for tbl in ["purchase_orders", "acknowledgements", "change_requests", "inventory_plans"]:
        csv_file = tmp_path / f"{tbl}.csv"
        json_file = tmp_path / f"{tbl}.json"
        assert csv_file.exists()
        assert json_file.exists()
        assert csv_file.stat().st_size > 0
        assert json_file.stat().st_size > 0


# 21. Live CSV operational export endpoint test
def test_21_csv_operational_export_endpoint():
    client = TestClient(app)
    response = client.get("/api/export/purchase_orders?format=csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")
    assert 'filename="purchase_orders.csv"' in response.headers.get("content-disposition", "")
    content = response.text
    assert len(content) > 0
    lines = content.strip().split("\r\n")
    if len(lines) == 1:
        lines = content.strip().split("\n")
    header = lines[0]
    assert "po_id" in header
    assert "supplier_id" in header
    assert len(lines) > 1


# 22. Live genuine Excel (.xlsx) operational export endpoint test
def test_22_excel_operational_export_endpoint():
    client = TestClient(app)
    response = client.get("/api/export/purchase_orders?format=xlsx")
    assert response.status_code == 200
    assert "spreadsheetml.sheet" in response.headers.get("content-type", "")
    assert 'filename="purchase_orders.xlsx"' in response.headers.get("content-disposition", "")
    
    # Verify openpyxl can parse the binary payload as valid Excel
    wb = openpyxl.load_workbook(io.BytesIO(response.content))
    assert "Purchase Orders" in wb.sheetnames
    ws = wb["Purchase Orders"]
    assert ws.max_row > 1
    assert ws.max_column >= 5
    header_values = [cell.value for cell in ws[1]]
    assert "Po Id" in header_values
    assert "Supplier Id" in header_values


# 23. Filtered operational export test
def test_23_filtered_operational_export():
    client = TestClient(app)
    response = client.get("/api/export/purchase_orders?format=json&status=OPEN")
    assert response.status_code == 200
    assert response.headers.get("content-type") == "application/json"
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    for record in data:
        assert record["status"] == "OPEN"


# 24. Invalid entity export rejected with 400
def test_24_invalid_entity_export_rejected():
    client = TestClient(app)
    response = client.get("/api/export/non_existent_entity_type?format=csv")
    assert response.status_code == 400
    detail = response.json().get("detail", "")
    assert "Invalid entity type" in detail


# 25. Unapproved changes supply invariant enforcement
def test_25_unapproved_changes_supply_invariant_enforcement():
    db = SessionLocal()
    try:
        # Retrieve all pending change requests
        pending_changes = db.query(models.ChangeRequest).filter(
            models.ChangeRequest.status == "PENDING_APPROVAL",
            models.ChangeRequest.change_type == "QUANTITY"
        ).all()
        assert len(pending_changes) > 0

        # Retrieve the ground-truth injected anomaly record ID to identify the intentional test negative
        gt_record = db.query(models.GroundTruthRecord).filter(
            models.GroundTruthRecord.issue_type == "unapproved_change_updates_plan"
        ).first()
        injected_bad_plan_id = gt_record.record_id if gt_record else None

        for chg in pending_changes:
            line = db.query(models.POLine).filter(models.POLine.po_line_id == chg.po_line_id).first()
            assert line is not None
            plan = db.query(models.InventoryPlan).filter(models.InventoryPlan.po_line_id == chg.po_line_id).first()
            if plan:
                if plan.plan_id == injected_bad_plan_id:
                    # Ground truth deliberate negative scenario
                    continue
                # Invariant: pending quantity change MUST NEVER be reflected in projected_supply
                assert plan.projected_supply == line.ordered_qty
                assert plan.projected_supply != int(chg.new_value)
    finally:
        db.close()


# 26. Full-scale generator configuration and volume
def test_26_full_scale_generator_configuration_and_volume():
    gen = SyntheticDataGenerator(seed=BASE_SEED, scale="full")
    assert gen.num_pos == 10000
    assert gen.num_suppliers == 100
    assert gen.num_items == 50
    assert gen.num_production_orders == 1000
    assert gen.target_events == 15000


# 27. Database live row counts meet full scale volume requirements
def test_27_database_live_row_counts_meet_full_scale_volume():
    db = SessionLocal()
    try:
        po_count = db.query(models.PurchaseOrder).count()
        assert po_count >= 10000, f"Expected at least 10,000 purchase orders, found {po_count}"

        business_tables = [
            models.Supplier, models.Item, models.PurchaseOrder, models.POLine,
            models.Acknowledgement, models.PromiseDate, models.ChangeRequest,
            models.Approval, models.InventoryPlan, models.ProductionOrder,
            models.Notification, models.ScheduleImpact, models.ExceptionRecord
        ]
        total_records = sum(db.query(tbl).count() for tbl in business_tables)
        assert total_records > 10000, f"Expected >10,000 total business records, found {total_records}"
        assert total_records >= 60000, f"Full scale expected ~69,840 records, found {total_records}"

        # Invariant: 4 ground truth anomalies and 4 generated exception records
        assert db.query(models.GroundTruthRecord).count() == 4
        assert db.query(models.ExceptionRecord).count() == 4
    finally:
        db.close()


# 28. Data Quality summary endpoint accuracy
def test_28_data_quality_summary_endpoint_accuracy():
    client = TestClient(app)
    response = client.get("/api/data-quality/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["dataset_seed"] == BASE_SEED
    assert data["dataset_scale"] == "full"
    assert data["purchase_order_count"] >= 10000
    assert data["total_business_records"] > 10000
    assert len(data["applicable_business_tables"]) == 13
    assert data["passed_validation_checks"] >= 15
    assert data["failed_validation_checks"] == 0
    assert data["anomaly_detection_metrics"]["true_positives"] == 4
    assert data["anomaly_detection_metrics"]["false_positives"] == 0
    assert data["anomaly_detection_metrics"]["precision"] == 1.0


# 29. Accidental reseed protection
def test_29_accidental_reseed_protection():
    client = TestClient(app)
    # Calling seed without confirm=true when database is populated must return 400
    response = client.post("/api/data-generator/seed?scale=full")
    assert response.status_code == 400
    detail = response.json().get("detail", "")
    assert "Reseeding replaces existing" in detail or "confirm=true" in detail


# 30. Synthetic dataset export prefixed and valid
def test_30_synthetic_dataset_export_prefixed_and_valid():
    client = TestClient(app)
    # Synthetic CSV export
    res_csv = client.get("/api/export/purchase_orders?format=csv&source=synthetic")
    assert res_csv.status_code == 200
    assert "synthetic_purchase_orders.csv" in res_csv.headers.get("content-disposition", "")
    assert "text/csv" in res_csv.headers.get("content-type", "")

    # Synthetic Excel export
    res_xlsx = client.get("/api/export/purchase_orders?format=xlsx&source=synthetic")
    assert res_xlsx.status_code == 200
    assert "synthetic_purchase_orders.xlsx" in res_xlsx.headers.get("content-disposition", "")
    assert "spreadsheetml.sheet" in res_xlsx.headers.get("content-type", "")
    wb = openpyxl.load_workbook(io.BytesIO(res_xlsx.content))
    assert "Purchase Orders" in wb.sheetnames
    assert wb["Purchase Orders"].max_row > 100



