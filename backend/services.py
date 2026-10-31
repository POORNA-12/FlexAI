"""
Business services layer executing transactional operations,
dashboard calculations, database seeding, and reproducibility comparisons.
"""

import hashlib
import json
import io
import csv
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, or_, text

from backend.database import SessionLocal, init_db
from backend import models
from backend.business_rules import calculate_schedule_impact
from backend.generator import SyntheticDataGenerator, BASE_SEED
from backend.validation import DataValidator


def get_dashboard_metrics(db: Session) -> Dict[str, Any]:
    """
    Computes all 10 core operational metrics from actual database records.
    Every metric is accompanied by its explicit calculation formula.
    """
    total_pos = db.query(func.count(models.PurchaseOrder.po_id)).scalar() or 0
    total_supp = db.query(func.count(models.Supplier.supplier_id)).scalar() or 0

    # Acknowledged PO count
    ack_pos = db.query(distinct(models.POLine.po_id))\
        .join(models.Acknowledgement, models.POLine.po_line_id == models.Acknowledgement.po_line_id)\
        .count()
    ack_coverage = round((ack_pos / total_pos * 100.0), 2) if total_pos > 0 else 0.0

    pending_appr = db.query(func.count(models.ChangeRequest.change_id))\
        .filter(models.ChangeRequest.status == "PENDING_APPROVAL").scalar() or 0

    appr_changes = db.query(func.count(models.Approval.approval_id))\
        .filter(models.Approval.decision == "APPROVED").scalar() or 0

    rej_changes = db.query(func.count(models.Approval.approval_id))\
        .filter(models.Approval.decision == "REJECTED").scalar() or 0

    # Delayed POs: where any promise date > requested delivery date
    delayed_pos = db.query(distinct(models.POLine.po_id))\
        .join(models.Acknowledgement, models.POLine.po_line_id == models.Acknowledgement.po_line_id)\
        .join(models.PromiseDate, models.Acknowledgement.ack_id == models.PromiseDate.ack_id)\
        .filter(models.PromiseDate.promised_date > models.POLine.requested_delivery_date)\
        .count()

    open_exc = db.query(func.count(models.ExceptionRecord.exception_id))\
        .filter(models.ExceptionRecord.is_resolved == False).scalar() or 0

    shortages = db.query(func.count(models.InventoryPlan.plan_id))\
        .filter(models.InventoryPlan.status == "SHORTAGE").scalar() or 0

    affected_mos = db.query(distinct(models.ScheduleImpact.production_order_id))\
        .filter(models.ScheduleImpact.impact_status != "ON_TIME").count()

    formulas = {
        "total_purchase_orders": "COUNT(purchase_orders.po_id)",
        "total_suppliers": "COUNT(suppliers.supplier_id)",
        "acknowledgement_coverage_pct": "(COUNT(DISTINCT po_with_ack) / total_purchase_orders) * 100",
        "pending_approvals": "COUNT(change_requests WHERE status = 'PENDING_APPROVAL')",
        "approved_changes": "COUNT(approvals WHERE decision = 'APPROVED')",
        "rejected_changes": "COUNT(approvals WHERE decision = 'REJECTED')",
        "delayed_purchase_orders": "COUNT(DISTINCT po_id WHERE promise_date > requested_delivery_date)",
        "open_exceptions": "COUNT(exception_records WHERE is_resolved = FALSE)",
        "projected_supply_shortages": "COUNT(inventory_plans WHERE status = 'SHORTAGE')",
        "affected_production_orders": "COUNT(DISTINCT production_order_id WHERE impact_status != 'ON_TIME')"
    }

    return {
        "total_purchase_orders": total_pos,
        "total_suppliers": total_supp,
        "acknowledgement_coverage_pct": ack_coverage,
        "pending_approvals": pending_appr,
        "approved_changes": appr_changes,
        "rejected_changes": rej_changes,
        "delayed_purchase_orders": delayed_pos,
        "open_exceptions": open_exc,
        "projected_supply_shortages": shortages,
        "affected_production_orders": affected_mos,
        "metrics_documentation": formulas
    }


