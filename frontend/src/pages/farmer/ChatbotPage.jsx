import React, { useState, useEffect, useRef } from 'react';
import { chatbotService } from '../../services/monitoringService';
import {
  MessageSquare,
  Send,
  BookOpen,
  Sparkles,
  Bot,
  User,
  ShieldCheck,
  PlusCircle,
} from 'lucide-react';

export default function ChatbotPage({ activeBatch }) {
  const [conversations, setConversations] = useState([]);
  const [currentConvoId, setCurrentConvoId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef(null);

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
          // Auto create first conversation
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

  const selectConversation = async (convoId) => {
    setCurrentConvoId(convoId);
    try {
      const msgs = await chatbotService.getMessages(convoId);
      setMessages(msgs);
    } catch (err) {
      console.error(err);
    }
  };

  const handleNewConversation = async () => {
    try {
      const newConvo = await chatbotService.createConversation({
        title: `Advisory for ${activeBatch ? activeBatch.custom_batch_name : 'Crop Storage'}`,
        batch_id: activeBatch?.batch_id,
        language: 'en',
      });
      setConversations(prev => [newConvo, ...prev]);
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

    setMessages(prev => [...prev, userMsg]);
    setInputMessage('');
    setSending(true);

    try {
      const response = await chatbotService.sendMessage(currentConvoId, {
        message: text,
        batch_id: activeBatch?.batch_id,
        language: 'en',
      });
      setMessages(prev => [...prev, response]);
    } catch (err) {
      alert(err.message || 'Error generating AI response');
    } finally {
      setSending(false);
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', height: 'calc(100vh - 120px)' }}>
      {/* Header */}
      <div className="glass-panel" style={{ padding: '16px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <span className="badge badge-verified">
            <Sparkles size={12} /> Workflow 8: Groq LLM with Traditional RAG Knowledge
          </span>
          <h1 style={{ fontSize: '1.5rem', marginTop: '2px' }}>AI Agricultural Storage Advisory</h1>
        </div>
        <button className="btn-secondary" onClick={handleNewConversation} style={{ fontSize: '0.85rem' }}>
          <PlusCircle size={16} /> New Chat
        </button>
      </div>

      {/* Chat Area */}
      <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Messages Stream */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {messages.length === 0 && (
            <div style={{ textAlign: 'center', margin: 'auto', maxWidth: '550px' }}>
              <div style={{
                width: '60px',
                height: '60px',
                borderRadius: '50%',
                background: 'rgba(16, 185, 129, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 16px'
              }}>
                <Bot size={32} color="#10b981" />
              </div>
              <h3 style={{ fontSize: '1.3rem', marginBottom: '8px' }}>How can I assist your crop storage today?</h3>
              <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginBottom: '24px', lineHeight: 1.5 }}>
                Ask any question regarding temperature bounds, humidity control, natural neem pest prevention, ventilation schedules, or traditional storage methods.
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', textAlign: 'left' }}>
                {suggestedQuestions.map((q, idx) => (
                  <button
                    key={idx}
                    className="btn-secondary"
                    style={{ fontSize: '0.85rem', padding: '8px 14px', borderRadius: '8px', textAlign: 'left' }}
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
            return (
              <div
                key={m.message_id || idx}
                style={{
                  display: 'flex',
                  gap: '12px',
                  alignSelf: isBot ? 'flex-start' : 'flex-end',
                  maxWidth: '85%'
                }}
              >
                {isBot && (
                  <div style={{
                    width: '36px',
                    height: '36px',
                    borderRadius: '50%',
                    background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0
                  }}>
                    <Bot size={18} color="#fff" />
                  </div>
                )}

                <div style={{
                  background: isBot ? 'rgba(30, 41, 59, 0.85)' : 'linear-gradient(135deg, rgba(16, 185, 129, 0.3) 0%, rgba(5, 150, 105, 0.25) 100%)',
                  border: isBot ? '1px solid rgba(255, 255, 255, 0.08)' : '1px solid rgba(16, 185, 129, 0.4)',
                  borderRadius: '14px',
                  padding: '14px 18px',
                  color: '#f8fafc',
                  fontSize: '0.92rem',
                  lineHeight: 1.6,
                  whiteSpace: 'pre-wrap'
                }}>
                  {m.content}

                  {/* Sources Citations Accordion / Badges */}
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
                    width: '36px',
                    height: '36px',
                    borderRadius: '50%',
                    background: 'rgba(255, 255, 255, 0.1)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0
                  }}>
                    <User size={18} color="#f8fafc" />
                  </div>
                )}
              </div>
            );
          })}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div style={{ padding: '16px 20px', borderTop: '1px solid rgba(255, 255, 255, 0.08)', background: 'rgba(15, 23, 42, 0.6)' }}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            style={{ display: 'flex', gap: '10px' }}
          >
            <input
              type="text"
              className="input-field"
              placeholder="Ask FarmShield about storage preservation, pests, or temperature limits..."
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              disabled={sending}
            />
            <button type="submit" disabled={sending || !inputMessage.trim()} className="btn-primary" style={{ padding: '0 20px' }}>
              <Send size={18} />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
