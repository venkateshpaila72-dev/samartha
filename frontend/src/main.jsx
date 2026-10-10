import React, { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './styles/global.css';
import App from './App.jsx';
import { AuthProvider } from './context/AuthContext';
import { LanguageProvider } from './context/LanguageContext';
import AutoTranslateDocument from './components/AutoTranslateDocument';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <AuthProvider>
      <LanguageProvider>
        <AutoTranslateDocument />
        <App />
      </LanguageProvider>
    </AuthProvider>
  </StrictMode>,
);
