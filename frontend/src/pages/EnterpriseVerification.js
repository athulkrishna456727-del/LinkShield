import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Shield, FileCheck, IdCard, Camera, Building2, Globe, Loader2, CheckCircle2, AlertCircle, Copy } from 'lucide-react';
import { toast } from 'sonner';
import FingerprintJS from '@fingerprintjs/fingerprintjs';

const API_URL = process.env.REACT_APP_BACKEND_URL + '/api';

const StatusBadge = ({ status }) => {
  const map = {
    pending_docs: { color: 'text-yellow-300 bg-yellow-400/10 border-yellow-400/30', label: 'Documents under review' },
    pending_company: { color: 'text-orange-300 bg-orange-400/10 border-orange-400/30', label: 'Company email verification pending' },
    pending_owner: { color: 'text-blue-300 bg-blue-400/10 border-blue-400/30', label: 'Awaiting owner approval' },
    approved: { color: 'text-green-300 bg-green-400/10 border-green-400/30', label: 'Approved' },
    rejected: { color: 'text-red-300 bg-red-400/10 border-red-400/30', label: 'Rejected' },
    expired: { color: 'text-zinc-300 bg-zinc-700/40 border-zinc-700', label: 'Expired / Revoked' },
  };
  const m = map[status] || { color: 'text-zinc-300', label: status };
  return <span className={`px-2.5 py-1 text-xs font-mono uppercase rounded-full border ${m.color}`} data-testid="verif-status-badge">{m.label}</span>;
};

const FileDrop = ({ label, file, onChange, icon: Icon, testid }) => (
  <div className="space-y-2">
    <label className="flex items-center text-sm font-medium"><Icon className="h-4 w-4 mr-2 text-primary" />{label}</label>
    <div className="border-2 border-dashed border-border rounded-xl p-4 hover:border-primary/50 transition-all bg-black/30">
      <input type="file" accept=".pdf,.png,.jpg,.jpeg,.webp" onChange={onChange} className="block w-full text-sm font-mono text-muted-foreground file:mr-3 file:py-2 file:px-4 file:rounded-md file:border-0 file:bg-primary/20 file:text-primary file:hover:bg-primary/30 cursor-pointer" data-testid={testid} />
      {file && <p className="mt-2 text-xs font-mono text-primary">✓ {file.name} ({(file.size / 1024).toFixed(1)} KB)</p>}
    </div>
  </div>
);

