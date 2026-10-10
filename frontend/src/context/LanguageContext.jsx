import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { apiRequest } from '../services/apiClient';

const LanguageContext = createContext(null);
const CACHE_PREFIX = 'farmshield_translation_cache_v1:';
const CACHE_LIMIT = 800;

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
    dashboard: 'Farmer Dashboard', my_batches: 'Storage Batches', monitoring: 'Live Monitoring',
    diary: 'Crop Diary', ai_assistant: 'AI Advisor', alerts: 'Storage Alerts',
    weather: 'Weather Forecast', market: 'Mandi Prices', traditional: 'Traditional Guidance',
    admin: 'Admin Portal', onboarding: 'Crop Onboarding', navigation: 'Navigation',
    system_admin: 'System Admin', admin_management: 'Admin Management',
    temperature: 'Temperature', humidity: 'Relative Humidity', safe_range: 'Safe Range',
    freshness: 'Sensor Freshness', monitoring_batch: 'Monitoring Batch',
    logout: 'Log out', search_prices: 'Search Prices',
  },
  hi: {
    dashboard: 'किसान डैशबोर्ड', my_batches: 'भंडारण बैच', monitoring: 'लाइव निगरानी',
    diary: 'फसल डायरी', ai_assistant: 'एआई सलाहकार', alerts: 'भंडारण अलर्ट',
    weather: 'मौसम पूर्वानुमान', market: 'मंडी भाव', traditional: 'पारंपरिक मार्गदर्शन',
    admin: 'प्रशासन पोर्टल', onboarding: 'फसल पंजीकरण', navigation: 'नेविगेशन',
    system_admin: 'सिस्टम व्यवस्थापक', admin_management: 'व्यवस्थापक प्रबंधन',
    temperature: 'तापमान', humidity: 'सापेक्ष आर्द्रता', safe_range: 'सुरक्षित सीमा',
    freshness: 'सेंसर की स्थिति', monitoring_batch: 'निगरानी बैच', logout: 'लॉग आउट',
    search_prices: 'कीमतें खोजें',
  },
  te: {
    dashboard: 'రైతు డాష్‌బోర్డ్', my_batches: 'నిల్వ బ్యాచ్‌లు', monitoring: 'ప్రత్యక్ష పర్యవేక్షణ',
    diary: 'పంట డైరీ', ai_assistant: 'ఏఐ సలహాదారు', alerts: 'నిల్వ హెచ్చరికలు',
    weather: 'వాతావరణ సూచన', market: 'మార్కెట్ ధరలు', traditional: 'సాంప్రదాయ మార్గదర్శకం',
    admin: 'అడ్మిన్ పోర్టల్', onboarding: 'పంట నమోదు', navigation: 'నావిగేషన్',
    system_admin: 'సిస్టమ్ అడ్మిన్', admin_management: 'అడ్మిన్ నిర్వహణ',
    temperature: 'ఉష్ణోగ్రత', humidity: 'సాపేక్ష ఆర్ద్రత', safe_range: 'సురక్షిత పరిధి',
    freshness: 'సెన్సార్ తాజాదనం', monitoring_batch: 'పర్యవేక్షణ బ్యాచ్', logout: 'లాగ్ అవుట్',
    search_prices: 'ధరలను వెతకండి',
  },
  ta: {
    dashboard: 'விவசாயி டாஷ்போர்டு', my_batches: 'சேமிப்பு தொகுதிகள்', monitoring: 'நேரடி கண்காணிப்பு',
    diary: 'பயிர் நாட்குறிப்பு', ai_assistant: 'AI ஆலோசகர்', alerts: 'சேமிப்பு எச்சரிக்கைகள்',
    weather: 'வானிலை முன்னறிவிப்பு', market: 'சந்தை விலைகள்', traditional: 'பாரம்பரிய வழிகாட்டுதல்',
    admin: 'நிர்வாக போர்டல்', onboarding: 'பயிர் பதிவு', navigation: 'வழிசெலுத்தல்',
    system_admin: 'கணினி நிர்வாகி', admin_management: 'நிர்வாக மேலாண்மை',
    temperature: 'வெப்பநிலை', humidity: 'ஒப்பீட்டு ஈரப்பதம்', safe_range: 'பாதுகாப்பான வரம்பு',
    freshness: 'சென்சார் நிலை', monitoring_batch: 'கண்காணிப்பு தொகுதி', logout: 'வெளியேறு',
    search_prices: 'விலைகளைத் தேடு',
  },
  kn: {
    dashboard: 'ರೈತರ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್', my_batches: 'ಸಂಗ್ರಹಣೆ ಬ್ಯಾಚ್‌ಗಳು', monitoring: 'ನೇರ ಮೇಲ್ವಿಚಾರಣೆ',
    diary: 'ಬೆಳೆ ದಿನಚರಿ', ai_assistant: 'AI ಸಲಹೆಗಾರ', alerts: 'ಸಂಗ್ರಹಣೆ ಎಚ್ಚರಿಕೆಗಳು',
    weather: 'ಹವಾಮಾನ ಮುನ್ಸೂಚನೆ', market: 'ಮಾರುಕಟ್ಟೆ ಬೆಲೆಗಳು', traditional: 'ಸಾಂಪ್ರದಾಯಿಕ ಮಾರ್ಗದರ್ಶನ',
    admin: 'ನಿರ್ವಾಹಕ ಪೋರ್ಟಲ್', onboarding: 'ಬೆಳೆ ನೋಂದಣಿ', navigation: 'ನ್ಯಾವಿಗೇಶನ್',
    system_admin: 'ಸಿಸ್ಟಮ್ ನಿರ್ವಾಹಕ', admin_management: 'ನಿರ್ವಾಹಕ ನಿರ್ವಹಣೆ',
    temperature: 'ತಾಪಮಾನ', humidity: 'ಸಾಪೇಕ್ಷ ಆರ್ದ್ರತೆ', safe_range: 'ಸುರಕ್ಷಿತ ವ್ಯಾಪ್ತಿ',
    freshness: 'ಸೆನ್ಸರ್ ಸ್ಥಿತಿ', monitoring_batch: 'ಮೇಲ್ವಿಚಾರಣಾ ಬ್ಯಾಚ್', logout: 'ಲಾಗ್ ಔಟ್',
    search_prices: 'ಬೆಲೆಗಳನ್ನು ಹುಡುಕಿ',
  },
  mr: {
    dashboard: 'शेतकरी डॅशबोर्ड', my_batches: 'साठवण बॅच', monitoring: 'थेट निरीक्षण',
    diary: 'पीक डायरी', ai_assistant: 'एआय सल्लागार', alerts: 'साठवण सूचना',
    weather: 'हवामान अंदाज', market: 'बाजारभाव', traditional: 'पारंपरिक मार्गदर्शन',
    admin: 'प्रशासक पोर्टल', onboarding: 'पीक नोंदणी', navigation: 'नेव्हिगेशन',
    system_admin: 'सिस्टम प्रशासक', admin_management: 'प्रशासक व्यवस्थापन',
    temperature: 'तापमान', humidity: 'सापेक्ष आर्द्रता', safe_range: 'सुरक्षित मर्यादा',
    freshness: 'सेन्सर स्थिती', monitoring_batch: 'निरीक्षण बॅच', logout: 'लॉग आउट',
    search_prices: 'किंमती शोधा',
  },
  pa: {
    dashboard: 'ਕਿਸਾਨ ਡੈਸ਼ਬੋਰਡ', my_batches: 'ਸਟੋਰੇਜ ਬੈਚ', monitoring: 'ਲਾਈਵ ਨਿਗਰਾਨੀ',
    diary: 'ਫਸਲ ਡਾਇਰੀ', ai_assistant: 'AI ਸਲਾਹਕਾਰ', alerts: 'ਸਟੋਰੇਜ ਚੇਤਾਵਨੀਆਂ',
    weather: 'ਮੌਸਮ ਦੀ ਭਵਿੱਖਬਾਣੀ', market: 'ਮੰਡੀ ਭਾਅ', traditional: 'ਰਵਾਇਤੀ ਮਾਰਗਦਰਸ਼ਨ',
    admin: 'ਐਡਮਿਨ ਪੋਰਟਲ', onboarding: 'ਫਸਲ ਰਜਿਸਟ੍ਰੇਸ਼ਨ', navigation: 'ਨੇਵੀਗੇਸ਼ਨ',
    system_admin: 'ਸਿਸਟਮ ਐਡਮਿਨ', admin_management: 'ਐਡਮਿਨ ਪ੍ਰਬੰਧਨ',
    temperature: 'ਤਾਪਮਾਨ', humidity: 'ਸਾਪੇਖ ਨਮੀ', safe_range: 'ਸੁਰੱਖਿਅਤ ਹੱਦ',
    freshness: 'ਸੈਂਸਰ ਸਥਿਤੀ', monitoring_batch: 'ਨਿਗਰਾਨੀ ਬੈਚ', logout: 'ਲੌਗ ਆਉਟ',
    search_prices: 'ਕੀਮਤਾਂ ਖੋਜੋ',
  },
  bn: {
    dashboard: 'কৃষক ড্যাশবোর্ড', my_batches: 'সংরক্ষণ ব্যাচ', monitoring: 'লাইভ পর্যবেক্ষণ',
    diary: 'ফসলের ডায়েরি', ai_assistant: 'এআই উপদেষ্টা', alerts: 'সংরক্ষণ সতর্কতা',
    weather: 'আবহাওয়ার পূর্বাভাস', market: 'বাজারদর', traditional: 'ঐতিহ্যবাহী নির্দেশনা',
    admin: 'অ্যাডমিন পোর্টাল', onboarding: 'ফসল নিবন্ধন', navigation: 'নেভিগেশন',
    system_admin: 'সিস্টেম অ্যাডমিন', admin_management: 'অ্যাডমিন ব্যবস্থাপনা',
    temperature: 'তাপমাত্রা', humidity: 'আপেক্ষিক আর্দ্রতা', safe_range: 'নিরাপদ সীমা',
    freshness: 'সেন্সরের অবস্থা', monitoring_batch: 'পর্যবেক্ষণ ব্যাচ', logout: 'লগ আউট',
    search_prices: 'দাম খুঁজুন',
  },
};

