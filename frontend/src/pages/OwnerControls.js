import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';
import { Crown, UserPlus, Mail, Lock, User, Activity, Filter } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';

const API_URL = process.env.REACT_APP_BACKEND_URL + '/api';

const OwnerControls = () => {
  const { user, token } = useAuth();
  const navigate = useNavigate();
  const [createAdminForm, setCreateAdminForm] = useState({
    email: '',
    name: '',
    temporaryPassword: ''
  });
  const [loading, setLoading] = useState(false);
  const [auditLogs, setAuditLogs] = useState([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [filterActionType, setFilterActionType] = useState('');

  useEffect(() => {
    if (user?.role === 'owner') {
      fetchAuditLogs();
    }
  }, [user, filterActionType]);

  const fetchAuditLogs = async () => {
    setLogsLoading(true);
    try {
      const params = filterActionType ? { action_type: filterActionType, limit: 50 } : { limit: 50 };
      const response = await axios.get(`${API_URL}/owner/audit-logs`, {
        headers: { Authorization: `Bearer ${token}` },
        params
      });
      setAuditLogs(response.data);
    } catch (error) {
      console.error('Failed to fetch audit logs', error);
    } finally {
      setLogsLoading(false);
    }
  };

  if (user?.role !== 'owner') {
    navigate('/dashboard');
    return null;
  }

  const handleCreateAdmin = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await axios.post(
        `${API_URL}/owner/create-admin`,
        {
          email: createAdminForm.email,
          name: createAdminForm.name,
          temporary_password: createAdminForm.temporaryPassword
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Admin account created successfully');
      setCreateAdminForm({ email: '', name: '', temporaryPassword: '' });
    } catch (error) {
      const errorMsg = error.response?.data?.detail || 'Failed to create admin';
      toast.error(typeof errorMsg === 'string' ? errorMsg : 'Failed to create admin');
    } finally {
      setLoading(false);
    }
  };

  const getActionBadgeColor = (actionType) => {
    if (actionType.includes('owner')) return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
    if (actionType.includes('role')) return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
    if (actionType.includes('plan')) return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20';
    if (actionType.includes('credit')) return 'bg-green-500/10 text-green-400 border-green-500/20';
    return 'bg-zinc-500/10 text-zinc-400 border-zinc-500/20';
  };

  return (
    <Layout>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8" data-testid="owner-controls-page">
        <div className="mb-8">
          <h1 className="font-heading text-4xl font-bold mb-2 flex items-center">
            <Crown className="h-10 w-10 text-primary mr-3" />
            Owner Controls
          </h1>
          <p className="text-muted-foreground">Full system control and administrative functions</p>
        </div>

        <Tabs defaultValue="admin" className="w-full">
          <TabsList className="grid w-full grid-cols-3 mb-8">
            <TabsTrigger value="admin">Create Admin</TabsTrigger>
            <TabsTrigger value="audit">Audit Logs</TabsTrigger>
            <TabsTrigger value="system">System Info</TabsTrigger>
          </TabsList>

          <TabsContent value="admin" className="space-y-6">
            <div className="bg-card border border-border rounded-xl p-6">
              <h2 className="font-heading text-2xl font-semibold mb-6 flex items-center">
                <UserPlus className="h-6 w-6 text-primary mr-2" />
                Create Admin Account
              </h2>
              <form onSubmit={handleCreateAdmin} className="space-y-4" data-testid="create-admin-form">
                <div>
                  <Label htmlFor="admin-name" className="flex items-center space-x-2">
                    <User className="h-4 w-4" />
                    <span>Full Name</span>
                  </Label>
                  <Input
                    id="admin-name"
                    type="text"
                    placeholder="John Doe"
                    value={createAdminForm.name}
                    onChange={(e) => setCreateAdminForm({ ...createAdminForm, name: e.target.value })}
                    required
                    className="bg-black/50 border-border/50 focus:border-primary/50 mt-2"
                    data-testid="admin-name-input"
                  />
                </div>
                <div>
                  <Label htmlFor="admin-email" className="flex items-center space-x-2">
                    <Mail className="h-4 w-4" />
                    <span>Email</span>
                  </Label>
                  <Input
                    id="admin-email"
                    type="email"
                    placeholder="admin@example.com"
                    value={createAdminForm.email}
                    onChange={(e) => setCreateAdminForm({ ...createAdminForm, email: e.target.value })}
                    required
                    className="bg-black/50 border-border/50 focus:border-primary/50 mt-2"
                    data-testid="admin-email-input"
                  />
                </div>
                <div>
                  <Label htmlFor="admin-password" className="flex items-center space-x-2">
                    <Lock className="h-4 w-4" />
                    <span>Temporary Password</span>
                  </Label>
                  <Input
                    id="admin-password"
                    type="password"
                    placeholder="Set a temporary password"
                    value={createAdminForm.temporaryPassword}
                    onChange={(e) => setCreateAdminForm({ ...createAdminForm, temporaryPassword: e.target.value })}
                    required
                    minLength={6}
                    className="bg-black/50 border-border/50 focus:border-primary/50 mt-2"
                    data-testid="admin-password-input"
                  />
                </div>
                <Button
                  type="submit"
                  disabled={loading}
                  className="bg-primary text-primary-foreground hover:bg-primary/90 shadow-[0_0_20px_-5px_rgba(0,255,148,0.4)]"
                  data-testid="create-admin-btn"
                >
                  <UserPlus className="h-4 w-4 mr-2" />
                  {loading ? 'Creating...' : 'Create Admin'}
                </Button>
              </form>
            </div>
          </TabsContent>

          <TabsContent value="audit" className="space-y-6">
            <div className="bg-card border border-border rounded-xl p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="font-heading text-2xl font-semibold flex items-center">
                  <Activity className="h-6 w-6 text-primary mr-2" />
                  Audit Trail
                </h2>
                <div className="flex items-center space-x-2">
                  <Filter className="h-4 w-4 text-muted-foreground" />
                  <Select value={filterActionType} onValueChange={setFilterActionType}>
                    <SelectTrigger className="w-48">
                      <SelectValue placeholder="All Actions" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">All Actions</SelectItem>
                      <SelectItem value="role_changed">Role Changes</SelectItem>
                      <SelectItem value="plan_changed">Plan Changes</SelectItem>
                      <SelectItem value="owner_promoted">Owner Promotions</SelectItem>
                      <SelectItem value="owner_demoted">Owner Demotions</SelectItem>
                      <SelectItem value="admin_created">Admin Created</SelectItem>
                      <SelectItem value="user_login">User Logins</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {logsLoading ? (
                <p className="text-center py-8 text-muted-foreground">Loading audit logs...</p>
              ) : auditLogs.length === 0 ? (
                <p className="text-center py-8 text-muted-foreground">No audit logs found</p>
              ) : (
                <div className="space-y-3">
                  {auditLogs.map((log, idx) => (
                    <div
                      key={log.id || idx}
                      className="flex items-start justify-between p-4 bg-accent/30 rounded-lg border border-border/50"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2 mb-2">
                          <span className={`px-2 py-1 rounded-full text-xs font-mono uppercase border ${getActionBadgeColor(log.action_type)}`}>
                            {log.action_type?.replace(/_/g, ' ')}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {new Date(log.timestamp).toLocaleString()}
                          </span>
                        </div>
                        <p className="text-sm mb-1 break-words" title={log.details}>
                          {log.details}
                        </p>
                        <div className="flex items-center space-x-4 text-xs text-muted-foreground">
                          {log.performed_by_info && (
                            <span>
                              By: <span className="font-mono">@{log.performed_by_info.username}</span> ({log.performed_by_info.role})
                            </span>
                          )}
                          {log.target_user_info && (
                            <span>
                              Target: <span className="font-mono">@{log.target_user_info.username}</span>
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="system" className="space-y-6">
            <h2 className="font-heading text-2xl font-semibold mb-4">System Information</h2>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between py-2 border-b border-border/50">
                <span className="text-muted-foreground">Your Role</span>
                <span className="font-mono font-semibold text-primary">OWNER</span>
              </div>
              <div className="flex justify-between py-2 border-b border-border/50">
                <span className="text-muted-foreground">Plan</span>
                <span className="font-mono font-semibold text-primary">ENTERPRISE</span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-muted-foreground">Credits</span>
                <span className="font-mono font-semibold">UNLIMITED</span>
              </div>
            </div>
          </div>

          <div className="bg-card border border-border rounded-xl p-6">
            <h2 className="font-heading text-2xl font-semibold mb-4">Quick Actions</h2>
            <div className="space-y-3">
              <Button
                variant="outline"
                className="w-full justify-start"
                onClick={() => navigate('/admin')}
                data-testid="goto-admin-dashboard-btn"
              >
                Manage Users & System
              </Button>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default OwnerControls;