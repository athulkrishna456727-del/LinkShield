import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Shield, Mail, Lock, User, Key, AtSign } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';

const Signup = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [username, setUsername] = useState('');
  const [loading, setLoading] = useState(false);
  const [showOTP, setShowOTP] = useState(false);
  const [otpCode, setOtpCode] = useState('');
  const [otpLoading, setOtpLoading] = useState(false);
  const { signup, verifyOTP, resendOTP } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const result = await signup(email, password, name, username);
      
      // Check if OTP verification is required
      if (result.requiresVerification) {
        setShowOTP(true);
        toast.success('Account created! Please verify your email with OTP');
      } else {
        toast.success('Account created successfully!');
        navigate('/dashboard');
      }
    } catch (error) {
      const errorMessage = error.response?.data?.detail || 
                          error.response?.data?.message || 
                          error.message || 
                          'Signup failed';
      toast.error(typeof errorMessage === 'string' ? errorMessage : 'Signup failed');
    } finally {
      setLoading(false);
    }
  };

  const handleOTPSubmit = async (e) => {
    e.preventDefault();
    setOtpLoading(true);
    try {
      await verifyOTP(email, otpCode);
      toast.success('Email verified! Account is now active!');
      navigate('/dashboard');
    } catch (error) {
      const errorMessage = error.response?.data?.detail || 
                          error.response?.data?.message || 
                          error.message || 
                          'Invalid OTP';
      toast.error(typeof errorMessage === 'string' ? errorMessage : 'Invalid OTP');
    } finally {
      setOtpLoading(false);
    }
  };

  const handleResendOTP = async () => {
    try {
      await resendOTP(email);
      toast.success('New OTP sent to your email');
    } catch (error) {
      const errorMessage = error.response?.data?.detail || 
                          error.response?.data?.message || 
                          'Failed to resend OTP';
      toast.error(typeof errorMessage === 'string' ? errorMessage : 'Failed to resend OTP');
    }
  };

  if (showOTP) {
    return (
      <div className="min-h-screen bg-background grid-pattern flex items-center justify-center px-4">
        <div className="w-full max-w-md">
          <div className="bg-card border border-border rounded-xl p-8 space-y-6">
            <div className="flex flex-col items-center space-y-2">
              <Key className="h-12 w-12 text-primary" />
              <h1 className="font-heading text-3xl font-bold">Verify Email</h1>
              <p className="text-muted-foreground text-center">
                Enter the 6-digit code sent to {email}
              </p>
            </div>

            <form onSubmit={handleOTPSubmit} className="space-y-4" data-testid="otp-form">
              <div className="space-y-2">
                <Label htmlFor="otp">OTP Code</Label>
                <Input
                  id="otp"
                  type="text"
                  placeholder="123456"
                  value={otpCode}
                  onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  required
                  maxLength={6}
                  className="bg-black/50 border-border/50 focus:border-primary/50 text-center text-2xl tracking-widest font-mono"
                  data-testid="otp-input"
                />
                <p className="text-xs text-muted-foreground">OTP expires in 10 minutes</p>
              </div>

              <Button
                type="submit"
                disabled={otpLoading || otpCode.length !== 6}
                className="w-full bg-primary text-primary-foreground hover:bg-primary/90"
                data-testid="otp-submit-btn"
              >
                {otpLoading ? 'Verifying...' : 'Verify Email'}
              </Button>
            </form>

            <div className="text-center space-y-2">
              <Button
                variant="ghost"
                onClick={handleResendOTP}
                className="text-sm text-muted-foreground hover:text-primary"
                data-testid="resend-otp-btn"
              >
                Didn't receive code? Resend OTP
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background grid-pattern flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="bg-card border border-border rounded-xl p-8 space-y-6">
          <div className="flex flex-col items-center space-y-2">
            <Shield className="h-12 w-12 text-primary" />
            <h1 className="font-heading text-3xl font-bold">Create Account</h1>
            <p className="text-muted-foreground text-center">Start scanning threats with Link Shield</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4" data-testid="signup-form">
            <div className="space-y-2">
              <Label htmlFor="name" className="flex items-center space-x-2">
                <User className="h-4 w-4" />
                <span>Full Name</span>
              </Label>
              <Input
                id="name"
                type="text"
                placeholder="John Doe"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="bg-black/50 border-border/50 focus:border-primary/50"
                data-testid="signup-name-input"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="username" className="flex items-center space-x-2">
                <AtSign className="h-4 w-4" />
                <span>Username</span>
              </Label>
              <Input
                id="username"
                type="text"
                placeholder="johndoe"
                value={username}
                onChange={(e) => setUsername(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ''))}
                required
                minLength={3}
                maxLength={20}
                className="bg-black/50 border-border/50 focus:border-primary/50"
                data-testid="signup-username-input"
              />
              <p className="text-xs text-muted-foreground">
                3-20 characters, letters, numbers, and underscore only
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="email" className="flex items-center space-x-2">
                <Mail className="h-4 w-4" />
                <span>Email</span>
              </Label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="bg-black/50 border-border/50 focus:border-primary/50"
                data-testid="signup-email-input"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="flex items-center space-x-2">
                <Lock className="h-4 w-4" />
                <span>Password</span>
              </Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
                className="bg-black/50 border-border/50 focus:border-primary/50"
                data-testid="signup-password-input"
              />
            </div>

            <Button
              type="submit"
              disabled={loading}
              className="w-full bg-primary text-primary-foreground hover:bg-primary/90 shadow-[0_0_20px_-5px_rgba(0,255,148,0.4)]"
              data-testid="signup-submit-btn"
            >
              {loading ? 'Creating account...' : 'Create Account'}
            </Button>
          </form>

          <div className="text-center space-y-2">
            <p className="text-sm text-muted-foreground">
              Already have an account?{' '}
              <Link to="/login" className="text-primary hover:underline" data-testid="signup-login-link">
                Sign in
              </Link>
            </p>
            <Link to="/" className="text-sm text-muted-foreground hover:text-foreground" data-testid="signup-home-link">
              Back to home
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Signup;
