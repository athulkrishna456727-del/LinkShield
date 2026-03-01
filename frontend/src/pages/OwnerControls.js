import React, { useState } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';
import { Crown, UserPlus, UserMinus, Mail, Lock, User } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
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

  if (user?.role !== 'owner') {
    navigate('/dashboard');
    return null;
  }

  const handleCreateAdmin = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await axios.post(
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
      toast.error(error.response?.data?.detail || 'Failed to create admin');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8" data-testid="owner-controls-page">
        <div className="mb-8">
          <h1 className="font-heading text-4xl font-bold mb-2 flex items-center">
            <Crown className="h-10 w-10 text-primary mr-3" />
            Owner Controls
          </h1>
          <p className="text-muted-foreground">Full system control and administrative functions</p>
        </div>

        <div className="grid grid-cols-1 gap-6">
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

          <div className="bg-card border border-border rounded-xl p-6">
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