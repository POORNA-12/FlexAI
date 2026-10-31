import React, { useState, useEffect } from 'react';
import { api } from '../api';
import DataTable from '../components/DataTable';
import StatusMessage from '../components/StatusMessage';

export default function Exceptions() {
  const [data, setData] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [totalPages, setTotalPages] = useState(1);
  const [issueType, setIssueType] = useState('');
  const [severity, setSeverity] = useState('');
  const [isResolved, setIsResolved] = useState('');
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    loadExceptions();
  }, [page, issueType, severity, isResolved]);

  const loadExceptions = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = { page, page_size: pageSize };
      if (issueType) params.issue_type = issueType;
      if (severity) params.severity = severity;
      if (isResolved !== '') params.is_resolved = isResolved === 'true';

      const res = await api.getExceptions(params);
      setData(res.items);
      setTotal(res.total);
      setTotalPages(res.total_pages);
    } catch (err) {
      setError(err.message || 'Failed to retrieve exception records.');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format) => {
    setExporting(true);
    setError(null);
    setSuccess(null);
    try {
      const params = {};
      if (issueType) params.issue_type = issueType;
      if (severity) params.severity = severity;
      if (isResolved !== '') params.is_resolved = isResolved === 'true';
      const res = await api.downloadExport('exceptions', format, params);
      setSuccess(`Exported ${res.filename} successfully.`);
    } catch (err) {
      setError(err.message || `Failed to export exceptions as ${format.toUpperCase()}.`);
    } finally {
      setExporting(false);
    }
  };

  const handleResolve = async (id) => {
    setError(null);
    setSuccess(null);
    try {
      await api.resolveException(id);
      setSuccess(`Exception ${id} marked as resolved.`);
      loadExceptions();
    } catch (err) {
      setError(err.message || 'Failed to resolve exception.');
    }
  };

  const getSeverityBadge = (sev) => {
    const map = {
      CRITICAL: 'badge-critical',
      HIGH: 'badge-rejected',
      WARNING: 'badge-pending',
      INFO: 'badge-applied'
    };
    return <span className={`badge-status ${map[sev] || 'badge-open'}`}>{sev}</span>;
  };

  const columns = [
    { header: 'Exception ID', accessor: 'exception_id', width: '15%' },
    { header: 'Record ID', accessor: 'record_id', width: '16%' },
    { header: 'Entity', accessor: 'entity_type', width: '12%' },
    { header: 'Issue Type', accessor: 'issue_type', width: '20%' },
    {
      header: 'Severity',
      accessor: (row) => getSeverityBadge(row.severity),
      width: '10%'
    },
    { header: 'Description', accessor: 'description', width: '27%' },
    {
      header: 'Status',
      accessor: (row) =>
        row.is_resolved ? (
          <span className="badge-status badge-active">RESOLVED</span>
        ) : (
          <button
            className="btn btn-enterprise btn-enterprise-secondary btn-sm"
            onClick={() => handleResolve(row.exception_id)}
          >
            Resolve
          </button>
        ),
      width: '10%'
    }
  ];

  return (
    <div className="container-fluid px-4 py-4">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h4 className="fw-bold text-dark mb-1">EXCEPTION MANAGEMENT</h4>
          <p className="text-muted small mb-0">
            Real-time audit log of rule violations, relational inconsistencies, and injected anomaly scenarios.
          </p>
        </div>
        <div className="btn-group btn-group-sm">
          <button
            className="btn btn-enterprise btn-enterprise-secondary"
            onClick={() => handleExport('csv')}
            disabled={exporting}
          >
            {exporting ? 'Exporting...' : 'Download CSV'}
          </button>
          <button
            className="btn btn-enterprise btn-enterprise-primary"
            onClick={() => handleExport('xlsx')}
            disabled={exporting}
          >
            {exporting ? 'Exporting...' : 'Download Excel'}
          </button>
        </div>
      </div>

      <StatusMessage type="success" message={success} onDismiss={() => setSuccess(null)} />
      <StatusMessage type="error" message={error} onDismiss={() => setError(null)} />

      {/* Mandatory Scenario Highlights */}
      <div className="row g-3 mb-4">
        <div className="col-md-3">
          <div className="bg-white border border-danger-subtle p-3 rounded-1 h-100">
            <span className="badge-status badge-critical mb-2">SCENARIO 1</span>
            <div className="fw-bold small text-dark">Unapproved Plan Update</div>
            <p className="text-muted small mb-0 mt-1">
              Detects when an inventory plan was modified by a change request that is still pending or was rejected.
            </p>
          </div>
        </div>
        <div className="col-md-3">
          <div className="bg-white border border-warning-subtle p-3 rounded-1 h-100">
            <span className="badge-status badge-pending mb-2">SCENARIO 2</span>
            <div className="fw-bold small text-dark">Mismatched PO Line Ref</div>
            <p className="text-muted small mb-0 mt-1">
              Detects an acknowledgement referencing a line belonging to a foreign purchase order.
            </p>
          </div>
        </div>
        <div className="col-md-3">
          <div className="bg-white border border-warning-subtle p-3 rounded-1 h-100">
            <span className="badge-status badge-pending mb-2">SCENARIO 3</span>
            <div className="fw-bold small text-dark">Pre-Order Promise Date</div>
            <p className="text-muted small mb-0 mt-1">
              Detects a promised delivery date that is chronologically earlier than the purchase order order date.
            </p>
          </div>
        </div>
        <div className="col-md-3">
          <div className="bg-white border border-danger-subtle p-3 rounded-1 h-100">
            <span className="badge-status badge-critical mb-2">SCENARIO 4</span>
            <div className="fw-bold small text-dark">Revision Sequence Conflict</div>
            <p className="text-muted small mb-0 mt-1">
              Detects an out-of-order or regressed revision number attempting to overwrite a newer valid record.
            </p>
          </div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="filter-bar">
        <div className="row g-2 align-items-center">
          <div className="col-auto">
            <select
              className="form-select form-select-sm"
              value={issueType}
              onChange={(e) => {
                setIssueType(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All Issue Types</option>
              <option value="unapproved_change_updates_plan">unapproved_change_updates_plan</option>
              <option value="ack_wrong_po_line">ack_wrong_po_line</option>
              <option value="promise_before_order_date">promise_before_order_date</option>
              <option value="older_revision_overwrites_newer">older_revision_overwrites_newer</option>
            </select>
          </div>
          <div className="col-auto">
            <select
              className="form-select form-select-sm"
              value={severity}
              onChange={(e) => {
                setSeverity(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All Severities</option>
              <option value="CRITICAL">CRITICAL</option>
              <option value="HIGH">HIGH</option>
              <option value="WARNING">WARNING</option>
            </select>
          </div>
          <div className="col-auto">
            <select
              className="form-select form-select-sm"
              value={isResolved}
              onChange={(e) => {
                setIsResolved(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All Resolution States</option>
              <option value="false">Open (Unresolved)</option>
              <option value="true">Resolved</option>
            </select>
          </div>
        </div>
      </div>

      <DataTable
        columns={columns}
        data={data}
        loading={loading}
        page={page}
        totalPages={totalPages}
        totalRecords={total}
        onPageChange={(p) => setPage(p)}
      />
    </div>
  );
}

