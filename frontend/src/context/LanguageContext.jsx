import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { apiRequest } from '../services/apiClient';

const LanguageContext = createContext(null);
const CACHE_PREFIX = 'farmshield_translation_cache_v1:';
const CACHE_LIMIT = 800;

export const SUPPORTED_LANGUAGES = [
  { code: 'en', name: 'English', native: 'English' },
  { code: 'te', name: 'Telugu', native: 'తెలుగు' },
  { code: 'hi', name: 'Hindi', native: 'हिन्दी' },
  { code: 'mr', name: 'Marathi', native: 'मराठी' },
  { code: 'bn', name: 'Bengali', native: 'বাংলা' },
  { code: 'ta', name: 'Tamil', native: 'தமிழ்' },
  { code: 'kn', name: 'Kannada', native: 'ಕನ್ನಡ' },
  { code: 'pa', name: 'Punjabi', native: 'ਪੰਜਾਬੀ' },
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
    onboarding: 'Crop Onboarding',
    navigation: 'Navigation',
    system_admin: 'System Admin',
    admin_management: 'Admin Management',
    temperature: 'Temperature',
    humidity: 'Relative Humidity',
    safe_range: 'Safe Range',
    freshness: 'Sensor Freshness',
    monitoring_batch: 'Monitoring Batch',
    logout: 'Log Out',
    search_prices: 'Search Prices',
    profile: 'My Profile',
    loading: 'Loading...',
    translating: 'Translating content...',
    search: 'Search',
    refresh: 'Refresh',
    save: 'Save',
    cancel: 'Cancel',
    submit: 'Submit',
    language: 'Language',
    no_data: 'No data available',
    error: 'Something went wrong',
    select_language: 'Select Language',
    crop_name: 'Crop Name',
    status: 'Status',
    date: 'Date',
    actions: 'Actions',
    workflow_weather: 'Workflow 9: Weather Forecast & Storage Aeration Impact',
    weather_title: 'Weather & Ambient Storage Advisory',
    weather_subtitle: 'Weather forecasts correlated with storage ventilation and condensation risk.',
    storage_impact: 'Storage Impact Summary',
    next_forecast: 'Next 24–48 Hours Forecast',
    search_location: 'Enter city or location',
    loading_data: 'Loading...',
    try_again: 'Try Again',
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
    traditional: 'पारंपरिक मार्गदर्शन',
    admin: 'प्रशासन पोर्टल',
    onboarding: 'फसल पंजीकरण',
    navigation: 'नेविगेशन',
    system_admin: 'सिस्टम व्यवस्थापक',
    admin_management: 'व्यवस्थापक प्रबंधन',
    temperature: 'तापमान',
    humidity: 'सापेक्ष आर्द्रता',
    safe_range: 'सुरक्षित सीमा',
    freshness: 'सेंसर की स्थिति',
    monitoring_batch: 'निगरानी बैच',
    logout: 'लॉग आउट',
    search_prices: 'कीमतें खोजें',
    profile: 'मेरी प्रोफ़ाइल',
    loading: 'लोड हो रहा है...',
    translating: 'अनुवाद हो रहा है...',
    search: 'खोजें',
    refresh: 'रिफ्रेश',
    save: 'सहेजें',
    cancel: 'रद्द करें',
    submit: 'जमा करें',
    language: 'भाषा',
    no_data: 'कोई डेटा उपलब्ध नहीं',
    error: 'कुछ गलत हो गया',
    select_language: 'भाषा चुनें',
    crop_name: 'फसल का नाम',
    status: 'स्थिति',
    date: 'तारीख',
    actions: 'कार्रवाई',
    workflow_weather: 'कार्यप्रवाह 9: मौसम पूर्वानुमान एवं भंडारण वायुसंचार प्रभाव',
    weather_title: 'मौसम एवं परिवेश भंडारण सलाह',
    weather_subtitle: 'भंडारण वेंटिलेशन और संक्षेपण जोखिम से संबंधित मौसम पूर्वानुमान।',
    storage_impact: 'भंडारण प्रभाव सारांश',
    next_forecast: 'अगले 24–48 घंटों का पूर्वानुमान',
    search_location: 'शहर या स्थान दर्ज करें',
    loading_data: 'डेटा लोड हो रहा है...',
    try_again: 'पुनः प्रयास करें',
  },
  te: {
    dashboard: 'రైతు డాష్‌బోర్డ్',
    my_batches: 'నిల్వ బ్యాచ్‌లు',
    monitoring: 'ప్రత్యక్ష పర్యవేక్షణ',
    diary: 'పంట డైరీ',
    ai_assistant: 'ఏఐ సలహాదారు',
    alerts: 'నిల్వ హెచ్చరికలు',
    weather: 'వాతావరణ సూచన',
    market: 'మార్కెట్ ధరలు',
    traditional: 'సాంప్రదాయ మార్గదర్శకం',
    admin: 'అడ్మిన్ పోర్టల్',
    onboarding: 'పంట నమోదు',
    navigation: 'నావిగేషన్',
    system_admin: 'సిస్టమ్ అడ్మిన్',
    admin_management: 'అడ్మిన్ నిర్వహణ',
    temperature: 'ఉష్ణోగ్రత',
    humidity: 'సాపేక్ష ఆర్ద్రత',
    safe_range: 'సురక్షిత పరిధి',
    freshness: 'సెన్సార్ తాజాదనం',
    monitoring_batch: 'పర్యవేక్షణ బ్యాచ్',
    logout: 'లాగ్ అవుట్',
    search_prices: 'ధరలను వెతకండి',
    profile: 'నా ప్రొఫైల్',
    loading: 'లోడ్ అవుతోంది...',
    translating: 'కంటెంట్ అనువదిస్తోంది...',
    search: 'వెతకండి',
    refresh: 'రిఫ్రెష్',
    save: 'సేవ్ చేయండి',
    cancel: 'రద్దు చేయండి',
    submit: 'సమర్పించండి',
    language: 'భాష',
    no_data: 'డేటా అందుబాటులో లేదు',
    error: 'ఏదో తప్పు జరిగింది',
    select_language: 'భాషను ఎంచుకోండి',
    crop_name: 'పంట పేరు',
    status: 'స్థితి',
    date: 'తేదీ',
    actions: 'చర్యలు',
    workflow_weather: 'వర్క్‌ఫ్లో 9: వాతావరణ సూచన & నిల్వ గాలి ప్రసరణ ప్రభావం',
    weather_title: 'వాతావరణం & పరిసర నిల్వ సలహా',
    weather_subtitle: 'నిల్వ వెంటిలేషన్ మరియు సంగ్రహణ ప్రమాదంతో ముడిపడి ఉన్న వాతావరణ సూచనలు.',
    storage_impact: 'నిల్వ ప్రభావ సారాంశం',
    next_forecast: 'తదుపరి 24–48 గంటల సూచన',
    search_location: 'నగరం లేదా స్థానాన్ని నమోదు చేయండి',
    loading_data: 'లోడ్ అవుతోంది...',
    try_again: 'మళ్ళీ ప్రయత్నించండి',
  },
  ta: {
    dashboard: 'விவசாயி டாஷ்போர்டு',
    my_batches: 'சேமிப்பு தொகுதிகள்',
    monitoring: 'நேரடி கண்காணிப்பு',
    diary: 'பயிர் நாட்குறிப்பு',
    ai_assistant: 'AI ஆலோசகர்',
    alerts: 'சேமிப்பு எச்சரிக்கைகள்',
    weather: 'வானிலை முன்னறிவிப்பு',
    market: 'சந்தை விலைகள்',
    traditional: 'பாரம்பரிய வழிகாட்டுதல்',
    admin: 'நிர்வாக போர்டல்',
    onboarding: 'பயிர் பதிவு',
    navigation: 'வழிசெலுத்தல்',
    system_admin: 'கணினி நிர்வாகி',
    admin_management: 'நிர்வாக மேலாண்மை',
    temperature: 'வெப்பநிலை',
    humidity: 'ஒப்பீட்டு ஈரப்பதம்',
    safe_range: 'பாதுகாப்பான வரம்பு',
    freshness: 'சென்சார் நிலை',
    monitoring_batch: 'கண்காணிப்பு தொகுதி',
    logout: 'வெளியேறு',
    search_prices: 'விலைகளைத் தேடு',
    profile: 'என் சுயவிவரம்',
    loading: 'ஏற்றுகிறது...',
    translating: 'மொழிபெயர்க்கப்படுகிறது...',
    search: 'தேடு',
    refresh: 'புதுப்பி',
    save: 'சேமி',
    cancel: 'ரத்து செய்',
    submit: 'சமர்ப்பி',
    language: 'மொழி',
    no_data: 'தரவு கிடைக்கவில்லை',
    error: 'ஏதோ தவறு நடந்துவிட்டது',
    select_language: 'மொழியைத் தேர்ந்தெடுக்கவும்',
    crop_name: 'பயிரின் பெயர்',
    status: 'நிலை',
    date: 'தேதி',
    actions: 'செயல்கள்',
  },
  kn: {
    dashboard: 'ರೈತರ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್',
    my_batches: 'ಸಂಗ್ರಹಣೆ ಬ್ಯಾಚ್‌ಗಳು',
    monitoring: 'ನೇರ ಮೇಲ್ವಿಚಾರಣೆ',
    diary: 'ಬೆಳೆ ದಿನಚರಿ',
    ai_assistant: 'AI ಸಲಹೆಗಾರ',
    alerts: 'ಸಂಗ್ರಹಣೆ ಎಚ್ಚರಿಕೆಗಳು',
    weather: 'ಹವಾಮಾನ ಮುನ್ಸೂಚನೆ',
    market: 'ಮಾರುಕಟ್ಟೆ ಬೆಲೆಗಳು',
    traditional: 'ಸಾಂಪ್ರದಾಯಿಕ ಮಾರ್ಗದರ್ಶನ',
    admin: 'ನಿರ್ವಾಹಕ ಪೋರ್ಟಲ್',
    onboarding: 'ಬೆಳೆ ನೋಂದಣಿ',
    navigation: 'ನ್ಯಾವಿಗೇಶನ್',
    system_admin: 'ಸಿಸ್ಟಮ್ ನಿರ್ವಾಹಕ',
    admin_management: 'ನಿರ್ವಾಹಕ ನಿರ್ವಹಣೆ',
    temperature: 'ತಾಪಮಾನ',
    humidity: 'ಸಾಪೇಕ್ಷ ಆರ್ದ್ರತೆ',
    safe_range: 'ಸುರಕ್ಷಿತ ವ್ಯಾಪ್ತಿ',
    freshness: 'ಸೆನ್ಸರ್ ಸ್ಥಿತಿ',
    monitoring_batch: 'ಮೇಲ್ವಿಚಾರಣಾ ಬ್ಯಾಚ್',
    logout: 'ಲಾಗ್ ಔಟ್',
    search_prices: 'ಬೆಲೆಗಳನ್ನು ಹುಡುಕಿ',
    profile: 'ನನ್ನ ಪ್ರೊಫೈಲ್',
    loading: 'ಲೋಡ್ ಆಗುತ್ತಿದೆ...',
    translating: 'ಅನುವಾದಿಸಲಾಗುತ್ತಿದೆ...',
    search: 'ಹುಡುಕಿ',
    refresh: 'ರಿಫ್ರೆಶ್',
    save: 'ಉಳಿಸಿ',
    cancel: 'ರದ್ದುಮಾಡಿ',
    submit: 'ಸಲ್ಲಿಸಿ',
    language: 'ಭಾಷೆ',
    no_data: 'ಯಾವುದೇ ಡೇಟಾ ಲಭ್ಯವಿಲ್ಲ',
    error: 'ಏನೋ ತಪ್ಪಾಗಿದೆ',
    select_language: 'ಭಾಷೆಯನ್ನು ಆಯ್ಕೆಮಾಡಿ',
    crop_name: 'ಬೆಳೆಯ ಹೆಸರು',
    status: 'ಸ್ಥಿತಿ',
    date: 'ದಿನಾಂಕ',
    actions: 'ಕ್ರಿಯೆಗಳು',
  },
  mr: {
    dashboard: 'शेतकरी डॅशबोर्ड',
    my_batches: 'साठवण बॅच',
    monitoring: 'थेट निरीक्षण',
    diary: 'पीक डायरी',
    ai_assistant: 'एआय सल्लागार',
    alerts: 'साठवण सूचना',
    weather: 'हवामान अंदाज',
    market: 'बाजारभाव',
    traditional: 'पारंपरिक मार्गदर्शन',
    admin: 'प्रशासक पोर्टल',
    onboarding: 'पीक नोंदणी',
    navigation: 'नेव्हिगेशन',
    system_admin: 'सिस्टम प्रशासक',
    admin_management: 'प्रशासक व्यवस्थापन',
    temperature: 'तापमान',
    humidity: 'सापेक्ष आर्द्रता',
    safe_range: 'सुरक्षित मर्यादा',
    freshness: 'सेन्सर स्थिती',
    monitoring_batch: 'निरीक्षण बॅच',
    logout: 'लॉग आउट',
    search_prices: 'किंमती शोधा',
    profile: 'माझे प्रोफाइल',
    loading: 'लोड होत आहे...',
    translating: 'भाषांतर होत आहे...',
    search: 'शोधा',
    refresh: 'ताजे करा',
    save: 'जतन करा',
    cancel: 'रद्द करा',
    submit: 'सादर करा',
    language: 'भाषा',
    no_data: 'डेटा उपलब्ध नाही',
    error: 'काहीतरी चूक झाली',
    select_language: 'भाषा निवडा',
    crop_name: 'पिकाचे नाव',
    status: 'स्थिती',
    date: 'तारीख',
    actions: 'कृती',
  },
  pa: {
    dashboard: 'ਕਿਸਾਨ ਡੈਸ਼ਬੋਰਡ',
    my_batches: 'ਸਟੋਰੇਜ ਬੈਚ',
    monitoring: 'ਲਾਈਵ ਨਿਗਰਾਨੀ',
    diary: 'ਫਸਲ ਡਾਇਰੀ',
    ai_assistant: 'AI ਸਲਾਹਕਾਰ',
    alerts: 'ਸਟੋਰੇਜ ਚੇਤਾਵਨੀਆਂ',
    weather: 'ਮੌਸਮ ਦੀ ਭਵਿੱਖਬਾਣੀ',
    market: 'ਮੰਡੀ ਭਾਅ',
    traditional: 'ਰਵਾਇਤੀ ਮਾਰਗਦਰਸ਼ਨ',
    admin: 'ਐਡਮਿਨ ਪੋਰਟਲ',
    onboarding: 'ਫਸਲ ਰਜਿਸਟ੍ਰੇਸ਼ਨ',
    navigation: 'ਨੇਵੀਗੇਸ਼ਨ',
    system_admin: 'ਸਿਸਟਮ ਐਡਮਿਨ',
    admin_management: 'ਐਡਮਿਨ ਪ੍ਰਬੰਧਨ',
    temperature: 'ਤਾਪਮਾਨ',
    humidity: 'ਸਾਪੇਖ ਨਮੀ',
    safe_range: 'ਸੁਰੱਖਿਅਤ ਹੱਦ',
    freshness: 'ਸੈਂਸਰ ਸਥਿਤੀ',
    monitoring_batch: 'ਨਿਗਰਾਨੀ ਬੈਚ',
    logout: 'ਲੌਗ ਆਉਟ',
    search_prices: 'ਕੀਮਤਾਂ ਖੋਜੋ',
    profile: 'ਮੇਰਾ ਪ੍ਰੋਫਾਈਲ',
    loading: 'ਲੋਡ ਹੋ ਰਿਹਾ ਹੈ...',
    translating: 'ਅਨੁਵਾਦ ਹੋ ਰਿਹਾ ਹੈ...',
    search: 'ਖੋਜ',
    refresh: 'ਤਾਜ਼ਾ ਕਰੋ',
    save: 'ਸੰਭਾਲੋ',
    cancel: 'ਰੱਦ ਕਰੋ',
    submit: 'ਜਮ੍ਹਾ ਕਰੋ',
    language: 'ਭਾਸ਼ਾ',
    no_data: 'ਕੋਈ ਡਾਟਾ ਉਪਲਬਧ ਨਹੀਂ',
    error: 'ਕੁਝ ਗਲਤ ਹੋ ਗਿਆ',
    select_language: 'ਭਾਸ਼ਾ ਚੁਣੋ',
    crop_name: 'ਫਸਲ ਦਾ ਨਾਮ',
    status: 'ਸਥਿਤੀ',
    date: 'ਤਾਰੀਖ',
    actions: 'ਕਾਰਵਾਈਆਂ',
  },
  bn: {
    dashboard: 'কৃষক ড্যাশবোর্ড',
    my_batches: 'সংরক্ষণ ব্যাচ',
    monitoring: 'লাইভ পর্যবেক্ষণ',
    diary: 'ফসলের ডায়েরি',
    ai_assistant: 'এআই উপদেষ্টা',
    alerts: 'সংরক্ষণ সতর্কতা',
    weather: 'আবহাওয়ার পূর্বাভাস',
    market: 'বাজারদর',
    traditional: 'ঐতিহ্যবাহী নির্দেশনা',
    admin: 'অ্যাডমিন পোর্টাল',
    onboarding: 'ফসল নিবন্ধন',
    navigation: 'নেভিগেশন',
    system_admin: 'সিস্টেম অ্যাডমিন',
    admin_management: 'অ্যাডমিন ব্যবস্থাপনা',
    temperature: 'तापমাত্রা',
    humidity: 'আপেক্ষিক আর্দ্রতা',
    safe_range: 'নিরাপদ সীমা',
    freshness: 'সেন্সরের অবস্থা',
    monitoring_batch: 'পর্যবেক্ষণ ব্যাচ',
    logout: 'লগ আউট',
    search_prices: 'দাম খুঁজুন',
    profile: 'আমার প্রোফাইল',
    loading: 'লোড হচ্ছে...',
    translating: 'অনুবাদ হচ্ছে...',
    search: 'অনুসন্ধান',
    refresh: 'রিফ্রেশ',
    save: 'সংরক্ষণ করুন',
    cancel: 'বাতিল করুন',
    submit: 'জমা দিন',
    language: 'ভাষা',
    no_data: 'কোন তথ্য নেই',
    error: 'কিছু ভুল হয়েছে',
    select_language: 'ভাষা নির্বাচন করুন',
    crop_name: 'ফসলের নাম',
    status: 'অবস্থা',
    date: 'তারিখ',
    actions: 'পদক্ষেপ',
  },
};

