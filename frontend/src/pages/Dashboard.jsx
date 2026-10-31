import React, { useState, useEffect } from 'react';
import { api } from '../api';
import StatusMessage from '../components/StatusMessage';

export default function Dashboard() {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadMetrics();
  }, []);

  const loadMetrics = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getDashboardMetrics();
      setMetrics(data);
    } catch (err) {
      setError(err.message || 'Failed to connect to backend service.');
    } finally {
      setLoading(false);
    }
  };

  const metricItems = [
    { key: 'total_purchase_orders', label: 'Total Purchase Orders', value: metrics?.total_purchase_orders, unit: '' },
    { key: 'total_suppliers', label: 'Active Suppliers', value: metrics?.total_suppliers, unit: '' },
    { key: 'acknowledgement_coverage_pct', label: 'Acknowledgement Coverage', value: metrics?.acknowledgement_coverage_pct, unit: '%' },
    { key: 'pending_approvals', label: 'Pending Approvals', value: metrics?.pending_approvals, unit: '' },
    { key: 'approved_changes', label: 'Approved Changes', value: metrics?.approved_changes, unit: '' },
    { key: 'rejected_changes', label: 'Rejected Changes', value: metrics?.rejected_changes, unit: '' },
    { key: 'delayed_purchase_orders', label: 'Delayed Deliveries', value: metrics?.delayed_purchase_orders, unit: '' },
    { key: 'open_exceptions', label: 'Open Exceptions', value: metrics?.open_exceptions, unit: '' },
    { key: 'projected_supply_shortages', label: 'Supply Shortages', value: metrics?.projected_supply_shortages, unit: '' },
    { key: 'affected_production_orders', label: 'Affected Production Orders', value: metrics?.affected_production_orders, unit: '' },
  ];

  return (
    <div className="container-fluid px-4 py-4">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h4 className="fw-bold text-dark mb-1">OPERATIONS DASHBOARD</h4>
          <p className="text-muted small mb-0">
            Real-time procurement tracking, supplier acknowledgement status, and downstream production risks.
          </p>
        </div>
        <button
          className="btn btn-enterprise btn-enterprise-secondary"
          onClick={loadMetrics}
          disabled={loading}
        >
          {loading ? 'Refreshing...' : 'Refresh Metrics'}
        </button>
      </div>

      <StatusMessage type="error" message={error} onDismiss={() => setError(null)} />

      {loading ? (
        <div className="state-container">
          <div className="spinner-border spinner-border-sm text-secondary me-2" role="status"></div>
          <span className="state-desc">Calculating real-time database metrics...</span>
        </div>
      ) : (
        <>
          <div className="row g-3 mb-4">
            {metricItems.map((item) => (
              <div key={item.key} className="col-12 col-sm-6 col-md-4 col-xl">
                <div className="metric-card h-100">
                  <div className="metric-label">{item.label}</div>
                  <div className="metric-value">
                    {item.value !== undefined && item.value !== null ? `${item.value}${item.unit}` : '0'}
                  </div>
                  <div className="metric-formula">
                    {metrics?.metrics_documentation?.[item.key] || 'Calculated from database records'}
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="row g-4">
            <div className="col-lg-6">
              <div className="bg-white border border-secondary-subtle rounded-1 p-3">
                <h6 className="fw-bold mb-2">Workflow Status Overview</h6>
                <p className="text-muted small mb-3">
                  Summary of current procurement pipeline and supply chain reconciliation states.
                </p>
                <ul className="list-group list-group-flush small">
                  <li className="list-group-item d-flex justify-content-between align-items-center px-0 py-2">
                    <span>Purchase Orders Acknowledged</span>
                    <span className="fw-semibold">{metrics?.acknowledgement_coverage_pct}%</span>
                  </li>
                  <li className="list-group-item d-flex justify-content-between align-items-center px-0 py-2">
                    <span>Pending Supplier Changes Requiring Review</span>
                    <span className="badge-status badge-pending">{metrics?.pending_approvals} PENDING</span>
                  </li>
                  <li className="list-group-item d-flex justify-content-between align-items-center px-0 py-2">
                    <span>Delayed Purchase Orders Impacting Timeline</span>
                    <span className="badge-status badge-rejected">{metrics?.delayed_purchase_orders} DELAYED</span>
                  </li>
                  <li className="list-group-item d-flex justify-content-between align-items-center px-0 py-2">
                    <span>Open Anomalies & Exception Records</span>
                    <span className="badge-status badge-rejected">{metrics?.open_exceptions} OPEN</span>
                  </li>
                </ul>
              </div>
            </div>

            <div className="col-lg-6">
              <div className="bg-white border border-secondary-subtle rounded-1 p-3">
                <h6 className="fw-bold mb-2">Enterprise Business Invariant Verification</h6>
                <p className="text-muted small mb-3">
                  System policy safeguards preventing unauthorized projected supply updates.
                </p>
                <div className="border border-secondary-subtle rounded-1 p-2 mb-2 bg-light">
                  <div className="fw-semibold small text-dark">Rule 1: Unapproved Supply Protection</div>
                  <div className="text-muted small">
                    Pending supplier change requests do NOT update projected supply until explicitly approved by an authorized planner.
                  </div>
                </div>
                <div className="border border-secondary-subtle rounded-1 p-2 mb-2 bg-light">
                  <div className="fw-semibold small text-dark">Rule 2: Revision Monotonicity</div>
                  <div className="text-muted small">
                    Older revisions cannot supersede newer valid records. Revisions must increase sequentially.
                  </div>
                </div>
                <div className="border border-secondary-subtle rounded-1 p-2 bg-light">
                  <div className="fw-semibold small text-dark">Rule 3: Deterministic Downstream Impact</div>
                  <div className="text-muted small">
                    Shortages and schedule conflicts are calculated strictly based on available stock, usable supply, and required dates.
                  </div>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

