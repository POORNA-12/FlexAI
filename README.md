# Supplier Acknowledgement and Schedule Impact Manager

An enterprise full-stack system designed to manage supplier purchase order acknowledgements, delivery promise dates, quantity/price change proposals, approval workflows, projected inventory supply, and downstream manufacturing schedule impacts.

---

## 1. Project Overview

In supply chain operations, purchase orders (POs) placed with suppliers frequently encounter modifications: suppliers may partially accept quantities, reject lines, propose price adjustments, or promise delivery dates that slip past original dock requirements.

The **Supplier Acknowledgement and Schedule Impact Manager** provides planners, logistics analysts, and operations managers with an auditable platform to:
- Trace what was originally ordered versus what the supplier accepted or rejected.
- Evaluate supplier delivery promises against manufacturing need dates.
- Enforce strict approval thresholds before unapproved supplier changes affect inventory supply plans.
- Prevent unapproved, rejected, or out-of-order changes from contaminating MRP / ERP supply projections.
- Detect relational, chronological, and sequence anomalies with high precision.

---

## 2. Business Problem and Core Workflow

```
[ Purchase Order Created ]
            │
            ▼
[ Supplier Acknowledgement ]
  ├── Full Acceptance (on-time delivery, matches order)
  ├── Partial Acceptance (accepted_qty < ordered_qty, rejected_qty > 0)
  ├── Delivery Slip (promised_date > requested_delivery_date)
  └── Supplier Silence (no acknowledgement within threshold)
            │
            ▼
[ Change Request Proposed ]
            │
            ▼
[ Approval Workflow ]
  ├── Under Threshold ──> Auto-System Acceptance
  └── Over Threshold  ──> Requires Planner / Operations Manager Review
            │
      ┌─────┴────────────────┐
      ▼                      ▼
  [ APPROVED ]          [ REJECTED ]
      │                      │
      ▼                      ▼
[ Transactional Supply ]  [ Projected Supply ]
  Projected Supply Updated  Remains UNCHANGED
  Schedule Impact Evaluated Decision logged in Audit
```

### Core Business Invariant:
**An unapproved or pending change request MUST NEVER update projected supply.** Projected supply in `inventory_plans` is only modified through a controlled, atomic database transaction when an explicit `APPROVED` decision is recorded. If rejected, original effective values are strictly preserved.

---

## 3. Technology Stack

- **Frontend**:
  - React 19 (JSX)
  - React Router DOM 7
  - Bootstrap 5.3 (enterprise layout, responsive tables, forms, badges)
  - Vite 6 (build tool & dev server)
  - HTML5 & Custom Enterprise CSS (strictly prohibited: gradients, pill buttons, fake counters, em dashes)
- **Backend**:
  - Python 3.10+ / Python 3.14
  - FastAPI (REST API with OpenAPI / Swagger UI)
  - Pydantic v2 (request/response schema validation)
  - SQLAlchemy 2.0 (ORM & transactional session management)
  - Uvicorn (ASGI server)
  - Pandas (data reconciliation and export formatting)
  - PyMySQL (pure-Python MySQL driver)
  - pytest (automated unit & integration testing)
- **Database**:
  - MySQL 8.0 (persistent storage with InnoDB, foreign keys, indexes, transactions)

---

## 4. Compact Project Structure

