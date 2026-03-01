import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';
import { FileSearch, Shield, AlertTriangle, CheckCircle, TrendingUp, Clock } from 'lucide-react';
import { Button } from '../components/ui/button';
import { useNavigate } from 'react-router-dom';

const API_URL = process.env.REACT_APP_BACKEND_URL + '/api';

const Dashboard = () => {
  const { user, token, refreshUser } = useAuth();
  const [stats, setStats] = useState(null);
  const [recentScans, setRecentScans] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    fetchStats();
    fetchRecentScans();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API_URL}/user/stats`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch stats', error);
    }
  };

  const fetchRecentScans = async () => {
    try {
      const response = await axios.get(`${API_URL}/scan/history/list`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setRecentScans(response.data.slice(0, 5));
    } catch (error) {
      console.error('Failed to fetch recent scans', error);
    }
  };

  const getRiskBadgeClass = (level) => {
    if (level === 'safe') return 'bg-green-500/10 text-green-400 border-green-500/20';
    if (level === 'suspicious') return 'bg-orange-500/10 text-orange-400 border-orange-500/20';
    return 'bg-red-500/10 text-red-400 border-red-500/20';
  };

  const getRiskIcon = (level) => {
    if (level === 'safe') return <CheckCircle className="h-4 w-4" />;
    if (level === 'suspicious') return <AlertTriangle className="h-4 w-4" />;
    return <Shield className="h-4 w-4" />;
  };

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8" data-testid="dashboard-page">
        <div className="mb-8">
          <h1 className="font-heading text-4xl font-bold mb-2">
            Welcome back, {user?.username ? `@${user.username}` : user?.name}
          </h1>
          <p className="text-muted-foreground">Monitor threats and manage your security scans</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-card border border-border rounded-xl p-6" data-testid="stat-total-scans">
            <div className="flex items-center justify-between mb-2">
              <TrendingUp className="h-8 w-8 text-primary" />
            </div>
            <div className="space-y-1">
              <p className="text-muted-foreground text-sm">Total Scans</p>
              <p className="font-mono text-3xl font-bold">{stats?.total_scans || 0}</p>
            </div>
          </div>

          <div className="bg-card border border-border rounded-xl p-6" data-testid="stat-safe">
            <div className="flex items-center justify-between mb-2">
              <CheckCircle className="h-8 w-8 text-green-400" />
            </div>
            <div className="space-y-1">
              <p className="text-muted-foreground text-sm">Safe</p>
              <p className="font-mono text-3xl font-bold text-green-400">{stats?.safe || 0}</p>
            </div>
          </div>

          <div className="bg-card border border-border rounded-xl p-6" data-testid="stat-suspicious">
            <div className="flex items-center justify-between mb-2">
              <AlertTriangle className="h-8 w-8 text-orange-400" />
            </div>
            <div className="space-y-1">
              <p className="text-muted-foreground text-sm">Suspicious</p>
              <p className="font-mono text-3xl font-bold text-orange-400">{stats?.suspicious || 0}</p>
            </div>
          </div>

          <div className="bg-card border border-border rounded-xl p-6" data-testid="stat-malicious">
            <div className="flex items-center justify-between mb-2">
              <Shield className="h-8 w-8 text-red-400" />
            </div>
            <div className="space-y-1">
              <p className="text-muted-foreground text-sm">Malicious</p>
              <p className="font-mono text-3xl font-bold text-red-400">{stats?.malicious || 0}</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-2 bg-card border border-border rounded-xl p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="font-heading text-2xl font-semibold">Recent Scans</h2>
              <Button variant="outline" size="sm" onClick={() => navigate('/history')} data-testid="view-all-scans-btn">
                View All
              </Button>
            </div>

            <div className="space-y-4">
              {recentScans.length === 0 ? (
                <div className="text-center py-12" data-testid="no-scans-message">
                  <FileSearch className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
                  <p className="text-muted-foreground">No scans yet. Start scanning now!</p>
                  <Button className="mt-4" onClick={() => navigate('/scan')} data-testid="start-scanning-btn">
                    Start Scanning
                  </Button>
                </div>
              ) : (
                recentScans.map((scan, index) => (
                  <div
                    key={scan.id}
                    className="flex items-center justify-between p-4 bg-accent/30 rounded-lg border border-border/50 hover:border-primary/50 transition-all cursor-pointer"
                    onClick={() => navigate(`/scan/${scan.id}`)}
                    data-testid={`recent-scan-${index}`}
                  >
                    <div className="flex items-center space-x-4 flex-1 min-w-0">
                      {getRiskIcon(scan.risk_level)}
                      <div className="flex-1 min-w-0">
                        <p 
                          className="font-mono text-sm font-medium truncate" 
                          title={scan.target}
                        >
                          {scan.target}
                        </p>
                        <p className="text-xs text-muted-foreground">{new Date(scan.created_at).toLocaleString()}</p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-4 flex-shrink-0">
                      <span className={`px-2.5 py-0.5 rounded-full text-xs font-mono uppercase tracking-wider border ${getRiskBadgeClass(scan.risk_level)}`}>
                        {scan.risk_level}
                      </span>
                      <span className="font-mono text-sm text-muted-foreground">{scan.risk_score}/100</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="bg-card border border-border rounded-xl p-6">
            <h2 className="font-heading text-2xl font-semibold mb-6">Quick Scan</h2>
            <div className="space-y-4">
              <Button
                className="w-full justify-start bg-primary/10 hover:bg-primary/20 text-primary border border-primary/30"
                onClick={() => navigate('/scan')}
                data-testid="quick-scan-url-btn"
              >
                <FileSearch className="h-5 w-5 mr-2" />
                Scan URL
              </Button>
              <Button
                className="w-full justify-start bg-primary/10 hover:bg-primary/20 text-primary border border-primary/30"
                onClick={() => navigate('/scan')}
                data-testid="quick-scan-file-btn"
              >
                <Shield className="h-5 w-5 mr-2" />
                Scan File
              </Button>

              <div className="pt-4 border-t border-border">
                <h3 className="font-semibold mb-3">Account Status</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Plan</span>
                    <span className="font-mono font-semibold uppercase text-primary" data-testid="account-plan">{user?.plan}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Credits</span>
                    <span className="font-mono font-semibold" data-testid="account-credits">{user?.credits}</span>
                  </div>
                </div>
                <Button variant="outline" className="w-full mt-4" onClick={() => navigate('/plans')} data-testid="upgrade-plan-btn">
                  View Plans
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default Dashboard;