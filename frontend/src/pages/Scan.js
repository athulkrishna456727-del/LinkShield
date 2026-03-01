import React, { useState, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';
import { FileSearch, Upload, Link as LinkIcon, Loader2, AlertCircle } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Progress } from '../components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL + '/api';

const Scan = () => {
  const { token, refreshUser } = useAuth();
  const [url, setUrl] = useState('');
  const [file, setFile] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [dragActive, setDragActive] = useState(false);
  const navigate = useNavigate();

  const handleUrlScan = async (e) => {
    e.preventDefault();
    if (!url) return;

    setScanning(true);
    setProgress(0);

    const progressInterval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 90) return prev;
        return prev + 10;
      });
    }, 200);

    try {
      const response = await axios.post(
        `${API_URL}/scan/url`,
        { url },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      clearInterval(progressInterval);
      setProgress(100);

      setTimeout(() => {
        refreshUser();
        navigate(`/scan/${response.data.id}`);
      }, 500);
    } catch (error) {
      clearInterval(progressInterval);
      if (error.response?.status === 402) {
        toast.error('Insufficient credits. Please upgrade your plan.');
      } else {
        toast.error(error.response?.data?.detail || 'Scan failed');
      }
      setScanning(false);
      setProgress(0);
    }
  };

  const handleFileScan = async () => {
    if (!file) return;

    setScanning(true);
    setProgress(0);

    const progressInterval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 90) return prev;
        return prev + 10;
      });
    }, 200);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post(`${API_URL}/scan/file`, formData, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data',
        },
      });

      clearInterval(progressInterval);
      setProgress(100);

      setTimeout(() => {
        refreshUser();
        navigate(`/scan/${response.data.id}`);
      }, 500);
    } catch (error) {
      clearInterval(progressInterval);
      if (error.response?.status === 402) {
        toast.error('Insufficient credits. Please upgrade your plan.');
      } else {
        toast.error(error.response?.data?.detail || 'Scan failed');
      }
      setScanning(false);
      setProgress(0);
    }
  };

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  }, []);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <Layout>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12" data-testid="scan-page">
        <div className="text-center mb-12">
          <h1 className="font-heading text-4xl md:text-5xl font-bold mb-4">Security Scanner</h1>
          <p className="text-muted-foreground text-lg">Analyze URLs and files for potential threats</p>
        </div>

        <Tabs defaultValue="url" className="w-full">
          <TabsList className="grid w-full grid-cols-2 mb-8" data-testid="scan-tabs">
            <TabsTrigger value="url" data-testid="tab-url">
              <LinkIcon className="h-4 w-4 mr-2" />
              URL Scan
            </TabsTrigger>
            <TabsTrigger value="file" data-testid="tab-file">
              <Upload className="h-4 w-4 mr-2" />
              File Scan
            </TabsTrigger>
          </TabsList>

          <TabsContent value="url" className="space-y-6">
            <div className="bg-card border border-border rounded-xl p-8">
              <form onSubmit={handleUrlScan} className="space-y-6" data-testid="url-scan-form">
                <div className="space-y-4">
                  <label className="block text-sm font-medium">Enter URL to Scan</label>
                  <Input
                    type="url"
                    placeholder="https://example.com"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    disabled={scanning}
                    className="bg-black/50 border-border/50 focus:border-primary/50 font-mono text-lg h-14"
                    required
                    data-testid="url-input"
                  />
                  <p className="text-sm text-muted-foreground flex items-center">
                    <AlertCircle className="h-4 w-4 mr-2" />
                    URL scan costs 5 credits (Free) or 3 credits (Premium)
                  </p>
                </div>

                {scanning && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Scanning in progress...</span>
                      <span className="font-mono font-semibold">{progress}%</span>
                    </div>
                    <Progress value={progress} className="h-2" data-testid="scan-progress" />
                  </div>
                )}

                <Button
                  type="submit"
                  disabled={scanning || !url}
                  className="w-full bg-primary text-primary-foreground hover:bg-primary/90 shadow-[0_0_20px_-5px_rgba(0,255,148,0.4)] h-12 text-lg"
                  data-testid="url-scan-btn"
                >
                  {scanning ? (
                    <>
                      <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                      Scanning...
                    </>
                  ) : (
                    <>
                      <FileSearch className="h-5 w-5 mr-2" />
                      Start URL Scan
                    </>
                  )}
                </Button>
              </form>
            </div>
          </TabsContent>

          <TabsContent value="file" className="space-y-6">
            <div className="bg-card border border-border rounded-xl p-8">
              <div className="space-y-6">
                <div
                  className={`border-2 border-dashed rounded-2xl p-12 text-center transition-all ${
                    dragActive
                      ? 'border-primary bg-primary/5'
                      : 'border-border hover:border-primary/50 bg-accent/5'
                  } ${scanning ? 'opacity-50 pointer-events-none' : 'cursor-pointer'}`}
                  onDragEnter={handleDrag}
                  onDragLeave={handleDrag}
                  onDragOver={handleDrag}
                  onDrop={handleDrop}
                  onClick={() => !scanning && document.getElementById('file-input').click()}
                  data-testid="file-dropzone"
                >
                  <input
                    id="file-input"
                    type="file"
                    className="hidden"
                    onChange={handleFileChange}
                    disabled={scanning}
                    data-testid="file-input"
                  />
                  <Upload className="h-16 w-16 text-primary mx-auto mb-4" />
                  {file ? (
                    <div className="space-y-2">
                      <p className="font-mono font-semibold text-lg">{file.name}</p>
                      <p className="text-muted-foreground">{formatFileSize(file.size)}</p>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          setFile(null);
                        }}
                        className="mt-2"
                        data-testid="remove-file-btn"
                      >
                        Remove File
                      </Button>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <p className="text-lg font-medium">Drop your file here or click to browse</p>
                      <p className="text-muted-foreground">Supports EXE, APK, ZIP, PDF, DOC, and images</p>
                    </div>
                  )}
                </div>

                <p className="text-sm text-muted-foreground flex items-center">
                  <AlertCircle className="h-4 w-4 mr-2" />
                  File scan costs 10 credits (Free) or 6 credits (Premium)
                </p>

                {scanning && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Analyzing file...</span>
                      <span className="font-mono font-semibold">{progress}%</span>
                    </div>
                    <Progress value={progress} className="h-2" data-testid="file-scan-progress" />
                  </div>
                )}

                <Button
                  onClick={handleFileScan}
                  disabled={scanning || !file}
                  className="w-full bg-primary text-primary-foreground hover:bg-primary/90 shadow-[0_0_20px_-5px_rgba(0,255,148,0.4)] h-12 text-lg"
                  data-testid="file-scan-btn"
                >
                  {scanning ? (
                    <>
                      <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <FileSearch className="h-5 w-5 mr-2" />
                      Start File Scan
                    </>
                  )}
                </Button>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
};

export default Scan;