function cacheKey(source, target, text) {
  return CACHE_PREFIX + encodeURIComponent(source + '|' + target + '|' + text);
}

function readCache(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeCache(key, value) {
  try {
    const keys = Object.keys(localStorage).filter((item) =>
      item.startsWith(CACHE_PREFIX)
    );
    if (keys.length >= CACHE_LIMIT) {
      keys
        .slice(0, Math.max(1, keys.length - CACHE_LIMIT + 1))
        .forEach((item) => localStorage.removeItem(item));
    }
    localStorage.setItem(key, value);
  } catch {
    /* Storage may be disabled or full; translation still works for this session. */
  }
}

export function LanguageProvider({ children }) {
  const [currentLang, setCurrentLang] = useState(() => {
    try {
      const saved = localStorage.getItem('farmshield_lang') || 'en';
      return SUPPORTED_LANGUAGES.some((language) => language.code === saved)
        ? saved
        : 'en';
    } catch {
      return 'en';
    }
  });

  const [translationCache, setTranslationCache] = useState({});
  const [translatingCount, setTranslatingCount] = useState(0);

  const changeLanguage = useCallback((code) => {
    if (!SUPPORTED_LANGUAGES.some((language) => language.code === code)) return;
    setCurrentLang(code);
    try {
      localStorage.setItem('farmshield_lang', code);
    } catch {
      /* ignore */
    }

    // Keep the server-side farmer profile in sync so WhatsApp and backend agent
    // responses use the same preferred language after a UI language change.
    apiRequest('/auth/me', {
      method: 'PATCH',
      body: JSON.stringify({ preferred_language: code }),
    }).catch((error) => {
      console.warn(
        'Could not persist preferred language to farmer profile:',
        error?.message || error
      );
    });
  }, []);

  const translateText = useCallback(
    async (text, targetLanguage = currentLang, sourceLanguage = 'en') => {
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
          body: JSON.stringify({
            text,
            target_language: targetLanguage,
            source_language: sourceLanguage,
          }),
        });
        const translated = response?.data?.translated_text || text;
        writeCache(key, translated);
        setTranslationCache((previous) => ({ ...previous, [key]: translated }));
        return translated;
      } catch (error) {
        // Do not cache failures; a later attempt can succeed after network/API recovery.
        console.warn(
          'Text translation unavailable; showing original text.',
          error?.message || error
        );
        return text;
      } finally {
        setTranslatingCount((count) => Math.max(0, count - 1));
      }
    },
    [currentLang, translationCache]
  );

  const t = useCallback(
    (key) => {
      const dictionary = UI_TRANSLATIONS[currentLang] || UI_TRANSLATIONS.en;
      return dictionary[key] || UI_TRANSLATIONS.en[key] || key;
    },
    [currentLang]
  );

  useEffect(() => {
    document.documentElement.lang = currentLang;
  }, [currentLang]);

  const value = useMemo(
    () => ({
      currentLang,
      changeLanguage,
      t,
      translateText,
      isTranslating: translatingCount > 0,
      supportedLanguages: SUPPORTED_LANGUAGES,
    }),
    [currentLang, changeLanguage, t, translateText, translatingCount]
  );

  return (
    <LanguageContext.Provider value={value}>
      {children}
      {translatingCount > 0 && (
        <div className="translation-progress" role="status" aria-live="polite">
          <span className="translation-spinner" aria-hidden="true" />
          <span>{t('translating')}</span>
        </div>
      )}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) throw new Error('useLanguage must be used within a LanguageProvider');
  return context;
}