```
supplier_schedule_manager/
|-- run.bat                         # One-command startup script
|-- stop.bat                        # One-command shutdown script (terminates ports 8000 & 5173)
|-- README.md                       # Comprehensive system documentation
|-- DATA_DICTIONARY.md              # Complete data dictionary for all entities
|-- .gitignore                      # Git exclusion rules
|-- .env                            # Active environment configuration
|
|-- frontend/                       # React 19 + Vite + Bootstrap 5
|   |-- package.json
|   |-- vite.config.js
|   |-- index.html
|   |-- public/
|   |   |-- favicon.png             # Original enterprise favicon
|   |-- src/
|       |-- main.jsx
|       |-- App.jsx
|       |-- api.js                  # Centralized API client
|       |-- styles.css              # Restrained enterprise styling
|       |-- components/
|       |   |-- Navbar.jsx
|       |   |-- DataTable.jsx       # Reusable paginated data table
|       |   |-- StatusMessage.jsx   # Feedback & alert banner
|       |-- pages/
|           |-- Dashboard.jsx       # Calculated metrics & formulas
|           |-- PurchaseOrders.jsx  # Registry with line item detail
|           |-- Acknowledgements.jsx# Responses, revisions, promises
|           |-- Approvals.jsx       # Interactive approve/reject workflow
|           |-- ScheduleImpact.jsx  # Downstream production shortages
|           |-- Exceptions.jsx      # Detected anomalies & resolution
|           |-- DataQuality.jsx     # Diagnostics, validation & seed
|           |-- PrivacyPolicy.jsx   # Data practices & architecture
|           |-- TermsAndConditions.jsx # Terms, limitations, advisory
|
|-- backend/                        # FastAPI REST API & Business Logic
|   |-- main.py                     # Entry point & CORS middleware
|   |-- database.py                 # SQLAlchemy engine & session maker
|   |-- models.py                   # 10 core entities & auxiliary tables
|   |-- schemas.py                  # Pydantic input/output schemas
|   |-- routes.py                   # Documented REST API endpoints
|   |-- services.py                 # Transactional operations & metrics
|   |-- generator.py                # Deterministic synthetic data engine
|   |-- business_rules.py           # Thresholds, variances, formulas
|   |-- validation.py               # 15 validation rules & evaluation
|   |-- check_db.py                 # MySQL connectivity tester for startup
|   |-- requirements.txt            # Python dependencies
|   |-- .env.example                # Configuration template
|
|-- database/
|   |-- schema.sql                  # MySQL 8.0 DDL schema script
|
|-- data/                           # Exported CSV, JSON & Ground Truth
|   |-- .gitkeep
|   |-- purchase_orders.csv / .json
|   |-- po_lines.csv / .json
|   |-- acknowledgements.csv / .json
|   |-- promise_dates.csv / .json
|   |-- change_requests.csv / .json
|   |-- approvals.csv / .json
|   |-- inventory_plans.csv / .json
|   |-- production_orders.csv / .json
|   |-- schedule_impacts.csv / .json
|   |-- notifications.csv / .json
|   |-- ground_truth.csv / .json
|   |-- validation_summary.json
|   |-- reproducibility_report.json
|
|-- tests/
    |-- test_project.py             # 20 automated pytest test cases
```

---

## 5. Prerequisites

Before running the application, ensure the following software is installed on your Windows machine:
1. **Python 3.10+**: Available in PATH (`python --version`).
2. **Node.js 18+ & npm**: Available in PATH (`node --version`, `npm --version`).
3. **MySQL Server 8.0**: Installed, running on port 3306.

---

## 6. Environment Configuration

The application uses local environment variables defined in `.env` (and `backend/.env`). A template is provided in `backend/.env.example`.

```ini
# MySQL Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=supplier_schedule_manager
DATABASE_URL=mysql+pymysql://root:your_mysql_password@localhost:3306/supplier_schedule_manager?charset=utf8mb4

# API Server Configuration
API_HOST=127.0.0.1
API_PORT=8000
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Synthetic Data Configuration
SYNTHETIC_DATA_SEED=20261022
DATASET_SCALE=dev

# Business Rule Thresholds
AUTO_APPROVE_QTY_DELTA_MAX=0.0
PLANNER_APPROVE_QTY_DELTA_MAX=10.0
AUTO_APPROVE_PRICE_DELTA_MAX=0.0
PLANNER_APPROVE_PRICE_DELTA_MAX=5.0
AUTO_APPROVE_DELAY_DAYS_MAX=0
PLANNER_APPROVE_DELAY_DAYS_MAX=7
SUPPLIER_SILENCE_DAYS=5
```

---

## 7. One-Command Startup and Shutdown

### 7.1 Startup (`run.bat`)
The system is started using the Windows root-level `run.bat` script:

```cmd
run.bat
```

