import React from 'react';

export default function StatusMessage({ type = 'info', message, onDismiss }) {
  if (!message) return null;

  const alertClassMap = {
    success: 'alert-success border-success text-success-emphasis',
    error: 'alert-danger border-danger text-danger-emphasis',
    warning: 'alert-warning border-warning text-warning-emphasis',
    info: 'alert-secondary border-secondary text-secondary-emphasis'
  };

  const alertClass = alertClassMap[type] || alertClassMap.info;

  return (
    <div className={`alert ${alertClass} d-flex justify-content-between align-items-center py-2 px-3 mb-3 rounded-1`} role="alert">
      <div className="small fw-semibold">{message}</div>
      {onDismiss && (
        <button type="button" className="btn-close btn-close-sm" aria-label="Close" onClick={onDismiss}></button>
      )}
    </div>
  );
}