const EnterpriseVerification = () => {
  const { token, user } = useAuth();
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    company_name: '', company_domain: '', submitted_email: '', ip_ranges: '',
  });
  const [authLetter, setAuthLetter] = useState(null);
  const [idCard, setIdCard] = useState(null);
  const [selfie, setSelfie] = useState(null);
  const [verifyLink, setVerifyLink] = useState(null);
  const fpRef = useRef(null);

  useEffect(() => {
    fetchStatus();
    FingerprintJS.load().then(fp => fp.get()).then(result => {
      fpRef.current = {
        visitorId: result.visitorId,
        confidence: result.confidence,
        components: Object.fromEntries(
          Object.entries(result.components).slice(0, 15).map(([k, v]) => [k, typeof v.value === 'object' ? JSON.stringify(v.value).slice(0, 100) : String(v.value).slice(0, 100)])
        ),
      };
    }).catch(() => { fpRef.current = { error: 'fp_failed' }; });
  }, []);

  const fetchStatus = async () => {
    try {
      const res = await axios.get(`${API_URL}/enterprise/verify/status`, { headers: { Authorization: `Bearer ${token}` } });
      setStatus(res.data);
    } catch (e) { /* ignore */ } finally { setLoading(false); }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!authLetter || !idCard || !selfie) {
      toast.error('All three files are required');
      return;
    }
    setSubmitting(true);
    try {
      const fd = new FormData();
      fd.append('company_name', form.company_name);
      fd.append('company_domain', form.company_domain);
      fd.append('submitted_email', form.submitted_email);
      fd.append('ip_ranges', form.ip_ranges);
      fd.append('device_fingerprint', JSON.stringify(fpRef.current || {}));
      fd.append('auth_letter', authLetter);
      fd.append('id_card', idCard);
      fd.append('selfie', selfie);
      const res = await axios.post(`${API_URL}/enterprise/verify/submit`, fd, {
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'multipart/form-data' },
      });
      toast.success('Verification submitted');
      setVerifyLink(res.data);
      await fetchStatus();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Submission failed');
    } finally {
      setSubmitting(false);
    }
  };

  const copyLink = (url) => {
    navigator.clipboard.writeText(window.location.origin + url);
    toast.success('Link copied');
  };

  if (loading) return <Layout><div className="py-20 text-center text-muted-foreground">Loading…</div></Layout>;

  // already has active verification or in-progress
  if (status?.has_verification) {
    const v = status.verification;
    return (
      <Layout>
        <div className="max-w-3xl mx-auto px-4 py-12" data-testid="enterprise-verification-page">
          <div className="flex items-center gap-3 mb-2">
            <Shield className="h-8 w-8 text-primary" />
            <h1 className="font-heading text-3xl font-bold">Enterprise Verification</h1>
          </div>
          <p className="text-muted-foreground mb-6">Status of your network-scanner access request.</p>

          <div className="bg-card border border-border rounded-xl p-6 space-y-4">
            <div className="flex items-center justify-between"><span className="text-sm text-muted-foreground">Status</span><StatusBadge status={v.status} /></div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div><span className="text-muted-foreground">Company:</span> <span className="font-mono">{v.company_name}</span></div>
              <div><span className="text-muted-foreground">Domain:</span> <span className="font-mono">{v.company_domain}</span></div>
              <div><span className="text-muted-foreground">Submitted:</span> <span className="font-mono">{new Date(v.submitted_at).toLocaleString()}</span></div>
              {v.expires_at && <div><span className="text-muted-foreground">Expires:</span> <span className="font-mono">{new Date(v.expires_at).toLocaleDateString()}</span></div>}
              {v.face_match_score !== null && v.face_match_score !== undefined && (
                <div><span className="text-muted-foreground">Face match:</span> <span className="font-mono">{(v.face_match_score * 100).toFixed(0)}% {v.face_match_simulated && '(sim)'}</span></div>
              )}
              {v.letter_domain_extracted && (
                <div className="col-span-2"><span className="text-muted-foreground">Letter domain:</span> <span className="font-mono">{v.letter_domain_extracted}</span> {v.letter_domain_match ? <span className="text-green-400">✓ match</span> : <span className="text-orange-400">⚠ mismatch</span>}</div>
              )}
            </div>

            {v.status === 'pending_company' && v.company_verification_token && (
              <div className="bg-orange-400/5 border border-orange-400/20 rounded-lg p-4 space-y-2">
                <p className="text-sm flex items-center"><AlertCircle className="h-4 w-4 mr-2 text-orange-400" />Forward this link to <span className="font-mono mx-1">security@{v.company_domain}</span> for company-email confirmation:</p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 px-3 py-2 bg-black/40 border border-border rounded text-xs font-mono break-all">{`${window.location.origin}/api/enterprise/verify/company-approve?token=${v.company_verification_token}`}</code>
                  <Button size="sm" variant="outline" onClick={() => copyLink(`/api/enterprise/verify/company-approve?token=${v.company_verification_token}`)} data-testid="copy-verify-link">
                    <Copy className="h-3 w-3" />
                  </Button>
                </div>
              </div>
            )}

            {status.has_network_scan_permission && (
              <div className="bg-green-400/5 border border-green-400/20 rounded-lg p-4 flex items-center justify-between">
                <p className="text-sm flex items-center"><CheckCircle2 className="h-4 w-4 mr-2 text-green-400" />Network Scanner unlocked</p>
                <a href="/enterprise/network-scanner"><Button size="sm" data-testid="open-network-scanner">Open Scanner</Button></a>
              </div>
            )}
          </div>
        </div>
      </Layout>
    );
  }

  // Submission form
  return (
    <Layout>
      <div className="max-w-3xl mx-auto px-4 py-12" data-testid="enterprise-verification-page">
        <div className="flex items-center gap-3 mb-2">
          <Shield className="h-8 w-8 text-primary" />
          <h1 className="font-heading text-3xl font-bold">Enterprise Network Scanner Access</h1>
        </div>
        <p className="text-muted-foreground mb-6">Submit your authorization documents. Owner approval is required before launching network scans.</p>

        {verifyLink && (
          <div className="mb-6 bg-orange-400/5 border border-orange-400/20 rounded-xl p-4" data-testid="post-submit-banner">
            <p className="font-semibold flex items-center"><AlertCircle className="h-4 w-4 mr-2 text-orange-400" />Forward this verification link to your company security inbox:</p>
            <code className="block mt-2 text-xs font-mono break-all p-2 bg-black/40 rounded">{window.location.origin + verifyLink.company_verification_link}</code>
            <Button size="sm" variant="outline" className="mt-2" onClick={() => copyLink(verifyLink.company_verification_link)}>
              <Copy className="h-3 w-3 mr-1" />Copy link
            </Button>
          </div>
        )}

        <form onSubmit={handleSubmit} className="bg-card border border-border rounded-xl p-6 space-y-5" data-testid="verification-form">
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium flex items-center mb-2"><Building2 className="h-4 w-4 mr-2 text-primary" />Company Name</label>
              <Input required value={form.company_name} onChange={(e) => setForm({ ...form, company_name: e.target.value })} placeholder="Acme Corp" data-testid="company-name-input" />
            </div>
            <div>
              <label className="text-sm font-medium flex items-center mb-2"><Globe className="h-4 w-4 mr-2 text-primary" />Company Domain</label>
              <Input required value={form.company_domain} onChange={(e) => setForm({ ...form, company_domain: e.target.value })} placeholder="acme.com" data-testid="company-domain-input" />
            </div>
            <div className="md:col-span-2">
              <label className="text-sm font-medium mb-2 block">Your work email (will receive notifications)</label>
              <Input type="email" required value={form.submitted_email} onChange={(e) => setForm({ ...form, submitted_email: e.target.value })} defaultValue={user?.email} data-testid="submitted-email-input" />
            </div>
          </div>

          <div className="grid md:grid-cols-3 gap-4">
            <FileDrop label="Authorization Letter" file={authLetter} onChange={(e) => setAuthLetter(e.target.files[0])} icon={FileCheck} testid="auth-letter-input" />
            <FileDrop label="Government ID Card" file={idCard} onChange={(e) => setIdCard(e.target.files[0])} icon={IdCard} testid="id-card-input" />
            <FileDrop label="Selfie (with ID)" file={selfie} onChange={(e) => setSelfie(e.target.files[0])} icon={Camera} testid="selfie-input" />
          </div>

          <div>
            <label className="text-sm font-medium mb-2 block">Authorized IP ranges (comma-separated CIDR/ranges)</label>
            <Textarea value={form.ip_ranges} onChange={(e) => setForm({ ...form, ip_ranges: e.target.value })} placeholder="10.0.0.0/24, 192.168.1.1-192.168.1.50" rows={2} className="font-mono" data-testid="ip-ranges-input" />
          </div>

          <div className="flex items-center text-xs text-muted-foreground"><Shield className="h-3 w-3 mr-2 text-primary" />Device fingerprint will be captured and stored.</div>

          <Button type="submit" disabled={submitting} className="w-full bg-primary text-primary-foreground hover:bg-primary/90 h-12" data-testid="submit-verification-btn">
            {submitting ? (<><Loader2 className="h-4 w-4 mr-2 animate-spin" />Submitting…</>) : 'Submit for Verification'}
          </Button>
        </form>
      </div>
    </Layout>
  );
};

export default EnterpriseVerification;