#### What `run.bat` executes automatically:
1. Determines the project directory dynamically (`cd /d "%~dp0"`).
2. Validates Python, Node.js, and npm installations.
3. Verifies all required project files exist.
4. Automatically sets up the local Python virtual environment (`venv`).
5. Installs backend dependencies (`pip install -r backend/requirements.txt`) only when needed.
6. Installs frontend packages (`npm install`) only when needed.
7. Verifies MySQL database connectivity using `backend/check_db.py`.
8. Detects and clears any stale instances on ports 8000 and 5173.
9. Starts the FastAPI backend server on port 8000 in a dedicated console window.
10. Starts the React development server on port 5173.
11. Displays the application access addresses and stopping instructions.

### 7.2 Shutdown (`stop.bat`)
To gracefully terminate both the backend API and frontend Vite servers, open a command prompt in the project root and execute:

```cmd
stop.bat
```
This inspects active listeners on ports 8000 and 5173 and terminates the corresponding processes cleanly.

### Expected Local Addresses:
- **Frontend Web Application**: [http://localhost:5173](http://localhost:5173)
- **FastAPI Backend Server**: [http://localhost:8000](http://localhost:8000)
- **FastAPI Interactive API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **FastAPI Alternative ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 8. Database Initialization and Schema

Database schema tables are defined with `CREATE TABLE IF NOT EXISTS` in `database/schema.sql` and SQLAlchemy metadata.
- Tables are created safely on first launch.
- Existing records are preserved across standard application launches.
- To manually execute the DDL:
```cmd
mysql -u root -p supplier_schedule_manager < database/schema.sql
```

---

## 9. Synthetic Data Generation and Full Volume

The generator produces deterministic, realistic supply chain datasets using the fixed random seed:
```
20261022
```

### 9.1 Supported Scales and Record Counts:

#### 1. Full Production Scale (`full`) — Default Initial Seed:
- **Purchase Orders**: 10,000 (meets requirement of at least 10,000 POs)
- **Suppliers**: 100
- **Items**: 50
- **Purchase Order Lines**: 12,477
- **Acknowledgements**: 12,599
- **Promise Dates**: 12,599
- **Change Requests**: 3,429
- **Approvals**: 2,920
- **Inventory Plans**: 12,477
- **Production Orders**: 1,000
- **Notifications**: 1,185
- **Schedule Impacts**: 1,000
- **Exception Records**: 4 (derived from automated validation)
- **Ground Truth Audit Records**: 4 (isolated benchmark records)
- **Combined Events**: 16,028 (Acknowledgements + Change Requests, exceeding the 15,000 requirement)
- **Total Operational Business Records**: **69,840** (across 13 business tables, heavily exceeding >10,000 requirement)
- **Total Database Records**: **69,844** (including ground truth audit table)
- **Generation & Bulk Insertion Time**: ~12.6 seconds into MySQL.

#### 2. Development Scale (`dev`):
- 200 Purchase Orders, 20 Suppliers, 15 Items, 50 Production Orders, ~350 Combined Events (~1,400 total records).

### 9.2 Initial Seeding and Database Preservation:
- On startup, the FastAPI server checks if MySQL contains existing purchase orders.
- If the database is completely empty, it seeds automatically using `DATASET_SCALE` (defaults to `"full"`).
- If the database is already populated, it preserves the database state across application restarts and never silently clears records.

### 9.3 How to Reseed or Switch Scale:
#### Via the Web UI:
1. Navigate to the **Data Quality & Reproducibility** page (`/data-quality`).
2. Click either:
   - **Generate Full Dataset (10,000 Purchase Orders)**
   - **Generate Development Dataset**
3. A confirmation modal will appear explaining that reseeding will replace existing database records, with guidance on exporting current data.
4. Click **Confirm & Generate**. The UI displays an active progress banner, disables buttons, and automatically refreshes all live database counts upon completion.

#### Via the REST API:
```bash
# Requires confirm=true when database is already populated
curl -X POST "http://localhost:8000/api/data-generator/seed?scale=full&confirm=true"
```

#### Via Command Line:
```cmd
venv\Scripts\python.exe -c "from backend.services import seed_database_from_generator; seed_database_from_generator('full')"
```

### 9.4 How to Verify Database Counts:
- Navigate to the **Data Quality & Reproducibility** page (`/data-quality`) to view live row counts queried directly from MySQL.
- Or query via the REST API:
```bash
curl -s http://localhost:8000/api/data-quality/summary
```
- Or run the automated test suite:
```cmd
pytest tests/test_project.py -k "test_27" -v
```

---

## 10. The Four Required Negative Scenarios

Four deliberate anomalies are injected into the dataset and recorded in the isolated `ground_truth.csv` and `ground_truth.json` files:

| Scenario | Injected Condition | Expected System Reaction | Rule Reference |
|---|---|---|---|
| **Scenario 1** | Unapproved change updates inventory plan | Detect unauthorized plan update; flag violation | RULE-PLAN-001 |
| **Scenario 2** | Acknowledgement references wrong PO line | Detect mismatched line reference; reject invalid relationship | RULE-ACK-002 |
| **Scenario 3** | Promised date occurs before PO order date | Detect invalid chronology; reject pre-order promise | RULE-PRM-001 |
| **Scenario 4** | Older revision overwrites newer revision | Detect sequence conflict; reject regressed revision | RULE-EVT-003 |

### Detection Performance against Ground Truth:
- **True Positives**: 4 / 4 (100%)
- **False Positives**: 0 (0%)
- **False Negatives**: 0 (0%)
- **Precision**: 1.0 (100.0%)
- **Recall**: 1.0 (100.0%)
- **F1 Score**: 1.0 (100.0%)

---

## 11. Automated Testing (pytest)

The project includes 30 automated tests in `tests/test_project.py` covering all core business requirements, negative scenarios, full-scale volume (>=10,000 POs and >10,000 business records), live operational exports, and invariant enforcement:

```cmd
python -m pytest tests/test_project.py -v
```

### Execution Output:
```
tests/test_project.py::test_01_deterministic_id_generation PASSED        [  3%]
tests/test_project.py::test_02_foreign_key_integrity PASSED              [  6%]
tests/test_project.py::test_03_partial_acknowledgement_handling PASSED   [ 10%]
tests/test_project.py::test_04_quantity_reconciliation PASSED            [ 13%]
tests/test_project.py::test_05_price_variance_calculation PASSED         [ 16%]
tests/test_project.py::test_06_delivery_delay_calculation PASSED         [ 20%]
tests/test_project.py::test_07_approval_thresholds PASSED                [ 23%]
tests/test_project.py::test_08_pending_changes_not_updating_projected_supply PASSED [ 26%]
tests/test_project.py::test_09_approved_changes_updating_plans_correctly PASSED [ 30%]
tests/test_project.py::test_10_rejected_changes_leaving_plans_unchanged PASSED [ 33%]
tests/test_project.py::test_11_duplicate_approval_prevention PASSED      [ 36%]
tests/test_project.py::test_12_transaction_rollback_on_failed_application PASSED [ 40%]
tests/test_project.py::test_13_revision_history_preservation PASSED      [ 43%]
tests/test_project.py::test_14_prevention_of_older_revision_overwrites PASSED [ 46%]
tests/test_project.py::test_15_downstream_shortage_calculations PASSED   [ 50%]
tests/test_project.py::test_16_supplier_silence_detection PASSED         [ 53%]
tests/test_project.py::test_17_all_four_required_negative_scenarios PASSED [ 56%]
tests/test_project.py::test_18_ground_truth_separation PASSED            [ 60%]
tests/test_project.py::test_19_fixed_seed_reproducibility PASSED         [ 63%]
tests/test_project.py::test_20_csv_and_json_export_integrity PASSED      [ 66%]
tests/test_project.py::test_21_csv_operational_export_endpoint PASSED    [ 70%]
tests/test_project.py::test_22_excel_operational_export_endpoint PASSED  [ 73%]
tests/test_project.py::test_23_filtered_operational_export PASSED        [ 76%]
tests/test_project.py::test_24_invalid_entity_export_rejected PASSED     [ 80%]
tests/test_project.py::test_25_unapproved_changes_supply_invariant_enforcement PASSED [ 83%]
tests/test_project.py::test_26_full_scale_generator_configuration_and_volume PASSED [ 86%]
tests/test_project.py::test_27_database_live_row_counts_meet_full_scale_volume PASSED [ 90%]
tests/test_project.py::test_28_data_quality_summary_endpoint_accuracy PASSED [ 93%]
tests/test_project.py::test_29_accidental_reseed_protection PASSED       [ 96%]
tests/test_project.py::test_30_synthetic_dataset_export_prefixed_and_valid PASSED [100%]

======================= 30 passed in 25.74s =======================
```

---

## 12. Operational Dataset Exporting (CSV and Genuine Excel .xlsx)

The application provides export capabilities directly accessible from both the UI tables and REST API:

### 12.1 Supported Entities:
- Purchase Orders (`purchase_orders`)
- Purchase Order Lines (`po_lines`)
- Acknowledgements (`acknowledgements`)
- Promise Dates (`promise_dates`)
- Change Requests (`change_requests`)
- Approvals (`approvals`)
- Inventory Plans (`inventory_plans`)
- Production Orders (`production_orders`)
- Schedule Impacts (`schedule_impacts`)
- Exception Records (`exception_records`)

### 12.2 Formats and Implementation:
- **CSV (`format=csv`)**: UTF-8 encoded text stream with RFC 4180 complaint escaping, headers, and standard MIME type `text/csv`.
- **Genuine Excel (`format=xlsx`)**: Built using `openpyxl`. Generates binary OpenXML workbook (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`) featuring:
  - Enterprise navy blue headers with white bold typography.
  - Thin cell borders.
  - Auto-fitted column widths based on cell text content.
  - Proper integer, float, and ISO date formatting.
  - Not a renamed CSV file; genuine `.xlsx` format verifiable with spreadsheet engines and openpyxl parser.
- **JSON (`format=json`)**: Standard REST array output.

### 12.3 Filtering and Modification Persistence:
- Exports query live database records (`source=db`), meaning any decisions made in the UI (approvals, rejections) are immediately reflected in downloaded exports.
- Table-level search and status filters (e.g., `status=OPEN` or `impact_status=CONFIRMED_SHORTAGE`) are preserved when exporting from UI action buttons.

### 12.4 API Endpoint Signature:
```http
GET /api/export/{entity_type}?format=csv|xlsx|json&source=db|synthetic&status={status}&search={search}
```

---

## 13. Reproducibility Verification

Reproducibility is tested by running dual independent generation cycles using seed `20261022` and comparing entity record counts and SHA256 checksums across all tables:

```cmd
python -c "from backend.services import run_reproducibility_test; rep = run_reproducibility_test(); print('Reproducible:', rep['overall_reproducible'])"
```
**Result**: 100% Match across all tables and derived decisions. Full report saved in `data/reproducibility_report.json`.

---

## 14. Data Dictionary

A comprehensive Data Dictionary is provided in [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md), documenting:
- All 10 core entities and auxiliary audit tables.
- Primary keys, foreign keys, and indexes.
- Data types, units, constraints, and validation rules.
- Distinction between original requested values, proposed supplier values, approved values, and effective projected supply.

---

## 15. Favicon and Legal Pages

- **Favicon**: Clean original enterprise graphic stored at `frontend/public/favicon.png`.
- **Privacy Policy**: Accessible via navigation and footer at `/privacy`. Real data practices, MySQL storage, exports, and local execution.
- **Terms and Conditions**: Accessible via navigation and footer at `/terms`. Intended usage, limitations of synthetic records, non-liability advisory.

---

## 16. Known Assumptions and Limitations

1. **Local Deployment**: Designed for local development on localhost before custom domain authorization.
2. **Deterministic Timeframe**: Synthetic records are centered around March to September 2026 to provide a realistic multi-month procurement timeline.
3. **Database Dependency**: MySQL 8.0 must be installed and running locally on port 3306.

---

## 17. Future Custom Domain Deployment Requirements

When authorized for public deployment with a custom domain:
1. Provision cloud hosting (e.g., Linux VM, container service, or managed Kubernetes).
2. Configure DNS records (A and CNAME records) pointing to reverse proxy ingress.
3. Configure reverse proxy (Nginx or Caddy) with automated TLS/SSL certificates (Let's Encrypt).
4. Update `CORS_ORIGINS` in backend configuration to include the verified domain.
5. Set `VITE_API_URL` to point to `https://api.yourcustomdomain.com/api`.

