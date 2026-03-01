import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';
import { Users, FileSearch, TrendingUp, Crown, Edit, Search } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';

const API_URL = process.env.REACT_APP_BACKEND_URL + '/api';

const AdminDashboard = () => {
  const { user, token } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [editingUser, setEditingUser] = useState(null);
  const [newCredits, setNewCredits] = useState('');
  const [newPlan, setNewPlan] = useState('');
  const [newRole, setNewRole] = useState('');

  useEffect(() => {
    if (user?.role !== 'admin' && user?.role !== 'owner') {
      navigate('/dashboard');
      return;
    }
    fetchStats();
    fetchUsers();
  }, [user]);

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API_URL}/admin/stats`, {
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

  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      fetchUsers();
    }, 500);
    return () => clearTimeout(delayDebounceFn);
  }, [searchTerm]);

  const handleUpdateCredits = async () => {
    if (!editingUser || !newCredits) return;

    try {
      await axios.put(
        `${API_URL}/admin/users/${editingUser.id}/credits`,
        { credits: parseInt(newCredits) },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Credits updated successfully');
      fetchUsers();
      setEditingUser(null);
      setNewCredits('');
    } catch (error) {
      toast.error('Failed to update credits');
    }
  };

  const handleUpdatePlan = async () => {
    if (!editingUser || !newPlan) return;

    try {
      await axios.put(
        `${API_URL}/admin/users/${editingUser.id}/plan`,
        { plan: newPlan },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Plan updated successfully');
      fetchUsers();
      setEditingUser(null);
      setNewPlan('');
    } catch (error) {
      toast.error('Failed to update plan');
    }
  };

  const handleUpdateRole = async () => {
    if (!editingUser || !newRole) return;

    try {
      await axios.put(
        `${API_URL}/admin/users/${editingUser.id}/role`,
        { role: newRole },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Role updated successfully');
      fetchUsers();
      setEditingUser(null);
      setNewRole('');
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
            Admin Dashboard
          </h1>
          <p className="text-muted-foreground">Manage users, credits, and monitor system activity</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-card border border-border rounded-xl p-6" data-testid="stat-total-users">
            <div className="flex items-center justify-between mb-2">
              <Users className="h-8 w-8 text-primary" />
            </div>
            <div className="space-y-1">
              <p className="text-muted-foreground text-sm">Total Users</p>
              <p className="font-mono text-3xl font-bold">{stats?.total_users || 0}</p>
            </div>
          </div>

          <div className="bg-card border border-border rounded-xl p-6" data-testid="stat-total-scans">
            <div className="flex items-center justify-between mb-2">
              <FileSearch className="h-8 w-8 text-primary" />
            </div>
            <div className="space-y-1">
              <p className="text-muted-foreground text-sm">Total Scans</p>
              <p className="font-mono text-3xl font-bold">{stats?.total_scans || 0}</p>
            </div>
          </div>

          <div className="bg-card border border-border rounded-xl p-6" data-testid="stat-premium-users">
            <div className="flex items-center justify-between mb-2">
              <Crown className="h-8 w-8 text-yellow-400" />
            </div>
            <div className="space-y-1">
              <p className="text-muted-foreground text-sm">Premium Users</p>
              <p className="font-mono text-3xl font-bold text-yellow-400">{stats?.premium_users || 0}</p>
            </div>
          </div>

          <div className="bg-card border border-border rounded-xl p-6" data-testid="stat-free-users">
            <div className="flex items-center justify-between mb-2">
              <TrendingUp className="h-8 w-8 text-green-400" />
            </div>
            <div className="space-y-1">
              <p className="text-muted-foreground text-sm">Free Users</p>
              <p className="font-mono text-3xl font-bold text-green-400">{stats?.free_users || 0}</p>
            </div>
          </div>
        </div>

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
                className="pl-10 bg-black/50 border-border/50 focus:border-primary/50"
                data-testid="user-search-input"
              />
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-4 font-semibold">Name</th>
                  <th className="text-left py-3 px-4 font-semibold">Email</th>
                  <th className="text-left py-3 px-4 font-semibold">Plan</th>
                  <th className="text-left py-3 px-4 font-semibold">Credits</th>
                  <th className="text-left py-3 px-4 font-semibold">Role</th>
                  <th className="text-left py-3 px-4 font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u, index) => (
                  <tr key={u.id} className="border-b border-border/50 hover:bg-accent/30" data-testid={`user-row-${index}`}>
                    <td className="py-3 px-4" data-testid={`user-name-${index}`}>{u.name}</td>
                    <td className="py-3 px-4 font-mono text-sm" data-testid={`user-email-${index}`}>{u.email}</td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-mono uppercase ${u.plan === 'premium' ? 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20' : 'bg-zinc-800 text-zinc-400 border border-zinc-700'}`} data-testid={`user-plan-${index}`}>
                        {u.plan}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono font-semibold" data-testid={`user-credits-${index}`}>{u.credits}</td>
                    <td className="py-3 px-4 font-mono text-xs uppercase" data-testid={`user-role-${index}`}>{u.role}</td>
                    <td className="py-3 px-4">
                      <div className="flex items-center space-x-2">
                        <Dialog>
                          <DialogTrigger asChild>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setEditingUser(u);
                                setNewCredits(u.credits.toString());
                              }}
                              data-testid={`edit-credits-btn-${index}`}
                            >
                              <Edit className="h-4 w-4" />
                            </Button>
                          </DialogTrigger>
                          <DialogContent>
                            <DialogHeader>
                              <DialogTitle>Edit Credits - {editingUser?.name}</DialogTitle>
                            </DialogHeader>
                            <div className="space-y-4 pt-4">
                              <div>
                                <Label>Credits</Label>
                                <Input
                                  type="number"
                                  value={newCredits}
                                  onChange={(e) => setNewCredits(e.target.value)}
                                  className="mt-2"
                                  data-testid="credits-input"
                                />
                              </div>
                              <Button onClick={handleUpdateCredits} className="w-full" data-testid="save-credits-btn">
                                Save Credits
                              </Button>
                            </div>
                          </DialogContent>
                        </Dialog>

                        <Dialog>
                          <DialogTrigger asChild>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setEditingUser(u);
                                setNewPlan(u.plan);
                              }}
                              data-testid={`edit-plan-btn-${index}`}
                            >
                              <Crown className="h-4 w-4" />
                            </Button>
                          </DialogTrigger>
                          <DialogContent>
                            <DialogHeader>
                              <DialogTitle>Edit Plan - {editingUser?.name}</DialogTitle>
                            </DialogHeader>
                            <div className="space-y-4 pt-4">
                              <div>
                                <Label>Plan</Label>
                                <Select value={newPlan} onValueChange={setNewPlan}>
                                  <SelectTrigger className="mt-2" data-testid="plan-select">
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="free">Free</SelectItem>
                                    <SelectItem value="premium">Premium</SelectItem>
                                  </SelectContent>
                                </Select>
                              </div>
                              <Button onClick={handleUpdatePlan} className="w-full" data-testid="save-plan-btn">
                                Save Plan
                              </Button>
                            </div>
                          </DialogContent>
                        </Dialog>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default AdminDashboard;