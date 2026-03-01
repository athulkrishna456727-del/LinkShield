import React, { useState } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';
import { Mail, Lock, Save } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Separator } from '../components/ui/separator';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL + '/api';

const AccountSettings = () => {
  const { user, token, refreshUser } = useAuth();
  const [emailForm, setEmailForm] = useState({
    currentPassword: '',
    newEmail: ''
  });
  const [passwordForm, setPasswordForm] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  });
  const [loading, setLoading] = useState(false);

  const handleEmailChange = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await axios.put(
        `${API_URL}/account/email`,
        {
          current_password: emailForm.currentPassword,
          new_email: emailForm.newEmail
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Email updated successfully');
      setEmailForm({ currentPassword: '', newEmail: '' });
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update email');
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      toast.error('New passwords do not match');
      return;
    }
    if (passwordForm.newPassword.length < 6) {
      toast.error('Password must be at least 6 characters');
      return;
    }
    setLoading(true);
    try {
      await axios.put(
        `${API_URL}/account/password`,
        {
          current_password: passwordForm.currentPassword,
          new_password: passwordForm.newPassword
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Password updated successfully');
      setPasswordForm({ currentPassword: '', newPassword: '', confirmPassword: '' });
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8" data-testid="account-settings-page">
        <div className="mb-8">
          <h1 className="font-heading text-4xl font-bold mb-2">Account Settings</h1>
          <p className="text-muted-foreground">Manage your account security and preferences</p>
        </div>

        <div className="space-y-6">
          <div className="bg-card border border-border rounded-xl p-6">
            <h2 className="font-heading text-2xl font-semibold mb-6 flex items-center">
              <Mail className="h-6 w-6 text-primary mr-2" />
              Change Email
            </h2>
            <form onSubmit={handleEmailChange} className="space-y-4" data-testid="email-change-form">
              <div>
                <Label htmlFor="current-email">Current Email</Label>
                <Input
                  id="current-email"
                  type="email"
                  value={user?.email}
                  disabled
                  className="bg-accent/30 mt-2"
                />
              </div>
              <div>
                <Label htmlFor="new-email">New Email</Label>
                <Input
                  id="new-email"
                  type="email"
                  placeholder="newemail@example.com"
                  value={emailForm.newEmail}
                  onChange={(e) => setEmailForm({ ...emailForm, newEmail: e.target.value })}
                  required
                  className="bg-black/50 border-border/50 focus:border-primary/50 mt-2"
                  data-testid="new-email-input"
                />
              </div>
              <div>
                <Label htmlFor="email-password">Current Password</Label>
                <Input
                  id="email-password"
                  type="password"
                  placeholder="Enter your current password"
                  value={emailForm.currentPassword}
                  onChange={(e) => setEmailForm({ ...emailForm, currentPassword: e.target.value })}
                  required
                  className="bg-black/50 border-border/50 focus:border-primary/50 mt-2"
                  data-testid="email-password-input"
                />
              </div>
              <Button
                type="submit"
                disabled={loading}
                className="bg-primary text-primary-foreground hover:bg-primary/90"
                data-testid="save-email-btn"
              >
                <Save className="h-4 w-4 mr-2" />
                {loading ? 'Saving...' : 'Save Email'}
              </Button>
            </form>
          </div>

          <div className="bg-card border border-border rounded-xl p-6">
            <h2 className="font-heading text-2xl font-semibold mb-6 flex items-center">
              <Lock className="h-6 w-6 text-primary mr-2" />
              Change Password
            </h2>
            <form onSubmit={handlePasswordChange} className="space-y-4" data-testid="password-change-form">
              <div>
                <Label htmlFor="current-password">Current Password</Label>
                <Input
                  id="current-password"
                  type="password"
                  placeholder="Enter your current password"
                  value={passwordForm.currentPassword}
                  onChange={(e) => setPasswordForm({ ...passwordForm, currentPassword: e.target.value })}
                  required
                  className="bg-black/50 border-border/50 focus:border-primary/50 mt-2"
                  data-testid="current-password-input"
                />
              </div>
              <div>
                <Label htmlFor="new-password">New Password</Label>
                <Input
                  id="new-password"
                  type="password"
                  placeholder="Enter new password (min 6 characters)"
                  value={passwordForm.newPassword}
                  onChange={(e) => setPasswordForm({ ...passwordForm, newPassword: e.target.value })}
                  required
                  minLength={6}
                  className="bg-black/50 border-border/50 focus:border-primary/50 mt-2"
                  data-testid="new-password-input"
                />
              </div>
              <div>
                <Label htmlFor="confirm-password">Confirm New Password</Label>
                <Input
                  id="confirm-password"
                  type="password"
                  placeholder="Confirm new password"
                  value={passwordForm.confirmPassword}
                  onChange={(e) => setPasswordForm({ ...passwordForm, confirmPassword: e.target.value })}
                  required
                  minLength={6}
                  className="bg-black/50 border-border/50 focus:border-primary/50 mt-2"
                  data-testid="confirm-password-input"
                />
              </div>
              <Button
                type="submit"
                disabled={loading}
                className="bg-primary text-primary-foreground hover:bg-primary/90"
                data-testid="save-password-btn"
              >
                <Save className="h-4 w-4 mr-2" />
                {loading ? 'Saving...' : 'Save Password'}
              </Button>
            </form>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default AccountSettings;