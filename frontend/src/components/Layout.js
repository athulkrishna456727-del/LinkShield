import React from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Shield, LogOut, User, LayoutDashboard, FileSearch, History, CreditCard, Settings, Crown } from 'lucide-react';
import { Button } from './ui/button';

const Layout = ({ children }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (path) => location.pathname === path;

  return (
    <div className="min-h-screen bg-background">
      <nav className="sticky top-0 z-50 bg-black/40 backdrop-blur-xl border-b border-white/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link to={user ? "/dashboard" : "/"} className="flex items-center space-x-2 group">
              <Shield className="h-8 w-8 text-primary" />
              <span className="font-heading text-2xl font-bold text-foreground">Link Shield</span>
            </Link>

            {user && (
              <div className="flex items-center space-x-6">
                <Link
                  to="/dashboard"
                  className={`flex items-center space-x-2 px-3 py-2 rounded-md transition-colors ${
                    isActive('/dashboard') ? 'bg-accent text-primary' : 'text-muted-foreground hover:text-foreground'
                  }`}
                  data-testid="nav-dashboard"
                >
                  <LayoutDashboard className="h-5 w-5" />
                  <span>Dashboard</span>
                </Link>
                <Link
                  to="/scan"
                  className={`flex items-center space-x-2 px-3 py-2 rounded-md transition-colors ${
                    isActive('/scan') ? 'bg-accent text-primary' : 'text-muted-foreground hover:text-foreground'
                  }`}
                  data-testid="nav-scan"
                >
                  <FileSearch className="h-5 w-5" />
                  <span>Scan</span>
                </Link>
                <Link
                  to="/history"
                  className={`flex items-center space-x-2 px-3 py-2 rounded-md transition-colors ${
                    isActive('/history') ? 'bg-accent text-primary' : 'text-muted-foreground hover:text-foreground'
                  }`}
                  data-testid="nav-history"
                >
                  <History className="h-5 w-5" />
                  <span>History</span>
                </Link>

                <div className="flex items-center space-x-4 ml-4 pl-4 border-l border-border">
                  <div className="flex items-center space-x-2 px-3 py-1 bg-card border border-border rounded-lg">
                    <CreditCard className="h-4 w-4 text-primary" />
                    <span className="font-mono text-sm font-semibold text-foreground" data-testid="nav-credits">{user.credits === 999999 ? '\u221E' : user.credits}</span>
                  </div>

                  {user.role === 'owner' && (
                    <Link to="/owner" data-testid="nav-owner">
                      <Button variant="ghost" size="sm" className="flex items-center space-x-2">
                        <Crown className="h-5 w-5 text-yellow-400" />
                      </Button>
                    </Link>
                  )}

                  <Link to="/settings" data-testid="nav-settings">
                    <Button variant="ghost" size="sm" className="flex items-center space-x-2">
                      <Settings className="h-5 w-5" />
                    </Button>
                  </Link>

                  <Link to="/profile" data-testid="nav-profile">
                    <Button variant="ghost" size="sm" className="flex items-center space-x-2">
                      <User className="h-5 w-5" />
                    </Button>
                  </Link>

                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleLogout}
                    className="flex items-center space-x-2"
                    data-testid="nav-logout"
                  >
                    <LogOut className="h-5 w-5" />
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      </nav>

      <main className="grid-pattern min-h-[calc(100vh-4rem)]">{children}</main>
    </div>
  );
};

export default Layout;