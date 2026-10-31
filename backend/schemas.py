"""
Pydantic validation schemas for API requests, responses, and metrics.
"""

from datetime import date, datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict


# --- Generic Pagination ---
class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


# --- Supplier Schemas ---
class SupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    supplier_id: str
    supplier_name: str
    lead_time_days: int
    status: str
    created_at: datetime
    updated_at: datetime


# --- Purchase Order Schemas ---
class POLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    po_line_id: str
    po_id: str
    item_id: str
    ordered_qty: int
    unit_price: float
    requested_delivery_date: date
    status: str


class PurchaseOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    po_id: str
    supplier_id: str
    order_date: date
    status: str
    total_amount: float
    created_at: datetime
    updated_at: datetime
    lines: Optional[List[POLineResponse]] = None


# --- Acknowledgement Schemas ---
class PromiseDateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    promise_id: str
    ack_id: str
    promised_date: date
    revision_no: int
    effective_at: datetime


class AcknowledgementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ack_id: str
    po_line_id: str
    revision_no: int
    accepted_qty: int
    rejected_qty: int
    acknowledgement_date: date
    status: str
    promise_dates: Optional[List[PromiseDateResponse]] = None


# --- Change Request & Approval Schemas ---
class ApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    approval_id: str
    change_id: str
    decision: str
    reviewer_id: Optional[str] = None
    decision_date: Optional[datetime] = None
    comments: Optional[str] = None


class ChangeRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    change_id: str
    po_line_id: str
    change_type: str
    old_value: str
    new_value: str
    revision_no: int
    status: str
    requested_at: datetime
    approvals: Optional[List[ApprovalResponse]] = None


class ApprovalActionRequest(BaseModel):
    reviewer_id: str = "PLN-001"
    comments: Optional[str] = "Reviewed and decided by planner."


# --- Inventory & Production Schemas ---
class InventoryPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plan_id: str
    po_line_id: str
    projected_supply: int
    required_qty: int
    status: str
    effective_at: datetime


class ProductionOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    production_order_id: str
    item_id: str
    required_qty: int
    required_date: date
    status: str


class ScheduleImpactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    impact_id: str
    production_order_id: str
    po_line_id: str
    po_id: str
    required_qty: int
    available_inventory: int
    projected_supply: int
    shortage_qty: int
    original_delivery_date: date
    current_promised_date: date
    delay_days: int
    impact_status: str
    updated_at: datetime


# --- Exception & Notification Schemas ---
class ExceptionRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    exception_id: str
    record_id: str
    entity_type: str
    issue_type: str
    severity: str
    description: str
    is_resolved: bool
    detected_at: datetime


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    notification_id: str
    recipient_id: str
    change_id: Optional[str] = None
    message: str
    status: str
    created_at: datetime


# --- Dashboard Metrics Schema ---
class DashboardMetricsResponse(BaseModel):
    total_purchase_orders: int
    total_suppliers: int
    acknowledgement_coverage_pct: float
    pending_approvals: int
    approved_changes: int
    rejected_changes: int
    delayed_purchase_orders: int
    open_exceptions: int
    projected_supply_shortages: int
    affected_production_orders: int
    metrics_documentation: Dict[str, str]


# --- Data Quality & Validation Summary ---
class DataQualitySummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dataset_seed: int
    dataset_scale: str
    purchase_order_count: int
    total_business_records: int
    total_database_records: int
    applicable_business_tables: List[str]
    entity_counts: Dict[str, int]
    passed_validation_checks: int
    failed_validation_checks: int
    anomaly_detection_metrics: Dict[str, Any]
    detected_anomalies: List[Dict[str, Any]]
    reproducibility_status: Dict[str, Any]

