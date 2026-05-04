import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Network, Loader2, Play, Lock, Server, AlertTriangle, ChevronRight } from 'lucide-react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL + '/api';

const PROTOCOL_PRESETS = [
  { id: 'tcp_common', label: 'TCP Common (22, 445, 3389, 5985, 5986)', ports: '22,445,3389,5985,5986' },
  { id: 'web', label: 'Web (80, 443, 8080, 8443)', ports: '80,443,8080,8443' },
  { id: 'all_admin', label: 'Admin Services (full)', ports: '22,80,135,139,443,445,3389,5985,5986,8080,8443' },
];

const StatusPill = ({ s }) => {
  const map = {
    queued: 'bg-zinc-700 text-zinc-200',
    running: 'bg-blue-500/20 text-blue-300 animate-pulse',
    completed: 'bg-green-500/20 text-green-300',
    failed: 'bg-red-500/20 text-red-300',
  };
  return <span className={`px-2 py-0.5 text-[10px] font-mono uppercase rounded ${map[s] || 'bg-zinc-700'}`}>{s}</span>;
};

const NetworkScanner = () => {
  const { token, user } = useAuth();
  const nav = useNavigate();
  const [permission, setPermission] = useState(null); // null=loading
  const [scans, setScans] = useState([]);
  const [ipRanges, setIpRanges] = useState('');
  const [credUser, setCredUser] = useState('');
  const [credPass, setCredPass] = useState('');
  const [preset, setPreset] = useState(PROTOCOL_PRESETS[0]);
  const [customPorts, setCustomPorts] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => { boot(); /* eslint-disable-next-line */ }, []);

  const boot = async () => {
    try {
      const s = await axios.get(`${API_URL}/enterprise/verify/status`, { headers: { Authorization: `Bearer ${token}` } });
      const allowed = s.data.has_network_scan_permission || user?.role === 'owner';
      setPermission(allowed);
      if (allowed) await fetchScans();
    } catch { setPermission(false); }
  };

  const fetchScans = async () => {
    try {
      const res = await axios.get(`${API_URL}/enterprise/network-scans`, { headers: { Authorization: `Bearer ${token}` } });
      setScans(res.data.scans || []);
    } catch { /* ignore */ }
  };

  const startScan = async (e) => {
    e.preventDefault();
    const ranges = ipRanges.split(/[,\n]/).map(s => s.trim()).filter(Boolean);
    if (ranges.length === 0) { toast.error('Provide at least one IP / CIDR / range'); return; }
    setSubmitting(true);
    try {
      const ports = customPorts.trim() || preset.ports;
      const body = {
        ip_ranges: ranges,
        ports,
        protocols: ['tcp'],
        credentials_used: !!(credUser && credPass), // metadata only
      };
      const res = await axios.post(`${API_URL}/enterprise/start-scan`, body, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Scan queued');
      nav(`/enterprise/network-scan/${res.data.id}`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Scan failed');
    } finally { setSubmitting(false); }
  };

  if (permission === null) return <Layout><div className="py-20 text-center text-muted-foreground">Loading…</div></Layout>;

  if (!permission) {
    return (
      <Layout>
        <div className="max-w-2xl mx-auto px-4 py-20 text-center" data-testid="locked-banner">
          <Lock className="h-16 w-16 text-orange-400 mx-auto mb-4" />
          <h1 className="font-heading text-3xl font-bold mb-2">Verification Required</h1>
          <p className="text-muted-foreground mb-6">The Enterprise Network Defense Scanner is gated by a strict verification process. Submit your authorization documents to request access.</p>
          <Button onClick={() => nav('/enterprise/verification')} className="bg-primary text-primary-foreground" data-testid="goto-verification-btn">
            Start Verification <ChevronRight className="h-4 w-4 ml-2" />
          </Button>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-6xl mx-auto px-4 py-10" data-testid="network-scanner-page">
        <div className="mb-8">
          <h1 className="font-heading text-3xl font-bold flex items-center"><Network className="h-7 w-7 text-primary mr-3" />Network Defense Scanner</h1>
          <p className="text-muted-foreground mt-1">Discover lateral-movement paths across your authorized IP ranges.</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <form onSubmit={startScan} className="bg-card border border-border rounded-xl p-6 space-y-5" data-testid="scan-launch-form">
            <h2 className="font-heading text-xl font-semibold flex items-center"><Server className="h-5 w-5 text-primary mr-2" />Launch a Scan</h2>

            <div>
              <label className="text-sm font-medium mb-2 block">Targets <span className="text-xs text-muted-foreground">(IP, CIDR, or range — comma/newline separated)</span></label>
              <Textarea value={ipRanges} onChange={(e) => setIpRanges(e.target.value)} placeholder={'10.0.0.0/24\n192.168.1.1-192.168.1.50\n127.0.0.1'} rows={4} className="font-mono" required data-testid="ip-ranges-textarea" />
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">Port profile</label>
              <div className="space-y-2">
                {PROTOCOL_PRESETS.map(p => (
                  <label key={p.id} className={`flex items-start p-3 rounded-lg border cursor-pointer transition ${preset.id === p.id ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/30'}`}>
                    <input type="radio" name="preset" checked={preset.id === p.id} onChange={() => setPreset(p)} className="mt-1 mr-3 accent-primary" data-testid={`preset-${p.id}`} />
                    <div className="flex-1">
                      <p className="text-sm font-medium">{p.label}</p>
                      <p className="text-xs font-mono text-muted-foreground">{p.ports}</p>
                    </div>
                  </label>
                ))}
              </div>
              <Input value={customPorts} onChange={(e) => setCustomPorts(e.target.value)} placeholder="Or custom ports e.g. 22,80,8443" className="mt-3 font-mono" data-testid="custom-ports-input" />
            </div>

            <details className="bg-black/20 border border-border rounded-lg p-3">
              <summary className="cursor-pointer text-sm font-medium">Optional credentials (transit only — never stored)</summary>
              <div className="mt-3 grid grid-cols-2 gap-3">
                <Input placeholder="username" value={credUser} onChange={(e) => setCredUser(e.target.value)} data-testid="cred-user" />
                <Input placeholder="password" type="password" value={credPass} onChange={(e) => setCredPass(e.target.value)} data-testid="cred-pass" />
              </div>
              <p className="mt-2 text-[10px] text-muted-foreground"><AlertTriangle className="h-3 w-3 inline mr-1 text-orange-400" />Credentials are sent over HTTPS and discarded after use. Not persisted.</p>
            </details>

            <Button type="submit" disabled={submitting} className="w-full bg-primary text-primary-foreground hover:bg-primary/90 h-12" data-testid="start-scan-btn">
              {submitting ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Queueing…</> : <><Play className="h-4 w-4 mr-2" />Start Network Scan</>}
            </Button>
          </form>

          <div className="bg-card border border-border rounded-xl p-6">
            <h2 className="font-heading text-xl font-semibold mb-4">Recent Scans</h2>
            {scans.length === 0 ? (
              <p className="text-muted-foreground text-center py-8">No scans yet</p>
            ) : (
              <div className="space-y-2" data-testid="recent-scans-list">
                {scans.slice(0, 15).map(s => (
                  <button
                    key={s.id}
                    onClick={() => nav(`/enterprise/network-scan/${s.id}`)}
                    className="w-full text-left bg-black/30 hover:bg-black/50 border border-border rounded-lg p-3 transition"
                    data-testid={`scan-row-${s.id}`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono text-sm truncate">{(s.ip_ranges || []).join(', ').slice(0, 50)}</span>
                      <StatusPill s={s.status} />
                    </div>
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>{new Date(s.started_at).toLocaleString()}</span>
                      <span className="font-mono">{s.hosts_total || 0} hosts</span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default NetworkScanner;
