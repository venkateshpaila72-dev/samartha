import React, {
  createContext,
  useContext,
  useState,
  useEffect,
} from 'react';
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
          const response = await apiRequest('/auth/me');
          setUser(response.data);
        } catch (error) {
          console.warn(
            'Session expired or invalid token:',
            error.message
          );

          localStorage.removeItem('farmshield_token');
          setUser(null);
        }
      }

      setLoading(false);
    }

    loadUser();
  }, []);

  const login = async (email, password, loginAs = 'farmer') => {
    const response = await apiRequest('/auth/login', {
      method: 'POST',
      body: JSON.stringify({
        email,
        password,
        login_as: loginAs,
      }),
    });

    localStorage.setItem(
      'farmshield_token',
      response.data.access_token
    );

    setUser(response.data.user);

    return response.data.user;
  };

  const register = async (userData) => {
    const response = await apiRequest('/auth/register', {
      method: 'POST',
      body: JSON.stringify(userData),
    });

    localStorage.setItem(
      'farmshield_token',
      response.data.access_token
    );

    setUser(response.data.user);

    return response.data.user;
  };

  const updateUser = (patch) => {
    setUser((prev) => (prev ? { ...prev, ...patch } : prev));
  };

  const refreshUser = async () => {
    try {
      const response = await apiRequest('/auth/me');
      setUser(response.data);
      return response.data;
    } catch {
      return null;
    }
  };

  const logout = () => {
    localStorage.removeItem('farmshield_token');
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        register,
        logout,
        updateUser,
        refreshUser,
      }}
    >
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