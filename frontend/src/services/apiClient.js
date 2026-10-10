
const BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

const LANG_KEY = "farmshield_lang";
const TOKEN_KEY = "farmshield_token";
const translationCache = new Map();
const MAX_CACHE = 3000;

const TRANSLATABLE_KEYS = new Set([
  "message",
  "detail",
  "description",
  "title",
  "content",
  "answer",
  "response",
  "recommendation",
  "recommended_action",
  "storage_impact_summary",
  "weather_condition",
  "summary",
  "advice",
  "guidance",
  "explanation",
  "insight",
  "notification",
  "body",
  "question",
  "text",
  "reason",
  "instructions",
  "display_message",
  "crop_name",
  "crop_type",
  "crop_name_local",
  "weather_description",
  "condition",
  "advice_text",
  "advisory",
  "alert_title",
  "alert_message",
  "action",
  "market_name",
  "mandi_name",
  "district_name",
  "state_name",
  "forecast_summary",
  "risk_description",
  "pest_name",
  "disease_name",
  "symptoms",
  "prevention",
  "treatment",
  "benefit",
  "tip",
  "tips",
  "headline",
  "news_title",
  "news_description",
  "news_summary",
  "recommendation_text",
  "suggestion",
  "label_text",
  "placeholder",
  "help_text",
]);

const NEVER_TRANSLATE_KEYS = new Set([
  "id",
  "user_id",
  "batch_id",
  "crop_id",
  "alert_id",
  "message_id",
  "conversation_id",
  "email",
  "phone",
  "token",
  "access_token",
  "refresh_token",
  "status",
  "severity",
  "role",
  "provider",
  "source",
  "source_name",
  "language",
  "target_language",
  "source_language",
  "timestamp",
  "created_at",
  "updated_at",
  "price_date",
  "date",
  "trend",
  "price_trend",
  "unit",
  "currency",
  "symbol",
  "code",
  "crop_code",
  "market_id",
  "district_id",
  "state_id",
  "latitude",
  "longitude",
  "lat",
  "lon",
  "lng",
]);

function getCurrentLanguage() {
  try {
    return localStorage.getItem(LANG_KEY) || "en";
  } catch {
    return "en";
  }
}

function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

async function translateTexts(texts, language) {
  const uniqueTexts = [
    ...new Set(
      texts.filter(
        (text) => typeof text === "string" && text.trim().length > 0,
      ),
    ),
  ];

  const missing = uniqueTexts.filter(
    (text) => !translationCache.has(`${language}\u0000${text}`),
  );

  const token = getToken();

  for (let offset = 0; offset < missing.length; offset += 100) {
    const chunk = missing.slice(offset, offset + 100);

    try {
      const response = await fetch(`${BASE_URL}/translation/batch`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          texts: chunk,
          target_language: language,
          source_language: "en",
        }),
      });

      if (!response.ok) {
        throw new Error(`Translation failed with HTTP ${response.status}`);
      }

      const payload = await response.json();
      const translated =
        payload?.data?.translated_texts ||
        payload?.translated_texts ||
        [];

      chunk.forEach((text, index) => {
        const translatedText = translated[index];
        translationCache.set(
          `${language}\u0000${text}`,
          typeof translatedText === "string" && translatedText
            ? translatedText
            : text,
        );
      });
    } catch (error) {
      chunk.forEach((text) => {
        translationCache.set(`${language}\u0000${text}`, text);
      });

      console.warn(
        "Azure translation failed. Original text will be used.",
        error?.message || error,
      );
    }

    if (translationCache.size > MAX_CACHE) {
      translationCache.clear();
    }
  }

  return new Map(
    uniqueTexts.map((text) => [
      text,
      translationCache.get(`${language}\u0000${text}`) || text,
    ]),
  );
}

function collectTranslatable(value, output = []) {
  if (Array.isArray(value)) {
    value.forEach((item) => collectTranslatable(item, output));
    return output;
  }

  if (!value || typeof value !== "object") {
    return output;
  }

  Object.entries(value).forEach(([key, child]) => {
    const normalizedKey = key.toLowerCase();

    if (
      typeof child === "string" &&
      TRANSLATABLE_KEYS.has(normalizedKey) &&
      !NEVER_TRANSLATE_KEYS.has(normalizedKey) &&
      child.trim()
    ) {
      output.push(child);
    } else if (child && typeof child === "object") {
      collectTranslatable(child, output);
    }
  });

  return output;
}

function applyTranslations(value, translations) {
  if (Array.isArray(value)) {
    return value.map((item) => applyTranslations(item, translations));
  }

  if (!value || typeof value !== "object") {
    return value;
  }

  const result = {};

  Object.entries(value).forEach(([key, child]) => {
    const normalizedKey = key.toLowerCase();

    if (
      typeof child === "string" &&
      TRANSLATABLE_KEYS.has(normalizedKey) &&
      !NEVER_TRANSLATE_KEYS.has(normalizedKey)
    ) {
      result[key] = translations.get(child) || child;
    } else {
      result[key] = applyTranslations(child, translations);
    }
  });

  return result;
}

export async function translateApiData(
  data,
  language = getCurrentLanguage(),
) {
  if (!data || language === "en") {
    return data;
  }

  const texts = collectTranslatable(data);

  if (!texts.length) {
    return data;
  }

  const translations = await translateTexts(texts, language);

  return applyTranslations(data, translations);
}

export async function apiRequest(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;
  const token = getToken();

  const isFormData =
    typeof FormData !== "undefined" && options.body instanceof FormData;

  const headers = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  const response = await fetch(url, {
    ...options,
    headers,
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const errorMessage =
      data?.detail || data?.message || `HTTP ${response.status} Error`;

    throw new Error(errorMessage);
  }

  // Translation results must not be translated a second time.
  if (!endpoint.startsWith("/translation")) {
    return translateApiData(data);
  }

  return data;
}
