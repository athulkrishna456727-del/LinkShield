import React, { createContext, useState, useContext, useEffect } from 'react';
import axios from 'axios';

const AuthContext = createContext();

const API_URL = process.env.REACT_APP_BACKEND_URL + '/api';

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      fetchUser();
    } else {
      setLoading(false);
    }
  }, [token]);

  const fetchUser = async () => {
    try {
      const response = await axios.get(`${API_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUser(response.data);
    } catch (error) {
      localStorage.removeItem('token');
      setToken(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    const response = await axios.post(`${API_URL}/auth/login`, { email, password });
    
    // Check if verification is required
    if (response.data.requires_verification) {
      return {
        requiresVerification: true,
        email: response.data.email,
        message: response.data.message || 'Please verify your email'
      };
    }
    
    // Normal login flow
    if (response.data.token && response.data.user) {
      setToken(response.data.token);
      setUser(response.data.user);
      localStorage.setItem('token', response.data.token);
    }
    
    return response.data;
  };

  const signup = async (email, password, name, username) => {
    const response = await axios.post(`${API_URL}/auth/signup`, { 
      email, 
      password, 
      name, 
      username 
    });
    
    // New signup flow returns requires_verification
    if (response.data.requires_verification) {
      return {
        requiresVerification: true,
        email: response.data.email,
        message: response.data.message || 'Please verify your email'
      };
    }
    
    // Legacy flow (if verification not enabled)
    if (response.data.token && response.data.user) {
      setToken(response.data.token);
      setUser(response.data.user);
      localStorage.setItem('token', response.data.token);
    }
    
    return response.data;
  };

  const verifyOTP = async (email, otpCode) => {
    const response = await axios.post(`${API_URL}/auth/verify-otp`, {
      email,
      otp_code: otpCode
    });
    
    if (response.data.token && response.data.user) {
      setToken(response.data.token);
      setUser(response.data.user);
      localStorage.setItem('token', response.data.token);
    }
    
    return response.data;
  };

  const resendOTP = async (email) => {
    const response = await axios.post(`${API_URL}/auth/resend-otp`, { email });
    return response.data;
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
  };

  const refreshUser = () => {
    if (token) {
      fetchUser();
    }
  };

  return (
    <AuthContext.Provider value={{ 
      user, 
      token, 
      login, 
      signup, 
      verifyOTP,
      resendOTP,
      logout, 
      loading, 
      refreshUser 
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
