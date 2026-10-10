import React, { useState, useEffect, useRef } from 'react';
import { chatbotService, speechService } from '../../services/monitoringService';
import { useLanguage } from '../../context/LanguageContext';
import {
  MessageSquare,
  Send,
  BookOpen,
  Sparkles,
  Bot,
  User,
  ShieldCheck,
  PlusCircle,
  Volume2,
  VolumeX,
  Mic,
  MicOff,
  CheckCircle,
  Calendar,
  CloudSun,
  TrendingUp,
  AlertTriangle,
  Globe,
  RefreshCw,
  Clock,
  Check,
} from 'lucide-react';

const SUPPORTED_LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'हिंदी (Hindi)' },
  { code: 'te', label: 'తెలుగు (Telugu)' },
  { code: 'ta', label: 'தமிழ் (Tamil)' },
  { code: 'kn', label: 'ಕನ್ನಡ (Kannada)' },
  { code: 'mr', label: 'मराठी (Marathi)' },
  { code: 'pa', label: 'ਪੰਜਾਬੀ (Punjabi)' },
  { code: 'bn', label: 'বাংলা (Bengali)' },
];

// Helper to parse sections with custom cards and icons
function parseSections(text) {
  if (!text) return [];
  const regex = /(?:^|\n)\s*\*\*([^*]+?):?\*\*\s*:?\s*/g;
  const sections = [];
  let lastIndex = 0;
  let currentHeader = null;
  let match;

  while ((match = regex.exec(text)) !== null) {
    const matchedHeader = match[1].trim();
    const matchStart = match.index;
    if (currentHeader) {
      const body = text.substring(lastIndex, matchStart).trim();
      sections.push({ header: currentHeader, body });
    } else {
      const leadingText = text.substring(0, matchStart).trim();
      if (leadingText) {
        sections.push({ header: null, body: leadingText });
      }
    }
    currentHeader = matchedHeader;
    lastIndex = match.index + match[0].length;
  }

  if (currentHeader) {
    const body = text.substring(lastIndex).trim();
    sections.push({ header: currentHeader, body });
  } else if (sections.length === 0) {
    sections.push({ header: null, body: text.trim() });
  }

  return sections;
}

// Inline bold formatter replacing **text** with clean <strong>
function renderInlineFormatting(text) {
  if (!text) return null;
  const parts = text.split(/(\*\*[^*]+?\*\*)/g);
  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**') && part.length >= 4) {
      const boldText = part.slice(2, -2);
      return (
        <strong key={index} style={{ color: '#38bdf8', fontWeight: '700' }}>
          {boldText}
        </strong>
      );
    }
    return part;
  });
}

function renderGeneralContent(text) {
  if (!text) return null;
  const lines = text.split('\n');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
      {lines.map((line, lIdx) => {
        const trimmed = line.trim();
        if (!trimmed) return null;

        // Numbered list item: e.g. "1. ..."
        const numMatch = trimmed.match(/^(\d+)\.\s*(.*)$/);
        if (numMatch) {
          return (
            <div key={lIdx} style={{ display: 'flex', gap: '9px', alignItems: 'flex-start', marginTop: '3px' }}>
              <span
                style={{
                  background: 'rgba(56, 189, 248, 0.2)',
                  color: '#38bdf8',
                  borderRadius: '50%',
                  width: '20px',
                  height: '20px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '0.74rem',
                  fontWeight: '700',
                  flexShrink: 0,
                  marginTop: '2px',
                }}
              >
                {numMatch[1]}
              </span>
              <span style={{ flex: 1 }}>{renderInlineFormatting(numMatch[2])}</span>
            </div>
          );
        }

        // Bullet item: e.g. "- ..." or "* ..." or "• ..."
        const bulletMatch = trimmed.match(/^[-*•]\s*(.*)$/);
        if (bulletMatch) {
          const isSub = line.startsWith('   ') || line.startsWith('\t');
          return (
            <div key={lIdx} style={{ display: 'flex', gap: '8px', alignItems: 'flex-start', marginLeft: isSub ? '20px' : '4px' }}>
              <span style={{ color: '#10b981', fontSize: '0.9rem', lineHeight: '1.4rem' }}>•</span>
              <span style={{ flex: 1 }}>{renderInlineFormatting(bulletMatch[1])}</span>
            </div>
          );
        }

        // Friendly closing line (e.g. "మీకు మరేదైనా సహాయం కావాలా?..." or "🙏")
        if (trimmed.includes('సహాయం') || trimmed.includes('🙏') || trimmed.includes('help') || trimmed.includes('మదద్')) {
          return (
            <div key={lIdx} style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px dashed rgba(255, 255, 255, 0.1)', color: '#94a3b8', fontStyle: 'italic', fontSize: '0.86rem' }}>
              {renderInlineFormatting(trimmed)}
            </div>
          );
        }

        return <div key={lIdx}>{renderInlineFormatting(trimmed)}</div>;
      })}
    </div>
  );
}