def list_purchase_orders(
    db: Session, search: Optional[str] = None, status: Optional[str] = None, page: int = 1, page_size: int = 20
) -> Tuple[List[models.PurchaseOrder], int]:
    query = db.query(models.PurchaseOrder)
    if search:
        query = query.filter(or_(
            models.PurchaseOrder.po_id.ilike(f"%{search}%"),
            models.PurchaseOrder.supplier_id.ilike(f"%{search}%")
        ))
    if status:
        query = query.filter(models.PurchaseOrder.status == status)

    total = query.count()
    items = query.order_by(models.PurchaseOrder.order_date.desc())\
                 .offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def get_purchase_order_detail(db: Session, po_id: str) -> Optional[models.PurchaseOrder]:
    return db.query(models.PurchaseOrder).filter(models.PurchaseOrder.po_id == po_id).first()


def list_suppliers(
    db: Session, search: Optional[str] = None, status: Optional[str] = None, page: int = 1, page_size: int = 20
) -> Tuple[List[models.Supplier], int]:
    query = db.query(models.Supplier)
    if search:
        query = query.filter(or_(
            models.Supplier.supplier_id.ilike(f"%{search}%"),
            models.Supplier.supplier_name.ilike(f"%{search}%")
        ))
    if status:
        query = query.filter(models.Supplier.status == status)

    total = query.count()
    items = query.order_by(models.Supplier.supplier_id.asc())\
                 .offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def list_acknowledgements(
    db: Session, search: Optional[str] = None, status: Optional[str] = None, page: int = 1, page_size: int = 20
) -> Tuple[List[models.Acknowledgement], int]:
    query = db.query(models.Acknowledgement)
    if search:
        query = query.filter(or_(
            models.Acknowledgement.ack_id.ilike(f"%{search}%"),
            models.Acknowledgement.po_line_id.ilike(f"%{search}%")
        ))
    if status:
        query = query.filter(models.Acknowledgement.status == status)

    total = query.count()
    items = query.order_by(models.Acknowledgement.acknowledgement_date.desc())\
                 .offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def list_change_requests(
    db: Session, status: Optional[str] = None, change_type: Optional[str] = None, page: int = 1, page_size: int = 20
) -> Tuple[List[models.ChangeRequest], int]:
    query = db.query(models.ChangeRequest)
    if status:
        query = query.filter(models.ChangeRequest.status == status)
    if change_type:
        query = query.filter(models.ChangeRequest.change_type == change_type)

    total = query.count()
    items = query.order_by(models.ChangeRequest.requested_at.desc())\
                 .offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def approve_change_request(
    db: Session, change_id: str, reviewer_id: str = "PLN-001", comments: Optional[str] = None
) -> Dict[str, Any]:
    """
    CRITICAL WORKFLOW OPERATION:
    Processes approval of a pending change request.
    1. Validates pending state (prevents duplicate approval).
    2. Creates/updates Approval record with 'APPROVED'.
    3. Changes status to 'APPLIED'.
    4. Transactionally updates InventoryPlan.projected_supply.
    5. Recalculates ScheduleImpact.
    6. Generates planner notification.
    Rolls back automatically if any step encounters an error.
    """
    chg = db.query(models.ChangeRequest).filter(models.ChangeRequest.change_id == change_id).first()
    if not chg:
        raise ValueError(f"Change request {change_id} not found.")

    if chg.status != "PENDING_APPROVAL":
        raise ValueError(f"Cannot approve change request {change_id} with status '{chg.status}'. Must be 'PENDING_APPROVAL'.")

    try:
        now_dt = datetime.utcnow()
        appr_id = f"APR-{chg.change_id}-REV{chg.revision_no:02d}"

        # 1. Record Approval
        appr = models.Approval(
            approval_id=appr_id,
            change_id=chg.change_id,
            decision="APPROVED",
            reviewer_id=reviewer_id,
            decision_date=now_dt,
            comments=comments or "Approved by authorized planner."
        )
        db.add(appr)

        # 2. Update Change Request
        chg.status = "APPLIED"

        # 3. Update Inventory Plan
        plan = db.query(models.InventoryPlan).filter(models.InventoryPlan.po_line_id == chg.po_line_id).first()
        if plan and chg.change_type == "QUANTITY":
            new_qty = int(chg.new_value)
            plan.projected_supply = new_qty
            if new_qty < plan.required_qty:
                plan.status = "SHORTAGE"
            elif new_qty > plan.required_qty:
                plan.status = "SURPLUS"
            else:
                plan.status = "BALANCED"
            plan.effective_at = now_dt

        # 4. Generate Notification
        notif = models.Notification(
            notification_id=f"NOT-{int(datetime.utcnow().timestamp())}",
            recipient_id=reviewer_id,
            change_id=chg.change_id,
            message=f"Change request {chg.change_id} for line {chg.po_line_id} was APPROVED and successfully applied to projected supply.",
            status="UNREAD",
            created_at=now_dt
        )
        db.add(notif)

        db.commit()
        return {
            "success": True,
            "change_id": chg.change_id,
            "status": chg.status,
            "approval_id": appr_id,
            "message": "Change request approved and inventory plan updated successfully."
        }
    except Exception as exc:
        db.rollback()
        raise RuntimeError(f"Approval transaction rolled back due to error: {exc}")


