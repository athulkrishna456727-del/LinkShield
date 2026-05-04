import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Toaster } from './components/ui/sonner';
import '@/App.css';

import Landing from './pages/Landing';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Dashboard from './pages/Dashboard';
import Scan from './pages/Scan';
import ScanResult from './pages/ScanResult';
import History from './pages/History';
import Profile from './pages/Profile';
import Plans from './pages/Plans';
import AdminDashboard from './pages/AdminDashboard';
import AccountSettings from './pages/AccountSettings';
import OwnerControls from './pages/OwnerControls';
import ApiKeys from './pages/ApiKeys';
import Teams from './pages/Teams';
import Webhooks from './pages/Webhooks';
import Reports from './pages/Reports';
import EnterpriseVerification from './pages/EnterpriseVerification';
import OwnerVerification from './pages/OwnerVerification';
import NetworkScanner from './pages/NetworkScanner';
import NetworkScanResult from './pages/NetworkScanResult';

const PrivateRoute = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading) return <div className="min-h-screen bg-background flex items-center justify-center"><p className="text-muted-foreground">Loading...</p></div>;
  return user ? children : <Navigate to="/login" />;
};

const PublicRoute = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading) return <div className="min-h-screen bg-background flex items-center justify-center"><p className="text-muted-foreground">Loading...</p></div>;
  return !user ? children : <Navigate to="/dashboard" />;
};

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<PublicRoute><Landing /></PublicRoute>} />
          <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
          <Route path="/signup" element={<PublicRoute><Signup /></PublicRoute>} />
          
          <Route path="/dashboard" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
          <Route path="/scan" element={<PrivateRoute><Scan /></PrivateRoute>} />
          <Route path="/scan/:scanId" element={<PrivateRoute><ScanResult /></PrivateRoute>} />
          <Route path="/history" element={<PrivateRoute><History /></PrivateRoute>} />
          <Route path="/profile" element={<PrivateRoute><Profile /></PrivateRoute>} />
          <Route path="/plans" element={<PrivateRoute><Plans /></PrivateRoute>} />
          <Route path="/admin" element={<PrivateRoute><AdminDashboard /></PrivateRoute>} />
          <Route path="/settings" element={<PrivateRoute><AccountSettings /></PrivateRoute>} />
          <Route path="/owner" element={<PrivateRoute><OwnerControls /></PrivateRoute>} />
          <Route path="/api-keys" element={<PrivateRoute><ApiKeys /></PrivateRoute>} />
          <Route path="/teams" element={<PrivateRoute><Teams /></PrivateRoute>} />
          <Route path="/webhooks" element={<PrivateRoute><Webhooks /></PrivateRoute>} />
          <Route path="/reports" element={<PrivateRoute><Reports /></PrivateRoute>} />
          <Route path="/enterprise/verification" element={<PrivateRoute><EnterpriseVerification /></PrivateRoute>} />
          <Route path="/enterprise/network-scanner" element={<PrivateRoute><NetworkScanner /></PrivateRoute>} />
          <Route path="/enterprise/network-scan/:scanId" element={<PrivateRoute><NetworkScanResult /></PrivateRoute>} />
          <Route path="/owner/verification" element={<PrivateRoute><OwnerVerification /></PrivateRoute>} />
        </Routes>
        <Toaster position="top-right" />
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;