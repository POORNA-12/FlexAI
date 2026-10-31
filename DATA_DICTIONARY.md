# SUPPLIER ACKNOWLEDGEMENT AND SCHEDULE IMPACT MANAGER - DATA DICTIONARY

## 1. Overview and Core Conventions

This Data Dictionary defines the complete data model for the Supplier Acknowledgement and Schedule Impact Manager. It details all 10 core entities, related auxiliary entities, fields, data types, constraints, validation rules, relationship cardinalities, and lifecycle constraints.

### Value Distinction Architecture
The system explicitly distinguishes between four states of operational values:
1. **Original Requested Values**: The initial quantities, delivery dates, and prices established on the purchase order line (`ordered_qty`, `requested_delivery_date`, `unit_price`).
2. **Proposed Supplier Values**: The supplier's suggested adjustments submitted via acknowledgements (`accepted_qty`, `rejected_qty`, `promised_date`, `new_value` in `change_requests`).
3. **Approved Values**: Explicit decisions made by planners/managers recorded in the `approvals` table (`decision = 'APPROVED'`).
4. **Current Effective Values**: Values committed to projected supply in `inventory_plans` and operational schedule calculations. **Crucial Rule**: Unapproved or pending changes are NEVER applied to current effective values.

---

## 2. Identifier Naming Conventions

All identifiers are deterministic, immutable, and follow zero-padded counter conventions:

| Entity | ID Pattern Example | Description |
|---|---|---|
| Supplier | `SUP-0001` | Supplier prefix and 4-digit sequence |
| Item | `ITM-00001` | Item catalog prefix and 5-digit sequence |
| Purchase Order | `PO-2026-000001` | Year prefix and 6-digit sequence |
| Purchase Order Line | `PO-2026-000001-L01` | Parent PO ID + Line suffix `L` + 2-digit line number |
| Acknowledgement | `ACK-PO-2026-000001-01` | `ACK-` + Parent PO ID + 2-digit line/rev counter |
| Promise Date | `PRM-ACK-PO-2026-000001-01-01` | `PRM-` + Parent ACK ID + 2-digit promise counter |
| Change Request | `CHG-PO-2026-000001-000001` | `CHG-` + Parent PO ID + 6-digit request counter |
| Approval | `APR-CHG-PO-2026-000001-000001-01`| `APR-` + Parent Change ID + 2-digit approval counter |
| Inventory Plan | `PLAN-PO-2026-000001-L01` | `PLAN-` + Referenced PO Line ID |
| Production Order | `PRD-2026-000001` | Production / Manufacturing order 6-digit sequence |
| Notification | `NOT-2026-000001` | Alert notification 6-digit sequence |
| Schedule Impact | `IMP-PRD-2026-000001-01` | Impact evaluation ID linking MO and PO line |
| Exception Record | `EXP-2026-000001` | Exception record 6-digit sequence |

---

## 3. Detailed Entity and Field Specifications

### 3.1 Supplier (`suppliers`)
Represents vendor organizations providing items and components.
- **Cardinality**: 1 Supplier to Many Purchase Orders (`1:N`).

| Field Name | Type | Req/Opt | Allowed Values | Units | Constraints | Relationship | Validation Rules & Lifecycle |
|---|---|---|---|---|---|---|---|
| `supplier_id` | VARCHAR(32) | Required | Pattern `^SUP-\d{4}$` | N/A | PK, Unique | None | Immutable identifier |
| `supplier_name` | VARCHAR(128) | Required | Non-empty string | N/A | None | None | 2 to 128 characters |
| `lead_time_days` | INT | Required | Integer >= 1 | Days | None | None | Standard manufacturing lead time |
| `status` | ENUM | Required | `ACTIVE`, `SUSPENDED`, `UNDER_REVIEW` | N/A | None | None | Only `ACTIVE` suppliers receive new orders |
| `created_at` | DATETIME | Required | Valid ISO datetime | N/A | None | None | Record creation timestamp |
| `updated_at` | DATETIME | Required | Valid ISO datetime | N/A | None | None | Record modification timestamp |

---

### 3.2 PurchaseOrder (`purchase_orders`)
Header record for a procurement order placed with a supplier.
- **Cardinality**: N Purchase Orders to 1 Supplier (`N:1`); 1 Purchase Order to Many PO Lines (`1:N`).

