import React, { useState, useEffect } from 'react';
import { api } from '../api';
import DataTable from '../components/DataTable';
import StatusMessage from '../components/StatusMessage';

export default function Acknowledgements() {
  const [data, setData] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [totalPages, setTotalPages] = useState(1);
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    loadAcknowledgements();
  }, [page, status]);

  const loadAcknowledgements = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = { page, page_size: pageSize };
      if (search) params.search = search;
      if (status) params.status = status;

      const res = await api.getAcknowledgements(params);
      setData(res.items);
      setTotal(res.total);
      setTotalPages(res.total_pages);
    } catch (err) {
      setError(err.message || 'Failed to retrieve supplier acknowledgements.');
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
      if (search) params.search = search;
      if (status) params.status = status;
      const res = await api.downloadExport('acknowledgements', format, params);
      setSuccess(`Exported ${res.filename} successfully.`);
    } catch (err) {
      setError(err.message || `Failed to export acknowledgements as ${format.toUpperCase()}.`);
    } finally {
      setExporting(false);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    loadAcknowledgements();
  };

  const getStatusBadge = (st) => {
    const map = {
      FULL_ACCEPTANCE: 'badge-full-acceptance',
      PARTIAL_ACCEPTANCE: 'badge-partial-acceptance',
      REJECTED: 'badge-rejected',
      CHANGE_PROPOSED: 'badge-change-proposed'
    };
    return <span className={`badge-status ${map[st] || 'badge-open'}`}>{st}</span>;
  };

  const columns = [
    { header: 'Ack ID', accessor: 'ack_id', width: '18%' },
    { header: 'PO Line ID', accessor: 'po_line_id', width: '18%' },
    { header: 'Rev', accessor: (row) => `Rev ${row.revision_no}`, width: '8%' },
    {
      header: 'Accepted Qty',
      accessor: (row) => <span className="fw-semibold text-success">{row.accepted_qty}</span>,
      width: '12%'
    },
    {
      header: 'Rejected Qty',
      accessor: (row) => (
        <span className={row.rejected_qty > 0 ? 'fw-semibold text-danger' : 'text-muted'}>
          {row.rejected_qty}
        </span>
      ),
      width: '12%'
    },
    { header: 'Ack Date', accessor: 'acknowledgement_date', width: '12%' },
    {
      header: 'Promised Delivery',
      accessor: (row) => {
        const prm = row.promise_dates?.[0];
        return prm ? prm.promised_date : 'N/A';
      },
      width: '14%'
    },
    {
      header: 'Status',
      accessor: (row) => getStatusBadge(row.status),
      width: '16%'
    }
  ];

  return (
    <div className="container-fluid px-4 py-4">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h4 className="fw-bold text-dark mb-1">SUPPLIER ACKNOWLEDGEMENTS</h4>
          <p className="text-muted small mb-0">
            Supplier response tracking, promised delivery dates, partial fulfillment commitments, and revision history.
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
        <form className="row g-2 align-items-center" onSubmit={handleSearchSubmit}>
          <div className="col-auto">
            <input
              type="text"
              className="form-control form-control-sm"
              placeholder="Search Ack or PO Line ID..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div className="col-auto">
            <select
              className="form-select form-select-sm"
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All Response Types</option>
              <option value="FULL_ACCEPTANCE">FULL_ACCEPTANCE</option>
              <option value="PARTIAL_ACCEPTANCE">PARTIAL_ACCEPTANCE</option>
              <option value="REJECTED">REJECTED</option>
              <option value="CHANGE_PROPOSED">CHANGE_PROPOSED</option>
            </select>
          </div>
          <div className="col-auto">
            <button type="submit" className="btn btn-enterprise btn-enterprise-primary btn-sm">
              Search
            </button>
          </div>
        </form>
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

