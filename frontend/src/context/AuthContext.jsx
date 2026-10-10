import React, { createContext, useContext, useState, useEffect } from 'react';
import { apiRequest } from '../services/apiClient';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadUser() {
      const token = localStorage.getItem('farmshield_token');
      if (token) {
        try {
          const res = await apiRequest('/auth/me');
          setUser(res.data);
        } catch (err) {
          console.warn('Session expired or invalid token:', err.message);
          localStorage.removeItem('farmshield_token');
          setUser(null);
        }
      }
      setLoading(false);
    }
    loadUser();
  }, []);

  const login = async (email, password) => {
    const res = await apiRequest('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    localStorage.setItem('farmshield_token', res.data.access_token);
    setUser(res.data.user);
    return res.data.user;
  };

  const register = async (userData) => {
    const res = await apiRequest('/auth/register', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
    localStorage.setItem('farmshield_token', res.data.access_token);
    setUser(res.data.user);
    return res.data.user;
  };

  const updateProfile = async (updates) => {
    const response = await apiRequest('/auth/me', { method: 'PATCH', body: JSON.stringify(updates) });
    setUser(response.data);
    return response.data;
  };

  const updateProfile = async (updates) => {
    const response = await apiRequest('/auth/me', { method: 'PATCH', body: JSON.stringify(updates) });
    setUser(response.data);
    return response.data;
  };

  const logout = () => {
    localStorage.removeItem('farmshield_token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, updateProfile, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
