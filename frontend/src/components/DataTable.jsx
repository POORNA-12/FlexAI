import React from 'react';

export default function DataTable({
  columns = [],
  data = [],
  loading = false,
  emptyMessage = "No records found matching criteria.",
  page = 1,
  totalPages = 1,
  totalRecords = 0,
  onPageChange
}) {
  if (loading) {
    return (
      <div className="state-container my-3">
        <div className="spinner-border spinner-border-sm text-secondary me-2" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
        <span className="state-desc">Loading records from server...</span>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="state-container my-3">
        <div className="state-title">No Records Available</div>
        <div className="state-desc">{emptyMessage}</div>
      </div>
    );
  }

  return (
    <div className="table-responsive bg-white border border-secondary-subtle rounded-1 mb-3">
      <table className="table table-custom table-hover mb-0">
        <thead>
          <tr>
            {columns.map((col, idx) => (
              <th key={idx} style={{ width: col.width || 'auto' }}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, rowIdx) => (
            <tr key={row.id || rowIdx}>
              {columns.map((col, colIdx) => (
                <td key={colIdx}>
                  {typeof col.accessor === 'function'
                    ? col.accessor(row)
                    : row[col.accessor] !== undefined && row[col.accessor] !== null
                    ? String(row[col.accessor])
                    : 'N/A'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>

      {totalPages > 1 && onPageChange && (
        <div className="d-flex justify-content-between align-items-center px-3 py-2 border-top bg-light text-muted small">
          <div>
            Page {page} of {totalPages} ({totalRecords} total records)
          </div>
          <div className="btn-group btn-group-sm">
            <button
              className="btn btn-enterprise btn-enterprise-secondary"
              disabled={page <= 1}
              onClick={() => onPageChange(page - 1)}
            >
              Previous
            </button>
            <button
              className="btn btn-enterprise btn-enterprise-secondary"
              disabled={page >= totalPages}
              onClick={() => onPageChange(page + 1)}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

