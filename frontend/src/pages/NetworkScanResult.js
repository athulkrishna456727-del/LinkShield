import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Network as NetworkIcon, Loader2, Zap, Download, FileText, Image as ImageIcon, ChevronLeft, AlertCircle, Play, Square } from 'lucide-react';
import { toast } from 'sonner';
import { Network as VisNetwork } from 'vis-network/standalone';
import { DataSet } from 'vis-data/standalone';

const API_URL = process.env.REACT_APP_BACKEND_URL + '/api';

const RISK_BG = {
  high: 'bg-red-500/10 border-red-500/30 text-red-300',
  medium: 'bg-orange-400/10 border-orange-400/30 text-orange-300',
  low: 'bg-yellow-400/10 border-yellow-400/30 text-yellow-300',
};

const NetworkScanResult = () => {
  const { scanId } = useParams();
  const { token } = useAuth();
  const nav = useNavigate();
  const [scan, setScan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [animatingFrom, setAnimatingFrom] = useState(null);
  const containerRef = useRef(null);
  const networkRef = useRef(null);
  const nodesDsRef = useRef(null);
  const edgesDsRef = useRef(null);
  const overlayCanvasRef = useRef(null);
  const animFrameRef = useRef(null);
  const pollRef = useRef(null);

  const fetchScan = useCallback(async () => {
    try {
      const res = await axios.get(`${API_URL}/enterprise/network-scans/${scanId}`, { headers: { Authorization: `Bearer ${token}` } });
      setScan(res.data);
      if (res.data.status === 'completed' || res.data.status === 'failed') {
        if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
      }
    } catch {
      toast.error('Failed to load scan');
    } finally { setLoading(false); }
  }, [scanId, token]);

  useEffect(() => {
    fetchScan();
    pollRef.current = setInterval(fetchScan, 4000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [fetchScan]);

  // Build vis-network when graph data is ready
  useEffect(() => {
    if (!scan?.graph?.nodes || scan.graph.nodes.length === 0 || !containerRef.current) return;
    if (networkRef.current) return; // already built

    const nodesData = scan.graph.nodes.map(n => ({
      id: n.id,
      label: `${n.label}\n${n.ip}`,
      title: n.title,
      color: { background: n.color, border: '#222', highlight: { background: n.color, border: '#00ff94' } },
      font: { color: '#fafafa', size: 12, face: 'monospace' },
      shape: 'dot',
      size: 20 + (n.risk_score / 4),
    }));
    const edgesData = scan.graph.edges.map(e => ({
      ...e,
      smooth: { enabled: true, type: 'curvedCW', roundness: 0.15 },
      font: { color: '#a1a1aa', size: 10, face: 'monospace', align: 'middle' },
    }));

    nodesDsRef.current = new DataSet(nodesData);
    edgesDsRef.current = new DataSet(edgesData);

    const opts = {
      physics: {
        enabled: true,
        barnesHut: { gravitationalConstant: -8000, springLength: 140, springConstant: 0.04 },
        stabilization: { iterations: 200 },
      },
      interaction: { hover: true, tooltipDelay: 200 },
      nodes: { borderWidth: 2 },
      edges: { arrows: { to: { enabled: true, scaleFactor: 0.6 } }, color: { inherit: false } },
      layout: { improvedLayout: true },
    };

    networkRef.current = new VisNetwork(
      containerRef.current,
      { nodes: nodesDsRef.current, edges: edgesDsRef.current },
      opts,
    );

    networkRef.current.on('click', (params) => {
      if (params.nodes.length > 0) animateFromNode(params.nodes[0]);
    });

    // Setup overlay canvas for the moving dot animation
    networkRef.current.on('afterDrawing', (ctx) => {
      // hook so overlay canvas tracks
    });
    // eslint-disable-next-line
  }, [scan?.graph?.nodes?.length]);

  // BFS reachable from a source node, returns ordered edge sequences
  const bfsPaths = (sourceId) => {
    if (!scan?.graph) return [];
    const adj = {};
    scan.graph.edges.forEach(e => {
      if (!adj[e.from]) adj[e.from] = [];
      adj[e.from].push(e);
    });
    const visited = new Set([sourceId]);
    const queue = [{ node: sourceId, path: [] }];
    const allPaths = [];
    while (queue.length) {
      const { node, path } = queue.shift();
      const edges = adj[node] || [];
      for (const e of edges) {
        if (visited.has(e.to)) continue;
        visited.add(e.to);
        const newPath = [...path, e];
        allPaths.push(newPath);
        queue.push({ node: e.to, path: newPath });
      }
    }
    return allPaths;
  };

  const animateFromNode = (sourceId) => {
    if (animFrameRef.current) { cancelAnimationFrame(animFrameRef.current); animFrameRef.current = null; }
    const paths = bfsPaths(sourceId);
    if (paths.length === 0) {
      toast.info('No outbound edges from this node');
      setAnimatingFrom(null);
      return;
    }
    setAnimatingFrom(sourceId);

    // Highlight reachable nodes
    const reachable = new Set([sourceId]);
    paths.forEach(p => p.forEach(e => reachable.add(e.to)));
    nodesDsRef.current.update(scan.graph.nodes.map(n => ({
      id: n.id,
      borderWidth: reachable.has(n.id) ? 4 : 1,
      color: {
        background: n.color,
        border: n.id === sourceId ? '#00ff94' : (reachable.has(n.id) ? '#00ff94' : '#222'),
      },
    })));

    // Animate moving dot along each path sequentially
    let pathIdx = 0;
    let edgeIdx = 0;
    let progress = 0;

    const step = () => {
      if (pathIdx >= paths.length) {
        // restart loop
        pathIdx = 0; edgeIdx = 0; progress = 0;
      }
      const path = paths[pathIdx];
      if (!path || edgeIdx >= path.length) {
        pathIdx++; edgeIdx = 0; progress = 0;
        animFrameRef.current = requestAnimationFrame(step);
        return;
      }

      const edge = path[edgeIdx];
      const fromPos = networkRef.current.getPositions([edge.from])[edge.from];
      const toPos = networkRef.current.getPositions([edge.to])[edge.to];
      if (!fromPos || !toPos) {
        edgeIdx++; progress = 0;
        animFrameRef.current = requestAnimationFrame(step);
        return;
      }

      progress += 0.025;
      if (progress >= 1) { progress = 0; edgeIdx++; }

      // interpolated position
      const x = fromPos.x + (toPos.x - fromPos.x) * progress;
      const y = fromPos.y + (toPos.y - fromPos.y) * progress;

      // Translate using vis network transform
      const dom = networkRef.current.canvasToDOM({ x, y });
      const overlay = overlayCanvasRef.current;
      if (overlay) {
        overlay.style.left = `${dom.x - 8}px`;
        overlay.style.top = `${dom.y - 8}px`;
        overlay.style.opacity = '1';
        overlay.style.background = edge.risk_level === 'high' ? '#ef4444' : edge.risk_level === 'medium' ? '#f59e0b' : '#facc15';
        overlay.style.boxShadow = `0 0 20px ${edge.risk_level === 'high' ? '#ef4444' : '#f59e0b'}`;
      }

      animFrameRef.current = requestAnimationFrame(step);
    };

    animFrameRef.current = requestAnimationFrame(step);
  };

  const stopAnimation = () => {
    if (animFrameRef.current) { cancelAnimationFrame(animFrameRef.current); animFrameRef.current = null; }
    if (overlayCanvasRef.current) overlayCanvasRef.current.style.opacity = '0';
    if (nodesDsRef.current && scan?.graph?.nodes) {
      nodesDsRef.current.update(scan.graph.nodes.map(n => ({
        id: n.id, borderWidth: 2, color: { background: n.color, border: '#222' },
      })));
    }
    setAnimatingFrom(null);
  };

  const exportPng = () => {
    if (!networkRef.current) return;
    const canvas = containerRef.current.querySelector('canvas');
    if (!canvas) { toast.error('Canvas not found'); return; }
    const link = document.createElement('a');
    link.download = `network_scan_${scanId.slice(0, 8)}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
    toast.success('PNG downloaded');
  };

  const exportPdf = async () => {
    try {
      const res = await axios.get(`${API_URL}/enterprise/network-scans/${scanId}/export?format=pdf`, {
        headers: { Authorization: `Bearer ${token}` }, responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url; link.download = `network_scan_${scanId.slice(0, 8)}.pdf`;
      document.body.appendChild(link); link.click(); link.remove();
      toast.success('PDF downloaded');
    } catch { toast.error('PDF export failed'); }
  };

  const exportJson = async () => {
    try {
      const res = await axios.get(`${API_URL}/enterprise/network-scans/${scanId}/export?format=json`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url; link.download = `network_scan_${scanId.slice(0, 8)}.json`;
      document.body.appendChild(link); link.click(); link.remove();
      toast.success('JSON downloaded');
    } catch { toast.error('Export failed'); }
  };

  if (loading) return <Layout><div className="py-20 text-center text-muted-foreground">Loading…</div></Layout>;
  if (!scan) return <Layout><div className="py-20 text-center text-muted-foreground">Scan not found</div></Layout>;

  const summary = scan.graph?.summary || {};
  const weak = scan.graph?.weak_endpoints || [];

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 py-8" data-testid="network-scan-result-page">
        <div className="flex items-center justify-between mb-6 gap-3 flex-wrap">
          <div>
            <Button variant="ghost" size="sm" onClick={() => nav('/enterprise/network-scanner')} className="mb-2"><ChevronLeft className="h-4 w-4 mr-1" />Back</Button>
            <h1 className="font-heading text-3xl font-bold flex items-center"><NetworkIcon className="h-7 w-7 text-primary mr-3" />Network Scan Result</h1>
            <p className="text-muted-foreground text-sm mt-1 font-mono">{(scan.ip_ranges || []).join(', ')}</p>
          </div>
          <div className="flex gap-2 flex-wrap">
            <Button variant="outline" size="sm" onClick={exportPng} data-testid="export-png-btn"><ImageIcon className="h-4 w-4 mr-2" />PNG</Button>
            <Button variant="outline" size="sm" onClick={exportPdf} data-testid="export-pdf-btn"><FileText className="h-4 w-4 mr-2" />PDF</Button>
            <Button variant="outline" size="sm" onClick={exportJson} data-testid="export-json-btn"><Download className="h-4 w-4 mr-2" />JSON</Button>
          </div>
        </div>

        {scan.status !== 'completed' && (
          <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4 mb-6 flex items-center" data-testid="scan-status-banner">
            <Loader2 className={`h-5 w-5 mr-3 ${scan.status === 'running' ? 'animate-spin text-blue-400' : 'text-zinc-400'}`} />
            <div>
              <p className="font-medium uppercase font-mono text-sm">{scan.status}</p>
              <p className="text-xs text-muted-foreground">{scan.progress}</p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6" data-testid="summary-cards">
          {[
            { label: 'Hosts', value: summary.hosts_total || 0, color: 'text-primary' },
            { label: 'High Risk', value: summary.hosts_high_risk || 0, color: 'text-red-400' },
            { label: 'Medium Risk', value: summary.hosts_medium_risk || 0, color: 'text-orange-400' },
            { label: 'Lateral Edges', value: summary.edges_total || 0, color: 'text-yellow-400' },
          ].map(c => (
            <div key={c.label} className="bg-card border border-border rounded-xl p-4">
              <p className="text-xs text-muted-foreground uppercase">{c.label}</p>
              <p className={`font-mono text-3xl font-bold mt-1 ${c.color}`}>{c.value}</p>
            </div>
          ))}
        </div>

        <div className="bg-card border border-border rounded-xl p-4 mb-6 relative" data-testid="graph-container">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-heading text-lg font-semibold flex items-center"><Zap className="h-5 w-5 text-primary mr-2" />Lateral Movement Graph</h3>
            {animatingFrom ? (
              <Button variant="outline" size="sm" onClick={stopAnimation} data-testid="stop-anim-btn"><Square className="h-3 w-3 mr-2" />Stop animation ({animatingFrom})</Button>
            ) : (
              <p className="text-xs text-muted-foreground"><Play className="h-3 w-3 inline mr-1" />Click any node to animate reachable paths</p>
            )}
          </div>
          <div ref={containerRef} className="w-full h-[520px] bg-black/40 rounded-lg border border-border relative overflow-hidden" data-testid="vis-network-canvas">
            {scan.graph?.nodes?.length === 0 && scan.status === 'completed' && (
              <div className="absolute inset-0 flex items-center justify-center text-muted-foreground">
                <div className="text-center">
                  <AlertCircle className="h-10 w-10 mx-auto mb-2 opacity-50" />
                  <p>No reachable hosts in this range.</p>
                </div>
              </div>
            )}
            <div ref={overlayCanvasRef} className="absolute pointer-events-none w-4 h-4 rounded-full transition-opacity" style={{ opacity: 0, zIndex: 10 }} data-testid="anim-dot"></div>
          </div>
        </div>

        <div className="bg-card border border-border rounded-xl p-6" data-testid="weak-endpoints-table">
          <h3 className="font-heading text-lg font-semibold mb-4 flex items-center"><AlertCircle className="h-5 w-5 text-orange-400 mr-2" />Weak Endpoints &amp; Remediation</h3>
          {weak.length === 0 ? (
            <p className="text-muted-foreground text-center py-6">No weak endpoints detected.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-2 px-2">Risk</th>
                    <th className="text-left py-2 px-2">Host</th>
                    <th className="text-left py-2 px-2">Issue</th>
                    <th className="text-left py-2 px-2">Port</th>
                    <th className="text-left py-2 px-2">Remediation</th>
                  </tr>
                </thead>
                <tbody>
                  {weak.map((w, idx) => (
                    <tr key={idx} className="border-b border-border/30 hover:bg-accent/20">
                      <td className="py-2 px-2"><span className={`px-2 py-0.5 text-[10px] uppercase font-mono rounded border ${RISK_BG[w.level] || ''}`}>{w.level}</span></td>
                      <td className="py-2 px-2 font-mono text-xs">{w.hostname}<br /><span className="text-muted-foreground">{w.ip}</span></td>
                      <td className="py-2 px-2 font-medium">{w.label}<br /><span className="text-xs text-muted-foreground">{w.detail}</span></td>
                      <td className="py-2 px-2 font-mono">{w.port}</td>
                      <td className="py-2 px-2 text-xs text-muted-foreground max-w-md">{w.remediation}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
};

export default NetworkScanResult;
