import React, { useEffect, useState } from 'react';
import { useLanguage } from '../context/LanguageContext';

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