| Field Name | Type | Req/Opt | Allowed Values | Units | Constraints | Relationship | Validation Rules & Lifecycle |
|---|---|---|---|---|---|---|---|
| `po_id` | VARCHAR(32) | Required | Pattern `^PO-2026-\d{6}$` | N/A | PK, Unique | None | Immutable identifier |
| `supplier_id` | VARCHAR(32) | Required | Existing supplier_id | N/A | FK | `suppliers.supplier_id` | Supplier must be in `ACTIVE` state |
| `order_date` | DATE | Required | Valid date | N/A | None | None | Must be on or before current date |
| `status` | ENUM | Required | `OPEN`, `ACKNOWLEDGED`, `CHANGE_PENDING`, `APPROVED`, `REJECTED`, `CLOSED` | N/A | None | None | Lifecycle: OPEN -> ACKNOWLEDGED / CHANGE_PENDING -> APPROVED / REJECTED -> CLOSED |
| `total_amount` | DECIMAL(14,2)| Required | Decimal >= 0.00 | USD | None | None | Sum of all child PO line totals |
| `created_at` | DATETIME | Required | Valid ISO datetime | N/A | None | None | Creation timestamp |
| `updated_at` | DATETIME | Required | Valid ISO datetime | N/A | None | None | Modification timestamp |

---

### 3.3 POLine (`po_lines`)
Individual line item in a purchase order specifying ordered SKU, quantity, price, and required date.
- **Cardinality**: N Lines to 1 Purchase Order (`N:1`); 1 Line to Many Acknowledgements (`1:N`); 1 Line to 1 Inventory Plan (`1:1`).

| Field Name | Type | Req/Opt | Allowed Values | Units | Constraints | Relationship | Validation Rules & Lifecycle |
|---|---|---|---|---|---|---|---|
| `po_line_id` | VARCHAR(32) | Required | Pattern `^PO-2026-\d{6}-L\d{2}$` | N/A | PK, Unique | None | Derived from parent PO ID + line |
| `po_id` | VARCHAR(32) | Required | Existing po_id | N/A | FK | `purchase_orders.po_id` | Must match prefix of po_line_id |
| `item_id` | VARCHAR(32) | Required | Existing item_id | N/A | FK | `items.item_id` | Referenced item must exist |
| `ordered_qty` | INT | Required | Integer > 0 | Units | None | None | Original requested quantity |
| `unit_price` | DECIMAL(12,2)| Required | Decimal > 0.00 | USD/unit | None | None | Agreed contract unit price |
| `requested_delivery_date` | DATE | Required | Valid date >= order_date | N/A | None | None | Requested dock arrival date |
| `status` | ENUM | Required | `OPEN`, `ACKNOWLEDGED`, `CHANGE_REQUESTED`, `CANCELLED`, `CLOSED` | N/A | None | None | Line-level lifecycle state |

---

### 3.4 Acknowledgement (`acknowledgements`)
Records supplier responses, confirming acceptance, rejection, or proposing modifications.
- **Cardinality**: N Acknowledgements to 1 PO Line (`N:1`); 1 Acknowledgement to N Promise Dates (`1:N`).

| Field Name | Type | Req/Opt | Allowed Values | Units | Constraints | Relationship | Validation Rules & Lifecycle |
|---|---|---|---|---|---|---|---|
| `ack_id` | VARCHAR(32) | Required | Pattern `^ACK-PO-2026-\d{6}-\d{2}$` | N/A | PK, Unique | None | Immutable identifier |
| `po_line_id` | VARCHAR(32) | Required | Existing po_line_id | N/A | FK | `po_lines.po_line_id` | In valid baseline, must belong to parent PO |
| `revision_no` | INT | Required | Integer >= 1 | Rev # | None | None | Monotonically increasing revision counter |
| `accepted_qty` | INT | Required | Integer >= 0 | Units | None | None | Quantity supplier commits to deliver |
| `rejected_qty` | INT | Required | Integer >= 0 | Units | None | None | Quantity supplier cannot fulfill |
| `acknowledgement_date`| DATE | Required | Date >= PO order_date | N/A | None | None | Date response was received |
| `status` | ENUM | Required | `FULL_ACCEPTANCE`, `PARTIAL_ACCEPTANCE`, `REJECTED`, `CHANGE_PROPOSED` | N/A | None | None | `FULL_ACCEPTANCE` if accepted == ordered; `PARTIAL_ACCEPTANCE` if accepted < ordered and accepted > 0; `REJECTED` if accepted == 0 |

---

### 3.5 PromiseDate (`promise_dates`)
Records promised delivery dates from the supplier and tracking date slips.
- **Cardinality**: N Promise Dates to 1 Acknowledgement (`N:1`).

