import React, { useState, useEffect } from 'react';
import { api } from '../api';
import DataTable from '../components/DataTable';
import StatusMessage from '../components/StatusMessage';

export default function ScheduleImpact() {
  const [data, setData] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [totalPages, setTotalPages] = useState(1);
  const [impactStatus, setImpactStatus] = useState('');
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    loadImpacts();
  }, [page, impactStatus]);

  const loadImpacts = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = { page, page_size: pageSize };
      if (impactStatus) params.impact_status = impactStatus;

      const res = await api.getScheduleImpacts(params);
      setData(res.items);
      setTotal(res.total);
      setTotalPages(res.total_pages);
    } catch (err) {
      setError(err.message || 'Failed to retrieve schedule impact records.');
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
      if (impactStatus) params.impact_status = impactStatus;
      const res = await api.downloadExport('schedule_impacts', format, params);
      setSuccess(`Exported ${res.filename} successfully.`);
    } catch (err) {
      setError(err.message || `Failed to export schedule impacts as ${format.toUpperCase()}.`);
    } finally {
      setExporting(false);
    }
  };

  const getStatusBadge = (st) => {
    const map = {
      ON_TIME: 'badge-on-time',
      POTENTIAL_SHORTAGE: 'badge-potential-shortage',
      CONFIRMED_SHORTAGE: 'badge-confirmed-shortage',
      SCHEDULE_CONFLICT: 'badge-schedule-conflict'
    };
    return <span className={`badge-status ${map[st] || 'badge-open'}`}>{st}</span>;
  };

  const columns = [
    { header: 'Impact ID', accessor: 'impact_id', width: '15%' },
    { header: 'Production Order', accessor: 'production_order_id', width: '13%' },
    { header: 'PO Line', accessor: 'po_line_id', width: '13%' },
    { header: 'Required Qty', accessor: 'required_qty', width: '9%' },
    { header: 'Available Stock', accessor: 'available_inventory', width: '9%' },
    { header: 'Projected Supply', accessor: 'projected_supply', width: '9%' },
    {
      header: 'Shortage Qty',
      accessor: (row) => (
        <span className={row.shortage_qty > 0 ? 'fw-bold text-danger' : 'text-muted'}>
          {row.shortage_qty}
        </span>
      ),
      width: '9%'
    },
    {
      header: 'Promised Delivery',
      accessor: 'current_promised_date',
      width: '11%'
    },
    {
      header: 'Slip Days',
      accessor: (row) => (
        <span className={row.delay_days > 0 ? 'text-danger fw-semibold' : 'text-muted'}>
          {row.delay_days > 0 ? `+${row.delay_days}d` : '0d'}
        </span>
      ),
      width: '7%'
    },
    {
      header: 'Impact Status',
      accessor: (row) => getStatusBadge(row.impact_status),
      width: '15%'
    }
  ];

  return (
    <div className="container-fluid px-4 py-4">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h4 className="fw-bold text-dark mb-1">DOWNSTREAM SCHEDULE IMPACT</h4>
          <p className="text-muted small mb-0">
            Reconciliation of manufacturing work order requirements against projected supplier deliveries.
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
              value={impactStatus}
              onChange={(e) => {
                setImpactStatus(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All Impact Statuses</option>
              <option value="ON_TIME">ON_TIME</option>
              <option value="POTENTIAL_SHORTAGE">POTENTIAL_SHORTAGE</option>
              <option value="CONFIRMED_SHORTAGE">CONFIRMED_SHORTAGE</option>
              <option value="SCHEDULE_CONFLICT">SCHEDULE_CONFLICT</option>
            </select>
          </div>
          <div className="col-auto ms-auto text-muted small">
            Calculation: Shortage = max(0, Required - (Available + Usable Projected Supply))
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

