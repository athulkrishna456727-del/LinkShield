import React from 'react';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';
import { User, Mail, CreditCard, Shield, Calendar } from 'lucide-react';

const Profile = () => {
  const { user } = useAuth();

  return (
    <Layout>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8" data-testid="profile-page">
        <div className="mb-8">
          <h1 className="font-heading text-4xl font-bold mb-2">Profile</h1>
          <p className="text-muted-foreground">Manage your account information</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-card border border-border rounded-xl p-6">
            <h2 className="font-heading text-xl font-semibold mb-4">Account Details</h2>
            <div className="space-y-4">
              <div className="flex items-start space-x-3">
                <User className="h-5 w-5 text-primary mt-1" />
                <div className="flex-1">
                  <p className="text-sm text-muted-foreground">Name</p>
                  <p className="font-semibold" data-testid="profile-name">{user?.name}</p>
                </div>
              </div>
              <div className="flex items-start space-x-3">
                <Mail className="h-5 w-5 text-primary mt-1" />
                <div className="flex-1">
                  <p className="text-sm text-muted-foreground">Email</p>
                  <p className="font-mono text-sm" data-testid="profile-email">{user?.email}</p>
                </div>
              </div>
              <div className="flex items-start space-x-3">
                <Shield className="h-5 w-5 text-primary mt-1" />
                <div className="flex-1">
                  <p className="text-sm text-muted-foreground">Role</p>
                  <p className="font-semibold uppercase" data-testid="profile-role">{user?.role}</p>
                </div>
              </div>
              <div className="flex items-start space-x-3">
                <Calendar className="h-5 w-5 text-primary mt-1" />
                <div className="flex-1">
                  <p className="text-sm text-muted-foreground">Member Since</p>
                  <p className="font-semibold" data-testid="profile-created">
                    {user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-card border border-border rounded-xl p-6">
            <h2 className="font-heading text-xl font-semibold mb-4">Subscription</h2>
            <div className="space-y-4">
              <div className="bg-accent/30 rounded-lg p-4 border border-border/50">
                <p className="text-sm text-muted-foreground mb-2">Current Plan</p>
                <p className="font-heading text-3xl font-bold uppercase text-primary" data-testid="profile-plan">
                  {user?.plan}
                </p>
              </div>
              <div className="bg-accent/30 rounded-lg p-4 border border-border/50">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">Credits Balance</p>
                    <p className="font-mono text-2xl font-bold" data-testid="profile-credits">{user?.credits}</p>
                  </div>
                  <CreditCard className="h-8 w-8 text-primary" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default Profile;