| Field Name | Type | Req/Opt | Allowed Values | Units | Constraints | Relationship | Validation Rules & Lifecycle |
|---|---|---|---|---|---|---|---|
| `promise_id` | VARCHAR(64) | Required | Pattern `^PRM-ACK-.*` | N/A | PK, Unique | None | Immutable identifier |
| `ack_id` | VARCHAR(32) | Required | Existing ack_id | N/A | FK | `acknowledgements.ack_id` | Foreign key to parent acknowledgement |
| `promised_date`| DATE | Required | Valid date | N/A | None | None | Must be >= PO order_date (checked in validation) |
| `revision_no` | INT | Required | Integer >= 1 | Rev # | None | None | Revision number matching acknowledgement |
| `effective_at` | DATETIME | Required | Valid ISO datetime | N/A | None | None | Timestamp when promise becomes effective |

---

### 3.6 ChangeRequest (`change_requests`)
Formal change proposal when supplier response deviates from ordered terms (quantity reduction, price increase, date delay).
- **Cardinality**: N Change Requests to 1 PO Line (`N:1`); 1 Change Request to N Approvals (`1:N`).

| Field Name | Type | Req/Opt | Allowed Values | Units | Constraints | Relationship | Validation Rules & Lifecycle |
|---|---|---|---|---|---|---|---|
| `change_id` | VARCHAR(32) | Required | Pattern `^CHG-PO-2026-\d{6}-\d{6}$` | N/A | PK, Unique | None | Immutable identifier |
| `po_line_id` | VARCHAR(32) | Required | Existing po_line_id | N/A | FK | `po_lines.po_line_id` | Target line being changed |
| `change_type` | ENUM | Required | `QUANTITY`, `PRICE`, `DELIVERY_DATE`, `COMBINED` | N/A | None | None | Category of requested change |
| `old_value` | VARCHAR(255) | Required | String representation | N/A | None | None | Original requested value |
| `new_value` | VARCHAR(255) | Required | String representation | N/A | None | None | Supplier proposed value |
| `revision_no` | INT | Required | Integer >= 1 | Rev # | None | None | Revision counter |
| `status` | ENUM | Required | `PROPOSED`, `PENDING_APPROVAL`, `APPROVED`, `REJECTED`, `APPLIED`, `SUPERSEDED` | N/A | None | None | `PENDING_APPROVAL` until reviewed; only `APPROVED` can transition to `APPLIED` |
| `requested_at`| DATETIME | Required | Valid ISO datetime | N/A | None | None | Timestamp of change proposal |

---

### 3.7 Approval (`approvals`)
Planner or operations manager review decision on a pending ChangeRequest.
- **Cardinality**: N Approvals to 1 Change Request (`N:1`).

| Field Name | Type | Req/Opt | Allowed Values | Units | Constraints | Relationship | Validation Rules & Lifecycle |
|---|---|---|---|---|---|---|---|
| `approval_id` | VARCHAR(64) | Required | Pattern `^APR-CHG-.*` | N/A | PK, Unique | None | Immutable identifier |
| `change_id` | VARCHAR(32) | Required | Existing change_id | N/A | FK | `change_requests.change_id` | Target change request |
| `decision` | ENUM | Required | `APPROVED`, `REJECTED`, `PENDING` | N/A | None | None | Reviewer's determination |
| `reviewer_id` | VARCHAR(64) | Optional | String identifier | N/A | None | None | Planner ID or AUTO_SYSTEM |
| `decision_date`| DATETIME | Optional | Valid ISO datetime | N/A | None | None | Timestamp when decision occurred |
| `comments` | TEXT | Optional | String explanation | N/A | None | None | Audit rationale for decision |

---

### 3.8 InventoryPlan (`inventory_plans`)
Operational projected supply plan linked to purchase order lines and consumed by production scheduling.
- **Cardinality**: 1 Inventory Plan to 1 PO Line (`1:1`).

| Field Name | Type | Req/Opt | Allowed Values | Units | Constraints | Relationship | Validation Rules & Lifecycle |
|---|---|---|---|---|---|---|---|
| `plan_id` | VARCHAR(64) | Required | Pattern `^PLAN-.*` | N/A | PK, Unique | None | Plan identifier |
| `po_line_id` | VARCHAR(32) | Required | Existing po_line_id | N/A | FK, Unique | `po_lines.po_line_id` | One-to-one relationship with PO line |
| `projected_supply`| INT | Required | Integer >= 0 | Units | None | None | Expected usable units. Only updated upon APPROVED change |
| `required_qty` | INT | Required | Integer >= 0 | Units | None | None | Quantity demanded by downstream operations |
| `status` | ENUM | Required | `BALANCED`, `SHORTAGE`, `SURPLUS` | N/A | None | None | `SHORTAGE` if projected_supply < required_qty |
| `effective_at` | DATETIME | Required | Valid ISO datetime | N/A | None | None | Timestamp of latest valid plan update |

