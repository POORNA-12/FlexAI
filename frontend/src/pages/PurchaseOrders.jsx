import React, { useState, useEffect } from 'react';
import { api } from '../api';
import DataTable from '../components/DataTable';
import StatusMessage from '../components/StatusMessage';

export default function PurchaseOrders() {
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
  const [selectedPO, setSelectedPO] = useState(null);

  useEffect(() => {
    loadOrders();
  }, [page, status]);

  const loadOrders = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = { page, page_size: pageSize };
      if (search) params.search = search;
      if (status) params.status = status;

      const res = await api.getPurchaseOrders(params);
      setData(res.items);
      setTotal(res.total);
      setTotalPages(res.total_pages);
    } catch (err) {
      setError(err.message || 'Failed to retrieve purchase orders.');
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
      const res = await api.downloadExport('purchase_orders', format, params);
      setSuccess(`Exported ${res.filename} successfully.`);
    } catch (err) {
      setError(err.message || `Failed to export purchase orders as ${format.toUpperCase()}.`);
    } finally {
      setExporting(false);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    loadOrders();
  };

  const getStatusBadge = (st) => {
    const map = {
      OPEN: 'badge-open',
      ACKNOWLEDGED: 'badge-acknowledged',
      CHANGE_PENDING: 'badge-pending',
      APPROVED: 'badge-approved',
      REJECTED: 'badge-rejected',
      CLOSED: 'badge-active'
    };
    return <span className={`badge-status ${map[st] || 'badge-open'}`}>{st}</span>;
  };

  const columns = [
    { header: 'PO ID', accessor: 'po_id', width: '15%' },
    { header: 'Supplier ID', accessor: 'supplier_id', width: '15%' },
    { header: 'Order Date', accessor: 'order_date', width: '15%' },
    {
      header: 'Total Amount',
      accessor: (row) => `$${row.total_amount?.toLocaleString(undefined, { minimumFractionDigits: 2 })}`,
      width: '15%'
    },
    {
      header: 'Status',
      accessor: (row) => getStatusBadge(row.status),
      width: '15%'
    },
    {
      header: 'Lines Count',
      accessor: (row) => `${row.lines?.length || 0} line(s)`,
      width: '12%'
    },
    {
      header: 'Action',
      accessor: (row) => (
        <button
          className="btn btn-enterprise btn-enterprise-secondary btn-sm"
          onClick={() => setSelectedPO(row)}
        >
          View Details
        </button>
      ),
      width: '13%'
    }
  ];

  return (
    <div className="container-fluid px-4 py-4">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h4 className="fw-bold text-dark mb-1">PURCHASE ORDERS</h4>
          <p className="text-muted small mb-0">
            Comprehensive purchase order registry with line item allocations and supplier response states.
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
              placeholder="Search PO or Supplier ID..."
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
              <option value="">All Statuses</option>
              <option value="OPEN">OPEN</option>
              <option value="ACKNOWLEDGED">ACKNOWLEDGED</option>
              <option value="CHANGE_PENDING">CHANGE_PENDING</option>
              <option value="APPROVED">APPROVED</option>
              <option value="REJECTED">REJECTED</option>
              <option value="CLOSED">CLOSED</option>
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

      {/* Detail Modal */}
      {selectedPO && (
        <div className="modal d-block" tabIndex="-1" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-lg modal-dialog-centered">
            <div className="modal-content rounded-1">
              <div className="modal-header py-2 px-3 bg-light border-bottom">
                <h6 className="modal-title fw-bold">Purchase Order Details: {selectedPO.po_id}</h6>
                <button
                  type="button"
                  className="btn-close btn-sm"
                  aria-label="Close"
                  onClick={() => setSelectedPO(null)}
                ></button>
              </div>
              <div className="modal-body p-3">
                <div className="row g-2 mb-3 small">
                  <div className="col-sm-4">
                    <span className="text-muted">Supplier ID:</span>{' '}
                    <span className="fw-semibold">{selectedPO.supplier_id}</span>
                  </div>
                  <div className="col-sm-4">
                    <span className="text-muted">Order Date:</span>{' '}
                    <span className="fw-semibold">{selectedPO.order_date}</span>
                  </div>
                  <div className="col-sm-4">
                    <span className="text-muted">Status:</span>{' '}
                    {getStatusBadge(selectedPO.status)}
                  </div>
                </div>

                <h6 className="fw-bold small mb-2 border-bottom pb-1">Order Lines</h6>
                <div className="table-responsive">
                  <table className="table table-custom table-sm mb-0">
                    <thead>
                      <tr>
                        <th>Line ID</th>
                        <th>Item ID</th>
                        <th>Ordered Qty</th>
                        <th>Unit Price</th>
                        <th>Requested Date</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedPO.lines && selectedPO.lines.length > 0 ? (
                        selectedPO.lines.map((l) => (
                          <tr key={l.po_line_id}>
                            <td className="font-monospace">{l.po_line_id}</td>
                            <td>{l.item_id}</td>
                            <td className="fw-semibold">{l.ordered_qty}</td>
                            <td>${l.unit_price?.toFixed(2)}</td>
                            <td>{l.requested_delivery_date}</td>
                            <td>{getStatusBadge(l.status)}</td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan="6" className="text-center text-muted">
                            No lines found for this order.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
              <div className="modal-footer py-2 px-3 border-top">
                <button
                  type="button"
                  className="btn btn-enterprise btn-enterprise-secondary btn-sm"
                  onClick={() => setSelectedPO(null)}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

