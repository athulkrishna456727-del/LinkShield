import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';
import { Shield, AlertTriangle, Download, FileText, Copy, Gauge, Database, Info, Search } from 'lucide-react';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL + '/api';

const ScanResult = () => {
  const { scanId } = useParams();
  const { user, token } = useAuth();
  const [scan, setScan] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchScan();
  }, [scanId]);

  const fetchScan = async () => {
    try {
      const res = await axios.get(`${API_URL}/scan/${scanId}`, { headers: { Authorization: `Bearer ${token}` } });
      setScan(res.data);
    } catch (error) {
      toast.error('Failed to load scan');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPdf = async () => {
    try {
      const res = await axios.get(`${API_URL}/reports/scan/${scanId}/pdf`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `scan_report_${scanId.slice(0, 8)}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success('Report downloaded');
    } catch (error) {
      if (error.response?.status === 403) toast.error('PDF reports require Premium plan');
      else toast.error('Failed to download report');
    }
  };

  const handleExportIocs = async (format) => {
    try {
      if (format === 'csv') {
        const res = await axios.get(`${API_URL}/iocs/export/${scanId}?format=csv`, {
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        });
        const url = window.URL.createObjectURL(new Blob([res.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `iocs_${scanId.slice(0, 8)}.csv`);
        document.body.appendChild(link);
        link.click();
        link.remove();
      } else {
        const res = await axios.get(`${API_URL}/iocs/export/${scanId}?format=json`, { headers: { Authorization: `Bearer ${token}` } });
        navigator.clipboard.writeText(JSON.stringify(res.data.iocs, null, 2));
        toast.success('IOCs copied to clipboard');
      }
    } catch (error) {
      if (error.response?.status === 403) toast.error('IOC export requires Premium plan');
      else toast.error('Failed to export IOCs');
    }
  };

  const getRiskColor = (level) => {
    if (level === 'critical') return 'text-red-500';
    if (level === 'high') return 'text-red-400';
    if (level === 'suspicious') return 'text-orange-400';
    if (level === 'low') return 'text-yellow-400';
    if (level === 'safe') return 'text-green-400';
    return 'text-zinc-400';
  };

  const getRiskBg = (level) => {
    if (level === 'critical') return 'bg-red-500/10 border-red-500/30';
    if (level === 'high') return 'bg-red-400/10 border-red-400/30';
    if (level === 'suspicious') return 'bg-orange-400/10 border-orange-400/30';
    if (level === 'low') return 'bg-yellow-400/10 border-yellow-400/30';
    if (level === 'safe') return 'bg-green-400/10 border-green-400/30';
    return 'bg-zinc-800 border-zinc-700';
  };

  const sensitivityColor = {
    low: 'text-green-400 border-green-400/30 bg-green-400/5',
    normal: 'text-primary border-primary/30 bg-primary/5',
    high: 'text-orange-400 border-orange-400/30 bg-orange-400/5',
    aggressive: 'text-red-400 border-red-400/30 bg-red-400/5',
  };

  if (loading) return <Layout><div className="flex items-center justify-center py-20"><p>Loading scan...</p></div></Layout>;
  if (!scan) return <Layout><div className="flex items-center justify-center py-20"><p>Scan not found</p></div></Layout>;

  return (
    <Layout>
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8" data-testid="scan-result-page">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="font-heading text-3xl font-bold mb-1">Scan Result</h1>
            <p className="text-sm text-muted-foreground font-mono truncate max-w-lg" title={scan.target}>{scan.target}</p>
          </div>
          <div className="flex gap-2">
            {user?.plan !== 'free' && (
              <Button variant="outline" size="sm" onClick={handleDownloadPdf} data-testid="download-pdf-btn">
                <FileText className="h-4 w-4 mr-2" /> PDF
              </Button>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <div className={`col-span-1 border rounded-xl p-6 text-center ${getRiskBg(scan.risk_level)}`} data-testid="risk-score-card">
            <p className="text-sm text-muted-foreground mb-1">Risk Score</p>
            <p className={`font-mono text-5xl font-bold ${getRiskColor(scan.risk_level)}`}>{scan.risk_score}</p>
            <p className={`text-lg font-semibold uppercase mt-1 ${getRiskColor(scan.risk_level)}`}>{scan.risk_level}</p>
            {scan.sensitivity && (
              <span
                className={`inline-flex items-center gap-1 mt-3 px-2.5 py-0.5 text-xs font-mono uppercase border rounded-full ${sensitivityColor[scan.sensitivity] || ''}`}
                data-testid="sensitivity-badge"
              >
                <Gauge className="h-3 w-3" /> {scan.sensitivity}
              </span>
            )}
          </div>
          <div className="col-span-2 bg-card border border-border rounded-xl p-6">
            <h3 className="font-semibold mb-3">Scan Details</h3>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div><span className="text-muted-foreground">Type:</span> <span className="font-mono uppercase">{scan.scan_type}</span></div>
              <div><span className="text-muted-foreground">Date:</span> <span className="font-mono">{new Date(scan.created_at).toLocaleString()}</span></div>
              <div>
                <span className="text-muted-foreground">Detections:</span>{' '}
                <span className="font-mono">{scan.engines_detected ?? 0}/{scan.engines_total ?? 0} engines</span>
              </div>
              {scan.file_type_detected && (
                <div><span className="text-muted-foreground">File Type:</span> <span className="font-mono uppercase">{scan.file_type_detected}</span></div>
              )}
              {scan.heuristic_score !== undefined && scan.scan_type === 'file' && (
                <div><span className="text-muted-foreground">Heuristic:</span> <span className="font-mono">{scan.heuristic_score}/100</span></div>
              )}
              {scan.file_hash && <div className="col-span-2"><span className="text-muted-foreground">SHA256:</span> <span className="font-mono text-xs break-all">{scan.file_hash}</span></div>}
              {scan.from_cache && (
                <div className="col-span-2 flex items-center text-xs text-muted-foreground" data-testid="cache-badge">
                  <Database className="h-3 w-3 mr-1.5 text-primary" /> Result served from 24h cache
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Explanations */}
        {scan.explanations?.length > 0 && (
          <div className="bg-card border border-border rounded-xl p-6 mb-6" data-testid="explanations-section">
            <h3 className="font-heading text-xl font-semibold mb-4 flex items-center">
              <Info className="h-5 w-5 text-primary mr-2" /> Analysis Summary
            </h3>
            <ul className="space-y-2">
              {scan.explanations.map((exp, idx) => (
                <li
                  key={idx}
                  className="flex items-start text-sm font-mono p-2.5 bg-black/30 border border-border/40 rounded-lg"
                  data-testid={`explanation-${idx}`}
                >
                  <span className="text-primary mr-2.5 mt-0.5">▸</span>
                  <span className="text-foreground/90">{exp}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Heuristic Findings (file scans) */}
        {scan.heuristic_findings?.length > 0 && (
          <div className="bg-card border border-border rounded-xl p-6 mb-6" data-testid="heuristic-section">
            <h3 className="font-heading text-xl font-semibold mb-4 flex items-center">
              <Search className="h-5 w-5 text-orange-400 mr-2" /> Local Heuristic Findings ({scan.heuristic_findings.length})
            </h3>
            <div className="space-y-2">
              {scan.heuristic_findings.slice(0, 15).map((f, idx) => (
                <div key={idx} className="flex items-start justify-between gap-3 p-3 bg-orange-400/5 border border-orange-400/10 rounded-lg">
                  <div className="flex-1 min-w-0">
                    <p className="font-mono text-sm text-orange-300">{f.detail || f.description || JSON.stringify(f)}</p>
                    {f.category && (
                      <span className="inline-block mt-1 px-2 py-0.5 text-[10px] uppercase font-mono bg-orange-400/10 text-orange-300 rounded">
                        {f.category}
                      </span>
                    )}
                  </div>
                  {f.score !== undefined && (
                    <span className="font-mono text-xs text-orange-300/80 whitespace-nowrap">+{f.score}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Threats */}
        {scan.threats?.length > 0 && (
          <div className="bg-card border border-border rounded-xl p-6 mb-6">
            <h3 className="font-heading text-xl font-semibold mb-4 flex items-center">
              <AlertTriangle className="h-5 w-5 text-red-400 mr-2" /> Detected Threats ({scan.threats.length})
            </h3>
            <div className="space-y-2">
              {scan.threats.map((threat, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 bg-red-500/5 border border-red-500/10 rounded-lg">
                  <span className="font-mono text-sm text-red-300">{threat.result}</span>
                  <span className="text-xs text-muted-foreground">{threat.engine}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* IOCs */}
        {scan.iocs?.length > 0 && (
          <div className="bg-card border border-border rounded-xl p-6 mb-6" data-testid="iocs-section">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-heading text-xl font-semibold flex items-center">
                <Shield className="h-5 w-5 text-primary mr-2" /> Indicators of Compromise ({scan.iocs.length})
              </h3>
              {user?.plan !== 'free' && (
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => handleExportIocs('csv')} data-testid="export-iocs-csv">
                    <Download className="h-3 w-3 mr-1" /> CSV
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => handleExportIocs('json')} data-testid="export-iocs-json">
                    <Copy className="h-3 w-3 mr-1" /> JSON
                  </Button>
                </div>
              )}
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-2 px-3">Type</th>
                    <th className="text-left py-2 px-3">Value</th>
                    <th className="text-left py-2 px-3">Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {scan.iocs.map((ioc, idx) => (
                    <tr key={idx} className="border-b border-border/30 hover:bg-accent/20">
                      <td className="py-2 px-3">
                        <span className="px-2 py-0.5 bg-primary/10 text-primary text-xs font-mono rounded">{ioc.ioc_type}</span>
                      </td>
                      <td className="py-2 px-3 font-mono text-xs break-all max-w-xs">{ioc.value}</td>
                      <td className="py-2 px-3">
                        <div className="flex items-center space-x-2">
                          <div className="w-16 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                            <div className="h-full bg-primary rounded-full" style={{ width: `${ioc.confidence}%` }} />
                          </div>
                          <span className="text-xs font-mono">{ioc.confidence}%</span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {user?.plan === 'free' && (
              <div className="mt-4 p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg text-sm text-yellow-300">
                Upgrade to Premium to export IOCs as CSV/JSON
              </div>
            )}
          </div>
        )}

        <div className="flex gap-3">
          <Link to="/history"><Button variant="outline">View All Scans</Button></Link>
          <Link to="/scan"><Button data-testid="scan-again-btn">Scan Another</Button></Link>
        </div>
      </div>
    </Layout>
  );
};

export default ScanResult;