function cacheKey(source, target, text) {
  return CACHE_PREFIX + encodeURIComponent(source + '|' + target + '|' + text);
}

function readCache(key) {
  try { return localStorage.getItem(key); } catch { return null; }
}

function writeCache(key, value) {
  try {
    const keys = Object.keys(localStorage).filter((item) => item.startsWith(CACHE_PREFIX));
    if (keys.length >= CACHE_LIMIT) keys.slice(0, Math.max(1, keys.length - CACHE_LIMIT + 1)).forEach((item) => localStorage.removeItem(item));
    localStorage.setItem(key, value);
  } catch { /* Storage may be disabled or full; translation still works for this session. */ }
}

export function LanguageProvider({ children }) {
  const [currentLang, setCurrentLang] = useState(() => {
    try {
      const saved = localStorage.getItem('farmshield_lang') || 'en';
      return SUPPORTED_LANGUAGES.some((language) => language.code === saved) ? saved : 'en';
    } catch { return 'en'; }
  });
  const [translationCache, setTranslationCache] = useState({});
  const [translatingCount, setTranslatingCount] = useState(0);

  const changeLanguage = useCallback((code) => {
    if (!SUPPORTED_LANGUAGES.some((language) => language.code === code)) return;
    setCurrentLang(code);
    try { localStorage.setItem('farmshield_lang', code); } catch { /* ignore */ }
  }, []);

  const translateText = useCallback(async (text, targetLanguage = currentLang, sourceLanguage = 'en') => {
    if (!text || targetLanguage === sourceLanguage) return text;
    const key = cacheKey(sourceLanguage, targetLanguage, text);
    const inMemory = translationCache[key];
    if (inMemory) return inMemory;
    const persisted = readCache(key);
    if (persisted) {
      setTranslationCache((previous) => ({ ...previous, [key]: persisted }));
      return persisted;
    }
    setTranslatingCount((count) => count + 1);
    try {
      const response = await apiRequest('/translation', {
        method: 'POST',
        body: JSON.stringify({ text, target_language: targetLanguage, source_language: sourceLanguage }),
      });
      const translated = response?.data?.translated_text || text;
      writeCache(key, translated);
      setTranslationCache((previous) => ({ ...previous, [key]: translated }));
      return translated;
    } catch (error) {
      // Do not cache failures; a later attempt can succeed after network/API recovery.
      console.warn('Text translation unavailable; showing original text.', error?.message || error);
      return text;
    } finally {
      setTranslatingCount((count) => Math.max(0, count - 1));
    }
  }, [currentLang, translationCache]);

  const t = useCallback((key) => {
    const dictionary = UI_TRANSLATIONS[currentLang] || UI_TRANSLATIONS.en;
    return dictionary[key] || UI_TRANSLATIONS.en[key] || key;
  }, [currentLang]);

  const value = useMemo(() => ({
    currentLang, changeLanguage, t, translateText, isTranslating: translatingCount > 0,
    supportedLanguages: SUPPORTED_LANGUAGES,
  }), [currentLang, changeLanguage, t, translateText, translatingCount]);

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) throw new Error('useLanguage must be used within a LanguageProvider');
  return context;
}