// High-impact structured response card formatter for farming recommendations
function FormattedMessage({ content }) {
  if (!content) return null;
  const sections = parseSections(content);

  // If there are no structured sections, render cleanly as formatted paragraphs
  if (sections.length === 1 && !sections[0].header) {
    return <div style={{ lineHeight: 1.6 }}>{renderGeneralContent(content)}</div>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      {sections.map((sec, idx) => {
        if (!sec.header) {
          return (
            <div key={idx} style={{ lineHeight: 1.6, color: '#f8fafc' }}>
              {renderGeneralContent(sec.body)}
            </div>
          );
        }

        const hLower = sec.header.toLowerCase();
        let badge = {
          bg: 'rgba(56, 189, 248, 0.08)',
          border: 'rgba(56, 189, 248, 0.25)',
          left: '#38bdf8',
          color: '#38bdf8',
          icon: <CheckCircle size={15} color="#38bdf8" />,
        };

        if (hLower.includes('recommend') || hLower.includes('సిఫార్సు') || hLower.includes('सिफारिश')) {
          badge = {
            bg: 'linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(5, 150, 105, 0.08) 100%)',
            border: 'rgba(16, 185, 129, 0.35)',
            left: '#10b981',
            color: '#34d399',
            icon: <Sparkles size={15} color="#10b981" />,
          };
        } else if (hLower.includes('why') || hLower.includes('ఎందుకు') || hLower.includes('कारण')) {
          badge = {
            bg: 'rgba(56, 189, 248, 0.08)',
            border: 'rgba(56, 189, 248, 0.25)',
            left: '#38bdf8',
            color: '#38bdf8',
            icon: <CheckCircle size={15} color="#38bdf8" />,
          };
        } else if (hLower.includes('next') || hLower.includes('చర్య') || hLower.includes('करें')) {
          badge = {
            bg: 'rgba(245, 158, 11, 0.08)',
            border: 'rgba(245, 158, 11, 0.25)',
            left: '#f59e0b',
            color: '#fbbf24',
            icon: <Calendar size={15} color="#f59e0b" />,
          };
        } else if (hLower.includes('risk') || hLower.includes('ప్రమాద') || hLower.includes('जोखिम')) {
          badge = {
            bg: 'rgba(244, 63, 94, 0.08)',
            border: 'rgba(244, 63, 94, 0.25)',
            left: '#f43f5e',
            color: '#fb7185',
            icon: <AlertTriangle size={15} color="#f43f5e" />,
          };
        } else if (hLower.includes('data') || hLower.includes('డేటా') || hLower.includes('डेटा')) {
          badge = {
            bg: 'rgba(99, 102, 241, 0.08)',
            border: 'rgba(99, 102, 241, 0.25)',
            left: '#818cf8',
            color: '#a5b4fc',
            icon: <ShieldCheck size={15} color="#818cf8" />,
          };
        }

        return (
          <div
            key={idx}
            style={{
              background: badge.bg,
              border: `1px solid ${badge.border}`,
              borderLeft: `4px solid ${badge.left}`,
              borderRadius: '10px',
              padding: '12px 16px',
              boxShadow: '0 2px 6px rgba(0, 0, 0, 0.15)',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '7px',
                color: badge.color,
                fontWeight: '700',
                fontSize: '0.88rem',
                marginBottom: '8px',
                textTransform: 'capitalize',
              }}
            >
              {badge.icon}
              <span>{sec.header}</span>
            </div>
            <div style={{ fontSize: '0.91rem', lineHeight: 1.65, color: '#f1f5f9' }}>
              {renderGeneralContent(sec.body)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function ChatbotPage({ activeBatch }) {
  // Synchronize with global website language
  let globalLang = 'en';
  let setGlobalLanguage = null;
  try {
    const langContext = useLanguage();
    globalLang = langContext.currentLang;
    setGlobalLanguage = langContext.changeLanguage;
  } catch {
    // Fallback if rendered outside provider
  }

  const [chatLang, setChatLang] = useState(() => {
    return globalLang || localStorage.getItem('farmshield_lang') || 'en';
  });

  const [autoVoice, setAutoVoice] = useState(() => {
    try {
      const saved = localStorage.getItem('farmshield_auto_voice');
      return saved !== null ? saved === 'true' : true;
    } catch {
      return true;
    }
  });

  const [conversations, setConversations] = useState([]);
  const [currentConvoId, setCurrentConvoId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [confirmingAction, setConfirmingAction] = useState(false);

  // Audio / Speech-to-Text & Text-to-Speech State
  const [speakingMessageId, setSpeakingMessageId] = useState(null);
  const [loadingSpeechMessageId, setLoadingSpeechMessageId] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [speechError, setSpeechError] = useState(null);

  const messagesEndRef = useRef(null);
  const activeAudioRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recordTimerRef = useRef(null);
  const recognitionRef = useRef(null);

  const suggestedQuestions = [
    { label: '🌦️ 7-Day Weather Forecast', text: 'What is the 7-day weather forecast and rain probability for my farm?' },
    { label: '🌡️ Storage Temperature Limits', text: 'How are my wheat storage temperature and safe ICAR limits?' },
    { label: '💰 Best Day to Sell Harvest', text: 'Should I sell my wheat harvest today or hold for better mandi prices?' },
    { label: '🐛 Natural Weevil Deterrence', text: 'How do I protect my stored grain from weevils naturally using neem?' },
    { label: '📅 Plan Wheat Harvest Date', text: 'I want to harvest my wheat on October 18.' },
  ];

  // Sync when website global language changes
  useEffect(() => {
    if (globalLang && globalLang !== chatLang) {
      setChatLang(globalLang);
    }
  }, [globalLang]);

  const handleLanguageChange = (code) => {
    stopSpeaking();
    setChatLang(code);
    if (setGlobalLanguage) {
      setGlobalLanguage(code);
    }
    try {
      localStorage.setItem('farmshield_lang', code);
    } catch {}
  };

  // Stop any active audio playback immediately
  const stopSpeaking = () => {
    if (activeAudioRef.current) {
      activeAudioRef.current.pause();
      activeAudioRef.current.currentTime = 0;
      activeAudioRef.current = null;
    }
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    setSpeakingMessageId(null);
    setLoadingSpeechMessageId(null);
  };

  useEffect(() => {
    stopSpeaking();
  }, [currentConvoId, chatLang]);

  useEffect(() => {
    async function loadConversations() {
      setLoading(true);
      try {
        const convos = await chatbotService.getConversations();
        setConversations(convos);
        if (convos && convos.length > 0) {
          selectConversation(convos[0].conversation_id);
        } else {
          handleNewConversation();
        }
      } catch (err) {
        console.error('Error loading conversations:', err);
      } finally {
        setLoading(false);
      }
    }
    loadConversations();

    return () => {
      stopSpeaking();
    };
  }, [activeBatch]);

  // Stop audio on language change
  useEffect(() => {
    stopSpeaking();
  }, [chatLang]);

  const selectConversation = async (convoId) => {
    stopSpeaking();
    setCurrentConvoId(convoId);
    try {
      const msgs = await chatbotService.getMessages(convoId);
      setMessages(msgs);
    } catch (err) {
      console.error(err);
    }
  };

  const handleNewConversation = async () => {
    stopSpeaking();
    try {
      const newConvo = await chatbotService.createConversation({
        title: `Advisory for ${activeBatch ? activeBatch.custom_batch_name : 'Crop Storage'}`,
        batch_id: activeBatch?.batch_id,
        language: chatLang,
      });
      setConversations((prev) => [newConvo, ...prev]);
      setCurrentConvoId(newConvo.conversation_id);
      setMessages([]);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSendMessage = async (textToSend = null) => {
    stopSpeaking();
    const text = textToSend || inputMessage;
    if (!text.trim() || !currentConvoId) return;

    const userMsg = {
      message_id: `temp_${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
      sources: [],
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputMessage('');
    setSending(true);

    try {
      const response = await chatbotService.sendMessage(currentConvoId, {
        message: text,
        batch_id: activeBatch?.batch_id,
        language: chatLang,
      });
      setMessages((prev) => [...prev, response]);

      // Automatically read aloud in selected language if autoVoice is active
      if (autoVoice && response.content) {
        handleToggleSpeak(response.message_id, response.content);
      }
    } catch (err) {
      alert(err.message || 'Error generating AI response');
    } finally {
      setSending(false);
    }
  };

  // Structured Confirmation Action Execution (1-click from UI card)
  const handleConfirmPendingAction = async (actionData) => {
    if (!currentConvoId || !actionData) return;
    stopSpeaking();
    setConfirmingAction(true);
    try {
      const response = await chatbotService.confirmAction(currentConvoId, actionData);
      setMessages((prev) => [...prev, response]);
      // Trigger global event so dashboard updates without reload
      window.dispatchEvent(new CustomEvent('farmshield:alert-updated', { detail: { action: 'schedule_updated' } }));
    } catch (err) {
      alert(err.message || 'Failed to confirm farming activity.');
    } finally {
      setConfirmingAction(false);
    }
  };

  const langCodes = {
    en: 'en-IN',
    hi: 'hi-IN',
    te: 'te-IN',
    ta: 'ta-IN',
    kn: 'kn-IN',
    mr: 'mr-IN',
    pa: 'pa-IN',
    bn: 'bn-IN',
  };

  const cleanSpeechText = (rawText) => {
    if (!rawText) return '';
    return rawText
      .replace(/```[\s\S]*?```/g, ' ')
      .replace(/\{[\s\S]*?\}/g, ' ')
      .replace(/^\|.*\|$/gm, ' ')
      .replace(/\n*###?\s*Referenced Sources[\s\S]*$/gi, '')
      .replace(/\n*Referenced Sources:[\s\S]*$/gi, '')
      .replace(/https?:\/\/\S+/g, '')
      .replace(/[*#_`>~\[\]]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  };

  // Text-To-Speech Playback with Azure Neural TTS & Browser Native Fallback
  const handleToggleSpeak = async (messageId, text) => {
    if (speakingMessageId === messageId || loadingSpeechMessageId === messageId) {
      stopSpeaking();
      return;
    }

    stopSpeaking();
    setLoadingSpeechMessageId(messageId);
    setSpeechError(null);

    const cleanText = cleanSpeechText(text);
    if (!cleanText) {
      setLoadingSpeechMessageId(null);
      return;
    }

    try {
      // 1. Attempt Azure Neural Text-to-Speech via backend
      const audioBlob = await speechService.synthesizeSpeech(cleanText, chatLang);
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);

      audio.onplay = () => {
        setLoadingSpeechMessageId(null);
        setSpeakingMessageId(messageId);
      };

      audio.onended = () => {
        setSpeakingMessageId(null);
        setLoadingSpeechMessageId(null);
        URL.revokeObjectURL(audioUrl);
      };

      audio.onerror = () => {
        URL.revokeObjectURL(audioUrl);
        fallbackBrowserSpeech(cleanText, messageId);
      };

      activeAudioRef.current = audio;
      await audio.play();
    } catch (err) {
      console.warn('Azure TTS endpoint unavailable, falling back to browser speech:', err.message);
      fallbackBrowserSpeech(cleanText, messageId);
    }
  };

  const fallbackBrowserSpeech = (cleanText, messageId) => {
    if (!window.speechSynthesis) {
      setSpeakingMessageId(null);
      setLoadingSpeechMessageId(null);
      setSpeechError('Text-to-speech is not supported in this browser.');
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(cleanText);

    utterance.lang = langCodes[chatLang] || 'en-IN';
    utterance.rate = 0.95;

    utterance.onstart = () => {
      setLoadingSpeechMessageId(null);
      setSpeakingMessageId(messageId);
    };

    utterance.onend = () => {
      setSpeakingMessageId(null);
      setLoadingSpeechMessageId(null);
    };

    utterance.onerror = (e) => {
      console.warn('Browser speech synthesis error:', e);
      setSpeakingMessageId(null);
      setLoadingSpeechMessageId(null);
    };

    window.speechSynthesis.speak(utterance);
  };

  // Voice Input (Speech-to-Text Microphone Recording)
  const startRecording = async () => {
    stopSpeaking();
    setSpeechError(null);

    // Prefer Web Speech API if supported in browser for real-time transcription
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (SpeechRecognition) {
      try {
        const recognition = new SpeechRecognition();
        recognitionRef.current = recognition;
        recognition.lang = langCodes[chatLang] || 'en-IN';
        recognition.continuous = false;
        recognition.interimResults = false;

        recognition.onstart = () => {
          setIsRecording(true);
          setRecordingSeconds(0);
          recordTimerRef.current = setInterval(() => {
            setRecordingSeconds((prev) => prev + 1);
          }, 1000);
        };

        recognition.onresult = (event) => {
          const transcript = event.results[0]?.[0]?.transcript;
          if (transcript) {
            setInputMessage((prev) => (prev ? `${prev} ${transcript}` : transcript));
          }
        };

        recognition.onerror = (event) => {
          console.warn('Web Speech recognition notice:', event.error);
          if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
            setSpeechError('Microphone permission was denied. Please allow microphone access in your browser.');
          } else if (event.error !== 'no-speech') {
            startMediaRecorderFallback();
          }
        };

        recognition.onend = () => {
          setIsRecording(false);
          clearInterval(recordTimerRef.current);
          recognitionRef.current = null;
        };

        recognition.start();
        return;
      } catch (e) {
        console.warn('Could not initialize Web Speech, falling back to MediaRecorder:', e);
      }
    }

    // MediaRecorder + Backend Azure/Whisper fallback
    await startMediaRecorderFallback();
  };

  const startMediaRecorderFallback = async () => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setSpeechError('Microphone access is not supported in this browser.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];

      const options = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? { mimeType: 'audio/webm;codecs=opus' }
        : MediaRecorder.isTypeSupported('audio/ogg;codecs=opus')
        ? { mimeType: 'audio/ogg;codecs=opus' }
        : {};

      const mediaRecorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        const mimeType = mediaRecorder.mimeType || 'audio/webm';
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });

        if (audioBlob.size < 400) {
          return;
        }

        setIsTranscribing(true);
        try {
          const ext = mimeType.includes('ogg') ? 'ogg' : 'webm';
          const file = new File([audioBlob], `voice_query.${ext}`, { type: mimeType });
          const res = await speechService.transcribeAudio(file, chatLang);
          if (res?.transcript) {
            setInputMessage((prev) => (prev ? `${prev} ${res.transcript}` : res.transcript));
            setSpeechError(null);
          }
        } catch (err) {
          console.warn('Voice transcription error:', err.message);
          setSpeechError(err.message || 'Could not recognize speech. Please try speaking again.');
        } finally {
          setIsTranscribing(false);
        }
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordingSeconds(0);
      recordTimerRef.current = setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setSpeechError('Microphone permission was denied. Please allow microphone access in your browser settings.');
      } else {
        setSpeechError(`Could not access microphone: ${err.message || 'Unknown error'}`);
      }
    }
  };

  const stopRecording = () => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {
        // ignore
      }
      recognitionRef.current = null;
    }
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
    clearInterval(recordTimerRef.current);
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', height: 'calc(100vh - 120px)' }}>
      {/* Top Header Bar */}
      <div className="glass-panel" style={{ padding: '16px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="badge badge-verified">
              <Sparkles size={13} /> Friendly Multi-Lingual AI Farmer Assistant
            </span>
            {activeBatch && (
              <span style={{ fontSize: '0.82rem', color: '#94a3b8' }}>
                Batch: <strong style={{ color: '#38bdf8' }}>{activeBatch.custom_batch_name}</strong>
              </span>
            )}
          </div>
          <h1 style={{ fontSize: '1.5rem', marginTop: '4px', color: '#f8fafc' }}>
            FarmShield AI Farming Advisor & Diary Assistant
          </h1>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Language Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(255, 255, 255, 0.05)', padding: '6px 12px', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
            <Globe size={15} color="#38bdf8" />
            <select
              style={{ background: 'transparent', border: 'none', color: '#f8fafc', fontSize: '0.85rem', outline: 'none', cursor: 'pointer' }}
              value={chatLang}
              onChange={(e) => handleLanguageChange(e.target.value)}
            >
              {SUPPORTED_LANGUAGES.map((l) => (
                <option key={l.code} value={l.code} style={{ background: '#0f172a', color: '#fff' }}>
                  {l.label}
                </option>
              ))}
            </select>
          </div>

          {/* Auto Voice Read-Aloud Toggle */}
          <button
            type="button"
            className="btn-secondary"
            onClick={() => {
              const next = !autoVoice;
              setAutoVoice(next);
              try {
                localStorage.setItem('farmshield_auto_voice', String(next));
              } catch {}
              if (!next) stopSpeaking();
            }}
            style={{
              fontSize: '0.82rem',
              padding: '6px 12px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: autoVoice ? 'rgba(16, 185, 129, 0.15)' : 'rgba(255, 255, 255, 0.05)',
              border: autoVoice ? '1px solid rgba(16, 185, 129, 0.35)' : '1px solid rgba(255, 255, 255, 0.1)',
              color: autoVoice ? '#34d399' : '#94a3b8',
              borderRadius: '8px',
              cursor: 'pointer',
            }}
            title={autoVoice ? "Auto read-aloud active (click to turn off auto voice)" : "Auto read-aloud off (click to enable auto voice)"}
          >
            {autoVoice ? <Volume2 size={15} /> : <VolumeX size={15} />}
            <span>{autoVoice ? 'Auto Voice: ON' : 'Auto Voice: OFF'}</span>
          </button>

          <button className="btn-secondary" onClick={handleNewConversation} style={{ fontSize: '0.85rem' }} title="Start a fresh advisory conversation">
            <PlusCircle size={16} /> New Chat
          </button>
        </div>
      </div>

      {/* Main Chat Panel */}
      <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Messages Stream */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {messages.length === 0 && (
            <div style={{ textAlign: 'center', margin: 'auto', maxWidth: '620px', padding: '20px' }}>
              <div style={{
                width: '68px',
                height: '68px',
                borderRadius: '50%',
                background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.25) 0%, rgba(5, 150, 105, 0.15) 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 16px',
                border: '1px solid rgba(16, 185, 129, 0.4)'
              }}>
                <Bot size={36} color="#10b981" />
              </div>
              <h2 style={{ fontSize: '1.45rem', marginBottom: '8px', color: '#f8fafc' }}>
                Namaste! How can I assist your farm today?
              </h2>
              <p style={{ color: '#94a3b8', fontSize: '0.92rem', marginBottom: '24px', lineHeight: 1.6 }}>
                Ask any question naturally by typing or using your microphone. I can evaluate your crop storage temperature, give 7-day weather advisories, recommend when to sell in local mandis, or schedule your upcoming harvest.
              </p>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '10px', textAlign: 'left' }}>
                {suggestedQuestions.map((q, idx) => (
                  <button
                    key={idx}
                    className="btn-secondary"
                    style={{ fontSize: '0.84rem', padding: '10px 14px', borderRadius: '10px', textAlign: 'left', lineHeight: 1.4 }}
                    onClick={() => handleSendMessage(q.text)}
                  >
                    <div style={{ fontWeight: '600', color: '#38bdf8', marginBottom: '2px' }}>{q.label}</div>
                    <div style={{ color: '#cbd5e1', fontSize: '0.78rem' }}>{q.text}</div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, idx) => {
            const isBot = m.role === 'assistant';
            const isSpeaking = speakingMessageId === m.message_id;
            const isLoadingSpeech = loadingSpeechMessageId === m.message_id;

            return (
              <div
                key={m.message_id || idx}
                style={{
                  display: 'flex',
                  gap: '12px',
                  alignSelf: isBot ? 'flex-start' : 'flex-end',
                  maxWidth: isBot ? '85%' : '75%',
                }}
              >
                {isBot && (
                  <div style={{
                    width: '38px',
                    height: '38px',
                    borderRadius: '50%',
                    background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                    boxShadow: '0 4px 10px rgba(16, 185, 129, 0.3)'
                  }}>
                    <Bot size={20} color="#fff" />
                  </div>
                )}

                <div style={{
                  background: isBot ? 'rgba(30, 41, 59, 0.9)' : 'linear-gradient(135deg, rgba(16, 185, 129, 0.3) 0%, rgba(5, 150, 105, 0.25) 100%)',
                  border: isBot ? '1px solid rgba(255, 255, 255, 0.1)' : '1px solid rgba(16, 185, 129, 0.4)',
                  borderRadius: '14px',
                  padding: '16px 20px',
                  color: '#f8fafc',
                  fontSize: '0.93rem',
                  lineHeight: 1.6,
                  whiteSpace: 'pre-wrap',
                  position: 'relative'
                }}>
                  {/* Read Aloud Button on Bot Messages */}
                  {isBot && m.content && (
                    <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '8px' }}>
                      <button
                        onClick={() => {
                          if (isSpeaking || isLoadingSpeech) {
                            stopSpeaking();
                          } else {
                            handleToggleSpeak(m.message_id, m.content);
                          }
                        }}
                        style={{
                          background: isSpeaking ? 'rgba(239, 68, 68, 0.2)' : isLoadingSpeech ? 'rgba(245, 158, 11, 0.15)' : 'rgba(56, 189, 248, 0.15)',
                          border: isSpeaking ? '1px solid rgba(239, 68, 68, 0.4)' : isLoadingSpeech ? '1px solid rgba(245, 158, 11, 0.4)' : '1px solid rgba(56, 189, 248, 0.3)',
                          color: isSpeaking ? '#f87171' : isLoadingSpeech ? '#fbbf24' : '#38bdf8',
                          padding: '4px 10px',
                          borderRadius: '6px',
                          fontSize: '0.78rem',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '5px'
                        }}
                        title={isSpeaking ? 'Stop voice playback' : isLoadingSpeech ? 'Generating speech...' : 'Read message aloud in selected language'}
                      >
                        {isLoadingSpeech ? (
                          <>
                            <RefreshCw size={13} className="spin" /> Generating speech...
                          </>
                        ) : isSpeaking ? (
                          <>
                            <VolumeX size={13} /> Stop Speaking
                          </>
                        ) : (
                          <>
                            <Volume2 size={13} /> Read Aloud
                          </>
                        )}
                      </button>
                    </div>
                  )}

                  {isBot ? <FormattedMessage content={m.content} /> : m.content}

                  {/* Interactive Structured Confirmation Card */}
                  {m.pending_action && (
                    <div style={{
                      marginTop: '14px',
                      background: 'rgba(15, 23, 42, 0.85)',
                      border: '1px solid rgba(56, 189, 248, 0.4)',
                      borderRadius: '10px',
                      padding: '14px 16px',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#38bdf8', fontWeight: '600', fontSize: '0.88rem', marginBottom: '6px' }}>
                        <Calendar size={16} /> Schedule Activity Confirmation
                      </div>
                      <div style={{ fontSize: '0.88rem', color: '#cbd5e1', marginBottom: '12px' }}>
                        {m.pending_action.confirmation_prompt || `Set ${m.pending_action.crop_name} harvest date to ${m.pending_action.harvest_date}?`}
                      </div>
                      <div style={{ display: 'flex', gap: '10px' }}>
                        <button
                          className="btn-primary"
                          style={{ fontSize: '0.82rem', padding: '6px 14px' }}
                          disabled={confirmingAction}
                          onClick={() => handleConfirmPendingAction(m.pending_action)}
                        >
                          <Check size={14} /> {confirmingAction ? 'Updating...' : 'Yes, Confirm Schedule'}
                        </button>
                        <button
                          className="btn-secondary"
                          style={{ fontSize: '0.82rem', padding: '6px 12px' }}
                          onClick={() => handleSendMessage('No, please cancel this')}
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Action Executed Confirmation Badge */}
                  {m.action_executed && (
                    <div style={{
                      marginTop: '12px',
                      background: 'rgba(16, 185, 129, 0.15)',
                      borderLeft: '3px solid #10b981',
                      padding: '8px 12px',
                      borderRadius: '6px',
                      fontSize: '0.82rem',
                      color: '#34d399',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}>
                      <CheckCircle size={15} /> Verified record updated: Harvest date set to <strong>{m.action_executed.harvest_date}</strong>
                    </div>
                  )}

                  {/* Deduplicated Source Citations */}
                  {m.sources && m.sources.length > 0 && (
                    <div style={{ marginTop: '14px', paddingTop: '10px', borderTop: '1px solid rgba(255, 255, 255, 0.1)' }}>
                      <span style={{ fontSize: '0.75rem', fontWeight: '700', textTransform: 'uppercase', color: '#10b981', display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '6px' }}>
                        <ShieldCheck size={14} /> Referenced Sources ({m.sources.length})
                      </span>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {m.sources.map((src, sIdx) => (
                          <div key={sIdx} style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '6px 10px', borderRadius: '6px', fontSize: '0.78rem' }}>
                            <strong style={{ color: '#34d399' }}>{src.title}</strong> — <span style={{ color: '#94a3b8' }}>{src.source_name}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {!isBot && (
                  <div style={{
                    width: '38px',
                    height: '38px',
                    borderRadius: '50%',
                    background: 'rgba(255, 255, 255, 0.1)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0
                  }}>
                    <User size={20} color="#f8fafc" />
                  </div>
                )}
              </div>
            );
          })}

          {sending && (
            <div style={{ display: 'flex', gap: '12px', alignSelf: 'flex-start' }}>
              <div style={{
                width: '38px',
                height: '38px',
                borderRadius: '50%',
                background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0
              }}>
                <Bot size={20} color="#fff" />
              </div>
              <div style={{ background: 'rgba(30, 41, 59, 0.85)', padding: '12px 18px', borderRadius: '12px', fontSize: '0.88rem', color: '#94a3b8' }}>
                Consulting ICAR verified parameters & live farm telemetry...
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Suggested Action Quick Pills */}
        <div style={{
          padding: '8px 20px',
          background: 'rgba(15, 23, 42, 0.4)',
          borderTop: '1px solid rgba(255, 255, 255, 0.05)',
          display: 'flex',
          gap: '8px',
          overflowX: 'auto',
          whiteSpace: 'nowrap'
        }}>
          <button
            className="btn-secondary"
            style={{ fontSize: '0.76rem', padding: '4px 10px', borderRadius: '6px' }}
            onClick={() => handleSendMessage('What is the 7-day weather forecast and rain probability?')}
          >
            <CloudSun size={12} /> Check Weather
          </button>
          <button
            className="btn-secondary"
            style={{ fontSize: '0.76rem', padding: '4px 10px', borderRadius: '6px' }}
            onClick={() => handleSendMessage('Check storage temperature and active alerts')}
          >
            <AlertTriangle size={12} /> Storage Alerts
          </button>
          <button
            className="btn-secondary"
            style={{ fontSize: '0.76rem', padding: '4px 10px', borderRadius: '6px' }}
            onClick={() => handleSendMessage('What are the latest APMC mandi market prices and selling recommendation?')}
          >
            <TrendingUp size={12} /> Mandi Prices
          </button>
          <button
            className="btn-secondary"
            style={{ fontSize: '0.76rem', padding: '4px 10px', borderRadius: '6px' }}
            onClick={() => handleSendMessage('I want to plan my wheat harvest for next week.')}
          >
            <Calendar size={12} /> Plan Harvest
          </button>
        </div>

        {/* Input Bar with Microphone Voice & Send */}
        <div style={{ padding: '16px 20px', borderTop: '1px solid rgba(255, 255, 255, 0.08)', background: 'rgba(15, 23, 42, 0.7)' }}>
          {speechError && (
            <div style={{
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              color: '#f87171',
              padding: '8px 14px',
              borderRadius: '8px',
              fontSize: '0.82rem',
              marginBottom: '10px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <span>{speechError}</span>
              <button
                type="button"
                onClick={() => setSpeechError(null)}
                style={{ background: 'none', border: 'none', color: '#f87171', cursor: 'pointer', fontSize: '1.1rem', lineHeight: 1 }}
              >
                ×
              </button>
            </div>
          )}

          {/* Active Voice-Over Status Banner with Immediate Stop */}
          {(speakingMessageId || loadingSpeechMessageId) && (
            <div style={{
              background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(6, 95, 70, 0.25) 100%)',
              border: '1px solid rgba(16, 185, 129, 0.4)',
              padding: '8px 14px',
              borderRadius: '8px',
              color: '#34d399',
              fontSize: '0.84rem',
              marginBottom: '10px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.2)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Volume2 size={16} className="pulse" />
                <span>
                  {loadingSpeechMessageId
                    ? 'Preparing voice-over in selected language...'
                    : `Speaking response in ${SUPPORTED_LANGUAGES.find((l) => l.code === chatLang)?.label || chatLang}...`}
                </span>
              </div>
              <button
                type="button"
                onClick={stopSpeaking}
                style={{
                  background: 'rgba(239, 68, 68, 0.25)',
                  border: '1px solid #ef4444',
                  color: '#fca5a5',
                  padding: '4px 12px',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '0.8rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '5px'
                }}
                title="Stop voice playback"
              >
                <VolumeX size={14} /> Stop Voice-Over
              </button>
            </div>
          )}

          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            style={{ display: 'flex', gap: '10px', alignItems: 'center' }}
          >
            <input
              type="text"
              className="input-field"
              placeholder={isRecording ? `Listening... (${recordingSeconds}s)` : isTranscribing ? "Transcribing speech..." : "Ask FarmShield about storage, weather, mandi selling, or schedule harvest..."}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              disabled={sending || isRecording || isTranscribing}
              style={{ flex: 1 }}
            />

            {/* Microphone Button */}
            <button
              type="button"
              disabled={sending || isTranscribing}
              onClick={isRecording ? stopRecording : startRecording}
              style={{
                background: isRecording ? 'rgba(239, 68, 68, 0.25)' : isTranscribing ? 'rgba(245, 158, 11, 0.2)' : 'rgba(56, 189, 248, 0.15)',
                border: isRecording ? '1px solid #ef4444' : isTranscribing ? '1px solid #f59e0b' : '1px solid rgba(56, 189, 248, 0.3)',
                color: isRecording ? '#ef4444' : isTranscribing ? '#fbbf24' : '#38bdf8',
                borderRadius: '8px',
                padding: '10px 14px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '0.85rem'
              }}
              title={isRecording ? 'Stop recording voice' : isTranscribing ? 'Transcribing speech...' : 'Ask question by voice (Speech-to-Text)'}
            >
              {isRecording ? (
                <>
                  <MicOff size={18} className="pulse" /> Stop ({recordingSeconds}s)
                </>
              ) : isTranscribing ? (
                <>
                  <RefreshCw size={18} className="spin" /> Transcribing...
                </>
              ) : (
                <Mic size={18} />
              )}
            </button>

            <button
              type="submit"
              disabled={sending || isRecording || isTranscribing || !inputMessage.trim()}
              className="btn-primary"
              style={{ padding: '10px 20px' }}
            >
              <Send size={18} />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
