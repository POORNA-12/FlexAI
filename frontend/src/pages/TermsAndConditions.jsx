import React from 'react';

export default function TermsAndConditions() {
  return (
    <div className="container px-4 py-5" style={{ maxWidth: '850px' }}>
      <h3 className="fw-bold text-dark mb-2">TERMS AND CONDITIONS</h3>
      <p className="text-muted small mb-4">Last Updated: October 30, 2026</p>

      <div className="bg-white border border-secondary-subtle rounded-1 p-4 mb-4">
        <h5 className="fw-bold mb-3">1. Purpose and Intended Use</h5>
        <p className="small text-muted mb-3">
          The Supplier Acknowledgement and Schedule Impact Manager is provided as software for supply chain planning
          demonstrations, academic evaluations, architectural benchmarks, and data reconciliation testing. It is designed
          to demonstrate how supplier quantity adjustments, delivery delays, and approval workflows interact with
          projected inventory and downstream manufacturing orders.
        </p>

        <h5 className="fw-bold mb-3">2. Limitations of Synthetic Data</h5>
        <p className="small text-muted mb-3">
          Users acknowledge that all generated suppliers, purchase order identifiers, parts, pricing figures, and
          promised delivery dates are strictly synthetic. They do not constitute actual legal commitments, commercial
          binding contracts, or genuine logistics schedules.
        </p>

        <h5 className="fw-bold mb-3">3. Production Advisory and Verification</h5>
        <p className="small text-muted mb-3">
          Before applying business logic, variance calculations, or approval rules from this application in a commercial
          or physical manufacturing environment, all calculations, safety stock models, and supplier lead times must be
          independently reviewed and verified against enterprise operational policies.
        </p>

        <h5 className="fw-bold mb-3">4. Development Status</h5>
        <p className="small text-muted mb-3">
          This system is provided in its current development state for local testing. While it implements transactional
          safety and validation checks, the developers provide no express warranties regarding suitability for physical
          logistics, safety-critical assembly operations, or production ERP synchronization.
        </p>

        <h5 className="fw-bold mb-3">5. Intellectual Property and Open Architecture</h5>
        <p className="small text-muted mb-0">
          The codebase, relational schemas, synthetic data generators, and validation suites are developed with open
          standard tools (React, FastAPI, SQLAlchemy, MySQL, Bootstrap 5). Users are free to inspect, modify, and extend
          the logic for organizational testing.
        </p>
      </div>
    </div>
  );
}

