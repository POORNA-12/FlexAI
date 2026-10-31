"""
SQLAlchemy ORM models for all core business entities and evaluation tables.
"""

from datetime import datetime, date
from sqlalchemy import (
    Column,
    String,
    Integer,
    Numeric,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Text,
    Boolean,
    Index
)
from sqlalchemy.orm import relationship
from backend.database import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    supplier_id = Column(String(32), primary_key=True)
    supplier_name = Column(String(128), nullable=False)
    lead_time_days = Column(Integer, nullable=False, default=7)
    status = Column(
        Enum("ACTIVE", "SUSPENDED", "UNDER_REVIEW", name="supplier_status"),
        nullable=False,
        default="ACTIVE"
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")


class Item(Base):
    __tablename__ = "items"

    item_id = Column(String(32), primary_key=True)
    sku = Column(String(64), nullable=False, unique=True)
    item_name = Column(String(128), nullable=False)
    category = Column(String(64), nullable=False)
    unit_cost = Column(Numeric(12, 2), nullable=False)
    lead_time_days = Column(Integer, nullable=False, default=7)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    po_lines = relationship("POLine", back_populates="item")
    production_orders = relationship("ProductionOrder", back_populates="item")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    po_id = Column(String(32), primary_key=True)
    supplier_id = Column(String(32), ForeignKey("suppliers.supplier_id"), nullable=False, index=True)
    order_date = Column(Date, nullable=False)
    status = Column(
        Enum("OPEN", "ACKNOWLEDGED", "CHANGE_PENDING", "APPROVED", "REJECTED", "CLOSED", name="po_status"),
        nullable=False,
        default="OPEN",
        index=True
    )
    total_amount = Column(Numeric(14, 2), nullable=False, default=0.00)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    supplier = relationship("Supplier", back_populates="purchase_orders")
    lines = relationship("POLine", back_populates="purchase_order", cascade="all, delete-orphan")


class POLine(Base):
    __tablename__ = "po_lines"

    po_line_id = Column(String(32), primary_key=True)
    po_id = Column(String(32), ForeignKey("purchase_orders.po_id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(String(32), ForeignKey("items.item_id"), nullable=False, index=True)
    ordered_qty = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    requested_delivery_date = Column(Date, nullable=False)
    status = Column(
        Enum("OPEN", "ACKNOWLEDGED", "CHANGE_REQUESTED", "CANCELLED", "CLOSED", name="po_line_status"),
        nullable=False,
        default="OPEN"
    )

    # Relationships
    purchase_order = relationship("PurchaseOrder", back_populates="lines")
    item = relationship("Item", back_populates="po_lines")
    acknowledgements = relationship("Acknowledgement", back_populates="po_line", cascade="all, delete-orphan")
    change_requests = relationship("ChangeRequest", back_populates="po_line", cascade="all, delete-orphan")
    inventory_plan = relationship("InventoryPlan", back_populates="po_line", uselist=False, cascade="all, delete-orphan")
    schedule_impacts = relationship("ScheduleImpact", back_populates="po_line", cascade="all, delete-orphan")


class Acknowledgement(Base):
    __tablename__ = "acknowledgements"

    ack_id = Column(String(32), primary_key=True)
    po_line_id = Column(String(32), ForeignKey("po_lines.po_line_id", ondelete="CASCADE"), nullable=False, index=True)
    revision_no = Column(Integer, nullable=False, default=1)
    accepted_qty = Column(Integer, nullable=False)
    rejected_qty = Column(Integer, nullable=False, default=0)
    acknowledgement_date = Column(Date, nullable=False)
    status = Column(
        Enum("FULL_ACCEPTANCE", "PARTIAL_ACCEPTANCE", "REJECTED", "CHANGE_PROPOSED", name="ack_status"),
        nullable=False
    )

    # Relationships
    po_line = relationship("POLine", back_populates="acknowledgements")
    promise_dates = relationship("PromiseDate", back_populates="acknowledgement", cascade="all, delete-orphan")


class PromiseDate(Base):
    __tablename__ = "promise_dates"

    promise_id = Column(String(64), primary_key=True)
    ack_id = Column(String(32), ForeignKey("acknowledgements.ack_id", ondelete="CASCADE"), nullable=False, index=True)
    promised_date = Column(Date, nullable=False)
    revision_no = Column(Integer, nullable=False, default=1)
    effective_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    acknowledgement = relationship("Acknowledgement", back_populates="promise_dates")


class ChangeRequest(Base):
    __tablename__ = "change_requests"

    change_id = Column(String(32), primary_key=True)
    po_line_id = Column(String(32), ForeignKey("po_lines.po_line_id", ondelete="CASCADE"), nullable=False, index=True)
    change_type = Column(
        Enum("QUANTITY", "PRICE", "DELIVERY_DATE", "COMBINED", name="change_type"),
        nullable=False
    )
    old_value = Column(String(255), nullable=False)
    new_value = Column(String(255), nullable=False)
    revision_no = Column(Integer, nullable=False, default=1)
    status = Column(
        Enum("PROPOSED", "PENDING_APPROVAL", "APPROVED", "REJECTED", "APPLIED", "SUPERSEDED", name="change_status"),
        nullable=False,
        default="PENDING_APPROVAL",
        index=True
    )
    requested_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    po_line = relationship("POLine", back_populates="change_requests")
    approvals = relationship("Approval", back_populates="change_request", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="change_request")


class Approval(Base):
    __tablename__ = "approvals"

    approval_id = Column(String(64), primary_key=True)
    change_id = Column(String(32), ForeignKey("change_requests.change_id", ondelete="CASCADE"), nullable=False, index=True)
    decision = Column(
        Enum("APPROVED", "REJECTED", "PENDING", name="approval_decision"),
        nullable=False,
        default="PENDING"
    )
    reviewer_id = Column(String(64), nullable=True)
    decision_date = Column(DateTime, nullable=True)
    comments = Column(Text, nullable=True)

    # Relationships
    change_request = relationship("ChangeRequest", back_populates="approvals")


class InventoryPlan(Base):
    __tablename__ = "inventory_plans"

    plan_id = Column(String(64), primary_key=True)
    po_line_id = Column(String(32), ForeignKey("po_lines.po_line_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    projected_supply = Column(Integer, nullable=False)
    required_qty = Column(Integer, nullable=False)
    status = Column(
        Enum("BALANCED", "SHORTAGE", "SURPLUS", name="plan_status"),
        nullable=False,
        default="BALANCED"
    )
    effective_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    po_line = relationship("POLine", back_populates="inventory_plan")


class ProductionOrder(Base):
    __tablename__ = "production_orders"

    production_order_id = Column(String(32), primary_key=True)
    item_id = Column(String(32), ForeignKey("items.item_id"), nullable=False, index=True)
    required_qty = Column(Integer, nullable=False)
    required_date = Column(Date, nullable=False)
    status = Column(
        Enum("PLANNED", "RELEASED", "IN_PROGRESS", "RESCHEDULED", "COMPLETED", name="mo_status"),
        nullable=False,
        default="PLANNED"
    )

    # Relationships
    item = relationship("Item", back_populates="production_orders")
    schedule_impacts = relationship("ScheduleImpact", back_populates="production_order", cascade="all, delete-orphan")


class Notification(Base):
    __tablename__ = "notifications"

    notification_id = Column(String(32), primary_key=True)
    recipient_id = Column(String(64), nullable=False, index=True)
    change_id = Column(String(32), ForeignKey("change_requests.change_id", ondelete="SET NULL"), nullable=True, index=True)
    message = Column(Text, nullable=False)
    status = Column(
        Enum("UNREAD", "READ", "ARCHIVED", name="notification_status"),
        nullable=False,
        default="UNREAD"
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    change_request = relationship("ChangeRequest", back_populates="notifications")


class ScheduleImpact(Base):
    __tablename__ = "schedule_impacts"

    impact_id = Column(String(64), primary_key=True)
    production_order_id = Column(String(32), ForeignKey("production_orders.production_order_id", ondelete="CASCADE"), nullable=False, index=True)
    po_line_id = Column(String(32), ForeignKey("po_lines.po_line_id", ondelete="CASCADE"), nullable=False, index=True)
    po_id = Column(String(32), nullable=False)
    required_qty = Column(Integer, nullable=False)
    available_inventory = Column(Integer, nullable=False, default=0)
    projected_supply = Column(Integer, nullable=False)
    shortage_qty = Column(Integer, nullable=False, default=0)
    original_delivery_date = Column(Date, nullable=False)
    current_promised_date = Column(Date, nullable=False)
    delay_days = Column(Integer, nullable=False, default=0)
    impact_status = Column(
        Enum("ON_TIME", "POTENTIAL_SHORTAGE", "CONFIRMED_SHORTAGE", "SCHEDULE_CONFLICT", name="impact_status"),
        nullable=False,
        index=True
    )
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    production_order = relationship("ProductionOrder", back_populates="schedule_impacts")
    po_line = relationship("POLine", back_populates="schedule_impacts")


class ExceptionRecord(Base):
    __tablename__ = "exception_records"

    exception_id = Column(String(64), primary_key=True)
    record_id = Column(String(64), nullable=False, index=True)
    entity_type = Column(String(64), nullable=False)
    issue_type = Column(String(64), nullable=False, index=True)
    severity = Column(
        Enum("INFO", "WARNING", "HIGH", "CRITICAL", name="exception_severity"),
        nullable=False,
        default="WARNING"
    )
    description = Column(Text, nullable=False)
    is_resolved = Column(Boolean, nullable=False, default=False, index=True)
    detected_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class GroundTruthRecord(Base):
    __tablename__ = "ground_truth_records"

    gt_id = Column(String(64), primary_key=True)
    record_id = Column(String(64), nullable=False, index=True)
    entity_type = Column(String(64), nullable=False)
    issue_type = Column(String(64), nullable=False, index=True)
    expected_outcome = Column(String(64), nullable=False)
    expected_status = Column(String(64), nullable=False)
    affected_record_id = Column(String(64), nullable=True)
    severity = Column(String(32), nullable=False, default="CRITICAL")

