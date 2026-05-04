import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';
import { FileText, Download, Calendar, Mail, Clock } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';

const API_URL = process.env.REACT_APP_BACKEND_URL + '/api';

const Reports = () => {
  const { user, token } = useAuth();
  const navigate = useNavigate();
  const [schedule, setSchedule] = useState(null);
  const [frequency, setFrequency] = useState('weekly');
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (user?.plan === 'free') {
      navigate('/plans');
      return;
    }
    fetchSchedule();
  }, [user]);

  const fetchSchedule = async () => {
    try {
      const res = await axios.get(`${API_URL}/reports/schedule`, { headers: { Authorization: `Bearer ${token}` } });
      setSchedule(res.data);
      if (res.data.frequency) setFrequency(res.data.frequency);
    } catch (error) {
      console.error('Failed to fetch schedule');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSchedule = async () => {
    try {
      const res = await axios.post(`${API_URL}/reports/schedule`, { frequency, format: 'pdf' }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success(`Report schedule set to ${frequency}`);
      fetchSchedule();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save schedule');
    }
  };

  const handleDisableSchedule = async () => {
    try {
      await axios.delete(`${API_URL}/reports/schedule`, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Schedule disabled');
      fetchSchedule();
    } catch (error) {
      toast.error('Failed to disable schedule');
    }
  };

  const handleDownloadPdf = async (period) => {
    setDownloading(true);
    try {
      const res = await axios.get(`${API_URL}/reports/summary?period=${period}`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `linkshield_${period}_report.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success('Report downloaded');
    } catch (error) {
      toast.error('Failed to generate report');
    } finally {
      setDownloading(false);
    }
  };

  const handleSendNow = async () => {
    setSending(true);
    try {
      const res = await axios.post(`${API_URL}/reports/send-now`, {}, { headers: { Authorization: `Bearer ${token}` } });
      toast.success(res.data.message);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send report');
    } finally {
      setSending(false);
    }
  };

  if (user?.plan === 'free') return null;

  return (
    <Layout>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8" data-testid="reports-page">
        <div className="mb-8">
          <h1 className="font-heading text-4xl font-bold mb-2 flex items-center">
            <FileText className="h-10 w-10 text-primary mr-3" />
            Reports
          </h1>
          <p className="text-muted-foreground">Download scan reports and configure automated email delivery</p>
        </div>

        <div className="space-y-6">
          <div className="bg-card border border-border rounded-xl p-6">
            <h2 className="font-heading text-xl font-semibold mb-4 flex items-center">
              <Download className="h-5 w-5 text-primary mr-2" /> Download Reports
            </h2>
            <p className="text-sm text-muted-foreground mb-4">Generate a PDF summary of your scans</p>
            <div className="flex flex-wrap gap-3">
              <Button variant="outline" onClick={() => handleDownloadPdf('daily')} disabled={downloading} data-testid="download-daily-btn">
                <Calendar className="h-4 w-4 mr-2" /> Last 24 Hours
              </Button>
              <Button variant="outline" onClick={() => handleDownloadPdf('weekly')} disabled={downloading} data-testid="download-weekly-btn">
                <Calendar className="h-4 w-4 mr-2" /> Last 7 Days
              </Button>
              <Button variant="outline" onClick={() => handleDownloadPdf('monthly')} disabled={downloading} data-testid="download-monthly-btn">
                <Calendar className="h-4 w-4 mr-2" /> Last 30 Days
              </Button>
            </div>
          </div>

          <div className="bg-card border border-border rounded-xl p-6">
            <h2 className="font-heading text-xl font-semibold mb-4 flex items-center">
              <Mail className="h-5 w-5 text-primary mr-2" /> Email Schedule
            </h2>
            <p className="text-sm text-muted-foreground mb-4">Automatically receive scan summary reports via email</p>
            
            {schedule?.enabled ? (
              <div className="space-y-4">
                <div className="p-4 bg-green-500/10 border border-green-500/20 rounded-lg flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <Clock className="h-5 w-5 text-green-400" />
                    <div>
                      <p className="font-medium text-green-400">Schedule Active</p>
                      <p className="text-xs text-muted-foreground">
                        Frequency: <span className="font-mono">{schedule.frequency}</span> | 
                        Next: {schedule.next_send ? new Date(schedule.next_send).toLocaleDateString() : 'N/A'}
                      </p>
                    </div>
                  </div>
                  <Button variant="outline" size="sm" onClick={handleDisableSchedule} data-testid="disable-schedule-btn">
                    Disable
                  </Button>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-end gap-4">
                  <div className="flex-1">
                    <Label>Frequency</Label>
                    <Select value={frequency} onValueChange={setFrequency}>
                      <SelectTrigger className="mt-1" data-testid="schedule-frequency-select">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="daily">Daily</SelectItem>
                        <SelectItem value="weekly">Weekly</SelectItem>
                        <SelectItem value="monthly">Monthly</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <Button onClick={handleSaveSchedule} data-testid="save-schedule-btn">
                    Enable Schedule
                  </Button>
                </div>
              </div>
            )}
          </div>

          <div className="bg-card border border-border rounded-xl p-6">
            <h2 className="font-heading text-xl font-semibold mb-4">Send Report Now</h2>
            <p className="text-sm text-muted-foreground mb-4">Send a report to your registered email address immediately</p>
            <Button onClick={handleSendNow} disabled={sending} data-testid="send-now-btn">
              <Mail className="h-4 w-4 mr-2" /> {sending ? 'Sending...' : 'Send Report to Email'}
            </Button>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default Reports;
