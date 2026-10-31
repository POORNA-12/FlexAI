import React from 'react';

export default function PrivacyPolicy() {
  return (
    <div className="container px-4 py-5" style={{ maxWidth: '850px' }}>
      <h3 className="fw-bold text-dark mb-2">PRIVACY POLICY</h3>
      <p className="text-muted small mb-4">Last Updated: October 30, 2026</p>

      <div className="bg-white border border-secondary-subtle rounded-1 p-4 mb-4">
        <h5 className="fw-bold mb-3">1. Scope and Architecture</h5>
        <p className="small text-muted mb-3">
          This application, the Supplier Acknowledgement and Schedule Impact Manager, operates as a standalone local
          system designed to simulate and manage procurement acknowledgement lifecycles, change requests, and downstream
          production order schedule impacts. This policy accurately reflects the technical data practices implemented in
          the software.
        </p>

        <h5 className="fw-bold mb-3">2. Synthetic Data Practices</h5>
        <p className="small text-muted mb-3">
          All supplier names, purchase orders, component specifications, prices, and acknowledgement records are
          synthetically generated using deterministic algorithms rooted in a fixed random seed (20261022). No real-world
          supplier commitments, proprietary commercial agreements, or customer personal data are imported, processed,
          or represented by the application.
        </p>

        <h5 className="fw-bold mb-3">3. Persistent Database Storage</h5>
        <p className="small text-muted mb-3">
          Operational records are stored locally in a relational MySQL database running on your local workstation. Data
          persisted includes supplier records, purchase order lines, acknowledgements, promised delivery dates, change
          requests, approval logs, and evaluation reports. All data remains within the local environment and is not
          transmitted to external servers.
        </p>

        <h5 className="fw-bold mb-3">4. User Inputs and Operational Actions</h5>
        <p className="small text-muted mb-3">
          When planners interactively submit approval decisions, reviewer identifiers (such as "PLN-001") and decision
          rationale comments are recorded alongside timestamps in the local database to support transactional auditability
          and prevent duplicate actions.
        </p>

        <h5 className="fw-bold mb-3">5. Exports and File Storage</h5>
        <p className="small text-muted mb-3">
          The application generates CSV and JSON export files stored in the local <code>data/</code> folder. These files
          contain generated procurement tables, validation summaries, reproducibility reports, and isolated ground truth
          records for evaluation.
        </p>

        <h5 className="fw-bold mb-3">6. Credentials and Configuration</h5>
        <p className="small text-muted mb-3">
          Database connection credentials and API server ports are managed exclusively through environment variables
          stored in a local <code>.env</code> file. Credentials are used solely for local database session management and
          are never exposed to the frontend React bundle or transmitted over network interfaces.
        </p>

        <h5 className="fw-bold mb-3">7. External Services and Telemetry</h5>
        <p className="small text-muted mb-0">
          This application contains no external analytics, third-party trackers, cloud telemetry endpoints, or marketing
          pixels. All request handling, calculation logic, and page rendering take place locally between your browser and
          the local FastAPI and MySQL services.
        </p>
      </div>
    </div>
  );
}

