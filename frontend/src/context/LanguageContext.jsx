import React, { createContext, useContext, useState } from 'react';

const LanguageContext = createContext(null);

export const SUPPORTED_LANGUAGES = [
  { code: 'en', name: 'English', native: 'English' },
  { code: 'hi', name: 'Hindi', native: 'हिंदी' },
  { code: 'te', name: 'Telugu', native: 'తెలుగు' },
  { code: 'ta', name: 'Tamil', native: 'தமிழ்' },
  { code: 'kn', name: 'Kannada', native: 'ಕನ್ನಡ' },
  { code: 'mr', name: 'Marathi', native: 'मराठी' },
  { code: 'pa', name: 'Punjabi', native: 'ਪੰਜਾਬੀ' },
  { code: 'bn', name: 'Bengali', native: 'বাংলা' },
];

const UI_TRANSLATIONS = {
  en: {
    dashboard: 'Farmer Dashboard',
    my_batches: 'Storage Batches',
    monitoring: 'Live Monitoring',
    diary: 'Crop Diary',
    ai_assistant: 'AI Advisor',
    alerts: 'Storage Alerts',
    weather: 'Weather Forecast',
    market: 'Mandi Prices',
    traditional: 'Traditional Guidance',
    admin: 'Admin Portal',
    temperature: 'Temperature',
    humidity: 'Relative Humidity',
    safe_range: 'Safe Range',
    freshness: 'Sensor Freshness',
  },
  hi: {
    dashboard: 'किसान डैशबोर्ड',
    my_batches: 'भंडारण बैच',
    monitoring: 'लाइव निगरानी',
    diary: 'फसल डायरी',
    ai_assistant: 'एआई सलाहकार',
    alerts: 'भंडारण अलर्ट',
    weather: 'मौसम पूर्वानुमान',
    market: 'मंडी भाव',
    traditional: 'पारंपरिक ज्ञान',
    admin: 'प्रशासन पोर्टल',
    temperature: 'तापमान',
    humidity: 'आर्द्रता',
    safe_range: 'सुरक्षित सीमा',
    freshness: 'सेंसर स्थिति',
  },
  te: {
    dashboard: 'రైతు డాష్‌బోర్డ్',
    my_batches: 'నిల్వ నిల్వలు',
    monitoring: 'ప్రత్యక్ష పర్యవేక్షణ',
    diary: 'పంట డైరీ',
    ai_assistant: 'ఏఐ సలహాదారు',
    alerts: 'నిల్వ హెచ్చరికలు',
    weather: 'వాతావరణ సూచన',
    market: 'మార్కెట్ ధరలు',
    traditional: 'సాంప్రదాయ నిల్వ పద్ధతులు',
    admin: 'అడ్మిన్ పోర్టల్',
    temperature: 'ఉష్ణోగ్రత',
    humidity: 'తేమ శాతం',
    safe_range: 'సురక్షిత పరిమితి',
    freshness: 'సెన్సార్ స్థితి',
  },
};

export function LanguageProvider({ children }) {
  const [currentLang, setCurrentLang] = useState(() => {
    return localStorage.getItem('farmshield_lang') || 'en';
  });

  const changeLanguage = (code) => {
    setCurrentLang(code);
    localStorage.setItem('farmshield_lang', code);
  };

  const t = (key) => {
    const langDict = UI_TRANSLATIONS[currentLang] || UI_TRANSLATIONS.en;
    return langDict[key] || UI_TRANSLATIONS.en[key] || key;
  };

  return (
    <LanguageContext.Provider value={{ currentLang, changeLanguage, t, supportedLanguages: SUPPORTED_LANGUAGES }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
}