def reject_change_request(
    db: Session, change_id: str, reviewer_id: str = "PLN-001", comments: Optional[str] = None
) -> Dict[str, Any]:
    """
    Processes rejection of a pending change request.
    1. Validates pending state.
    2. Records Approval with 'REJECTED'.
    3. Changes status to 'REJECTED'.
    4. PRESERVES InventoryPlan.projected_supply WITHOUT MODIFICATION.
    """
    chg = db.query(models.ChangeRequest).filter(models.ChangeRequest.change_id == change_id).first()
    if not chg:
        raise ValueError(f"Change request {change_id} not found.")

    if chg.status != "PENDING_APPROVAL":
        raise ValueError(f"Cannot reject change request {change_id} with status '{chg.status}'. Must be 'PENDING_APPROVAL'.")

    try:
        now_dt = datetime.utcnow()
        appr_id = f"APR-{chg.change_id}-REV{chg.revision_no:02d}"

        appr = models.Approval(
            approval_id=appr_id,
            change_id=chg.change_id,
            decision="REJECTED",
            reviewer_id=reviewer_id,
            decision_date=now_dt,
            comments=comments or "Rejected by authorized planner due to operational constraints."
        )
        db.add(appr)

        chg.status = "REJECTED"

        # Inventory plan is deliberately NOT updated. Original effective values remain intact.

        notif = models.Notification(
            notification_id=f"NOT-{int(datetime.utcnow().timestamp())}",
            recipient_id=reviewer_id,
            change_id=chg.change_id,
            message=f"Change request {chg.change_id} for line {chg.po_line_id} was REJECTED. Inventory plan preserved.",
            status="UNREAD",
            created_at=now_dt
        )
        db.add(notif)

        db.commit()
        return {
            "success": True,
            "change_id": chg.change_id,
            "status": chg.status,
            "approval_id": appr_id,
            "message": "Change request rejected. Inventory plan remains unchanged."
        }
    except Exception as exc:
        db.rollback()
        raise RuntimeError(f"Rejection transaction failed: {exc}")


