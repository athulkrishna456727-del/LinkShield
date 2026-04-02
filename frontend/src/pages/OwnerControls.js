import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';
import { Crown, UserPlus, Mail, Lock, User, Activity, Filter, CreditCard, Eye, EyeOff, CheckCircle, XCircle, Loader2 } from 'lucide-react';
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

  // Payment settings state
  const [paymentSettings, setPaymentSettings] = useState(null);
  const [paymentForm, setPaymentForm] = useState({ key_id: '', key_secret: '', is_active: true });
  const [paymentLoading, setPaymentLoading] = useState(false);
  const [showSecret, setShowSecret] = useState(false);
  const [testingConnection, setTestingConnection] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState(null);

  useEffect(() => {
    if (user?.role !== 'owner') {
      navigate('/dashboard');
      return;
    }
    fetchAuditLogs();
    fetchPaymentSettings();
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

  const fetchPaymentSettings = async () => {
    try {
      const response = await axios.get(`${API_URL}/owner/payment-settings`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setPaymentSettings(response.data);
      setPaymentForm({
        key_id: response.data.key_id || '',
        key_secret: '',
        is_active: response.data.is_active !== false
      });
    } catch (error) {
      console.error('Failed to fetch payment settings', error);
    }
  };

  const handleSavePaymentSettings = async (e) => {
    e.preventDefault();
    if (!paymentForm.key_id) {
      toast.error('Razorpay Key ID is required');
      return;
    }
    if (!paymentForm.key_secret && !paymentSettings?.key_secret_masked) {
      toast.error('Razorpay Key Secret is required');
      return;
    }

    setPaymentLoading(true);
    try {
      const payload = {
        gateway: 'razorpay',
        key_id: paymentForm.key_id,
        key_secret: paymentForm.key_secret || 'UNCHANGED',
        is_active: paymentForm.is_active
      };

      // Only send if secret was actually changed
      if (!paymentForm.key_secret) {
        toast.error('Please enter the Key Secret to save');
        setPaymentLoading(false);
        return;
      }

      await axios.put(`${API_URL}/owner/payment-settings`, payload, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Payment gateway settings saved successfully');
      setPaymentForm(prev => ({ ...prev, key_secret: '' }));
      setConnectionStatus(null);
      fetchPaymentSettings();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save payment settings');
    } finally {
      setPaymentLoading(false);
    }
  };

  const handleTestConnection = async () => {
    setTestingConnection(true);
    setConnectionStatus(null);
    try {
      const response = await axios.post(`${API_URL}/owner/payment-settings/test`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setConnectionStatus(response.data);
    } catch (error) {
      setConnectionStatus({ status: 'error', message: 'Failed to test connection' });
    } finally {
      setTestingConnection(false);
    }
  };

  if (user?.role !== 'owner') {
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
    if (actionType?.includes('payment')) return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
    if (actionType?.includes('owner')) return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
    if (actionType?.includes('role')) return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
    if (actionType?.includes('plan')) return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20';
    if (actionType?.includes('credit')) return 'bg-green-500/10 text-green-400 border-green-500/20';
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
          <TabsList className="grid w-full grid-cols-4 mb-8">
            <TabsTrigger value="admin">Create Admin</TabsTrigger>
            <TabsTrigger value="payment" data-testid="payment-settings-tab">Payment Settings</TabsTrigger>
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

          <TabsContent value="payment" className="space-y-6">
            <div className="bg-card border border-border rounded-xl p-6">
              <h2 className="font-heading text-2xl font-semibold mb-2 flex items-center">
                <CreditCard className="h-6 w-6 text-primary mr-2" />
                Payment Gateway Configuration
              </h2>
              <p className="text-sm text-muted-foreground mb-6">
                Configure your Razorpay payment gateway credentials. Changes take effect immediately without server restart.
              </p>

              <form onSubmit={handleSavePaymentSettings} className="space-y-5" data-testid="payment-settings-form">
                <div className="flex items-center justify-between p-3 bg-accent/20 rounded-lg border border-border/50">
                  <div className="flex items-center space-x-3">
                    <span className="text-sm font-medium">Gateway</span>
                    <span className="px-2 py-0.5 bg-blue-500/10 text-blue-400 text-xs font-mono rounded-full border border-blue-500/20">
                      RAZORPAY
                    </span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-xs text-muted-foreground">Active</span>
                    <button
                      type="button"
                      onClick={() => setPaymentForm(prev => ({ ...prev, is_active: !prev.is_active }))}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        paymentForm.is_active ? 'bg-primary' : 'bg-zinc-700'
                      }`}
                      data-testid="gateway-active-toggle"
                    >
                      <span className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${
                        paymentForm.is_active ? 'translate-x-6' : 'translate-x-1'
                      }`} />
                    </button>
                  </div>
                </div>

                <div>
                  <Label htmlFor="razorpay-key-id">Razorpay Key ID</Label>
                  <Input
                    id="razorpay-key-id"
                    type="text"
                    placeholder="rzp_test_xxxxxxxxxxxxx"
                    value={paymentForm.key_id}
                    onChange={(e) => setPaymentForm(prev => ({ ...prev, key_id: e.target.value }))}
                    required
                    className="bg-black/50 border-border/50 focus:border-primary/50 mt-2 font-mono"
                    data-testid="razorpay-key-id-input"
                  />
                  {paymentSettings?.is_default && (
                    <p className="text-xs text-orange-400 mt-1">Currently using default/demo key from environment</p>
                  )}
                </div>

                <div>
                  <Label htmlFor="razorpay-key-secret">Razorpay Key Secret</Label>
                  <div className="relative mt-2">
                    <Input
                      id="razorpay-key-secret"
                      type={showSecret ? 'text' : 'password'}
                      placeholder={paymentSettings?.key_secret_masked ? `Current: ${paymentSettings.key_secret_masked}` : 'Enter key secret'}
                      value={paymentForm.key_secret}
                      onChange={(e) => setPaymentForm(prev => ({ ...prev, key_secret: e.target.value }))}
                      className="bg-black/50 border-border/50 focus:border-primary/50 font-mono pr-10"
                      data-testid="razorpay-key-secret-input"
                    />
                    <button
                      type="button"
                      onClick={() => setShowSecret(!showSecret)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                      {showSecret ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Secret is encrypted before storage. Enter a new value to update.
                  </p>
                </div>

                {paymentSettings?.updated_at && (
                  <div className="text-xs text-muted-foreground p-2 bg-accent/10 rounded">
                    Last updated: {new Date(paymentSettings.updated_at).toLocaleString()}
                  </div>
                )}

                <div className="flex items-center gap-3">
                  <Button
                    type="submit"
                    disabled={paymentLoading}
                    className="bg-primary text-primary-foreground hover:bg-primary/90"
                    data-testid="save-payment-settings-btn"
                  >
                    {paymentLoading ? (
                      <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Saving...</>
                    ) : (
                      'Save Settings'
                    )}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleTestConnection}
                    disabled={testingConnection}
                    data-testid="test-connection-btn"
                  >
                    {testingConnection ? (
                      <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Testing...</>
                    ) : (
                      'Test Connection'
                    )}
                  </Button>
                </div>

                {connectionStatus && (
                  <div className={`flex items-center gap-2 p-3 rounded-lg border ${
                    connectionStatus.status === 'success'
                      ? 'bg-green-500/10 border-green-500/20 text-green-400'
                      : 'bg-red-500/10 border-red-500/20 text-red-400'
                  }`} data-testid="connection-status">
                    {connectionStatus.status === 'success' ? (
                      <CheckCircle className="h-5 w-5 flex-shrink-0" />
                    ) : (
                      <XCircle className="h-5 w-5 flex-shrink-0" />
                    )}
                    <span className="text-sm">{connectionStatus.message}</span>
                  </div>
                )}
              </form>
            </div>

            <div className="bg-card border border-border rounded-xl p-6">
              <h3 className="font-semibold mb-3">Supported Gateways</h3>
              <div className="space-y-2">
                <div className="flex items-center justify-between p-3 bg-accent/20 rounded-lg border border-primary/30">
                  <div className="flex items-center space-x-3">
                    <CreditCard className="h-5 w-5 text-primary" />
                    <span className="font-medium">Razorpay</span>
                  </div>
                  <span className="text-xs font-mono text-primary bg-primary/10 px-2 py-0.5 rounded-full">ACTIVE</span>
                </div>
                <div className="flex items-center justify-between p-3 bg-accent/10 rounded-lg border border-border/30 opacity-50">
                  <div className="flex items-center space-x-3">
                    <CreditCard className="h-5 w-5 text-muted-foreground" />
                    <span className="font-medium text-muted-foreground">Stripe</span>
                  </div>
                  <span className="text-xs font-mono text-muted-foreground bg-zinc-800 px-2 py-0.5 rounded-full">COMING SOON</span>
                </div>
                <div className="flex items-center justify-between p-3 bg-accent/10 rounded-lg border border-border/30 opacity-50">
                  <div className="flex items-center space-x-3">
                    <CreditCard className="h-5 w-5 text-muted-foreground" />
                    <span className="font-medium text-muted-foreground">PayPal</span>
                  </div>
                  <span className="text-xs font-mono text-muted-foreground bg-zinc-800 px-2 py-0.5 rounded-full">COMING SOON</span>
                </div>
              </div>
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
                  <Select value={filterActionType || "all"} onValueChange={(val) => setFilterActionType(val === "all" ? "" : val)}>
                    <SelectTrigger className="w-48">
                      <SelectValue placeholder="All Actions" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Actions</SelectItem>
                      <SelectItem value="role_changed">Role Changes</SelectItem>
                      <SelectItem value="plan_changed">Plan Changes</SelectItem>
                      <SelectItem value="payment_settings_updated">Payment Settings</SelectItem>
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
            <div className="bg-card border border-border rounded-xl p-6">
              <h2 className="font-heading text-2xl font-semibold mb-4">System Information</h2>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between py-2 border-b border-border/50">
                  <span className="text-muted-foreground">Your Role</span>
                  <span className="font-mono font-semibold text-primary">OWNER</span>
                </div>
                <div className="flex justify-between py-2 border-b border-border/50">
                  <span className="text-muted-foreground">Username</span>
                  <span className="font-mono font-semibold">@{user?.username}</span>
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
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
};

export default OwnerControls;
