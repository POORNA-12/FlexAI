"""
Deterministic Synthetic Data Generator for Supplier Acknowledgement and Schedule Impact Manager.
Generates baseline business data, calculates derived decisions, injects 4 required negative scenarios,
records ground truth, and outputs CSV/JSON datasets.
"""

import csv
import json
import os
import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Any, Tuple

from backend.business_rules import (
    calculate_quantity_variance,
    calculate_price_variance,
    calculate_delivery_delay,
    evaluate_approval_requirement,
    calculate_schedule_impact,
)

BASE_SEED = 20261022


class SyntheticDataGenerator:
    def __init__(self, seed: int = BASE_SEED, scale: str = "dev"):
        self.seed = seed
        self.scale = scale
        self.rng = random.Random(seed)

        # Scale parameters
        if scale == "full":
            self.num_pos = 10000
            self.target_events = 15000
            self.num_suppliers = 100
            self.num_items = 50
            self.num_production_orders = 1000
        else:  # dev scale
            self.num_pos = 200
            self.target_events = 350
            self.num_suppliers = 20
            self.num_items = 15
            self.num_production_orders = 50

        self.tables: Dict[str, List[Dict[str, Any]]] = {
            "suppliers": [],
            "items": [],
            "purchase_orders": [],
            "po_lines": [],
            "acknowledgements": [],
            "promise_dates": [],
            "change_requests": [],
            "approvals": [],
            "inventory_plans": [],
            "production_orders": [],
            "notifications": [],
            "schedule_impacts": [],
            "exception_records": [],
            "ground_truth_records": [],
        }

        self.ground_truth: List[Dict[str, Any]] = []

    def generate_all(self) -> Dict[str, List[Dict[str, Any]]]:
        """Runs the entire deterministic generation pipeline."""
        self._generate_suppliers()
        self._generate_items()
        self._generate_purchase_orders_and_lines()
        self._generate_production_orders()
        self._generate_baseline_inventory_plans()
        self._generate_acknowledgements_and_changes()
        self._process_approvals_and_apply_plans()
        self._calculate_schedule_impacts()
        self._generate_notifications()
        self._inject_negative_scenarios()
        return self.tables

    def _generate_suppliers(self):
        supplier_names = [
            "Apex Industrial Components", "Vanguard Precision Dynamics", "Pinnacle Material Solutions",
            "Titan Logistics & Supply", "Nexus Global Manufacturing", "Summit Electro-Mechanics",
            "Starlight Polymers", "Quantum Alloys Corp", "Horizon Micro-Tech", "Crestview Fasteners",
            "Pacific Precision Tooling", "Alliance Metal Works", "Beacon Semiconductor", "Frontier Assemblies",
            "Optima Hydraulics", "Matrix Sensors Inc", "Vertex Cable Systems", "Precision Castings Ltd",
            "AeroTech Composites", "Starlight Foundry", "Global Tech Hardware", "Reliant Electronics"
        ]
        for i in range(1, self.num_suppliers + 1):
            s_id = f"SUP-{i:04d}"
            name = supplier_names[(i - 1) % len(supplier_names)]
            if i > len(supplier_names):
                name = f"{name} {i // len(supplier_names) + 1}"
            lead_time = self.rng.choice([5, 7, 10, 14, 21])
            status = "ACTIVE" if i <= int(self.num_suppliers * 0.95) else "UNDER_REVIEW"
            created_at = datetime(2026, 1, 1, 8, 0, 0) + timedelta(days=i % 60)
            self.tables["suppliers"].append({
                "supplier_id": s_id,
                "supplier_name": name,
                "lead_time_days": lead_time,
                "status": status,
                "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": created_at.strftime("%Y-%m-%d %H:%M:%S")
            })

    def _generate_items(self):
        categories = ["FASTENERS", "ELECTRONICS", "HYDRAULICS", "RAW_METALS", "SENSORS", "MOTORS"]
        for i in range(1, self.num_items + 1):
            item_id = f"ITM-{i:05d}"
            sku = f"SKU-{1000 + i}"
            category = categories[i % len(categories)]
            cost = round(Decimal(self.rng.uniform(10.0, 500.0)), 2)
            lead_time = self.rng.choice([5, 7, 10, 14, 21])
            self.tables["items"].append({
                "item_id": item_id,
                "sku": sku,
                "item_name": f"{category.capitalize()} Component Type-{i}",
                "category": category,
                "unit_cost": float(cost),
                "lead_time_days": lead_time,
                "created_at": "2026-01-01 00:00:00"
            })

    def _generate_purchase_orders_and_lines(self):
        base_order_date = date(2026, 3, 1)
        supplier_ids = [s["supplier_id"] for s in self.tables["suppliers"] if s["status"] == "ACTIVE"]
        items = self.tables["items"]

        line_counter = 1
        for i in range(1, self.num_pos + 1):
            po_id = f"PO-2026-{i:06d}"
            supplier_id = self.rng.choice(supplier_ids)
            order_days_offset = (i * 7) % 180
            order_date = base_order_date + timedelta(days=order_days_offset)
            created_at = datetime.combine(order_date, datetime.min.time()) + timedelta(hours=9)

            # 1 to 2 lines per PO
            num_lines = 1 if self.rng.random() < 0.75 else 2
            po_total = Decimal("0.00")

            for l_idx in range(1, num_lines + 1):
                po_line_id = f"{po_id}-L{l_idx:02d}"
                item = self.rng.choice(items)
                qty = self.rng.choice([50, 100, 150, 200, 250, 500, 1000])
                unit_price = Decimal(str(item["unit_cost"])) * Decimal(str(round(self.rng.uniform(0.95, 1.05), 2)))
                unit_price = round(unit_price, 2)
                lead_time = item["lead_time_days"]
                req_delivery_date = order_date + timedelta(days=lead_time + self.rng.choice([3, 5, 7, 10]))

                po_total += (Decimal(qty) * unit_price)

                self.tables["po_lines"].append({
                    "po_line_id": po_line_id,
                    "po_id": po_id,
                    "item_id": item["item_id"],
                    "ordered_qty": qty,
                    "unit_price": float(unit_price),
                    "requested_delivery_date": req_delivery_date.strftime("%Y-%m-%d"),
                    "status": "OPEN"
                })
                line_counter += 1

            self.tables["purchase_orders"].append({
                "po_id": po_id,
                "supplier_id": supplier_id,
                "order_date": order_date.strftime("%Y-%m-%d"),
                "status": "OPEN",
                "total_amount": float(po_total),
                "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": created_at.strftime("%Y-%m-%d %H:%M:%S")
            })

    def _generate_production_orders(self):
        items = self.tables["items"]
        base_date = date(2026, 3, 20)
        for i in range(1, self.num_production_orders + 1):
            mo_id = f"PRD-2026-{i:06d}"
            item = self.rng.choice(items)
            req_qty = self.rng.choice([80, 100, 150, 200, 300, 500])
            req_date = base_date + timedelta(days=(i * 3) % 180)
            status = self.rng.choice(["PLANNED", "RELEASED", "IN_PROGRESS"])
            self.tables["production_orders"].append({
                "production_order_id": mo_id,
                "item_id": item["item_id"],
                "required_qty": req_qty,
                "required_date": req_date.strftime("%Y-%m-%d"),
                "status": status
            })

    def _generate_baseline_inventory_plans(self):
        """Creates initial inventory plans matching PO lines before any changes."""
        for line in self.tables["po_lines"]:
            plan_id = f"PLAN-{line['po_line_id']}"
            self.tables["inventory_plans"].append({
                "plan_id": plan_id,
                "po_line_id": line["po_line_id"],
                "projected_supply": line["ordered_qty"],
                "required_qty": line["ordered_qty"],
                "status": "BALANCED",
                "effective_at": "2026-03-01 08:00:00"
            })

    def _generate_acknowledgements_and_changes(self):
        po_map = {p["po_id"]: p for p in self.tables["purchase_orders"]}
        
        # Track ack counter per PO
        po_ack_counts = {}
        po_chg_counts = {}

        for line in self.tables["po_lines"]:
            po = po_map[line["po_id"]]
            po_id = po["po_id"]
            po_order_d = date.fromisoformat(po["order_date"])
            req_deliv_d = date.fromisoformat(line["requested_delivery_date"])

            po_ack_counts[po_id] = po_ack_counts.get(po_id, 0) + 1
            po_chg_counts[po_id] = po_chg_counts.get(po_id, 0) + 1
            ack_num = po_ack_counts[po_id]
            chg_num = po_chg_counts[po_id]

            roll = self.rng.random()

            if roll < 0.03:
                # Supplier silence scenario: no acknowledgement created
                line["status"] = "OPEN"
                continue

            ack_date = po_order_d + timedelta(days=self.rng.choice([1, 2, 3]))

            if roll < 0.73:
                # Full acceptance, on-time
                ack_id = f"ACK-{po_id}-{ack_num:02d}"
                self.tables["acknowledgements"].append({
                    "ack_id": ack_id,
                    "po_line_id": line["po_line_id"],
                    "revision_no": 1,
                    "accepted_qty": line["ordered_qty"],
                    "rejected_qty": 0,
                    "acknowledgement_date": ack_date.strftime("%Y-%m-%d"),
                    "status": "FULL_ACCEPTANCE"
                })
                self.tables["promise_dates"].append({
                    "promise_id": f"PRM-{ack_id}-01",
                    "ack_id": ack_id,
                    "promised_date": req_deliv_d.strftime("%Y-%m-%d"),
                    "revision_no": 1,
                    "effective_at": f"{ack_date.strftime('%Y-%m-%d')} 10:00:00"
                })
                line["status"] = "ACKNOWLEDGED"
                po["status"] = "ACKNOWLEDGED"

            elif roll < 0.88:
                # Proposed change: quantity reduction or date delay
                ack_id = f"ACK-{po_id}-{ack_num:02d}"

                is_qty_change = self.rng.random() < 0.6
                if is_qty_change:
                    accepted = int(line["ordered_qty"] * self.rng.choice([0.75, 0.80, 0.85, 0.90]))
                    rejected = line["ordered_qty"] - accepted
                    ack_status = "PARTIAL_ACCEPTANCE"
                    change_type = "QUANTITY"
                    old_val = str(line["ordered_qty"])
                    new_val = str(accepted)
                    promised_d = req_deliv_d
                else:
                    accepted = line["ordered_qty"]
                    rejected = 0
                    ack_status = "CHANGE_PROPOSED"
                    change_type = "DELIVERY_DATE"
                    slip_days = self.rng.choice([3, 5, 7, 10, 14])
                    promised_d = req_deliv_d + timedelta(days=slip_days)
                    old_val = req_deliv_d.strftime("%Y-%m-%d")
                    new_val = promised_d.strftime("%Y-%m-%d")

                self.tables["acknowledgements"].append({
                    "ack_id": ack_id,
                    "po_line_id": line["po_line_id"],
                    "revision_no": 1,
                    "accepted_qty": accepted,
                    "rejected_qty": rejected,
                    "acknowledgement_date": ack_date.strftime("%Y-%m-%d"),
                    "status": ack_status
                })
                self.tables["promise_dates"].append({
                    "promise_id": f"PRM-{ack_id}-01",
                    "ack_id": ack_id,
                    "promised_date": promised_d.strftime("%Y-%m-%d"),
                    "revision_no": 1,
                    "effective_at": f"{ack_date.strftime('%Y-%m-%d')} 10:00:00"
                })

                chg_id = f"CHG-{po_id}-{chg_num:06d}"
                self.tables["change_requests"].append({
                    "change_id": chg_id,
                    "po_line_id": line["po_line_id"],
                    "change_type": change_type,
                    "old_value": old_val,
                    "new_value": new_val,
                    "revision_no": 1,
                    "status": "PENDING_APPROVAL",
                    "requested_at": f"{ack_date.strftime('%Y-%m-%d')} 10:00:00"
                })
                line["status"] = "CHANGE_REQUESTED"
                po["status"] = "CHANGE_PENDING"

            elif roll < 0.96:
                # Direct rejection
                ack_id = f"ACK-{po_id}-{ack_num:02d}"
                self.tables["acknowledgements"].append({
                    "ack_id": ack_id,
                    "po_line_id": line["po_line_id"],
                    "revision_no": 1,
                    "accepted_qty": 0,
                    "rejected_qty": line["ordered_qty"],
                    "acknowledgement_date": ack_date.strftime("%Y-%m-%d"),
                    "status": "REJECTED"
                })
                self.tables["promise_dates"].append({
                    "promise_id": f"PRM-{ack_id}-01",
                    "ack_id": ack_id,
                    "promised_date": req_deliv_d.strftime("%Y-%m-%d"),
                    "revision_no": 1,
                    "effective_at": f"{ack_date.strftime('%Y-%m-%d')} 10:00:00"
                })
                chg_id = f"CHG-{po_id}-{chg_num:06d}"
                self.tables["change_requests"].append({
                    "change_id": chg_id,
                    "po_line_id": line["po_line_id"],
                    "change_type": "QUANTITY",
                    "old_value": str(line["ordered_qty"]),
                    "new_value": "0",
                    "revision_no": 1,
                    "status": "PENDING_APPROVAL",
                    "requested_at": f"{ack_date.strftime('%Y-%m-%d')} 10:00:00"
                })
                line["status"] = "CHANGE_REQUESTED"
                po["status"] = "CHANGE_PENDING"

            else:
                # Multiple revisions scenario (Rev 1 proposed change, Rev 2 finalized)
                ack_id_rev1 = f"ACK-{po_id}-{ack_num:02d}"
                po_ack_counts[po_id] += 1
                ack_id_rev2 = f"ACK-{po_id}-{po_ack_counts[po_id]:02d}"

                self.tables["acknowledgements"].append({
                    "ack_id": ack_id_rev1,
                    "po_line_id": line["po_line_id"],
                    "revision_no": 1,
                    "accepted_qty": int(line["ordered_qty"] * 0.70),
                    "rejected_qty": int(line["ordered_qty"] * 0.30),
                    "acknowledgement_date": ack_date.strftime("%Y-%m-%d"),
                    "status": "PARTIAL_ACCEPTANCE"
                })
                self.tables["promise_dates"].append({
                    "promise_id": f"PRM-{ack_id_rev1}-01",
                    "ack_id": ack_id_rev1,
                    "promised_date": (req_deliv_d + timedelta(days=7)).strftime("%Y-%m-%d"),
                    "revision_no": 1,
                    "effective_at": f"{ack_date.strftime('%Y-%m-%d')} 10:00:00"
                })

                ack_date_rev2 = ack_date + timedelta(days=2)
                self.tables["acknowledgements"].append({
                    "ack_id": ack_id_rev2,
                    "po_line_id": line["po_line_id"],
                    "revision_no": 2,
                    "accepted_qty": int(line["ordered_qty"] * 0.90),
                    "rejected_qty": int(line["ordered_qty"] * 0.10),
                    "acknowledgement_date": ack_date_rev2.strftime("%Y-%m-%d"),
                    "status": "PARTIAL_ACCEPTANCE"
                })
                self.tables["promise_dates"].append({
                    "promise_id": f"PRM-{ack_id_rev2}-02",
                    "ack_id": ack_id_rev2,
                    "promised_date": (req_deliv_d + timedelta(days=3)).strftime("%Y-%m-%d"),
                    "revision_no": 2,
                    "effective_at": f"{ack_date_rev2.strftime('%Y-%m-%d')} 11:00:00"
                })

                chg_id = f"CHG-{po_id}-{chg_num:06d}"
                self.tables["change_requests"].append({
                    "change_id": chg_id,
                    "po_line_id": line["po_line_id"],
                    "change_type": "QUANTITY",
                    "old_value": str(line["ordered_qty"]),
                    "new_value": str(int(line["ordered_qty"] * 0.90)),
                    "revision_no": 2,
                    "status": "PENDING_APPROVAL",
                    "requested_at": f"{ack_date_rev2.strftime('%Y-%m-%d')} 11:00:00"
                })
                line["status"] = "CHANGE_REQUESTED"
                po["status"] = "CHANGE_PENDING"

    def _process_approvals_and_apply_plans(self):
        """
        Processes approvals for change requests.
        CRITICAL INVARIANT: Only APPROVED changes update inventory_plans.
        Pending and Rejected changes leave inventory plans untouched!
        """
        line_map = {l["po_line_id"]: l for l in self.tables["po_lines"]}
        plan_map = {p["po_line_id"]: p for p in self.tables["inventory_plans"]}

        approval_counter = 1
        for chg in self.tables["change_requests"]:
            appr_id = f"APR-{chg['change_id']}-{approval_counter:02d}"
            approval_counter += 1

            line = line_map[chg["po_line_id"]]
            req_d = date.fromisoformat(line["requested_delivery_date"])

            # Parse proposed vs original values
            if chg["change_type"] == "QUANTITY":
                orig_qty = int(chg["old_value"])
                prop_qty = int(chg["new_value"])
                orig_price = line["unit_price"]
                prop_price = line["unit_price"]
                prom_d = req_d
            elif chg["change_type"] == "DELIVERY_DATE":
                orig_qty = line["ordered_qty"]
                prop_qty = line["ordered_qty"]
                orig_price = line["unit_price"]
                prop_price = line["unit_price"]
                prom_d = date.fromisoformat(chg["new_value"])
            else:
                orig_qty = line["ordered_qty"]
                prop_qty = line["ordered_qty"]
                orig_price = line["unit_price"]
                prop_price = float(chg["new_value"])
                prom_d = req_d

            req_appr, tier, reason = evaluate_approval_requirement(
                chg["change_type"], orig_qty, prop_qty, orig_price, prop_price, req_d, prom_d
            )

            # Decision distribution:
            # 65% Approved
            # 20% Rejected
            # 15% Left Pending Approval
            roll = self.rng.random()
            if roll < 0.65:
                decision = "APPROVED"
                reviewer = "AUTO_SYSTEM" if not req_appr else "PLN-001"
                comments = f"Approved: {reason}"
                dec_date = datetime.strptime(chg["requested_at"], "%Y-%m-%d %H:%M:%S") + timedelta(hours=4)

                self.tables["approvals"].append({
                    "approval_id": appr_id,
                    "change_id": chg["change_id"],
                    "decision": decision,
                    "reviewer_id": reviewer,
                    "decision_date": dec_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "comments": comments
                })

                # Apply approved change to inventory plan
                chg["status"] = "APPLIED"
                plan = plan_map[chg["po_line_id"]]
                if chg["change_type"] == "QUANTITY":
                    plan["projected_supply"] = prop_qty
                    if prop_qty < plan["required_qty"]:
                        plan["status"] = "SHORTAGE"
                    elif prop_qty > plan["required_qty"]:
                        plan["status"] = "SURPLUS"
                    else:
                        plan["status"] = "BALANCED"
                plan["effective_at"] = dec_date.strftime("%Y-%m-%d %H:%M:%S")

            elif roll < 0.85:
                decision = "REJECTED"
                reviewer = "PLN-001"
                comments = f"Rejected: Impact on downstream production too severe. {reason}"
                dec_date = datetime.strptime(chg["requested_at"], "%Y-%m-%d %H:%M:%S") + timedelta(hours=6)

                self.tables["approvals"].append({
                    "approval_id": appr_id,
                    "change_id": chg["change_id"],
                    "decision": decision,
                    "reviewer_id": reviewer,
                    "decision_date": dec_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "comments": comments
                })
                chg["status"] = "REJECTED"
                # Inventory plan remains untouched!

            else:
                # Left Pending
                chg["status"] = "PENDING_APPROVAL"
                # No approval record created yet, inventory plan untouched!

    def _calculate_schedule_impacts(self):
        """Computes downstream schedule impacts linking production orders and PO lines."""
        plan_map = {p["po_line_id"]: p for p in self.tables["inventory_plans"]}
        prm_by_line = {}
        for prm in self.tables["promise_dates"]:
            # find ack
            for ack in self.tables["acknowledgements"]:
                if ack["ack_id"] == prm["ack_id"]:
                    prm_by_line[ack["po_line_id"]] = prm
                    break

        impact_counter = 1
        # Link production orders with PO lines for matching item_ids
        lines_by_item = {}
        for l in self.tables["po_lines"]:
            lines_by_item.setdefault(l["item_id"], []).append(l)

        for mo in self.tables["production_orders"]:
            matching_lines = lines_by_item.get(mo["item_id"], [])
            if not matching_lines:
                continue

            # Pick a related PO line
            line = matching_lines[(impact_counter * 7) % len(matching_lines)]
            plan = plan_map[line["po_line_id"]]
            prm = prm_by_line.get(line["po_line_id"])

            req_deliv_d = date.fromisoformat(line["requested_delivery_date"])
            prom_d = date.fromisoformat(prm["promised_date"]) if prm else req_deliv_d
            mo_req_d = date.fromisoformat(mo["required_date"])

            avail_stock = self.rng.choice([0, 10, 25, 50])
            delay_days, shortage_qty, impact_status = calculate_schedule_impact(
                required_qty=mo["required_qty"],
                available_inventory=avail_stock,
                projected_supply=plan["projected_supply"],
                requested_delivery_date=req_deliv_d,
                current_promised_date=prom_d,
                production_required_date=mo_req_d
            )

            imp_id = f"IMP-PRD-2026-{impact_counter:06d}-01"
            impact_counter += 1
            self.tables["schedule_impacts"].append({
                "impact_id": imp_id,
                "production_order_id": mo["production_order_id"],
                "po_line_id": line["po_line_id"],
                "po_id": line["po_id"],
                "required_qty": mo["required_qty"],
                "available_inventory": avail_stock,
                "projected_supply": plan["projected_supply"],
                "shortage_qty": shortage_qty,
                "original_delivery_date": req_deliv_d.strftime("%Y-%m-%d"),
                "current_promised_date": prom_d.strftime("%Y-%m-%d"),
                "delay_days": delay_days,
                "impact_status": impact_status,
                "updated_at": "2026-03-15 12:00:00"
            })

    def _generate_notifications(self):
        notif_counter = 1
        for chg in self.tables["change_requests"]:
            if chg["status"] in ("PENDING_APPROVAL", "REJECTED"):
                msg = f"Change request {chg['change_id']} for line {chg['po_line_id']} requires attention. Type: {chg['change_type']}, Proposed: {chg['new_value']}."
                self.tables["notifications"].append({
                    "notification_id": f"NOT-2026-{notif_counter:06d}",
                    "recipient_id": "PLN-001",
                    "change_id": chg["change_id"],
                    "message": msg,
                    "status": "UNREAD",
                    "created_at": chg["requested_at"]
                })
                notif_counter += 1

    def _inject_negative_scenarios(self):
        """
        Injects the four mandatory negative scenarios into distinct labeled records
        and records expected decisions in ground truth.
        """
        rng = random.Random(self.seed + 9999)
        used_records = set()

        # Scenario 1: Unapproved change updates inventory plan
        # We find an inventory plan linked to a PENDING_APPROVAL change and artificially update projected_supply
        pending_changes = [c for c in self.tables["change_requests"] if c["status"] == "PENDING_APPROVAL" and c["change_type"] == "QUANTITY"]
        if pending_changes:
            target_chg = pending_changes[0]
            for plan in self.tables["inventory_plans"]:
                if plan["po_line_id"] == target_chg["po_line_id"]:
                    # Artificially update plan with unapproved new value
                    plan["projected_supply"] = int(target_chg["new_value"])
                    used_records.add(plan["plan_id"])

                    self.tables["ground_truth_records"].append({
                        "gt_id": f"GT-SCENARIO-01-{target_chg['change_id']}",
                        "record_id": plan["plan_id"],
                        "entity_type": "inventory_plans",
                        "issue_type": "unapproved_change_updates_plan",
                        "expected_outcome": "FLAG_UNAPPROVED_PLAN_UPDATE",
                        "expected_status": "CRITICAL_VIOLATION",
                        "affected_record_id": target_chg["change_id"],
                        "severity": "CRITICAL"
                    })
                    break

        # Scenario 2: Acknowledgement references the wrong PO line
        # Mismatched parent-child relationship
        all_lines = self.tables["po_lines"]
        for ack in self.tables["acknowledgements"]:
            # Pick a line belonging to a completely different PO
            curr_line_id = ack["po_line_id"]
            curr_po_id = curr_line_id.split("-L")[0]
            foreign_lines = [l for l in all_lines if l["po_id"] != curr_po_id]
            if foreign_lines:
                other_line = foreign_lines[0]
                ack["po_line_id"] = other_line["po_line_id"]
                used_records.add(ack["ack_id"])

                self.tables["ground_truth_records"].append({
                    "gt_id": f"GT-SCENARIO-02-{ack['ack_id']}",
                    "record_id": ack["ack_id"],
                    "entity_type": "acknowledgements",
                    "issue_type": "ack_wrong_po_line",
                    "expected_outcome": "REJECT_MISMATCHED_LINE",
                    "expected_status": "RELATIONSHIP_VIOLATION",
                    "affected_record_id": other_line["po_line_id"],
                    "severity": "HIGH"
                })
                break

        # Scenario 3: Promised date occurs before the purchase order date
        # Date ordering violation
        po_map = {p["po_id"]: p for p in self.tables["purchase_orders"]}
        line_map = {l["po_line_id"]: l for l in self.tables["po_lines"]}
        ack_map = {a["ack_id"]: a for a in self.tables["acknowledgements"]}

        for prm in self.tables["promise_dates"]:
            ack = ack_map.get(prm["ack_id"])
            if not ack or ack["ack_id"] in used_records:
                continue
            line = line_map.get(ack["po_line_id"])
            if not line:
                continue
            po = po_map.get(line["po_id"])
            if not po:
                continue

            po_order_d = date.fromisoformat(po["order_date"])
            # Set promised date 5 days BEFORE order date
            bad_prom_d = po_order_d - timedelta(days=5)
            prm["promised_date"] = bad_prom_d.strftime("%Y-%m-%d")
            used_records.add(prm["promise_id"])

            self.tables["ground_truth_records"].append({
                "gt_id": f"GT-SCENARIO-03-{prm['promise_id']}",
                "record_id": prm["promise_id"],
                "entity_type": "promise_dates",
                "issue_type": "promise_before_order_date",
                "expected_outcome": "REJECT_PRE_ORDER_PROMISE",
                "expected_status": "CHRONOLOGY_VIOLATION",
                "affected_record_id": po["po_id"],
                "severity": "HIGH"
            })
            break

        # Scenario 4: Older revision overwrites a newer revision
        # Multi-revision acknowledgement sequence violation
        # Find lines with rev 2
        rev2_acks = [a for a in self.tables["acknowledgements"] if a["revision_no"] == 2 and a["ack_id"] not in used_records]
        if rev2_acks:
            target_rev2 = rev2_acks[0]
            # Mutate revision_no to 0 so it appears as an older/regressed revision
            target_rev2["revision_no"] = 0
            used_records.add(target_rev2["ack_id"])

            self.tables["ground_truth_records"].append({
                "gt_id": f"GT-SCENARIO-04-{target_rev2['ack_id']}",
                "record_id": target_rev2["ack_id"],
                "entity_type": "acknowledgements",
                "issue_type": "older_revision_overwrites_newer",
                "expected_outcome": "REJECT_OUT_OF_SEQUENCE_REVISION",
                "expected_status": "REVISION_VIOLATION",
                "affected_record_id": target_rev2["po_line_id"],
                "severity": "CRITICAL"
            })

    def export_data(self, output_dir: Path):
        """Exports all generated tables to CSV and JSON formats."""
        output_dir.mkdir(parents=True, exist_ok=True)

        for table_name, rows in self.tables.items():
            if not rows:
                continue

            # CSV Export
            csv_path = output_dir / f"{table_name}.csv"
            fieldnames = list(rows[0].keys())
            with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            # JSON Export
            json_path = output_dir / f"{table_name}.json"
            with open(json_path, mode="w", encoding="utf-8") as f:
                json.dump(rows, f, indent=2)

        # Export isolated Ground Truth
        gt_rows = self.tables["ground_truth_records"]
        if gt_rows:
            with open(output_dir / "ground_truth.json", mode="w", encoding="utf-8") as f:
                json.dump(gt_rows, f, indent=2)
            with open(output_dir / "ground_truth.csv", mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(gt_rows[0].keys()))
                writer.writeheader()
                writer.writerows(gt_rows)