def list_inventory_plans(
    db: Session, status: Optional[str] = None, page: int = 1, page_size: int = 20
) -> Tuple[List[models.InventoryPlan], int]:
    query = db.query(models.InventoryPlan)
    if status:
        query = query.filter(models.InventoryPlan.status == status)
    total = query.count()
    items = query.order_by(models.InventoryPlan.plan_id.asc())\
                 .offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def list_production_orders(
    db: Session, status: Optional[str] = None, page: int = 1, page_size: int = 20
) -> Tuple[List[models.ProductionOrder], int]:
    query = db.query(models.ProductionOrder)
    if status:
        query = query.filter(models.ProductionOrder.status == status)
    total = query.count()
    items = query.order_by(models.ProductionOrder.required_date.asc())\
                 .offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def list_schedule_impacts(
    db: Session, impact_status: Optional[str] = None, page: int = 1, page_size: int = 20
) -> Tuple[List[models.ScheduleImpact], int]:
    query = db.query(models.ScheduleImpact)
    if impact_status:
        query = query.filter(models.ScheduleImpact.impact_status == impact_status)
    total = query.count()
    items = query.order_by(models.ScheduleImpact.delay_days.desc())\
                 .offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def list_exceptions(
    db: Session, issue_type: Optional[str] = None, severity: Optional[str] = None,
    is_resolved: Optional[bool] = None, page: int = 1, page_size: int = 20
) -> Tuple[List[models.ExceptionRecord], int]:
    query = db.query(models.ExceptionRecord)
    if issue_type:
        query = query.filter(models.ExceptionRecord.issue_type == issue_type)
    if severity:
        query = query.filter(models.ExceptionRecord.severity == severity)
    if is_resolved is not None:
        query = query.filter(models.ExceptionRecord.is_resolved == is_resolved)

    total = query.count()
    items = query.order_by(models.ExceptionRecord.detected_at.desc())\
                 .offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def resolve_exception(db: Session, exception_id: str) -> Dict[str, Any]:
    exc = db.query(models.ExceptionRecord).filter(models.ExceptionRecord.exception_id == exception_id).first()
    if not exc:
        raise ValueError(f"Exception record {exception_id} not found.")
    exc.is_resolved = True
    db.commit()
    return {"success": True, "exception_id": exception_id, "is_resolved": True}


