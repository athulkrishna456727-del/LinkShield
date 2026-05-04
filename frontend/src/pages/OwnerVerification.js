import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { Shield, FileCheck, IdCard, Camera, CheckCircle2, XCircle, Eye, RefreshCw, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL + '/api';

const STATUS_COLORS = {
  pending_docs: 'border-yellow-400/30 bg-yellow-400/5 text-yellow-300',
  pending_company: 'border-orange-400/30 bg-orange-400/5 text-orange-300',
  pending_owner: 'border-blue-400/30 bg-blue-400/5 text-blue-300',
  approved: 'border-green-400/30 bg-green-400/5 text-green-300',
  rejected: 'border-red-400/30 bg-red-400/5 text-red-300',
  expired: 'border-zinc-700 bg-zinc-800 text-zinc-300',
};

const OwnerVerification = () => {
  const { token, user } = useAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [notes, setNotes] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => { fetchAll(); }, []);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_URL}/owner/verification`, { headers: { Authorization: `Bearer ${token}` } });
      setItems(res.data.verifications || []);
    } catch (e) {
      toast.error('Failed to load (owner role required)');
    } finally { setLoading(false); }
  };

  const fileUrl = (id, kind) => `${API_URL}/owner/verification/${id}/file/${kind}`;

  const decide = async (action) => {
    if (!selected) return;
    setBusy(true);
    try {
      await axios.post(`${API_URL}/owner/verification/${selected.id}/${action}`, { notes }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success(`Request ${action}d`);
      setSelected(null);
      setNotes('');
      await fetchAll();
    } catch (e) {
      toast.error(e.response?.data?.detail || `${action} failed`);
    } finally { setBusy(false); }
  };

  const revoke = async (id) => {
    if (!window.confirm('Revoke network-scanner access for this user?')) return;
    setBusy(true);
    try {
      await axios.post(`${API_URL}/owner/verification/${id}/revoke`, {}, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Access revoked');
      await fetchAll();
    } catch (e) {
      toast.error('Revoke failed');
    } finally { setBusy(false); }
  };

  if (user?.role !== 'owner') {
    return <Layout><div className="py-20 text-center"><AlertTriangle className="h-12 w-12 text-red-400 mx-auto mb-4" /><p>Owner access required.</p></div></Layout>;
  }

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 py-10" data-testid="owner-verification-page">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="font-heading text-3xl font-bold flex items-center"><Shield className="h-7 w-7 text-primary mr-3" />Enterprise Verification Queue</h1>
            <p className="text-muted-foreground mt-1">{items.length} request(s) total</p>
          </div>
          <Button variant="outline" onClick={fetchAll} disabled={loading} data-testid="refresh-btn"><RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />Refresh</Button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1 space-y-3" data-testid="verification-list">
            {items.length === 0 && !loading && <p className="text-muted-foreground text-center py-12">No requests yet</p>}
            {items.map(v => (
              <button
                key={v.id}
                onClick={() => setSelected(v)}
                className={`w-full text-left bg-card border rounded-xl p-4 transition-all hover:border-primary/50 ${selected?.id === v.id ? 'border-primary ring-1 ring-primary/30' : 'border-border'}`}
                data-testid={`verif-item-${v.id}`}
              >
                <div className="flex items-start justify-between mb-2">
                  <span className="font-semibold truncate" title={v.company_name}>{v.company_name}</span>
                  <span className={`px-2 py-0.5 text-[10px] font-mono uppercase rounded border ${STATUS_COLORS[v.status] || 'border-zinc-700'}`}>{v.status.replace('_', ' ')}</span>
                </div>
                <p className="text-xs font-mono text-muted-foreground truncate">{v.user_email}</p>
                <p className="text-xs text-muted-foreground mt-1">{new Date(v.submitted_at).toLocaleString()}</p>
              </button>
            ))}
          </div>

          <div className="lg:col-span-2">
            {!selected ? (
              <div className="bg-card border border-border rounded-xl p-12 text-center">
                <Shield className="h-12 w-12 text-muted-foreground mx-auto mb-4 opacity-50" />
                <p className="text-muted-foreground">Select a request to review</p>
              </div>
            ) : (
              <div className="bg-card border border-border rounded-xl p-6 space-y-5" data-testid="verification-detail">
                <div className="flex items-start justify-between">
                  <div>
                    <h2 className="font-heading text-xl font-bold">{selected.company_name}</h2>
                    <p className="text-sm font-mono text-muted-foreground">{selected.company_domain}</p>
                  </div>
                  <span className={`px-3 py-1 text-xs font-mono uppercase rounded border ${STATUS_COLORS[selected.status]}`}>{selected.status.replace('_', ' ')}</span>
                </div>

                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div><span className="text-muted-foreground">User:</span> <span className="font-mono">{selected.user_email}</span></div>
                  <div><span className="text-muted-foreground">Submitted email:</span> <span className="font-mono">{selected.submitted_email}</span></div>
                  <div><span className="text-muted-foreground">Submitted:</span> <span className="font-mono">{new Date(selected.submitted_at).toLocaleString()}</span></div>
                  <div><span className="text-muted-foreground">Company email verified:</span> {selected.company_email_verified ? <span className="text-green-400">✓ Yes</span> : <span className="text-orange-400">✗ Pending</span>}</div>
                  {selected.face_match_score !== null && selected.face_match_score !== undefined && (
                    <div><span className="text-muted-foreground">Face match:</span> <span className="font-mono">{(selected.face_match_score * 100).toFixed(0)}%</span> {selected.face_match_simulated && <span className="text-xs text-yellow-400">(sim)</span>}</div>
                  )}
                  {selected.letter_domain_extracted && (
                    <div><span className="text-muted-foreground">Letter domain:</span> <span className="font-mono">{selected.letter_domain_extracted}</span></div>
                  )}
                  {selected.expires_at && <div><span className="text-muted-foreground">Expires:</span> <span className="font-mono">{new Date(selected.expires_at).toLocaleString()}</span></div>}
                  {selected.ip_ranges?.length > 0 && (
                    <div className="col-span-2"><span className="text-muted-foreground">IP ranges:</span> <span className="font-mono text-xs">{selected.ip_ranges.join(', ')}</span></div>
                  )}
                </div>

                <div className="grid grid-cols-3 gap-3">
                  {[
                    { kind: 'auth_letter', label: 'Auth Letter', icon: FileCheck },
                    { kind: 'id_card', label: 'ID Card', icon: IdCard },
                    { kind: 'selfie', label: 'Selfie', icon: Camera },
                  ].map(({ kind, label, icon: Icon }) => (
                    <a
                      key={kind}
                      href={fileUrl(selected.id, kind) + `?t=${token}`}
                      target="_blank"
                      rel="noreferrer"
                      onClick={async (e) => {
                        e.preventDefault();
                        try {
                          const res = await axios.get(fileUrl(selected.id, kind), { headers: { Authorization: `Bearer ${token}` }, responseType: 'blob' });
                          const url = window.URL.createObjectURL(res.data);
                          window.open(url, '_blank');
                        } catch { toast.error('File missing'); }
                      }}
                      className="bg-black/40 border border-border hover:border-primary/50 rounded-lg p-3 text-center transition"
                      data-testid={`view-${kind}-btn`}
                    >
                      <Icon className="h-6 w-6 text-primary mx-auto mb-1" />
                      <p className="text-xs font-medium">{label}</p>
                      <p className="text-[10px] text-muted-foreground flex items-center justify-center mt-1"><Eye className="h-3 w-3 mr-1" />View</p>
                    </a>
                  ))}
                </div>

                {selected.device_fingerprint && (
                  <details className="bg-black/30 border border-border rounded-lg p-3">
                    <summary className="cursor-pointer text-sm font-medium">Device Fingerprint ({selected.device_fingerprint?.visitorId?.slice(0, 12) || 'unknown'}…)</summary>
                    <pre className="mt-2 text-[10px] font-mono overflow-auto max-h-40 text-muted-foreground">{JSON.stringify(selected.device_fingerprint, null, 2)}</pre>
                  </details>
                )}

                {['pending_docs', 'pending_company', 'pending_owner'].includes(selected.status) && (
                  <div className="space-y-3 pt-3 border-t border-border">
                    <Textarea placeholder="Decision notes (optional)" value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} data-testid="decision-notes" />
                    <div className="flex gap-3">
                      <Button onClick={() => decide('approve')} disabled={busy} className="flex-1 bg-green-500 hover:bg-green-600 text-white" data-testid="approve-btn">
                        <CheckCircle2 className="h-4 w-4 mr-2" />Approve (30 days)
                      </Button>
                      <Button onClick={() => decide('reject')} disabled={busy} variant="destructive" className="flex-1" data-testid="reject-btn">
                        <XCircle className="h-4 w-4 mr-2" />Reject
                      </Button>
                    </div>
                  </div>
                )}

                {selected.status === 'approved' && (
                  <Button onClick={() => revoke(selected.id)} disabled={busy} variant="outline" className="w-full text-red-400 border-red-400/30 hover:bg-red-400/10" data-testid="revoke-btn">
                    Revoke Access
                  </Button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default OwnerVerification;
