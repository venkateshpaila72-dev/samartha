import React, { useState, useEffect, useRef } from 'react';
import { chatbotService } from '../../services/monitoringService';
import { speechService, SUPPORTED_LANGUAGES } from '../../services/speechService';
import { useAuth } from '../../context/AuthContext';
import {
  MessageSquare,
  Send,
  BookOpen,
  Sparkles,
  Bot,
  User,
  ShieldCheck,
  PlusCircle,
  Mic,
  Volume2,
  VolumeX,
  Loader2,
  Square,
  Globe,
  Radio,
} from 'lucide-react';

export default function ChatbotPage({ activeBatch }) {
  const { user } = useAuth();
  const [conversations, setConversations] = useState([]);
  const [currentConvoId, setCurrentConvoId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);

  // Multi-Language & Speech States
  const [selectedLanguage, setSelectedLanguage] = useState(
    user?.preferred_language || 'en'
  );
  const [autoVoiceOver, setAutoVoiceOver] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [activePlayingId, setActivePlayingId] = useState(null);

  const messagesEndRef = useRef(null);
  const timerRef = useRef(null);
  const baseInputRef = useRef('');

  const currentLangObj =
    SUPPORTED_LANGUAGES.find((l) => l.code === selectedLanguage) ||
    SUPPORTED_LANGUAGES[0];

  const suggestedQuestions = [
    'How do I protect my stored grain from weevils naturally?',
    'What should I do if relative humidity exceeds verified limits?',
    'When is the best time to ventilate the storage warehouse?',
    'Explain the Pusa Bin hermetic storage technique.',
  ];

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
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadConversations();
  }, [activeBatch]);

  useEffect(() => {
    return () => {
      speechService.stopAudio();
      speechService.stopVoiceInput();
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const selectConversation = async (convoId) => {
    speechService.stopAudio();
    setActivePlayingId(null);
    setCurrentConvoId(convoId);
    try {
      const msgs = await chatbotService.getMessages(convoId);
      setMessages(msgs);
    } catch (err) {
      console.error(err);
    }
  };

  const handleNewConversation = async () => {
    speechService.stopAudio();
    setActivePlayingId(null);
    try {
      const newConvo = await chatbotService.createConversation({
        title: `Advisory for ${
          activeBatch ? activeBatch.custom_batch_name : 'Crop Storage'
        }`,
        batch_id: activeBatch?.batch_id,
        language: selectedLanguage,
      });
      setConversations((prev) => [newConvo, ...prev]);
      setCurrentConvoId(newConvo.conversation_id);
      setMessages([]);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSendMessage = async (textToSend = null) => {
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
        language: selectedLanguage,
      });
      setMessages((prev) => [...prev, response]);

      // Automatic Voice-Over if toggle is active
      if (autoVoiceOver && response?.content) {
        handlePlayTTS(response.message_id, response.content, selectedLanguage);
      }
    } catch (err) {
      alert(err.message || 'Error generating AI response');
    } finally {
      setSending(false);
    }
  };

  // Real-time Speech-to-Text (STT) using Browser Stream + Azure Speech Verification
  const handleStartVoice = async () => {
    try {
      speechService.stopAudio();
      setActivePlayingId(null);
      baseInputRef.current = inputMessage.trim();

      await speechService.startVoiceInput({
        language: selectedLanguage,
        onInterim: (liveTranscript) => {
          // Immediately display spoken text in the prompt bar in real-time!
          const prefix = baseInputRef.current;
          setInputMessage(
            prefix ? `${prefix} ${liveTranscript}` : liveTranscript
          );
        },
        onError: (err) => {
          console.warn('Real-time voice input warning:', err);
        },
      });

      setIsRecording(true);
      setRecordingSeconds(0);
      timerRef.current = setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      alert(`Could not start audio recording: ${err.message}`);
    }
  };

  const handleStopVoice = async () => {
    if (!isRecording) return;
    if (timerRef.current) clearInterval(timerRef.current);
    setIsRecording(false);
    setIsTranscribing(true);

    try {
      const audioBlob = await speechService.stopVoiceInput();
      if (audioBlob) {
        const res = await speechService.transcribeAudio(
          audioBlob,
          selectedLanguage
        );
        if (res?.transcript && res.transcript.trim()) {
          setInputMessage((prev) => {
            const current = (prev || '').trim();
            // If prompt bar was empty or equals original base prefix, update with Azure result
            if (!current || current === baseInputRef.current) {
              const prefix = baseInputRef.current;
              return prefix ? `${prefix} ${res.transcript}` : res.transcript;
            }
            return current;
          });
        }
      }
    } catch (err) {
      console.warn('Azure Speech STT refinement note:', err.message);
    } finally {
      setIsTranscribing(false);
      setRecordingSeconds(0);
    }
  };

  // Text-to-Speech (TTS) using Azure Speech Neural Voices
  const handlePlayTTS = async (msgId, text, lang = selectedLanguage) => {
    if (activePlayingId === msgId) {
      speechService.stopAudio();
      setActivePlayingId(null);
      return;
    }

    setActivePlayingId(msgId);
    try {
      await speechService.speakText(
        text,
        lang,
        () => setActivePlayingId(msgId),
        () => setActivePlayingId(null)
      );
    } catch (err) {
      console.error('Speech playback error:', err);
      setActivePlayingId(null);
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '20px',
        height: 'calc(100vh - 120px)',
      }}
    >
      {/* Top Header Bar */}
      <div
        className="glass-panel"
        style={{
          padding: '16px 24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div>
          <span className="badge badge-verified">
            <Sparkles size={12} /> Groq LLM + Azure Speech Cognitive Services
          </span>
          <h1 style={{ fontSize: '1.5rem', marginTop: '2px' }}>
            AI Agricultural Storage Advisory
          </h1>
        </div>

        {/* Multi-Language & Voice Control Center */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            flexWrap: 'wrap',
          }}
        >
          {/* Language Selector Dropdown */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: 'rgba(15, 23, 42, 0.7)',
              border: '1px solid rgba(16, 185, 129, 0.4)',
              borderRadius: '8px',
              padding: '4px 10px',
            }}
          >
            <Globe size={15} color="#34d399" />
            <select
              value={selectedLanguage}
              onChange={(e) => setSelectedLanguage(e.target.value)}
              aria-label="Select Advisory & Voice Language"
              style={{
                background: 'transparent',
                color: '#f8fafc',
                border: 'none',
                outline: 'none',
                fontSize: '0.85rem',
                cursor: 'pointer',
                fontWeight: '600',
              }}
            >
              {SUPPORTED_LANGUAGES.map((lang) => (
                <option
                  key={lang.code}
                  value={lang.code}
                  style={{ background: '#1e293b', color: '#fff' }}
                >
                  {lang.native} ({lang.label})
                </option>
              ))}
            </select>
          </div>

          {/* Auto Voice-Over Toggle */}
          <button
            type="button"
            onClick={() => setAutoVoiceOver((prev) => !prev)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '8px',
              fontSize: '0.82rem',
              fontWeight: '600',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              border: autoVoiceOver
                ? '1px solid #10b981'
                : '1px solid rgba(255, 255, 255, 0.15)',
              background: autoVoiceOver
                ? 'rgba(16, 185, 129, 0.2)'
                : 'rgba(255, 255, 255, 0.05)',
              color: autoVoiceOver ? '#34d399' : '#cbd5e1',
            }}
            title="Automatically voice over incoming AI responses in selected language"
          >
            {autoVoiceOver ? (
              <>
                <Volume2 size={15} color="#34d399" />
                <span>Auto Voice-Over: ON</span>
              </>
            ) : (
              <>
                <VolumeX size={15} color="#94a3b8" />
                <span>Auto Voice-Over: OFF</span>
              </>
            )}
          </button>

          {/* New Chat Button */}
          <button
            className="btn-secondary"
            onClick={handleNewConversation}
            style={{ fontSize: '0.85rem' }}
          >
            <PlusCircle size={16} /> New Chat
          </button>
        </div>
      </div>

      {/* Chat Area */}
      <div
        className="glass-panel"
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* Messages Stream */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            gap: '18px',
          }}
        >
          {messages.length === 0 && (
            <div
              style={{
                textAlign: 'center',
                margin: 'auto',
                maxWidth: '560px',
              }}
            >
              <div
                style={{
                  width: '64px',
                  height: '64px',
                  borderRadius: '50%',
                  background: 'rgba(16, 185, 129, 0.15)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 16px',
                }}
              >
                <Bot size={34} color="#10b981" />
              </div>
              <h3 style={{ fontSize: '1.3rem', marginBottom: '8px' }}>
                Storage Advisory in {currentLangObj.native} ({currentLangObj.label})
              </h3>
              <p
                style={{
                  color: '#94a3b8',
                  fontSize: '0.9rem',
                  marginBottom: '20px',
                  lineHeight: 1.5,
                }}
              >
                Speak or type in {currentLangObj.label}. Responses are generated
                using Groq LLM with traditional Indian storage intelligence and
                voiced over using Microsoft Azure Neural TTS.
              </p>
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                  textAlign: 'left',
                }}
              >
                {suggestedQuestions.map((q, idx) => (
                  <button
                    key={idx}
                    className="btn-secondary"
                    style={{
                      fontSize: '0.85rem',
                      padding: '8px 14px',
                      borderRadius: '8px',
                      textAlign: 'left',
                    }}
                    onClick={() => handleSendMessage(q)}
                  >
                    💬 {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, idx) => {
            const isBot = m.role === 'assistant';
            const msgId = m.message_id || idx;
            const isPlayingThis = activePlayingId === msgId;

            return (
              <div
                key={msgId}
                style={{
                  display: 'flex',
                  gap: '12px',
                  alignSelf: isBot ? 'flex-start' : 'flex-end',
                  maxWidth: '85%',
                }}
              >
                {isBot && (
                  <div
                    style={{
                      width: '36px',
                      height: '36px',
                      borderRadius: '50%',
                      background:
                        'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    <Bot size={18} color="#fff" />
                  </div>
                )}

                <div
                  style={{
                    background: isBot
                      ? 'rgba(30, 41, 59, 0.85)'
                      : 'linear-gradient(135deg, rgba(16, 185, 129, 0.3) 0%, rgba(5, 150, 105, 0.25) 100%)',
                    border: isBot
                      ? '1px solid rgba(255, 255, 255, 0.08)'
                      : '1px solid rgba(16, 185, 129, 0.4)',
                    borderRadius: '14px',
                    padding: '14px 18px',
                    color: '#f8fafc',
                    fontSize: '0.92rem',
                    lineHeight: 1.6,
                    whiteSpace: 'pre-wrap',
                  }}
                >
                  {m.content}

                  {/* Azure Voice-Over Button on Advisory Responses */}
                  {isBot && (
                    <div
                      style={{
                        marginTop: '12px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        flexWrap: 'wrap',
                      }}
                    >
                      <button
                        type="button"
                        onClick={() => handlePlayTTS(msgId, m.content)}
                        className="btn-secondary"
                        style={{
                          padding: '5px 12px',
                          fontSize: '0.8rem',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                          borderRadius: '6px',
                          border: isPlayingThis
                            ? '1px solid #10b981'
                            : '1px solid rgba(255, 255, 255, 0.15)',
                          background: isPlayingThis
                            ? 'rgba(16, 185, 129, 0.25)'
                            : 'rgba(255, 255, 255, 0.04)',
                          color: isPlayingThis ? '#34d399' : '#cbd5e1',
                          cursor: 'pointer',
                        }}
                      >
                        {isPlayingThis ? (
                          <>
                            <VolumeX size={15} color="#34d399" />
                            <span>Stop Voice-Over</span>
                          </>
                        ) : (
                          <>
                            <Volume2 size={15} color="#10b981" />
                            <span>
                              Voice Over ({currentLangObj.native} - Azure Neural TTS)
                            </span>
                          </>
                        )}
                      </button>

                      {isPlayingThis && (
                        <span
                          style={{
                            fontSize: '0.75rem',
                            color: '#34d399',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                          }}
                        >
                          <Radio size={12} className="spin-animation" />
                          Speaking with Azure Neural Voice...
                        </span>
                      )}
                    </div>
                  )}

                  {/* Sources Citations Accordion / Badges */}
                  {m.sources && m.sources.length > 0 && (
                    <div
                      style={{
                        marginTop: '14px',
                        paddingTop: '10px',
                        borderTop: '1px solid rgba(255, 255, 255, 0.1)',
                      }}
                    >
                      <span
                        style={{
                          fontSize: '0.75rem',
                          fontWeight: '700',
                          textTransform: 'uppercase',
                          color: '#10b981',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                          marginBottom: '6px',
                        }}
                      >
                        <ShieldCheck size={14} /> Referenced Sources (
                        {m.sources.length})
                      </span>
                      <div
                        style={{
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '6px',
                        }}
                      >
                        {m.sources.map((src, sIdx) => (
                          <div
                            key={sIdx}
                            style={{
                              background: 'rgba(15, 23, 42, 0.6)',
                              padding: '6px 10px',
                              borderRadius: '6px',
                              fontSize: '0.78rem',
                            }}
                          >
                            <strong style={{ color: '#34d399' }}>
                              {src.title}
                            </strong>{' '}
                            —{' '}
                            <span style={{ color: '#94a3b8' }}>
                              {src.source_name}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {!isBot && (
                  <div
                    style={{
                      width: '36px',
                      height: '36px',
                      borderRadius: '50%',
                      background: 'rgba(255, 255, 255, 0.1)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    <User size={18} color="#f8fafc" />
                  </div>
                )}
              </div>
            );
          })}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar with Real-Time STT Microphone */}
        <div
          style={{
            padding: '16px 20px',
            borderTop: '1px solid rgba(255, 255, 255, 0.08)',
            background: 'rgba(15, 23, 42, 0.6)',
          }}
        >
          {isRecording && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                marginBottom: '10px',
                padding: '8px 14px',
                borderRadius: '8px',
                background: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                color: '#f87171',
                fontSize: '0.86rem',
              }}
            >
              <span
                style={{
                  width: '10px',
                  height: '10px',
                  borderRadius: '50%',
                  background: '#ef4444',
                  display: 'inline-block',
                }}
                className="spin-animation"
              />
              <strong>
                Listening in {currentLangObj.native} ({currentLangObj.label})... ({recordingSeconds}s)
              </strong>
              <span style={{ color: '#cbd5e1' }}>
                Words appear in prompt bar in real-time as you speak.
              </span>
              <button
                type="button"
                onClick={handleStopVoice}
                className="btn-secondary"
                style={{
                  marginLeft: 'auto',
                  padding: '4px 10px',
                  fontSize: '0.8rem',
                  border: '1px solid #ef4444',
                  color: '#fca5a5',
                  cursor: 'pointer',
                }}
              >
                <Square size={12} style={{ fill: '#ef4444' }} /> Done Speaking
              </button>
            </div>
          )}

          {isTranscribing && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                marginBottom: '10px',
                color: '#34d399',
                fontSize: '0.85rem',
              }}
            >
              <Loader2 size={16} className="spin-animation" />
              Finalizing speech recognition with Azure Cognitive Services ({currentLangObj.locale})...
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
              placeholder={`Ask in ${currentLangObj.label} (${currentLangObj.native}) or click mic to speak...`}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              disabled={sending}
              style={{
                flex: 1,
                border: isRecording ? '1px solid #ef4444' : undefined,
                background: isRecording
                  ? 'rgba(239, 68, 68, 0.05)'
                  : undefined,
              }}
            />

            {/* STT Microphone Input Button */}
            {!isRecording ? (
              <button
                type="button"
                onClick={handleStartVoice}
                disabled={sending || isTranscribing}
                className="btn-secondary"
                title={`Speak question in ${currentLangObj.label} (STT)`}
                style={{
                  padding: '10px 14px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  border: '1px solid rgba(16, 185, 129, 0.4)',
                  color: '#34d399',
                  cursor: 'pointer',
                }}
              >
                <Mic size={18} />
              </button>
            ) : (
              <button
                type="button"
                onClick={handleStopVoice}
                className="btn-secondary"
                title="Stop recording"
                style={{
                  padding: '10px 14px',
                  background: '#ef4444',
                  color: '#fff',
                  border: 'none',
                  cursor: 'pointer',
                }}
              >
                <Square size={18} />
              </button>
            )}

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