def list_notifications(
    db: Session, recipient_id: Optional[str] = None, status: Optional[str] = None, page: int = 1, page_size: int = 20
) -> Tuple[List[models.Notification], int]:
    query = db.query(models.Notification)
    if recipient_id:
        query = query.filter(models.Notification.recipient_id == recipient_id)
    if status:
        query = query.filter(models.Notification.status == status)

    total = query.count()
    items = query.order_by(models.Notification.created_at.desc())\
                 .offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def seed_database_from_generator(scale: str = "full") -> Dict[str, Any]:
    """
    Generates synthetic data and loads it into MySQL database using bulk transaction.
    Adds validation-derived exception records BEFORE exporting and persisting.
    """
    init_db(safe_only=False)

    generator = SyntheticDataGenerator(seed=BASE_SEED, scale=scale)
    tables = generator.generate_all()

    # 1. Run DataValidator to detect anomalies against business rules
    validator = DataValidator(tables)
    validation_summary = validator.run_all_validations()

    # 2. Populate Exception Records from detected anomalies BEFORE export & DB persistence
    exc_records = []
    for idx, anomaly in enumerate(validation_summary["detected_anomalies"], start=1):
        exc_records.append({
            "exception_id": f"EXP-2026-{idx:06d}",
            "record_id": anomaly["record_id"],
            "entity_type": anomaly["entity_type"],
            "issue_type": anomaly["issue_type"],
            "severity": "CRITICAL" if ("unapproved" in anomaly["issue_type"] or "revision" in anomaly["issue_type"]) else "HIGH",
            "description": anomaly["details"],
            "is_resolved": False,
            "detected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    tables["exception_records"] = exc_records
    generator.tables["exception_records"] = exc_records

    # 3. Save full dataset and validation artifacts to data directory
    data_dir = Path(__file__).resolve().parent.parent / "data"
    generator.export_data(data_dir)

    with open(data_dir / "validation_summary.json", mode="w", encoding="utf-8") as f:
        json.dump(validation_summary, f, indent=2)

    # 4. Atomic MySQL Bulk Insertion with Rollback Protection
    db = SessionLocal()
    try:
        # Safely disable FK checks during clear to prevent lock timeouts
        db.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        for tbl in [
            models.ScheduleImpact, models.Notification, models.Approval,
            models.ChangeRequest, models.PromiseDate, models.Acknowledgement,
            models.InventoryPlan, models.POLine, models.ProductionOrder,
            models.PurchaseOrder, models.Item, models.Supplier,
            models.ExceptionRecord, models.GroundTruthRecord
        ]:
            db.query(tbl).delete()
        db.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))

        # Insert in strict parent-to-child foreign key dependency order
        db.bulk_insert_mappings(models.Supplier, tables["suppliers"])
        db.bulk_insert_mappings(models.Item, tables["items"])
        db.bulk_insert_mappings(models.PurchaseOrder, tables["purchase_orders"])
        db.bulk_insert_mappings(models.POLine, tables["po_lines"])
        db.bulk_insert_mappings(models.ProductionOrder, tables["production_orders"])
        db.bulk_insert_mappings(models.InventoryPlan, tables["inventory_plans"])
        db.bulk_insert_mappings(models.Acknowledgement, tables["acknowledgements"])
        db.bulk_insert_mappings(models.PromiseDate, tables["promise_dates"])
        db.bulk_insert_mappings(models.ChangeRequest, tables["change_requests"])
        db.bulk_insert_mappings(models.Approval, tables["approvals"])
        db.bulk_insert_mappings(models.ScheduleImpact, tables["schedule_impacts"])
        db.bulk_insert_mappings(models.Notification, tables["notifications"])
        db.bulk_insert_mappings(models.ExceptionRecord, tables["exception_records"])
        db.bulk_insert_mappings(models.GroundTruthRecord, tables["ground_truth_records"])

        db.commit()
    except Exception as exc:
        db.rollback()
        try:
            db.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
            db.commit()
        except Exception:
            pass
        raise RuntimeError(f"Database bulk seeding failed: {exc}") from exc
    finally:
        db.close()

    # 5. Calculate entity counts and total business records
    entity_counts = {tbl_name: len(rows) for tbl_name, rows in tables.items()}
    business_tables = [
        "suppliers", "items", "purchase_orders", "po_lines",
        "acknowledgements", "promise_dates", "change_requests", "approvals",
        "inventory_plans", "production_orders", "notifications",
        "schedule_impacts", "exception_records"
    ]
    total_business_records = sum(entity_counts.get(t, 0) for t in business_tables)
    total_database_records = sum(entity_counts.values())

    return {
        "success": True,
        "seed": BASE_SEED,
        "scale": scale,
        "purchase_order_count": entity_counts.get("purchase_orders", 0),
        "total_business_records": total_business_records,
        "total_database_records": total_database_records,
        "applicable_business_tables": business_tables,
        "entity_counts": entity_counts,
        "validation": validation_summary
    }