---

### 3.9 ProductionOrder (`production_orders`)
Manufacturing work orders requiring component inventory by specific completion dates.
- **Cardinality**: 1 Production Order to Many Schedule Impacts (`1:N`).

| Field Name | Type | Req/Opt | Allowed Values | Units | Constraints | Relationship | Validation Rules & Lifecycle |
|---|---|---|---|---|---|---|---|
| `production_order_id`| VARCHAR(32)| Required | Pattern `^PRD-2026-\d{6}$` | N/A | PK, Unique | None | Immutable identifier |
| `item_id` | VARCHAR(32) | Required | Existing item_id | N/A | FK | `items.item_id` | Required component item |
| `required_qty`| INT | Required | Integer > 0 | Units | None | None | Total units of component required |
| `required_date`| DATE | Required | Valid date | N/A | None | None | Required completion date |
| `status` | ENUM | Required | `PLANNED`, `RELEASED`, `IN_PROGRESS`, `RESCHEDULED`, `COMPLETED` | N/A | None | None | Production execution state |

---

### 3.10 Notification (`notifications`)
Operational alerts generated for planners when changes occur, delays exceed thresholds, or supplier silence is detected.
- **Cardinality**: N Notifications to 1 Change Request (`N:1`).

| Field Name | Type | Req/Opt | Allowed Values | Units | Constraints | Relationship | Validation Rules & Lifecycle |
|---|---|---|---|---|---|---|---|
| `notification_id`| VARCHAR(32)| Required | Pattern `^NOT-2026-\d{6}$` | N/A | PK, Unique | None | Immutable identifier |
| `recipient_id`| VARCHAR(64) | Required | String identifier | N/A | None | None | Planner or manager ID |
| `change_id` | VARCHAR(32) | Optional | Existing change_id | N/A | FK | `change_requests.change_id` | Related change request |
| `message` | TEXT | Required | Non-empty string | N/A | None | None | Plain explanatory alert text |
| `status` | ENUM | Required | `UNREAD`, `READ`, `ARCHIVED` | N/A | None | None | Alert acknowledgment state |
| `created_at` | DATETIME | Required | Valid ISO datetime | N/A | None | None | Creation timestamp |

---

## 4. Auxiliary and Evaluation Tables

### 4.1 ScheduleImpact (`schedule_impacts`)
Tracks evaluated downstream production risk per production order and purchase order line:
- `impact_id`: Primary key (`IMP-...`).
- `production_order_id`: Foreign key to `production_orders`.
- `po_line_id`: Foreign key to `po_lines`.
- `po_id`: Purchase order identifier.
- `required_qty`: Demanded units.
- `available_inventory`: Current stock available.
- `projected_supply`: Effective approved supply arriving on or before required date.
- `shortage_qty`: Calculated as `max(0, required_qty - (available_inventory + projected_supply))`.
- `original_delivery_date`: PO Line requested delivery date.
- `current_promised_date`: Valid promised delivery date.
- `delay_days`: Days promised date exceeds requested date (`max(0, promised - requested)`).
- `impact_status`: `ON_TIME`, `POTENTIAL_SHORTAGE`, `CONFIRMED_SHORTAGE`, `SCHEDULE_CONFLICT`.

### 4.2 ExceptionRecord (`exception_records`)
Captures detected anomalies and business rule violations:
- `exception_id`: Primary key (`EXP-...`).
- `record_id`: Affected entity record ID.
- `entity_type`: Table name of affected record.
- `issue_type`: Category of exception (e.g. `unapproved_change_updates_plan`, `ack_wrong_po_line`, etc.).
- `severity`: `INFO`, `WARNING`, `HIGH`, `CRITICAL`.
- `description`: Plain text diagnostic explanation.
- `is_resolved`: Boolean flag for planner resolution.
- `detected_at`: Timestamp when exception was discovered.

### 4.3 GroundTruth (`ground_truth_records`)
Isolated evaluation dataset recording injected anomalies and expected decisions:
- `gt_id`: Primary key (`GT-...`).
- `record_id`: Affected entity identifier.
- `entity_type`: Entity name.
- `issue_type`: Injected negative scenario label.
- `expected_outcome`: Expected system reaction.
- `expected_status`: Expected validation status.
- `affected_record_id`: Correlated record identifier.
- `severity`: Anomaly severity.

