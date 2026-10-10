import React, { useState, useEffect, useRef } from 'react';
import { chatbotService, speechService } from '../../services/monitoringService';
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

export default function ChatbotPage({ activeBatch }) {
  const [conversations, setConversations] = useState([]);
  const [currentConvoId, setCurrentConvoId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [chatLang, setChatLang] = useState('en');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [confirmingAction, setConfirmingAction] = useState(false);

  // Audio / Speech-to-Text & Text-to-Speech State
  const [speakingMessageId, setSpeakingMessageId] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);

  const messagesEndRef = useRef(null);
  const activeAudioRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recordTimerRef = useRef(null);

  const suggestedQuestions = [
    { label: '🌦️ 7-Day Weather Forecast', text: 'What is the 7-day weather forecast and rain probability for my farm?' },
    { label: '🌡️ Storage Temperature Limits', text: 'How are my wheat storage temperature and safe ICAR limits?' },
    { label: '💰 Best Day to Sell Harvest', text: 'Should I sell my wheat harvest today or hold for better mandi prices?' },
    { label: '🐛 Natural Weevil Deterrence', text: 'How do I protect my stored grain from weevils naturally using neem?' },
    { label: '📅 Plan Wheat Harvest Date', text: 'I want to harvest my wheat on October 18.' },
  ];

  // Stop any active audio playback
  const stopSpeaking = () => {
    if (activeAudioRef.current) {
      activeAudioRef.current.pause();
      activeAudioRef.current = null;
    }
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    setSpeakingMessageId(null);
  };

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

      // Check auto read-aloud preference from localStorage / profile
      try {
        const userProfile = JSON.parse(localStorage.getItem('farmshield_user') || '{}');
        if (userProfile.auto_read_aloud && response.content) {
          handleToggleSpeak(response.message_id, response.content);
        }
      } catch {
        // Ignore JSON error
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

  // Text-To-Speech Playback with Azure Neural TTS & Browser Native Fallback
  const handleToggleSpeak = async (messageId, text) => {
    if (speakingMessageId === messageId) {
      stopSpeaking();
      return;
    }

    stopSpeaking();
    setSpeakingMessageId(messageId);

    // Clean markdown and symbol characters for smooth speech
    const cleanSpeechText = text
      .replace(/[*#_`>~]/g, '')
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      .replace(/https?:\/\/\S+/g, '')
      .trim();

    try {
      // 1. Attempt Azure Neural Text-to-Speech via backend
      const audioBlob = await speechService.synthesizeSpeech(cleanSpeechText, chatLang);
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);

      audio.onended = () => {
        setSpeakingMessageId(null);
        URL.revokeObjectURL(audioUrl);
      };

      audio.onerror = () => {
        fallbackBrowserSpeech(cleanSpeechText);
      };

      activeAudioRef.current = audio;
      await audio.play();
    } catch (err) {
      console.warn('Azure TTS endpoint unavailable or unconfigured, using browser speech:', err.message);
      fallbackBrowserSpeech(cleanSpeechText);
    }
  };

  const fallbackBrowserSpeech = (cleanText) => {
    if (!window.speechSynthesis) {
      setSpeakingMessageId(null);
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(cleanText);

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
    utterance.lang = langCodes[chatLang] || 'en-IN';
    utterance.rate = 0.95;

    utterance.onend = () => {
      setSpeakingMessageId(null);
    };
    utterance.onerror = () => {
      setSpeakingMessageId(null);
    };

    window.speechSynthesis.speak(utterance);
  };

  // Voice Input (Speech-to-Text Microphone Recording)
  const startRecording = async () => {
    stopSpeaking();
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      alert('Microphone access is not supported in this browser.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        stream.getTracks().forEach((track) => track.stop());

        // Call backend speech transcription
        try {
          const file = new File([audioBlob], 'voice_query.wav', { type: 'audio/wav' });
          const res = await speechService.transcribeAudio(file);
          if (res?.transcript) {
            setInputMessage(res.transcript);
          }
        } catch (err) {
          console.warn('Voice transcription notice:', err.message);
        }
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordingSeconds(0);
      recordTimerRef.current = setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      alert('Could not access microphone: ' + (err.message || 'Permission denied'));
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      clearInterval(recordTimerRef.current);
    }
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
              onChange={(e) => setChatLang(e.target.value)}
            >
              {SUPPORTED_LANGUAGES.map((l) => (
                <option key={l.code} value={l.code} style={{ background: '#0f172a', color: '#fff' }}>
                  {l.label}
                </option>
              ))}
            </select>
          </div>

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
                        onClick={() => handleToggleSpeak(m.message_id, m.content)}
                        style={{
                          background: isSpeaking ? 'rgba(239, 68, 68, 0.2)' : 'rgba(56, 189, 248, 0.15)',
                          border: isSpeaking ? '1px solid rgba(239, 68, 68, 0.4)' : '1px solid rgba(56, 189, 248, 0.3)',
                          color: isSpeaking ? '#f87171' : '#38bdf8',
                          padding: '4px 10px',
                          borderRadius: '6px',
                          fontSize: '0.78rem',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '5px'
                        }}
                        title={isSpeaking ? 'Stop voice playback' : 'Read message aloud in selected language'}
                      >
                        {isSpeaking ? (
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

                  {m.content}

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
              placeholder={isRecording ? `Listening... (${recordingSeconds}s)` : "Ask FarmShield about storage, weather, mandi selling, or schedule harvest..."}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              disabled={sending || isRecording}
              style={{ flex: 1 }}
            />

            {/* Microphone Button */}
            <button
              type="button"
              onClick={isRecording ? stopRecording : startRecording}
              style={{
                background: isRecording ? 'rgba(239, 68, 68, 0.25)' : 'rgba(56, 189, 248, 0.15)',
                border: isRecording ? '1px solid #ef4444' : '1px solid rgba(56, 189, 248, 0.3)',
                color: isRecording ? '#ef4444' : '#38bdf8',
                borderRadius: '8px',
                padding: '10px 14px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '0.85rem'
              }}
              title={isRecording ? 'Stop recording voice' : 'Ask question by voice (Speech-to-Text)'}
            >
              {isRecording ? (
                <>
                  <MicOff size={18} className="pulse" /> Stop ({recordingSeconds}s)
                </>
              ) : (
                <Mic size={18} />
              )}
            </button>

            <button
              type="submit"
              disabled={sending || !inputMessage.trim()}
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
