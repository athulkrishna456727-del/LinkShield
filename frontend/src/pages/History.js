import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';
import { Search, Shield, AlertTriangle, CheckCircle } from 'lucide-react';
import { Input } from '../components/ui/input';
import { useNavigate } from 'react-router-dom';

const API_URL = process.env.REACT_APP_BACKEND_URL + '/api';

const History = () => {
  const { token } = useAuth();
  const [scans, setScans] = useState([]);
  const [filteredScans, setFilteredScans] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchScans();
  }, []);

  useEffect(() => {
    if (searchTerm) {
      setFilteredScans(
        scans.filter(
          (scan) =>
            scan.target.toLowerCase().includes(searchTerm.toLowerCase()) ||
            scan.risk_level.toLowerCase().includes(searchTerm.toLowerCase())
        )
      );
    } else {
      setFilteredScans(scans);
    }
  }, [searchTerm, scans]);

  const fetchScans = async () => {
    try {
      const response = await axios.get(`${API_URL}/scan/history/list`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setScans(response.data);
      setFilteredScans(response.data);
    } catch (error) {
      console.error('Failed to fetch scans', error);
    } finally {
      setLoading(false);
    }
  };

  const getRiskBadgeClass = (level) => {
    if (level === 'safe') return 'bg-green-500/10 text-green-400 border-green-500/20';
    if (level === 'suspicious') return 'bg-orange-500/10 text-orange-400 border-orange-500/20';
    return 'bg-red-500/10 text-red-400 border-red-500/20';
  };

  const getRiskIcon = (level) => {
    if (level === 'safe') return <CheckCircle className="h-5 w-5 text-green-400" />;
    if (level === 'suspicious') return <AlertTriangle className="h-5 w-5 text-orange-400" />;
    return <Shield className="h-5 w-5 text-red-400" />;
  };

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8" data-testid="history-page">
        <div className="mb-8">
          <h1 className="font-heading text-4xl font-bold mb-2">Scan History</h1>
          <p className="text-muted-foreground">View and analyze your previous scans</p>
        </div>

        <div className="bg-card border border-border rounded-xl p-6">
          <div className="mb-6">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-muted-foreground" />
              <Input
                type="text"
                placeholder="Search by target or risk level..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 bg-black/50 border-border/50 focus:border-primary/50"
                data-testid="search-input"
              />
            </div>
          </div>

          {loading ? (
            <div className="text-center py-12" data-testid="loading-state">
              <p className="text-muted-foreground">Loading scan history...</p>
            </div>
          ) : filteredScans.length === 0 ? (
            <div className="text-center py-12" data-testid="no-scans-state">
              <p className="text-muted-foreground">
                {searchTerm ? 'No scans match your search' : 'No scans yet'}
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredScans.map((scan, index) => (
                <div
                  key={scan.id}
                  className="flex items-center justify-between p-4 bg-accent/30 rounded-lg border border-border/50 hover:border-primary/50 transition-all cursor-pointer"
                  onClick={() => navigate(`/scan/${scan.id}`)}
                  data-testid={`scan-item-${index}`}
                >
                  <div className="flex items-center space-x-4 flex-1">
                    {getRiskIcon(scan.risk_level)}
                    <div className="flex-1 min-w-0">
                      <p className="font-mono text-sm font-medium truncate" data-testid={`scan-target-${index}`}>
                        {scan.target}
                      </p>
                      <div className="flex items-center space-x-4 text-xs text-muted-foreground mt-1">
                        <span data-testid={`scan-type-${index}`}>{scan.scan_type.toUpperCase()}</span>
                        <span>•</span>
                        <span>{new Date(scan.created_at).toLocaleDateString()}</span>
                        <span>•</span>
                        <span>{new Date(scan.created_at).toLocaleTimeString()}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-4">
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-mono uppercase tracking-wider border ${getRiskBadgeClass(
                        scan.risk_level
                      )}`}
                      data-testid={`scan-risk-${index}`}
                    >
                      {scan.risk_level}
                    </span>
                    <span className="font-mono text-lg font-semibold w-16 text-right" data-testid={`scan-score-${index}`}>
                      {scan.risk_score}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
};

export default History;