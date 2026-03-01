import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, FileSearch, Zap, Lock, BarChart3, Users } from 'lucide-react';
import { Button } from '../components/ui/button';

const Landing = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background">
      <nav className="sticky top-0 z-50 bg-black/40 backdrop-blur-xl border-b border-white/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-2">
              <Shield className="h-8 w-8 text-primary" />
              <span className="font-heading text-2xl font-bold text-foreground">Link Shield</span>
            </div>
            <div className="flex items-center space-x-4">
              <Button variant="ghost" onClick={() => navigate('/login')} data-testid="landing-login-btn">
                Login
              </Button>
              <Button onClick={() => navigate('/signup')} className="bg-primary text-primary-foreground hover:bg-primary/90 shadow-[0_0_20px_-5px_rgba(0,255,148,0.4)]" data-testid="landing-signup-btn">
                Get Started
              </Button>
            </div>
          </div>
        </div>
      </nav>

      <div className="relative overflow-hidden grid-pattern">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_rgba(0,255,148,0.15)_0%,_rgba(2,2,4,0)_70%)]" />
        
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <div className="text-center space-y-8">
            <h1 className="font-heading text-5xl md:text-7xl font-bold tracking-tighter">
              <span className="bg-gradient-to-r from-foreground to-muted-foreground bg-clip-text text-transparent">
                Cybersecurity Scanning
              </span>
              <br />
              <span className="text-primary">Made Simple</span>
            </h1>
            <p className="text-xl md:text-2xl text-muted-foreground max-w-3xl mx-auto">
              Advanced threat intelligence platform for scanning URLs, files, and applications.
              Detect malware, phishing, and malicious content instantly.
            </p>
            <div className="flex items-center justify-center space-x-4 pt-4">
              <Button
                size="lg"
                onClick={() => navigate('/signup')}
                className="bg-primary text-primary-foreground hover:bg-primary/90 shadow-[0_0_20px_-5px_rgba(0,255,148,0.4)] px-8 py-6 text-lg"
                data-testid="hero-get-started-btn"
              >
                Start Scanning Free
              </Button>
              <Button
                size="lg"
                variant="outline"
                onClick={() => navigate('/login')}
                className="border-primary/50 text-primary hover:bg-primary/10 px-8 py-6 text-lg"
                data-testid="hero-login-btn"
              >
                Sign In
              </Button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-24">
            <div className="bg-card border border-border/50 rounded-xl p-8 hover:border-primary/50 transition-all group" data-testid="feature-url-scan">
              <FileSearch className="h-12 w-12 text-primary mb-4" />
              <h3 className="font-heading text-2xl font-semibold mb-2">URL Scanning</h3>
              <p className="text-muted-foreground">
                Analyze suspicious links and domains for phishing attempts and malicious redirects.
              </p>
            </div>

            <div className="bg-card border border-border/50 rounded-xl p-8 hover:border-primary/50 transition-all group" data-testid="feature-file-analysis">
              <Lock className="h-12 w-12 text-primary mb-4" />
              <h3 className="font-heading text-2xl font-semibold mb-2">File Analysis</h3>
              <p className="text-muted-foreground">
                Upload and scan executables, documents, APKs, and archives for malware signatures.
              </p>
            </div>

            <div className="bg-card border border-border/50 rounded-xl p-8 hover:border-primary/50 transition-all group" data-testid="feature-threat-intel">
              <BarChart3 className="h-12 w-12 text-primary mb-4" />
              <h3 className="font-heading text-2xl font-semibold mb-2">Threat Intelligence</h3>
              <p className="text-muted-foreground">
                Extract IOCs including IPs, domains, and file hashes for comprehensive threat analysis.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Landing;