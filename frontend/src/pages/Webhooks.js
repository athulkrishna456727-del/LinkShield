import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';
import { Webhook, Plus, Trash2, Send, CheckCircle, XCircle } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';

const API_URL = process.env.REACT_APP_BACKEND_URL + '/api';
const VALID_EVENTS = ['scan.completed', 'scan.failed', 'credits.low', 'team.member_added'];

const Webhooks = () => {
  const { user, token } = useAuth();
  const navigate = useNavigate();
  const [webhooks, setWebhooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [url, setUrl] = useState('');
  const [selectedEvents, setSelectedEvents] = useState([]);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (user?.plan !== 'enterprise') {
      navigate('/plans');
      return;
    }
    fetchWebhooks();
  }, [user]);

  const fetchWebhooks = async () => {
    try {
      const res = await axios.get(`${API_URL}/webhooks`, { headers: { Authorization: `Bearer ${token}` } });
      setWebhooks(res.data);
    } catch (error) {
      if (error.response?.status === 403) navigate('/plans');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (selectedEvents.length === 0) { toast.error('Select at least one event'); return; }
    setCreating(true);
    try {
      await axios.post(`${API_URL}/webhooks`, { url, events: selectedEvents }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Webhook created!');
      setUrl('');
      setSelectedEvents([]);
      setShowCreate(false);
      fetchWebhooks();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create webhook');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this webhook?')) return;
    try {
      await axios.delete(`${API_URL}/webhooks/${id}`, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Webhook deleted');
      fetchWebhooks();
    } catch (error) {
      toast.error('Failed to delete');
    }
  };

  const handleTest = async (id) => {
    try {
      const res = await axios.post(`${API_URL}/webhooks/${id}/test`, {}, { headers: { Authorization: `Bearer ${token}` } });
      if (res.data.success) toast.success('Test ping sent successfully!');
      else toast.error(`Test failed: ${res.data.error || 'Unknown error'}`);
    } catch (error) {
      toast.error('Test failed');
    }
  };

  const toggleEvent = (event) => {
    setSelectedEvents(prev => prev.includes(event) ? prev.filter(e => e !== event) : [...prev, event]);
  };

  if (user?.plan !== 'enterprise') return null;

  return (
    <Layout>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8" data-testid="webhooks-page">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="font-heading text-4xl font-bold mb-2 flex items-center">
              <Webhook className="h-10 w-10 text-primary mr-3" />
              Webhooks
            </h1>
            <p className="text-muted-foreground">Receive real-time notifications for scan events</p>
          </div>
          <Button onClick={() => setShowCreate(!showCreate)} data-testid="create-webhook-btn">
            <Plus className="h-4 w-4 mr-2" /> New Webhook
          </Button>
        </div>

        {showCreate && (
          <div className="bg-card border border-border rounded-xl p-6 mb-6">
            <h2 className="font-heading text-xl font-semibold mb-4">Create Webhook</h2>
            <form onSubmit={handleCreate} className="space-y-4" data-testid="webhook-create-form">
              <div>
                <Label>Endpoint URL</Label>
                <Input
                  type="url"
                  placeholder="https://your-server.com/webhook"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  required
                  className="mt-1"
                  data-testid="webhook-url-input"
                />
              </div>
              <div>
                <Label className="mb-2 block">Events</Label>
                <div className="flex flex-wrap gap-2">
                  {VALID_EVENTS.map(event => (
                    <button
                      key={event}
                      type="button"
                      onClick={() => toggleEvent(event)}
                      className={`px-3 py-1.5 rounded-full text-xs font-mono border transition-colors ${
                        selectedEvents.includes(event)
                          ? 'bg-primary/20 text-primary border-primary/40'
                          : 'bg-accent/30 text-muted-foreground border-border/50 hover:border-primary/30'
                      }`}
                      data-testid={`event-${event}`}
                    >
                      {event}
                    </button>
                  ))}
                </div>
              </div>
              <Button type="submit" disabled={creating}>
                {creating ? 'Creating...' : 'Create Webhook'}
              </Button>
            </form>
          </div>
        )}

        <div className="space-y-4">
          {loading ? (
            <p className="text-center py-10 text-muted-foreground">Loading webhooks...</p>
          ) : webhooks.length === 0 ? (
            <div className="bg-card border border-border rounded-xl p-10 text-center">
              <Webhook className="h-12 w-12 text-muted-foreground mx-auto mb-3" />
              <p className="text-muted-foreground">No webhooks configured yet</p>
            </div>
          ) : (
            webhooks.map(wh => (
              <div key={wh.id} className="bg-card border border-border rounded-xl p-6" data-testid={`webhook-${wh.id}`}>
                <div className="flex items-center justify-between mb-3">
                  <code className="font-mono text-sm truncate max-w-[400px]" title={wh.url}>{wh.url}</code>
                  <div className="flex items-center space-x-2">
                    <Button variant="ghost" size="sm" onClick={() => handleTest(wh.id)} title="Send test ping" data-testid={`test-webhook-${wh.id}`}>
                      <Send className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleDelete(wh.id)} data-testid={`delete-webhook-${wh.id}`}>
                      <Trash2 className="h-4 w-4 text-red-400" />
                    </Button>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2 mb-3">
                  {wh.events?.map(e => (
                    <span key={e} className="px-2 py-0.5 bg-primary/10 text-primary text-xs font-mono rounded-full border border-primary/20">{e}</span>
                  ))}
                </div>
                {wh.recent_deliveries?.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-border/50">
                    <p className="text-xs text-muted-foreground mb-2">Recent Deliveries</p>
                    <div className="space-y-1">
                      {wh.recent_deliveries.map((d, i) => (
                        <div key={i} className="flex items-center justify-between text-xs">
                          <span className="font-mono">{d.event_type}</span>
                          <div className="flex items-center space-x-2">
                            <span className="text-muted-foreground">{new Date(d.created_at).toLocaleString()}</span>
                            {d.success ? <CheckCircle className="h-3 w-3 text-green-400" /> : <XCircle className="h-3 w-3 text-red-400" />}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </Layout>
  );
};

export default Webhooks;
