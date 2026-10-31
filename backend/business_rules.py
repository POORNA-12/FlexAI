"""
Business rules, variance calculations, approval threshold evaluations,
inventory projection reconciliation, and schedule impact logic.
"""

import os
from datetime import date, datetime, timedelta
from typing import Dict, Any, Tuple, Optional

# Business Rule Thresholds (Configurable via Environment)
AUTO_APPROVE_QTY_DELTA_MAX = float(os.getenv("AUTO_APPROVE_QTY_DELTA_MAX", "0.0"))
PLANNER_APPROVE_QTY_DELTA_MAX = float(os.getenv("PLANNER_APPROVE_QTY_DELTA_MAX", "10.0"))

AUTO_APPROVE_PRICE_DELTA_MAX = float(os.getenv("AUTO_APPROVE_PRICE_DELTA_MAX", "0.0"))
PLANNER_APPROVE_PRICE_DELTA_MAX = float(os.getenv("PLANNER_APPROVE_PRICE_DELTA_MAX", "5.0"))

AUTO_APPROVE_DELAY_DAYS_MAX = int(os.getenv("AUTO_APPROVE_DELAY_DAYS_MAX", "0"))
PLANNER_APPROVE_DELAY_DAYS_MAX = int(os.getenv("PLANNER_APPROVE_DELAY_DAYS_MAX", "7"))

SUPPLIER_SILENCE_DAYS = int(os.getenv("SUPPLIER_SILENCE_DAYS", "5"))


def calculate_quantity_variance(original_qty: int, proposed_qty: int) -> float:
    """Calculates percentage quantity variance. Negative value indicates a reduction."""
    if original_qty <= 0:
        return 0.0
    return round(((proposed_qty - original_qty) / original_qty) * 100.0, 2)


def calculate_price_variance(original_price: float, proposed_price: float) -> float:
    """Calculates percentage price variance. Positive value indicates a price increase."""
    if original_price <= 0.0:
        return 0.0
    return round(((proposed_price - original_price) / original_price) * 100.0, 2)


def calculate_delivery_delay(requested_date: date, promised_date: date) -> int:
    """Calculates delivery slip in days (positive means delayed)."""
    return (promised_date - requested_date).days


def evaluate_approval_requirement(
    change_type: str,
    original_qty: int,
    proposed_qty: int,
    original_price: float,
    proposed_price: float,
    requested_date: date,
    promised_date: date
) -> Tuple[bool, str, str]:
    """
    Evaluates whether a proposed change requires approval and which approval tier is needed.
    Returns: (requires_approval, required_role, rationale)
    """
    reasons = []
    highest_tier = "AUTO"

    # 1. Quantity reduction evaluation
    if proposed_qty < original_qty:
        pct_reduction = abs(calculate_quantity_variance(original_qty, proposed_qty))
        if pct_reduction > PLANNER_APPROVE_QTY_DELTA_MAX:
            highest_tier = "OPERATIONS_MANAGER"
            reasons.append(f"Quantity reduction of {pct_reduction:.1f}% exceeds manager threshold ({PLANNER_APPROVE_QTY_DELTA_MAX}%)")
        elif pct_reduction > AUTO_APPROVE_QTY_DELTA_MAX:
            if highest_tier == "AUTO":
                highest_tier = "PLANNER"
            reasons.append(f"Quantity reduction of {pct_reduction:.1f}% requires planner approval")

    # 2. Price increase evaluation
    if proposed_price > original_price:
        pct_increase = calculate_price_variance(original_price, proposed_price)
        if pct_increase > PLANNER_APPROVE_PRICE_DELTA_MAX:
            highest_tier = "OPERATIONS_MANAGER"
            reasons.append(f"Price increase of {pct_increase:.1f}% exceeds manager threshold ({PLANNER_APPROVE_PRICE_DELTA_MAX}%)")
        elif pct_increase > AUTO_APPROVE_PRICE_DELTA_MAX:
            if highest_tier == "AUTO":
                highest_tier = "PLANNER"
            reasons.append(f"Price increase of {pct_increase:.1f}% requires planner approval")

    # 3. Delivery date slip evaluation
    delay_days = calculate_delivery_delay(requested_date, promised_date)
    if delay_days > 0:
        if delay_days > PLANNER_APPROVE_DELAY_DAYS_MAX:
            highest_tier = "OPERATIONS_MANAGER"
            reasons.append(f"Delivery delay of {delay_days} days exceeds manager threshold ({PLANNER_APPROVE_DELAY_DAYS_MAX} days)")
        elif delay_days > AUTO_APPROVE_DELAY_DAYS_MAX:
            if highest_tier == "AUTO":
                highest_tier = "PLANNER"
            reasons.append(f"Delivery delay of {delay_days} days requires planner approval")

    if highest_tier == "AUTO":
        return False, "AUTO_SYSTEM", "Changes are within automatic acceptance thresholds."
    else:
        return True, highest_tier, "; ".join(reasons)


def calculate_schedule_impact(
    required_qty: int,
    available_inventory: int,
    projected_supply: int,
    requested_delivery_date: date,
    current_promised_date: date,
    production_required_date: date
) -> Tuple[int, int, str]:
    """
    Calculates shortage and schedule impact status.
    Returns: (delay_days, shortage_qty, impact_status)
    """
    delay_days = max(0, (current_promised_date - requested_delivery_date).days)
    
    # Supply arriving on or before the production required date is usable
    usable_supply = projected_supply if current_promised_date <= production_required_date else 0
    total_usable = available_inventory + usable_supply
    shortage_qty = max(0, required_qty - total_usable)

    if shortage_qty > 0:
        impact_status = "CONFIRMED_SHORTAGE"
    elif current_promised_date > production_required_date and delay_days > 0:
        impact_status = "SCHEDULE_CONFLICT"
    elif delay_days > 0:
        impact_status = "POTENTIAL_SHORTAGE"
    else:
        impact_status = "ON_TIME"

    return delay_days, shortage_qty, impact_status


def is_supplier_silent(order_date: date, last_ack_date: Optional[date], current_date: date) -> bool:
    """
    Checks if a supplier has remained silent beyond the acceptable response threshold.
    """
    if last_ack_date is not None:
        return False
    days_elapsed = (current_date - order_date).days
    return days_elapsed > SUPPLIER_SILENCE_DAYS

