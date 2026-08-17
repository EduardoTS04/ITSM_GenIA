import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import IncidentList from './pages/IncidentList';
import CreateTicket from './pages/CreateTicket';
import TicketDetail from './pages/TicketDetail';

export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route path="/" element={<IncidentList />} />
        <Route path="/incidents" element={<IncidentList />} />
        <Route path="/create" element={<CreateTicket />} />
        <Route path="/tickets/:id" element={<TicketDetail />} />
        {/* Catch-all → redirect to home */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

