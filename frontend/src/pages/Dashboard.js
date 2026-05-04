import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';
import { Link } from 'react-router-dom';
import { Shield, FileSearch, Upload, Key, Users, Webhook, FileText, TrendingUp, AlertTriangle, CheckCircle } from 'lucide-react';
import { Button } from '../components/ui/button';

const API_URL = process.env.REACT_APP_BACKEND_URL + '/api';

const Dashboard = () => {
  const { user, token } = useAuth();
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const res = await axios.get(`${API_URL}/user/stats`, { headers: { Authorization: `Bearer ${token}` } });
      setStats(res.data);
    } catch (error) {
      console.error('Failed to fetch stats', error);
    }
  };

  const getPlanBadge = () => {
    if (user?.plan === 'enterprise') return 'bg-purple-500/10 text-purple-400 border-purple-500/30';
    if (user?.plan === 'premium') return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30';
    return 'bg-zinc-800 text-zinc-400 border-zinc-700';
  };

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8" data-testid="user-dashboard">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="font-heading text-4xl font-bold mb-1">Welcome, {user?.name}</h1>
            <p className="text-muted-foreground">@{user?.username}</p>
          </div>
          <span className={`px-3 py-1 rounded-full text-xs font-mono uppercase border ${getPlanBadge()}`}>
            {user?.plan}
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Stats */}
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-card border border-border rounded-xl p-5">
                <p className="text-sm text-muted-foreground">Credits</p>
                <p className="font-mono text-3xl font-bold text-primary" data-testid="dashboard-credits">
                  {user?.credits === 999999 ? '\u221E' : (stats?.credits ?? user?.credits)}
                </p>
              </div>
              <div className="bg-card border border-border rounded-xl p-5">
                <p className="text-sm text-muted-foreground">Total Scans</p>
                <p className="font-mono text-3xl font-bold">{stats?.total_scans || 0}</p>
              </div>
              <div className="bg-card border border-border rounded-xl p-5">
                <p className="text-sm text-muted-foreground">API Key</p>
                <p className="font-mono text-xl font-bold">{stats?.has_api_key ? 'Active' : 'None'}</p>
              </div>
            </div>

            {/* Recent Scans */}
            <div className="bg-card border border-border rounded-xl p-6">
              <h2 className="font-heading text-xl font-semibold mb-4">Recent Scans</h2>
              {stats?.recent_scans?.length > 0 ? (
                <div className="space-y-3">
                  {stats.recent_scans.map(scan => (
                    <Link key={scan.id} to={`/scan/${scan.id}`} className="block">
                      <div className="flex items-center justify-between p-3 bg-accent/30 rounded-lg border border-border/50 hover:border-primary/30 transition-colors">
                        <div className="flex-1 min-w-0">
                          <p className="font-mono text-sm truncate" title={scan.target}>{scan.target}</p>
                          <p className="text-xs text-muted-foreground">{scan.scan_type.toUpperCase()} &bull; {new Date(scan.created_at).toLocaleDateString()}</p>
                        </div>
                        <div className="flex items-center space-x-3 flex-shrink-0 ml-4">
                          {scan.risk_level === 'safe' && <CheckCircle className="h-4 w-4 text-green-400" />}
                          {scan.risk_level === 'suspicious' && <AlertTriangle className="h-4 w-4 text-orange-400" />}
                          {(scan.risk_level === 'high' || scan.risk_level === 'critical') && <AlertTriangle className="h-4 w-4 text-red-400" />}
                          <span className="font-mono text-sm font-semibold">{scan.risk_score}/100</span>
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <p className="text-muted-foreground text-center py-6">No scans yet. Start your first scan!</p>
              )}
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Quick Actions */}
            <div className="bg-card border border-border rounded-xl p-6" data-testid="quick-actions">
              <h2 className="font-heading text-lg font-semibold mb-4">Quick Actions</h2>
              <div className="space-y-3">
                <Link to="/scan" className="block">
                  <Button variant="outline" className="w-full justify-start" data-testid="quick-scan-url-btn">
                    <FileSearch className="h-4 w-4 mr-3 text-primary" /> Scan URL
                  </Button>
                </Link>
                <Link to="/scan" className="block">
                  <Button variant="outline" className="w-full justify-start" data-testid="quick-scan-file-btn">
                    <Upload className="h-4 w-4 mr-3 text-primary" /> Scan File
                  </Button>
                </Link>
                {user?.plan !== 'free' && (
                  <>
                    <Link to="/api-keys" className="block">
                      <Button variant="outline" className="w-full justify-start" data-testid="quick-api-keys-btn">
                        <Key className="h-4 w-4 mr-3 text-primary" /> API Keys
                      </Button>
                    </Link>
                    <Link to="/reports" className="block">
                      <Button variant="outline" className="w-full justify-start" data-testid="quick-reports-btn">
                        <FileText className="h-4 w-4 mr-3 text-primary" /> Reports
                      </Button>
                    </Link>
                  </>
                )}
                {user?.plan === 'enterprise' && (
                  <>
                    <Link to="/teams" className="block">
                      <Button variant="outline" className="w-full justify-start" data-testid="quick-teams-btn">
                        <Users className="h-4 w-4 mr-3 text-primary" /> Team
                      </Button>
                    </Link>
                    <Link to="/webhooks" className="block">
                      <Button variant="outline" className="w-full justify-start" data-testid="quick-webhooks-btn">
                        <Webhook className="h-4 w-4 mr-3 text-primary" /> Webhooks
                      </Button>
                    </Link>
                  </>
                )}
              </div>
            </div>

            {/* Plan Info */}
            <div className="bg-card border border-border rounded-xl p-6">
              <h2 className="font-heading text-lg font-semibold mb-3">Your Plan</h2>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Plan</span>
                  <span className="font-mono font-semibold uppercase">{user?.plan}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Scan Priority</span>
                  <span className="font-mono font-semibold">
                    {user?.plan === 'enterprise' ? 'Highest' : user?.plan === 'premium' ? 'High' : 'Normal'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">IOC Export</span>
                  <span className="font-mono font-semibold">{user?.plan !== 'free' ? 'Yes' : 'No'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">API Access</span>
                  <span className="font-mono font-semibold">{user?.plan !== 'free' ? 'Yes' : 'No'}</span>
                </div>
              </div>
              {user?.plan === 'free' && (
                <Link to="/plans">
                  <Button className="w-full mt-4" size="sm" data-testid="upgrade-btn">
                    <TrendingUp className="h-4 w-4 mr-2" /> Upgrade Plan
                  </Button>
                </Link>
              )}
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default Dashboard;
