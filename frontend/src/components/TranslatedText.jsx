import React, { useEffect, useState } from 'react';
import { useLanguage } from '../context/LanguageContext';

const STATIC_TEXT = {
  "Mandi Market Prices": { hi: "मंडी बाजार भाव", te: "మండి మార్కెట్ ధరలు", ta: "மண்டி சந்தை விலைகள்", kn: "ಮಂಡಿ ಮಾರುಕಟ್ಟೆ ಬೆಲೆಗಳು", mr: "मंडी बाजारभाव", pa: "ਮੰਡੀ ਬਾਜ਼ਾਰ ਭਾਅ", bn: "মাণ্ডি বাজারদর" },
  "Agricultural Market Prices": { hi: "कृषि बाजार भाव", te: "వ్యవసాయ మార్కెట్ ధరలు", ta: "விவசாய சந்தை விலைகள்", kn: "ಕೃಷಿ ಮಾರುಕಟ್ಟೆ ಬೆಲೆಗಳು", mr: "कृषी बाजारभाव", pa: "ਖੇਤੀਬਾੜੀ ਬਾਜ਼ਾਰ ਭਾਅ", bn: "কৃষি বাজারদর" },
  "Selected crop": { hi: "चुनी गई फसल", te: "ఎంచుకున్న పంట", ta: "தேர்ந்தெடுத்த பயிர்", kn: "ಆಯ್ಕೆ ಮಾಡಿದ ಬೆಳೆ", mr: "निवडलेले पीक", pa: "ਚੁਣੀ ਫ਼ਸਲ", bn: "নির্বাচিত ফসল" },
  "State": { hi: "राज्य", te: "రాష్ట్రం", ta: "மாநிலம்", kn: "ರಾಜ್ಯ", mr: "राज्य", pa: "ਰਾਜ", bn: "রাজ্য" },
  "District (optional)": { hi: "जिला (वैकल्पिक)", te: "జిల్లా (ఐచ్ఛికం)", ta: "மாவட்டம் (விருப்பம்)", kn: "ಜಿಲ್ಲೆ (ಐಚ್ಛಿಕ)", mr: "जिल्हा (ऐच्छिक)", pa: "ਜ਼ਿਲ੍ਹਾ (ਵਿਕਲਪਿਕ)", bn: "জেলা (ঐচ্ছিক)" },
  "Search Prices": { hi: "कीमतें खोजें", te: "ధరలను వెతకండి", ta: "விலைகளைத் தேடு", kn: "ಬೆಲೆಗಳನ್ನು ಹುಡುಕಿ", mr: "किंमती शोधा", pa: "ਕੀਮਤਾਂ ਖੋਜੋ", bn: "দাম খুঁজুন" },
  "Loading…": { hi: "लोड हो रहा है…", te: "లోడ్ అవుతోంది…", ta: "ஏற்றப்படுகிறது…", kn: "ಲೋಡ್ ಆಗುತ್ತಿದೆ…", mr: "लोड होत आहे…", pa: "ਲੋਡ ਹੋ ਰਿਹਾ ਹੈ…", bn: "লোড হচ্ছে…" },
  "Market prices unavailable": { hi: "बाजार भाव उपलब्ध नहीं हैं", te: "మార్కెట్ ధరలు అందుబాటులో లేవు", ta: "சந்தை விலைகள் கிடைக்கவில்லை", kn: "ಮಾರುಕಟ್ಟೆ ಬೆಲೆಗಳು ಲಭ್ಯವಿಲ್ಲ", mr: "बाजारभाव उपलब्ध नाहीत", pa: "ਬਾਜ਼ਾਰ ਭਾਅ ਉਪਲਬਧ ਨਹੀਂ", bn: "বাজারদর পাওয়া যাচ্ছে না" },
  "Market information": { hi: "बाजार की जानकारी", te: "మార్కెట్ సమాచారం", ta: "சந்தை தகவல்", kn: "ಮಾರುಕಟ್ಟೆ ಮಾಹಿತಿ", mr: "बाजार माहिती", pa: "ਬਾਜ਼ਾਰ ਜਾਣਕਾਰੀ", bn: "বাজারের তথ্য" },
  "Historical market prices": { hi: "ऐतिहासिक बाजार भाव", te: "చారిత్రక మార్కెట్ ధరలు", ta: "வரலாற்று சந்தை விலைகள்", kn: "ಐತಿಹಾಸಿಕ ಮಾರುಕಟ್ಟೆ ಬೆಲೆಗಳು", mr: "ऐतिहासिक बाजारभाव", pa: "ਪੁਰਾਣੇ ਬਾਜ਼ਾਰ ਭਾਅ", bn: "ঐতিহাসিক বাজারদর" },
  "Actual historical prices": { hi: "वास्तविक ऐतिहासिक कीमतें", te: "వాస్తవ చారిత్రక ధరలు", ta: "உண்மையான வரலாற்று விலைகள்", kn: "ನೈಜ ಐತಿಹಾಸಿಕ ಬೆಲೆಗಳು", mr: "प्रत्यक्ष ऐतिहासिक किंमती", pa: "ਅਸਲ ਪੁਰਾਣੇ ਭਾਅ", bn: "প্রকৃত ঐতিহাসিক দাম" },
  "Indicative forecast": { hi: "संकेतात्मक पूर्वानुमान", te: "సూచనాత్మక అంచనా", ta: "குறிப்பான முன்னறிவிப்பு", kn: "ಸೂಚಕ ಮುನ್ಸೂಚನೆ", mr: "सूचक अंदाज", pa: "ਸੰਕੇਤਕ ਅਨੁਮਾਨ", bn: "ইঙ্গিতমূলক পূর্বাভাস" },
  "Date": { hi: "तारीख", te: "తేదీ", ta: "தேதி", kn: "ದಿನಾಂಕ", mr: "तारीख", pa: "ਤਾਰੀਖ", bn: "তারিখ" },
  "Observations": { hi: "अवलोकन", te: "పరిశీలనలు", ta: "கண்காணிப்புகள்", kn: "ಅವಲೋಕನಗಳು", mr: "निरीक्षणे", pa: "ਨਿਰੀਖਣ", bn: "পর্যবেক্ষণ" },
  "7-day price outlook": { hi: "7-दिन का मूल्य पूर्वानुमान", te: "7 రోజుల ధర అంచనా", ta: "7 நாள் விலை முன்னறிவிப்பு", kn: "7 ದಿನಗಳ ಬೆಲೆ ಮುನ್ಸೂಚನೆ", mr: "7-दिवसांचा किंमत अंदाज", pa: "7-ਦਿਨਾਂ ਦਾ ਕੀਮਤ ਅਨੁਮਾਨ", bn: "৭ দিনের দামের পূর্বাভাস" },
  "Forecast date": { hi: "पूर्वानुमान की तारीख", te: "అంచనా తేదీ", ta: "முன்னறிவிப்பு தேதி", kn: "ಮುನ್ಸೂಚನೆ ದಿನಾಂಕ", mr: "अंदाजाची तारीख", pa: "ਅਨੁਮਾਨ ਦੀ ਤਾਰੀਖ", bn: "পূর্বাভাসের তারিখ" },
  "Estimated price / quintal": { hi: "अनुमानित कीमत / क्विंटल", te: "అంచనా ధర / క్వింటాల్", ta: "மதிப்பிடப்பட்ட விலை / குவிண்டால்", kn: "ಅಂದಾಜು ಬೆಲೆ / ಕ್ವಿಂಟಾಲ್", mr: "अंदाजित किंमत / क्विंटल", pa: "ਅਨੁਮਾਨਿਤ ਕੀਮਤ / ਕੁਇੰਟਲ", bn: "আনুমানিক দাম / কুইন্টাল" },
  "Indicative range": { hi: "संकेतात्मक सीमा", te: "సూచనాత్మక పరిధి", ta: "குறிப்பான வரம்பு", kn: "ಸೂಚಕ ವ್ಯಾಪ್ತಿ", mr: "सूचक श्रेणी", pa: "ਸੰਕੇਤਕ ਸੀਮਾ", bn: "ইঙ্গিতমূলক পরিসর" },
};

/**
 * Translates visible copy when the selected language changes.
 * Cached translations are rendered immediately; new translations fade in.
 */
export default function TranslatedText({ text, as: Element = 'span', sourceLanguage = 'en', className = '', ...props }) {
  const { currentLang, translateText } = useLanguage();
  const [value, setValue] = useState(text);
  const [ready, setReady] = useState(currentLang === sourceLanguage);

  useEffect(() => {
    let active = true;
    setValue(text);
    if (currentLang === sourceLanguage) {
      setReady(true);
      return () => { active = false; };
    }

    const staticTranslation = STATIC_TEXT[String(text)]?.[currentLang];
    if (staticTranslation) {
      setValue(staticTranslation);
      setReady(true);
      return () => { active = false; };
    }

    setReady(false);
    translateText(String(text), currentLang, sourceLanguage).then((translated) => {
      if (active) {
        setValue(translated || text);
        setReady(true);
      }
    });
    return () => { active = false; };
  }, [text, currentLang, sourceLanguage, translateText]);

  return (
    <Element
      {...props}
      className={['translation-fade', ready ? 'translation-ready' : 'translation-pending', className].filter(Boolean).join(' ')}
      aria-busy={!ready}
    >
      {value}
    </Element>
  );
}
