import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';
import { Key, Copy, Trash2, RefreshCw, Shield, Lock } from 'lucide-react';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';

const API_URL = process.env.REACT_APP_BACKEND_URL + '/api';

const ApiKeys = () => {
  const { user, token } = useAuth();
  const navigate = useNavigate();
  const [usage, setUsage] = useState(null);
  const [newKey, setNewKey] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user?.plan === 'free') {
      navigate('/plans');
      return;
    }
    fetchUsage();
  }, [user]);

  const fetchUsage = async () => {
    try {
      const res = await axios.get(`${API_URL}/apikey/usage`, { headers: { Authorization: `Bearer ${token}` } });
      setUsage(res.data);
    } catch (error) {
      if (error.response?.status === 403) navigate('/plans');
    }
  };

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const res = await axios.post(`${API_URL}/apikey/generate`, {}, { headers: { Authorization: `Bearer ${token}` } });
      setNewKey(res.data.api_key);
      toast.success('API key generated!');
      fetchUsage();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to generate key');
    } finally {
      setLoading(false);
    }
  };

  const handleRevoke = async () => {
    if (!window.confirm('Are you sure? This will invalidate your current API key.')) return;
    try {
      await axios.delete(`${API_URL}/apikey/revoke`, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('API key revoked');
      setNewKey(null);
      fetchUsage();
    } catch (error) {
      toast.error('Failed to revoke key');
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  if (user?.plan === 'free') return null;

  return (
    <Layout>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8" data-testid="api-keys-page">
        <div className="mb-8">
          <h1 className="font-heading text-4xl font-bold mb-2 flex items-center">
            <Key className="h-10 w-10 text-primary mr-3" />
            API Keys
          </h1>
          <p className="text-muted-foreground">Access Link Shield scanning via REST API</p>
        </div>

        <div className="space-y-6">
          {newKey && (
            <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-6" data-testid="new-key-display">
              <h3 className="font-semibold text-green-400 mb-2 flex items-center">
                <Shield className="h-5 w-5 mr-2" /> New API Key Generated
              </h3>
              <p className="text-xs text-muted-foreground mb-3">Copy this key now. It won't be shown again in full.</p>
              <div className="flex items-center gap-2">
                <code className="flex-1 bg-black/50 p-3 rounded font-mono text-sm text-green-300 break-all">{newKey}</code>
                <Button variant="ghost" size="sm" onClick={() => copyToClipboard(newKey)}>
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}

          <div className="bg-card border border-border rounded-xl p-6">
            <h2 className="font-heading text-2xl font-semibold mb-4">Your API Key</h2>
            {usage?.has_key ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-accent/30 rounded-lg">
                  <div>
                    <p className="text-sm text-muted-foreground">Key Preview</p>
                    <code className="font-mono text-sm">{usage.key_preview}</code>
                  </div>
                  <Button variant="destructive" size="sm" onClick={handleRevoke} data-testid="revoke-key-btn">
                    <Trash2 className="h-4 w-4 mr-2" /> Revoke
                  </Button>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 bg-accent/20 rounded-lg">
                    <p className="text-sm text-muted-foreground">Calls Today</p>
                    <p className="font-mono text-2xl font-bold">{usage.calls_today}</p>
                  </div>
                  <div className="p-4 bg-accent/20 rounded-lg">
                    <p className="text-sm text-muted-foreground">Daily Limit</p>
                    <p className="font-mono text-2xl font-bold">{usage.daily_limit?.toLocaleString()}</p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-8">
                <Lock className="h-12 w-12 text-muted-foreground mx-auto mb-3" />
                <p className="text-muted-foreground mb-4">No API key generated yet</p>
                <Button onClick={handleGenerate} disabled={loading} data-testid="generate-key-btn">
                  <Key className="h-4 w-4 mr-2" /> {loading ? 'Generating...' : 'Generate API Key'}
                </Button>
              </div>
            )}
            {usage?.has_key && (
              <Button onClick={handleGenerate} disabled={loading} variant="outline" className="mt-4" data-testid="regenerate-key-btn">
                <RefreshCw className="h-4 w-4 mr-2" /> Regenerate Key
              </Button>
            )}
          </div>

          <div className="bg-card border border-border rounded-xl p-6">
            <h2 className="font-heading text-xl font-semibold mb-4">Usage Example</h2>
            <pre className="bg-black/50 p-4 rounded-lg text-sm font-mono text-green-300 overflow-x-auto">
{`curl -X POST "${process.env.REACT_APP_BACKEND_URL}/api/v1/scan/url" \\
  -H "X-API-Key: YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"url": "https://example.com"}'`}
            </pre>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default ApiKeys;
