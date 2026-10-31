import React, { useState, useEffect } from 'react';
import { api } from '../api';
import DataTable from '../components/DataTable';
import StatusMessage from '../components/StatusMessage';

export default function Approvals() {
  const [data, setData] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [totalPages, setTotalPages] = useState(1);
  const [status, setStatus] = useState('');
  const [changeType, setChangeType] = useState('');
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Action Modal State
  const [actionTarget, setActionTarget] = useState(null);
  const [actionType, setActionType] = useState('APPROVE'); // 'APPROVE' or 'REJECT'
  const [comments, setComments] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadChangeRequests();
  }, [page, status, changeType]);

  const loadChangeRequests = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = { page, page_size: pageSize };
      if (status) params.status = status;
      if (changeType) params.change_type = changeType;

      const res = await api.getChangeRequests(params);
      setData(res.items);
      setTotal(res.total);
      setTotalPages(res.total_pages);
    } catch (err) {
      setError(err.message || 'Failed to retrieve change requests.');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenAction = (chg, type) => {
    setActionTarget(chg);
    setActionType(type);
    setComments(type === 'APPROVE' ? 'Approved by operations planner.' : 'Rejected due to supply conflict.');
  };

  const handleExecuteAction = async () => {
    if (!actionTarget) return;
    setSubmitting(true);
    setError(null);
    setSuccess(null);

    try {
      if (actionType === 'APPROVE') {
        const res = await api.approveChangeRequest(actionTarget.change_id, {
          reviewer_id: 'PLN-001',
          comments
        });
        setSuccess(res.message);
      } else {
        const res = await api.rejectChangeRequest(actionTarget.change_id, {
          reviewer_id: 'PLN-001',
          comments
        });
        setSuccess(res.message);
      }
      setActionTarget(null);
      loadChangeRequests();
    } catch (err) {
      setError(err.message || 'Operation failed.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleExport = async (format) => {
    setExporting(true);
    setError(null);
    setSuccess(null);
    try {
      const params = {};
      if (status) params.status = status;
      if (changeType) params.change_type = changeType;
      const res = await api.downloadExport('change_requests', format, params);
      setSuccess(`Exported ${res.filename} successfully.`);
    } catch (err) {
      setError(err.message || `Failed to export change requests as ${format.toUpperCase()}.`);
    } finally {
      setExporting(false);
    }
  };

  const getStatusBadge = (st) => {
    const map = {
      PENDING_APPROVAL: 'badge-pending',
      APPROVED: 'badge-approved',
      REJECTED: 'badge-rejected',
      APPLIED: 'badge-applied',
      SUPERSEDED: 'badge-open'
    };
    return <span className={`badge-status ${map[st] || 'badge-open'}`}>{st}</span>;
  };

  const calculateVariance = (row) => {
    if (row.change_type === 'QUANTITY') {
      const orig = parseFloat(row.old_value);
      const prop = parseFloat(row.new_value);
      if (orig > 0) {
        const diff = ((prop - orig) / orig) * 100;
        return `${diff > 0 ? '+' : ''}${diff.toFixed(1)}%`;
      }
    }
    if (row.change_type === 'DELIVERY_DATE') {
      const d1 = new Date(row.old_value);
      const d2 = new Date(row.new_value);
      const diffDays = Math.round((d2 - d1) / (1000 * 60 * 60 * 24));
      return `${diffDays > 0 ? '+' : ''}${diffDays} day(s)`;
    }
    return 'N/A';
  };

  const columns = [
    { header: 'Change ID', accessor: 'change_id', width: '16%' },
    { header: 'PO Line ID', accessor: 'po_line_id', width: '16%' },
    { header: 'Type', accessor: 'change_type', width: '10%' },
    { header: 'Original', accessor: 'old_value', width: '10%' },
    { header: 'Proposed', accessor: 'new_value', width: '10%' },
    {
      header: 'Variance',
      accessor: (row) => <span className="fw-semibold">{calculateVariance(row)}</span>,
      width: '10%'
    },
    {
      header: 'Status',
      accessor: (row) => getStatusBadge(row.status),
      width: '13%'
    },
    {
      header: 'Actions',
      accessor: (row) => {
        if (row.status === 'PENDING_APPROVAL') {
          return (
            <div className="btn-group btn-group-sm">
              <button
                className="btn btn-enterprise btn-enterprise-success btn-sm me-1"
                onClick={() => handleOpenAction(row, 'APPROVE')}
              >
                Approve
              </button>
              <button
                className="btn btn-enterprise btn-enterprise-danger btn-sm"
                onClick={() => handleOpenAction(row, 'REJECT')}
              >
                Reject
              </button>
            </div>
          );
        }
        return <span className="text-muted small">Decided</span>;
      },
      width: '15%'
    }
  ];

  return (
    <div className="container-fluid px-4 py-4">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h4 className="fw-bold text-dark mb-1">CHANGE REQUESTS & APPROVALS</h4>
          <p className="text-muted small mb-0">
            Review proposed supplier quantity, price, and schedule changes. Enforce transactional approval safeguards.
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

      {/* Filter Bar */}
      <div className="filter-bar">
        <div className="row g-2 align-items-center">
          <div className="col-auto">
            <select
              className="form-select form-select-sm"
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All Statuses</option>
              <option value="PENDING_APPROVAL">PENDING_APPROVAL</option>
              <option value="APPROVED">APPROVED</option>
              <option value="REJECTED">REJECTED</option>
              <option value="APPLIED">APPLIED</option>
            </select>
          </div>
          <div className="col-auto">
            <select
              className="form-select form-select-sm"
              value={changeType}
              onChange={(e) => {
                setChangeType(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All Change Types</option>
              <option value="QUANTITY">QUANTITY</option>
              <option value="DELIVERY_DATE">DELIVERY_DATE</option>
              <option value="PRICE">PRICE</option>
            </select>
          </div>
          <div className="col-auto ms-auto text-muted small">
            Approval Policy: Only approved changes update projected supply plans.
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

      {/* Action Confirmation Modal */}
      {actionTarget && (
        <div className="modal d-block" tabIndex="-1" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content rounded-1">
              <div className="modal-header py-2 px-3 bg-light border-bottom">
                <h6 className="modal-title fw-bold">
                  {actionType === 'APPROVE' ? 'Confirm Approval' : 'Confirm Rejection'}: {actionTarget.change_id}
                </h6>
                <button
                  type="button"
                  className="btn-close btn-sm"
                  aria-label="Close"
                  onClick={() => setActionTarget(null)}
                ></button>
              </div>
              <div className="modal-body p-3">
                <p className="small mb-2">
                  {actionType === 'APPROVE' ? (
                    <span>
                      Approving this change will <strong>update the inventory plan projected supply</strong> to{' '}
                      <strong>{actionTarget.new_value}</strong> and recalculate downstream schedule impacts.
                    </span>
                  ) : (
                    <span>
                      Rejecting this change will preserve original values. The existing inventory plan will{' '}
                      <strong>remain unchanged</strong>.
                    </span>
                  )}
                </p>

                <div className="mb-3">
                  <label className="form-label small fw-semibold text-muted">Reviewer Comments / Rationale</label>
                  <textarea
                    className="form-control form-control-sm"
                    rows="3"
                    value={comments}
                    onChange={(e) => setComments(e.target.value)}
                  ></textarea>
                </div>
              </div>
              <div className="modal-footer py-2 px-3 border-top">
                <button
                  type="button"
                  className="btn btn-enterprise btn-enterprise-secondary btn-sm"
                  onClick={() => setActionTarget(null)}
                  disabled={submitting}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className={`btn btn-enterprise btn-sm ${
                    actionType === 'APPROVE' ? 'btn-enterprise-success' : 'btn-enterprise-danger'
                  }`}
                  onClick={handleExecuteAction}
                  disabled={submitting}
                >
                  {submitting ? 'Processing...' : actionType === 'APPROVE' ? 'Confirm Approval' : 'Confirm Rejection'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

