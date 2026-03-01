import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';
import { Shield, AlertTriangle, CheckCircle, Download, ArrowLeft, Globe, FileText, Hash, Server } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Separator } from '../components/ui/separator';

const API_URL = process.env.REACT_APP_BACKEND_URL + '/api';

const ScanResult = () => {
  const { scanId } = useParams();
  const { token } = useAuth();
  const [scan, setScan] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchScan();
  }, [scanId]);

  const fetchScan = async () => {
    try {
      const response = await axios.get(`${API_URL}/scan/${scanId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setScan(response.data);
    } catch (error) {
      console.error('Failed to fetch scan', error);
    } finally {
      setLoading(false);
    }
  };

  const getRiskConfig = (level) => {
    if (level === 'safe') {
      return {
        color: 'text-green-400',
        bgColor: 'bg-green-500/10',
        borderColor: 'border-green-500/20',
        icon: <CheckCircle className="h-12 w-12" />,
        title: 'Safe',
        description: 'No threats detected'
      };
    }
    if (level === 'suspicious') {
      return {
        color: 'text-orange-400',
        bgColor: 'bg-orange-500/10',
        borderColor: 'border-orange-500/20',
        icon: <AlertTriangle className="h-12 w-12" />,
        title: 'Suspicious',
        description: 'Potentially unsafe content detected'
      };
    }
    return {
      color: 'text-red-400',
      bgColor: 'bg-red-500/10',
      borderColor: 'border-red-500/20',
      icon: <Shield className="h-12 w-12" />,
      title: 'Malicious',
      description: 'Dangerous threats detected'
    };
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center min-h-[60vh]" data-testid="loading-state">
          <p className="text-muted-foreground">Loading scan results...</p>
        </div>
      </Layout>
    );
  }

  if (!scan) {
    return (
      <Layout>
        <div className="flex items-center justify-center min-h-[60vh]" data-testid="not-found-state">
          <p className="text-muted-foreground">Scan not found</p>
        </div>
      </Layout>
    );
  }

  const riskConfig = getRiskConfig(scan.risk_level);

  return (
    <Layout>
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8" data-testid="scan-result-page">
        <Button
          variant="ghost"
          onClick={() => navigate('/history')}
          className="mb-6"
          data-testid="back-to-history-btn"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to History
        </Button>

        <div className={`bg-card border ${riskConfig.borderColor} rounded-xl p-8 mb-6`}>
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-4">
              <div className={riskConfig.color}>{riskConfig.icon}</div>
              <div>
                <h1 className="font-heading text-3xl font-bold">{riskConfig.title}</h1>
                <p className="text-muted-foreground">{riskConfig.description}</p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm text-muted-foreground mb-1">Risk Score</p>
              <p className={`font-mono text-4xl font-bold ${riskConfig.color}`} data-testid="risk-score">
                {scan.risk_score}/100
              </p>
            </div>
          </div>

          <Separator className="my-6" />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-muted-foreground mb-1">Scan Type</p>
              <p className="font-mono font-semibold uppercase" data-testid="scan-type">{scan.scan_type}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground mb-1">Target</p>
              <p className="font-mono font-semibold break-all" data-testid="scan-target">{scan.target}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground mb-1">Status</p>
              <p className="font-mono font-semibold uppercase text-primary" data-testid="scan-status">{scan.status}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground mb-1">Scan Date</p>
              <p className="font-mono font-semibold" data-testid="scan-date">{new Date(scan.created_at).toLocaleString()}</p>
            </div>
          </div>
        </div>

        {scan.metadata && Object.keys(scan.metadata).length > 0 && (
          <div className="bg-card border border-border rounded-xl p-6 mb-6" data-testid="metadata-section">
            <h2 className="font-heading text-xl font-semibold mb-4 flex items-center">
              <FileText className="h-5 w-5 mr-2 text-primary" />
              Metadata
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.entries(scan.metadata).map(([key, value]) => (
                <div key={key} className="bg-accent/30 rounded-lg p-3">
                  <p className="text-sm text-muted-foreground capitalize mb-1">{key.replace('_', ' ')}</p>
                  <p className="font-mono text-sm font-semibold break-all">{String(value)}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {scan.iocs && (
          <div className="bg-card border border-border rounded-xl p-6" data-testid="iocs-section">
            <h2 className="font-heading text-xl font-semibold mb-4 flex items-center">
              <Hash className="h-5 w-5 mr-2 text-primary" />
              Indicators of Compromise (IOCs)
            </h2>

            <div className="space-y-4">
              {scan.iocs.ips && scan.iocs.ips.length > 0 && (
                <div>
                  <div className="flex items-center space-x-2 mb-2">
                    <Server className="h-4 w-4 text-primary" />
                    <h3 className="font-semibold">IP Addresses</h3>
                  </div>
                  <div className="space-y-2">
                    {scan.iocs.ips.map((ip, index) => (
                      <div key={index} className="bg-accent/30 rounded-lg p-3 font-mono text-sm" data-testid={`ioc-ip-${index}`}>
                        {ip}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {scan.iocs.domains && scan.iocs.domains.length > 0 && (
                <div>
                  <div className="flex items-center space-x-2 mb-2">
                    <Globe className="h-4 w-4 text-primary" />
                    <h3 className="font-semibold">Domains</h3>
                  </div>
                  <div className="space-y-2">
                    {scan.iocs.domains.map((domain, index) => (
                      <div key={index} className="bg-accent/30 rounded-lg p-3 font-mono text-sm" data-testid={`ioc-domain-${index}`}>
                        {domain}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {scan.iocs.hashes && scan.iocs.hashes.length > 0 && (
                <div>
                  <div className="flex items-center space-x-2 mb-2">
                    <Hash className="h-4 w-4 text-primary" />
                    <h3 className="font-semibold">File Hashes</h3>
                  </div>
                  <div className="space-y-2">
                    {scan.iocs.hashes.map((hash, index) => (
                      <div key={index} className="bg-accent/30 rounded-lg p-3 font-mono text-xs break-all" data-testid={`ioc-hash-${index}`}>
                        {hash}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default ScanResult;