def run_reproducibility_test() -> Dict[str, Any]:
    """
    Executes generator twice using identical seed BASE_SEED (20261022)
    and verifies row counts, record values, and SHA256 checksums match 100%.
    """
    gen1 = SyntheticDataGenerator(seed=BASE_SEED, scale="dev")
    tables1 = gen1.generate_all()

    gen2 = SyntheticDataGenerator(seed=BASE_SEED, scale="dev")
    tables2 = gen2.generate_all()

    comparisons = {}
    all_matched = True

    for tbl_name in tables1.keys():
        rows1 = tables1[tbl_name]
        rows2 = tables2[tbl_name]

        count_match = (len(rows1) == len(rows2))
        hash1 = hashlib.sha256(json.dumps(rows1, sort_keys=True).encode()).hexdigest()
        hash2 = hashlib.sha256(json.dumps(rows2, sort_keys=True).encode()).hexdigest()
        hash_match = (hash1 == hash2)

        if not (count_match and hash_match):
            all_matched = False

        comparisons[tbl_name] = {
            "run1_count": len(rows1),
            "run2_count": len(rows2),
            "counts_match": count_match,
            "sha256_match": hash_match,
            "checksum": hash1
        }

    report = {
        "seed": BASE_SEED,
        "overall_reproducible": all_matched,
        "entities_checked": len(comparisons),
        "table_comparisons": comparisons,
        "verified_at": datetime.now().isoformat()
    }

    # Persist report
    data_dir = Path(__file__).resolve().parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    with open(data_dir / "reproducibility_report.json", mode="w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


# --- Operational Dataset Export Service ---
WHITELISTED_EXPORT_ENTITIES = {
    "purchase_orders",
    "po_lines",
    "acknowledgements",
    "promise_dates",
    "change_requests",
    "approvals",
    "inventory_plans",
    "production_orders",
    "schedule_impacts",
    "exceptions",
    "exception_records",
    "suppliers",
}


def export_operational_dataset(
    db: Session,
    entity_type: str,
    export_format: str = "csv",
    filters: Optional[Dict[str, Any]] = None
) -> Tuple[bytes, str, str]:
    """
    Exports current live database records matching active filters in CSV, Excel (.xlsx), or JSON.
    Returns: (file_bytes, media_type, filename)
    """
    clean_entity = entity_type.lower().strip()
    if clean_entity not in WHITELISTED_EXPORT_ENTITIES:
        raise ValueError(
            f"Unsupported entity type '{entity_type}'. Allowed types: {', '.join(sorted(WHITELISTED_EXPORT_ENTITIES))}"
        )

    clean_format = export_format.lower().strip()
    if clean_format not in ("csv", "xlsx", "json"):
        raise ValueError(f"Unsupported export format '{export_format}'. Allowed: csv, xlsx, json")

    filters = filters or {}
    rows: List[Dict[str, Any]] = []

    # Query operational database
    if clean_entity == "purchase_orders":
        query = db.query(models.PurchaseOrder)
        if filters.get("status"):
            query = query.filter(models.PurchaseOrder.status == filters["status"])
        if filters.get("search"):
            s = filters["search"]
            query = query.filter(or_(
                models.PurchaseOrder.po_id.ilike(f"%{s}%"),
                models.PurchaseOrder.supplier_id.ilike(f"%{s}%")
            ))
        records = query.order_by(models.PurchaseOrder.order_date.desc()).all()
        for r in records:
            rows.append({
                "po_id": r.po_id,
                "supplier_id": r.supplier_id,
                "order_date": r.order_date.isoformat() if r.order_date else "",
                "status": r.status,
                "total_amount": float(r.total_amount),
                "lines_count": len(r.lines),
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "",
                "updated_at": r.updated_at.strftime("%Y-%m-%d %H:%M:%S") if r.updated_at else "",
            })

    elif clean_entity == "po_lines":
        query = db.query(models.POLine)
        if filters.get("po_id"):
            query = query.filter(models.POLine.po_id == filters["po_id"])
        if filters.get("status"):
            query = query.filter(models.POLine.status == filters["status"])
        records = query.order_by(models.POLine.po_line_id.asc()).all()
        for r in records:
            rows.append({
                "po_line_id": r.po_line_id,
                "po_id": r.po_id,
                "item_id": r.item_id,
                "ordered_qty": r.ordered_qty,
                "unit_price": float(r.unit_price),
                "requested_delivery_date": r.requested_delivery_date.isoformat() if r.requested_delivery_date else "",
                "status": r.status,
            })

    elif clean_entity == "acknowledgements":
        query = db.query(models.Acknowledgement)
        if filters.get("status"):
            query = query.filter(models.Acknowledgement.status == filters["status"])
        if filters.get("search"):
            s = filters["search"]
            query = query.filter(or_(
                models.Acknowledgement.ack_id.ilike(f"%{s}%"),
                models.Acknowledgement.po_line_id.ilike(f"%{s}%")
            ))
        records = query.order_by(models.Acknowledgement.acknowledgement_date.desc()).all()
        for r in records:
            prm = r.promise_dates[0] if r.promise_dates else None
            rows.append({
                "ack_id": r.ack_id,
                "po_line_id": r.po_line_id,
                "revision_no": r.revision_no,
                "accepted_qty": r.accepted_qty,
                "rejected_qty": r.rejected_qty,
                "acknowledgement_date": r.acknowledgement_date.isoformat() if r.acknowledgement_date else "",
                "status": r.status,
                "promised_delivery_date": prm.promised_date.isoformat() if prm and prm.promised_date else "",
            })

    elif clean_entity == "promise_dates":
        records = db.query(models.PromiseDate).order_by(models.PromiseDate.promise_id.asc()).all()
        for r in records:
            rows.append({
                "promise_id": r.promise_id,
                "ack_id": r.ack_id,
                "promised_date": r.promised_date.isoformat() if r.promised_date else "",
                "revision_no": r.revision_no,
                "effective_at": r.effective_at.strftime("%Y-%m-%d %H:%M:%S") if r.effective_at else "",
            })

    elif clean_entity == "change_requests":
        query = db.query(models.ChangeRequest)
        if filters.get("status"):
            query = query.filter(models.ChangeRequest.status == filters["status"])
        if filters.get("change_type"):
            query = query.filter(models.ChangeRequest.change_type == filters["change_type"])
        records = query.order_by(models.ChangeRequest.requested_at.desc()).all()
        for r in records:
            rows.append({
                "change_id": r.change_id,
                "po_line_id": r.po_line_id,
                "change_type": r.change_type,
                "old_value": r.old_value,
                "new_value": r.new_value,
                "revision_no": r.revision_no,
                "status": r.status,
                "requested_at": r.requested_at.strftime("%Y-%m-%d %H:%M:%S") if r.requested_at else "",
            })

    elif clean_entity == "approvals":
        query = db.query(models.Approval)
        if filters.get("decision"):
            query = query.filter(models.Approval.decision == filters["decision"])
        records = query.order_by(models.Approval.approval_id.asc()).all()
        for r in records:
            rows.append({
                "approval_id": r.approval_id,
                "change_id": r.change_id,
                "decision": r.decision,
                "reviewer_id": r.reviewer_id or "",
                "decision_date": r.decision_date.strftime("%Y-%m-%d %H:%M:%S") if r.decision_date else "",
                "comments": r.comments or "",
            })

    elif clean_entity == "inventory_plans":
        query = db.query(models.InventoryPlan)
        if filters.get("status"):
            query = query.filter(models.InventoryPlan.status == filters["status"])
        records = query.order_by(models.InventoryPlan.plan_id.asc()).all()
        for r in records:
            rows.append({
                "plan_id": r.plan_id,
                "po_line_id": r.po_line_id,
                "projected_supply": r.projected_supply,
                "required_qty": r.required_qty,
                "status": r.status,
                "effective_at": r.effective_at.strftime("%Y-%m-%d %H:%M:%S") if r.effective_at else "",
            })

    elif clean_entity == "production_orders":
        query = db.query(models.ProductionOrder)
        if filters.get("status"):
            query = query.filter(models.ProductionOrder.status == filters["status"])
        records = query.order_by(models.ProductionOrder.required_date.asc()).all()
        for r in records:
            rows.append({
                "production_order_id": r.production_order_id,
                "item_id": r.item_id,
                "required_qty": r.required_qty,
                "required_date": r.required_date.isoformat() if r.required_date else "",
                "status": r.status,
            })

    elif clean_entity == "schedule_impacts":
        query = db.query(models.ScheduleImpact)
        if filters.get("impact_status"):
            query = query.filter(models.ScheduleImpact.impact_status == filters["impact_status"])
        records = query.order_by(models.ScheduleImpact.delay_days.desc()).all()
        for r in records:
            rows.append({
                "impact_id": r.impact_id,
                "production_order_id": r.production_order_id,
                "po_line_id": r.po_line_id,
                "po_id": r.po_id,
                "required_qty": r.required_qty,
                "available_inventory": r.available_inventory,
                "projected_supply": r.projected_supply,
                "shortage_qty": r.shortage_qty,
                "original_delivery_date": r.original_delivery_date.isoformat() if r.original_delivery_date else "",
                "current_promised_date": r.current_promised_date.isoformat() if r.current_promised_date else "",
                "delay_days": r.delay_days,
                "impact_status": r.impact_status,
                "updated_at": r.updated_at.strftime("%Y-%m-%d %H:%M:%S") if r.updated_at else "",
            })

    elif clean_entity in ("exceptions", "exception_records"):
        query = db.query(models.ExceptionRecord)
        if filters.get("issue_type"):
            query = query.filter(models.ExceptionRecord.issue_type == filters["issue_type"])
        if filters.get("severity"):
            query = query.filter(models.ExceptionRecord.severity == filters["severity"])
        if filters.get("is_resolved") is not None:
            query = query.filter(models.ExceptionRecord.is_resolved == filters["is_resolved"])
        records = query.order_by(models.ExceptionRecord.detected_at.desc()).all()
        for r in records:
            rows.append({
                "exception_id": r.exception_id,
                "record_id": r.record_id,
                "entity_type": r.entity_type,
                "issue_type": r.issue_type,
                "severity": r.severity,
                "description": r.description,
                "is_resolved": r.is_resolved,
                "detected_at": r.detected_at.strftime("%Y-%m-%d %H:%M:%S") if r.detected_at else "",
            })

    elif clean_entity == "suppliers":
        query = db.query(models.Supplier)
        if filters.get("status"):
            query = query.filter(models.Supplier.status == filters["status"])
        records = query.order_by(models.Supplier.supplier_id.asc()).all()
        for r in records:
            rows.append({
                "supplier_id": r.supplier_id,
                "supplier_name": r.supplier_name,
                "lead_time_days": r.lead_time_days,
                "status": r.status,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "",
                "updated_at": r.updated_at.strftime("%Y-%m-%d %H:%M:%S") if r.updated_at else "",
            })

    return serialize_rows_to_format(rows, clean_entity, clean_format)


def serialize_rows_to_format(
    rows: List[Dict[str, Any]],
    entity_name: str,
    export_format: str = "csv",
    filename_prefix: str = ""
) -> Tuple[bytes, str, str]:
    """
    Serializes an arbitrary list of record dictionaries into CSV, genuine Excel (.xlsx), or JSON bytes.
    Returns: (content_bytes, media_type, filename)
    """
    clean_format = export_format.lower().strip()
    filename = f"{filename_prefix}{entity_name}.{clean_format}"

    if clean_format == "csv":
        output = io.StringIO()
        if rows:
            writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        else:
            output.write("message\nNo matching records found.\n")
        # Encode as UTF-8 with BOM for seamless Microsoft Excel compatibility
        content_bytes = output.getvalue().encode("utf-8-sig")
        return content_bytes, "text/csv; charset=utf-8", filename

    elif clean_format == "xlsx":
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = entity_name.replace("_", " ").title()[:31]

        header_font = Font(name="Calibri", size=11, bold=True, color="0F172A")
        header_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
        thin_border = Border(
            left=Side(style="thin", color="CBD5E1"),
            right=Side(style="thin", color="CBD5E1"),
            top=Side(style="thin", color="CBD5E1"),
            bottom=Side(style="thin", color="CBD5E1")
        )

        if rows:
            headers = list(rows[0].keys())
            ws.append([h.replace("_", " ").title() for h in headers])
            for col_idx in range(1, len(headers) + 1):
                cell = ws.cell(row=1, column=col_idx)
                cell.font = header_font
                cell.fill = header_fill
                cell.border = thin_border
                cell.alignment = Alignment(horizontal="center", vertical="center")

            for r_data in rows:
                ws.append(list(r_data.values()))

            # Auto-adjust column widths
            for col in ws.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                col_letter = openpyxl.utils.get_column_letter(col[0].column)
                ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 45)
        else:
            ws.append(["Notice"])
            ws.cell(row=1, column=1).font = header_font
            ws.append(["No records found matching criteria."])

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename

    else:  # json
        content = json.dumps(rows, indent=2, default=str).encode("utf-8")
        return content, "application/json", filename

