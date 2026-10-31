import React from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import PurchaseOrders from './pages/PurchaseOrders';
import Acknowledgements from './pages/Acknowledgements';
import Approvals from './pages/Approvals';
import ScheduleImpact from './pages/ScheduleImpact';
import Exceptions from './pages/Exceptions';
import DataQuality from './pages/DataQuality';
import PrivacyPolicy from './pages/PrivacyPolicy';
import TermsAndConditions from './pages/TermsAndConditions';

export default function App() {
  return (
    <div className="d-flex flex-column min-vh-100">
      <Navbar />

      <main className="flex-grow-1">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/purchase-orders" element={<PurchaseOrders />} />
          <Route path="/acknowledgements" element={<Acknowledgements />} />
          <Route path="/approvals" element={<Approvals />} />
          <Route path="/schedule-impact" element={<ScheduleImpact />} />
          <Route path="/exceptions" element={<Exceptions />} />
          <Route path="/data-quality" element={<DataQuality />} />
          <Route path="/privacy" element={<PrivacyPolicy />} />
          <Route path="/terms" element={<TermsAndConditions />} />
        </Routes>
      </main>

      <footer className="footer-custom mt-auto">
        <div className="container-fluid px-4 d-flex flex-wrap justify-content-between align-items-center">
          <div>
            <span className="fw-semibold">Supplier Acknowledgement & Schedule Impact Manager</span> | Local Enterprise Edition
          </div>
          <div className="d-flex gap-3">
            <Link to="/privacy">Privacy Policy</Link>
            <Link to="/terms">Terms & Conditions</Link>
            <Link to="/data-quality">System Diagnostics</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}

