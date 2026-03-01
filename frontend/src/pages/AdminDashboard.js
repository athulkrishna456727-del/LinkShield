import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';
import { 
  Users, FileSearch, TrendingUp, Crown, Edit, Search, Ban, CheckCircle, 
  XCircle, Plus, Minus, RotateCcw, Shield, DollarSign, Activity, Settings
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';

const API_URL = process.env.REACT_APP_BACKEND_URL + '/api';

const AdminDashboard = () => {
  const { user, token } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [scans, setScans] = useState([]);
  const [admins, setAdmins] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedUser, setSelectedUser] = useState(null);
  const [creditAmount, setCreditAmount] = useState('');
  const [creditReason, setCreditReason] = useState('');

  useEffect(() => {
    if (user?.role !== 'admin' && user?.role !== 'owner') {
      navigate('/dashboard');
      return;
    }
    fetchStats();
    fetchUsers();
    fetchScans();
    if (user?.role === 'owner') {
      fetchAdmins();
    }
  }, [user]);

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API_URL}/admin/analytics/detailed`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch stats', error);
    }
  };

  const fetchUsers = async () => {
    try {
      const response = await axios.get(`${API_URL}/admin/users`, {
        params: searchTerm ? { search: searchTerm } : {},
        headers: { Authorization: `Bearer ${token}` }
      });
      setUsers(response.data);
    } catch (error) {
      console.error('Failed to fetch users', error);
    }
  };

  const fetchScans = async () => {
    try {
      const response = await axios.get(`${API_URL}/admin/scans`, {
        params: { limit: 50 },
        headers: { Authorization: `Bearer ${token}` }
      });
      setScans(response.data);
    } catch (error) {
      console.error('Failed to fetch scans', error);
    }
  };

  const fetchAdmins = async () => {
    try {
      const response = await axios.get(`${API_URL}/owner/admins`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setAdmins(response.data);
    } catch (error) {
      console.error('Failed to fetch admins', error);
    }
  };

  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      fetchUsers();
    }, 500);
    return () => clearTimeout(delayDebounceFn);
  }, [searchTerm]);

  const handleAddCredits = async () => {
    if (!selectedUser || !creditAmount) return;
    try {
      await axios.post(
        `${API_URL}/admin/users/${selectedUser.id}/add-credits`,
        { amount: parseInt(creditAmount), reason: creditReason },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Credits added successfully');
      fetchUsers();
      setSelectedUser(null);
      setCreditAmount('');
      setCreditReason('');
    } catch (error) {
      toast.error('Failed to add credits');
    }
  };

  const handleDeductCredits = async () => {
    if (!selectedUser || !creditAmount) return;
    try {
      await axios.post(
        `${API_URL}/admin/users/${selectedUser.id}/deduct-credits`,
        { amount: parseInt(creditAmount), reason: creditReason },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Credits deducted successfully');
      fetchUsers();
      setSelectedUser(null);
      setCreditAmount('');
      setCreditReason('');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to deduct credits');
    }
  };

  const handleResetCredits = async (userId) => {
    try {
      await axios.post(
        `${API_URL}/admin/users/${userId}/reset-credits`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Credits reset successfully');
      fetchUsers();
    } catch (error) {
      toast.error('Failed to reset credits');
    }
  };

  const handleUpdateStatus = async (userId, status) => {
    try {
      await axios.put(
        `${API_URL}/admin/users/${userId}/status`,
        { status },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(`User ${status}`);
      fetchUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update status');
    }
  };

  const handleUpdatePlan = async (userId, plan) => {
    try {
      await axios.put(
        `${API_URL}/admin/users/${userId}/plan`,
        { plan },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Plan updated successfully');
      fetchUsers();
    } catch (error) {
      toast.error('Failed to update plan');
    }
  };

  const handleUpdateRole = async (userId, role) => {
    try {
      await axios.put(
        `${API_URL}/admin/users/${userId}/role`,
        { role },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Role updated successfully');
      fetchUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update role');
    }
  };

  if (user?.role !== 'admin' && user?.role !== 'owner') {
    return null;
  }

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8" data-testid="admin-dashboard">
        <div className="mb-8">
          <h1 className="font-heading text-4xl font-bold mb-2 flex items-center">
            <Crown className="h-10 w-10 text-primary mr-3" />
            {user?.role === 'owner' ? 'Owner' : 'Admin'} Dashboard
          </h1>
          <p className="text-muted-foreground">Platform management and monitoring</p>
        </div>

        <Tabs defaultValue="overview" className="w-full">
          <TabsList className="grid w-full grid-cols-5 mb-8">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="users">Users</TabsTrigger>
            <TabsTrigger value="scans">Scans</TabsTrigger>
            <TabsTrigger value="analytics">Analytics</TabsTrigger>
            {user?.role === 'owner' && <TabsTrigger value="owner">Owner</TabsTrigger>}
          </TabsList>

          <TabsContent value="overview" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="bg-card border border-border rounded-xl p-6">
                <div className="flex items-center justify-between mb-2">
                  <Users className="h-8 w-8 text-primary" />
                </div>
                <p className="text-muted-foreground text-sm">Total Users</p>
                <p className="font-mono text-3xl font-bold">{stats?.total_users || 0}</p>
              </div>

              <div className="bg-card border border-border rounded-xl p-6">
                <div className="flex items-center justify-between mb-2">
                  <FileSearch className="h-8 w-8 text-primary" />
                </div>
                <p className="text-muted-foreground text-sm">Total Scans</p>
                <p className="font-mono text-3xl font-bold">{stats?.total_scans || 0}</p>
              </div>

              <div className="bg-card border border-border rounded-xl p-6">
                <div className="flex items-center justify-between mb-2">
                  <Crown className="h-8 w-8 text-yellow-400" />
                </div>
                <p className="text-muted-foreground text-sm">Premium Users</p>
                <p className="font-mono text-3xl font-bold text-yellow-400">{stats?.premium_users || 0}</p>
              </div>

              <div className="bg-card border border-border rounded-xl p-6">
                <div className="flex items-center justify-between mb-2">
                  <TrendingUp className="h-8 w-8 text-green-400" />
                </div>
                <p className="text-muted-foreground text-sm">Scans Today</p>
                <p className="font-mono text-3xl font-bold text-green-400">{stats?.scans_today || 0}</p>
              </div>
            </div>

            {user?.role === 'owner' && stats?.total_revenue !== undefined && (
              <div className="bg-card border border-border rounded-xl p-6">
                <h2 className="font-heading text-2xl font-semibold mb-4 flex items-center">
                  <DollarSign className="h-6 w-6 text-primary mr-2" />
                  Revenue Overview
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Total Revenue</p>
                    <p className="font-mono text-2xl font-bold">₹{stats.total_revenue}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Enterprise Users</p>
                    <p className="font-mono text-2xl font-bold">{stats.enterprise_users}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Active Users</p>
                    <p className="font-mono text-2xl font-bold">{stats.active_users}</p>
                  </div>
                </div>
              </div>
            )}
          </TabsContent>

          <TabsContent value="users" className="space-y-6">
            <div className="bg-card border border-border rounded-xl p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="font-heading text-2xl font-semibold">User Management</h2>
                <div className="relative w-64">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    type="text"
                    placeholder="Search users..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-3 px-4">User</th>
                      <th className="text-left py-3 px-4">Plan</th>
                      <th className="text-left py-3 px-4">Credits</th>
                      <th className="text-left py-3 px-4">Role</th>
                      <th className="text-left py-3 px-4">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((u, idx) => (
                      <tr key={u.id} className="border-b border-border/50 hover:bg-accent/30">
                        <td className="py-3 px-4">
                          <div>
                            <p className="font-semibold">{u.name}</p>
                            <p className="text-sm text-muted-foreground">{u.email}</p>
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <span className={`px-2 py-1 rounded-full text-xs font-mono uppercase ${
                            u.plan === 'enterprise' ? 'bg-purple-500/10 text-purple-400 border border-purple-500/20' :
                            u.plan === 'premium' ? 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20' :
                            'bg-zinc-800 text-zinc-400 border border-zinc-700'
                          }`}>
                            {u.plan}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-mono font-semibold">{u.credits}</td>
                        <td className="py-3 px-4 font-mono text-xs uppercase">{u.role}</td>
                        <td className="py-3 px-4">
                          <div className="flex items-center space-x-2">
                            <Dialog>
                              <DialogTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => setSelectedUser(u)}
                                  title="Manage Credits"
                                >
                                  <Edit className="h-4 w-4" />
                                </Button>
                              </DialogTrigger>
                              <DialogContent>
                                <DialogHeader>
                                  <DialogTitle>Manage Credits - {selectedUser?.name}</DialogTitle>
                                </DialogHeader>
                                <div className="space-y-4 pt-4">
                                  <div>
                                    <Label>Amount</Label>
                                    <Input
                                      type="number"
                                      value={creditAmount}
                                      onChange={(e) => setCreditAmount(e.target.value)}
                                      className="mt-2"
                                    />
                                  </div>
                                  <div>
                                    <Label>Reason</Label>
                                    <Input
                                      type="text"
                                      value={creditReason}
                                      onChange={(e) => setCreditReason(e.target.value)}
                                      className="mt-2"
                                    />
                                  </div>
                                  <div className="flex space-x-2">
                                    <Button onClick={handleAddCredits} className="flex-1">
                                      <Plus className="h-4 w-4 mr-2" />
                                      Add
                                    </Button>
                                    <Button onClick={handleDeductCredits} variant="outline" className="flex-1">
                                      <Minus className="h-4 w-4 mr-2" />
                                      Deduct
                                    </Button>
                                  </div>
                                  <Button
                                    onClick={() => handleResetCredits(selectedUser?.id)}
                                    variant="outline"
                                    className="w-full"
                                  >
                                    <RotateCcw className="h-4 w-4 mr-2" />
                                    Reset to Plan Default
                                  </Button>
                                </div>
                              </DialogContent>
                            </Dialog>

                            {u.role !== 'owner' && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleUpdateStatus(u.id, u.status === 'active' ? 'suspended' : 'active')}
                                title={u.status === 'active' ? 'Suspend User' : 'Activate User'}
                              >
                                {u.status === 'active' ? <Ban className="h-4 w-4 text-red-400" /> : <CheckCircle className="h-4 w-4 text-green-400" />}
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="scans" className="space-y-6">
            <div className="bg-card border border-border rounded-xl p-6">
              <h2 className="font-heading text-2xl font-semibold mb-6">Recent Scans</h2>
              <div className="space-y-3">
                {scans.map((scan, idx) => (
                  <div
                    key={scan.id}
                    className="flex items-center justify-between p-4 bg-accent/30 rounded-lg border border-border/50"
                  >
                    <div className="flex-1">
                      <p className="font-mono text-sm font-medium">{scan.target}</p>
                      <p className="text-xs text-muted-foreground">
                        {scan.user_info?.email || 'Unknown'} • {new Date(scan.created_at).toLocaleString()}
                      </p>
                    </div>
                    <div className="flex items-center space-x-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-mono uppercase ${
                        scan.risk_level === 'safe' ? 'bg-green-500/10 text-green-400 border border-green-500/20' :
                        scan.risk_level === 'suspicious' ? 'bg-orange-500/10 text-orange-400 border border-orange-500/20' :
                        'bg-red-500/10 text-red-400 border border-red-500/20'
                      }`}>
                        {scan.risk_level}
                      </span>
                      <span className="font-mono text-sm">{scan.risk_score}/100</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </TabsContent>

          <TabsContent value="analytics" className="space-y-6">
            <div className="bg-card border border-border rounded-xl p-6">
              <h2 className="font-heading text-2xl font-semibold mb-6">Platform Analytics</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h3 className="font-semibold mb-4">User Distribution</h3>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span>Free Users</span>
                      <span className="font-mono font-bold">{stats?.free_users || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Premium Users</span>
                      <span className="font-mono font-bold text-yellow-400">{stats?.premium_users || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Enterprise Users</span>
                      <span className="font-mono font-bold text-purple-400">{stats?.enterprise_users || 0}</span>
                    </div>
                  </div>
                </div>
                <div>
                  <h3 className="font-semibold mb-4">Activity Metrics</h3>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span>Active Users</span>
                      <span className="font-mono font-bold">{stats?.active_users || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Total Scans</span>
                      <span className="font-mono font-bold">{stats?.total_scans || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Scans Today</span>
                      <span className="font-mono font-bold text-green-400">{stats?.scans_today || 0}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </TabsContent>

          {user?.role === 'owner' && (
            <TabsContent value="owner" className="space-y-6">
              <div className="bg-card border border-border rounded-xl p-6">
                <h2 className="font-heading text-2xl font-semibold mb-6">Admin Management</h2>
                <div className="space-y-3">
                  {admins.length === 0 ? (
                    <p className="text-muted-foreground text-center py-8">No admins found</p>
                  ) : (
                    admins.map((admin, idx) => (
                      <div
                        key={admin.id}
                        className="flex items-center justify-between p-4 bg-accent/30 rounded-lg border border-border/50"
                      >
                        <div>
                          <p className="font-semibold">{admin.name}</p>
                          <p className="text-sm text-muted-foreground">{admin.email}</p>
                        </div>
                        <div className="flex items-center space-x-2">
                          <span className="px-2 py-1 bg-primary/10 text-primary text-xs font-semibold rounded-full border border-primary/20">
                            ADMIN
                          </span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
                <Button
                  className="w-full mt-4"
                  onClick={() => navigate('/owner')}
                >
                  <Crown className="h-4 w-4 mr-2" />
                  Go to Owner Controls
                </Button>
              </div>
            </TabsContent>
          )}
        </Tabs>
      </div>
    </Layout>
  );
};

export default AdminDashboard;
