import { apiRequest } from './apiClient';

const BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export const SUPPORTED_LANGUAGES = [
  { code: 'en', label: 'English', native: 'English', locale: 'en-IN', voice: 'en-IN-NeerjaNeural' },
  { code: 'hi', label: 'Hindi', native: 'हिन्दी', locale: 'hi-IN', voice: 'hi-IN-SwaraNeural' },
  { code: 'te', label: 'Telugu', native: 'తెలుగు', locale: 'te-IN', voice: 'te-IN-ShrutiNeural' },
  { code: 'ta', label: 'Tamil', native: 'தமிழ்', locale: 'ta-IN', voice: 'ta-IN-PallaviNeural' },
  { code: 'kn', label: 'Kannada', native: 'ಕನ್ನಡ', locale: 'kn-IN', voice: 'kn-IN-SapnaNeural' },
  { code: 'mr', label: 'Marathi', native: 'मराठी', locale: 'mr-IN', voice: 'mr-IN-AarohiNeural' },
  { code: 'bn', label: 'Bengali', native: 'বাংলা', locale: 'bn-IN', voice: 'bn-IN-TanishaaNeural' },
  { code: 'gu', label: 'Gujarati', native: 'ગુજરાતી', locale: 'gu-IN', voice: 'gu-IN-DhwaniNeural' },
  { code: 'pa', label: 'Punjabi', native: 'ਪੰਜਾਬੀ', locale: 'pa-IN', voice: 'pa-IN-OjasNeural' },
];

export const LOCALE_MAP = {
  en: 'en-IN',
  hi: 'hi-IN',
  te: 'te-IN',
  ta: 'ta-IN',
  kn: 'kn-IN',
  mr: 'mr-IN',
  bn: 'bn-IN',
  gu: 'gu-IN',
  pa: 'pa-IN',
};

let currentAudioInstance = null;
let activeRecognition = null;

/**
 * Strips markdown symbols, asterisks, hashes, and links to make text natural for TTS speech synthesis.
 */
export function cleanMarkdownForTTS(markdownText) {
  if (!markdownText) return '';
  return markdownText
    .replace(/```[\s\S]*?```/g, '') // Remove code blocks
    .replace(/`([^`]+)`/g, '$1') // Inline code
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // Links
    .replace(/[*_~]{1,3}(.*?)[*_~]{1,3}/g, '$1') // Bold / italic / strikethrough
    .replace(/^#{1,6}\s+/gm, '') // Headers
    .replace(/^>\s+/gm, '') // Blockquotes
    .replace(/^[-*+]\s+/gm, '') // Unordered lists
    .replace(/^\d+\.\s+/gm, '') // Ordered lists
    .replace(/\|/g, ' ') // Table bars
    .replace(/\n{2,}/g, '. ') // Paragraph breaks to sentence pauses
    .replace(/\s+/g, ' ') // Multiple spaces
    .trim();
}

/**
 * Direct PCM Float32 audio recorder that encodes directly to standard 16kHz mono WAV
 * without container header corruption or decodeAudioData failures.
 */
class DirectAudioRecorder {
  constructor() {
    this.mediaStream = null;
    this.audioContext = null;
    this.sourceNode = null;
    this.processorNode = null;
    this.recordedSamples = [];
  }

  async start() {
    this.recordedSamples = [];
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error('Microphone access is not supported in this browser.');
    }

    this.mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });

    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    this.audioContext = new AudioContextClass();
    this.sourceNode = this.audioContext.createMediaStreamSource(this.mediaStream);

    // Use ScriptProcessor for broad browser compatibility without deprecation crashes
    // bufferSize 4096 gives ~92ms chunks at 44.1kHz
    this.processorNode = this.audioContext.createScriptProcessor(4096, 1, 1);
    this.processorNode.onaudioprocess = (e) => {
      const channel = e.inputBuffer.getChannelData(0);
      this.recordedSamples.push(new Float32Array(channel));
    };

    this.sourceNode.connect(this.processorNode);
    this.processorNode.connect(this.audioContext.destination);
  }

  async stop() {
    if (this.sourceNode && this.processorNode) {
      try {
        this.sourceNode.disconnect();
        this.processorNode.disconnect();
      } catch {
        /* noop */
      }
    }

    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }

    const inputSampleRate = this.audioContext ? this.audioContext.sampleRate : 44100;
    if (this.audioContext && this.audioContext.state !== 'closed') {
      try {
        await this.audioContext.close();
      } catch {
        /* noop */
      }
      this.audioContext = null;
    }

    // Merge float buffers
    let totalLength = 0;
    for (const chunk of this.recordedSamples) {
      totalLength += chunk.length;
    }

    const merged = new Float32Array(totalLength);
    let offset = 0;
    for (const chunk of this.recordedSamples) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }

    // Downsample to 16,000 Hz for Azure Speech Cognitive Services
    const downsampled = this.downsampleTo16kHz(merged, inputSampleRate);
    return this.encodeWAV(downsampled, 16000);
  }

  downsampleTo16kHz(samples, sourceRate) {
    if (sourceRate === 16000 || samples.length === 0) return samples;
    const ratio = sourceRate / 16000;
    const targetLength = Math.max(1, Math.round(samples.length / ratio));
    const result = new Float32Array(targetLength);
    for (let i = 0; i < targetLength; i++) {
      const srcIdx = Math.min(Math.floor(i * ratio), samples.length - 1);
      result[i] = samples[srcIdx];
    }
    return result;
  }

  encodeWAV(samples, sampleRate = 16000) {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);

    const writeString = (offset, string) => {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
      }
    };

    writeString(0, 'RIFF');
    view.setUint32(4, 36 + samples.length * 2, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true); // Subchunk1Size (16 for PCM)
    view.setUint16(20, 1, true); // AudioFormat (1 for PCM)
    view.setUint16(22, 1, true); // NumChannels (1 mono)
    view.setUint32(24, sampleRate, true); // SampleRate
    view.setUint32(28, sampleRate * 2, true); // ByteRate (sampleRate * 2)
    view.setUint16(32, 2, true); // BlockAlign (1 channel * 2 bytes)
    view.setUint16(34, 16, true); // BitsPerSample (16 bit)
    writeString(36, 'data');
    view.setUint32(40, samples.length * 2, true);

    // PCM 16-bit
    let outOffset = 44;
    for (let i = 0; i < samples.length; i++, outOffset += 2) {
      const s = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(outOffset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    }

    return new Blob([buffer], { type: 'audio/wav' });
  }
}

let activeRecorder = null;

export const speechService = {
  /**
   * Start live speech recognition (STT) + audio capture.
   * Words are streamed directly into onInterim callback in real-time as the user speaks!
   */
  async startVoiceInput({
    language = 'en',
    onInterim = null,
    onFinal = null,
    onError = null,
  } = {}) {
    this.stopAudio();
    this.stopVoiceInput();

    const locale = LOCALE_MAP[language] || 'en-IN';

    // 1. Start browser real-time speech recognition if supported
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (SpeechRecognition) {
      try {
        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = locale;

        let accumulatedFinal = '';

        recognition.onresult = (event) => {
          let interimText = '';
          for (let i = event.resultIndex; i < event.results.length; ++i) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
              accumulatedFinal += (accumulatedFinal ? ' ' : '') + transcript.trim();
            } else {
              interimText += transcript;
            }
          }

          const currentLiveText = (accumulatedFinal + ' ' + interimText).trim();
          if (onInterim && currentLiveText) {
            onInterim(currentLiveText);
          }
        };

        recognition.onerror = (err) => {
          console.warn('Browser SpeechRecognition warning:', err.error);
          if (onError && err.error !== 'no-speech') {
            onError(err.error);
          }
        };

        recognition.start();
        activeRecognition = recognition;
      } catch (recErr) {
        console.warn('Failed to start browser SpeechRecognition:', recErr);
      }
    }

    // 2. Start direct PCM audio recording for Azure Speech backend verification
    try {
      activeRecorder = new DirectAudioRecorder();
      await activeRecorder.start();
    } catch (audioErr) {
      console.warn('Audio recorder startup notice:', audioErr);
      if (!SpeechRecognition) {
        throw audioErr;
      }
    }
  },

  /**
   * Stop voice recording session and obtain WAV audio blob.
   */
  async stopVoiceInput() {
    if (activeRecognition) {
      try {
        activeRecognition.stop();
      } catch {
        /* noop */
      }
      activeRecognition = null;
    }

    if (activeRecorder) {
      try {
        const wavBlob = await activeRecorder.stop();
        activeRecorder = null;
        return wavBlob;
      } catch (err) {
        activeRecorder = null;
        console.warn('Error stopping active recorder:', err);
      }
    }
    return null;
  },

  /**
   * Legacy helper wrappers for start/stop recording.
   */
  async startRecording() {
    await this.startVoiceInput();
  },

  async stopRecording() {
    return await this.stopVoiceInput();
  },

  /**
   * Transcribe recorded audio file using Microsoft Azure Speech Cognitive Services.
   */
  async transcribeAudio(audioBlob, language = 'en') {
    if (!audioBlob || audioBlob.size === 0) {
      return { transcript: '', confidence: 0, language };
    }

    const formData = new FormData();
    formData.append('file', audioBlob, 'speech_input.wav');

    const token = localStorage.getItem('farmshield_token');
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const cleanLang = (language || 'en').toLowerCase().split('-')[0];
    const url = `${BASE_URL}/speech/transcribe?language=${encodeURIComponent(cleanLang)}`;

    const res = await fetch(url, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      throw new Error(
        errJson.detail || `Speech transcription failed (HTTP ${res.status}).`
      );
    }

    const data = await res.json();
    return data.data; // { transcript, confidence, language }
  },

  /**
   * Synthesize text to speech using Microsoft Azure Cognitive Neural Voices.
   */
  async synthesizeSpeech(text, language = 'en', voiceName = null) {
    const cleanText = cleanMarkdownForTTS(text);
    if (!cleanText) {
      throw new Error('No synthesizable text provided.');
    }

    const cleanLang = (language || 'en').toLowerCase().split('-')[0];
    const res = await apiRequest('/speech/synthesize', {
      method: 'POST',
      body: JSON.stringify({
        text: cleanText,
        language: cleanLang,
        voice_name: voiceName,
      }),
    });
    return res.data; // { audio_base64, media_type, language, voice_name }
  },

  /**
   * Stop any currently active audio playback or speech synthesis.
   */
  stopAudio() {
    if (currentAudioInstance) {
      try {
        currentAudioInstance.pause();
        currentAudioInstance.currentTime = 0;
      } catch {
        /* noop */
      }
      currentAudioInstance = null;
    }
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      try {
        window.speechSynthesis.cancel();
      } catch {
        /* noop */
      }
    }
  },

  /**
   * Speak text using Azure Speech Neural TTS in the user's selected language.
   * Includes seamless fallback to browser speechSynthesis.
   */
  async speakText(text, language = 'en', onStart = null, onEnd = null) {
    this.stopAudio();
    const cleanText = cleanMarkdownForTTS(text);
    if (!cleanText) return null;

    const cleanLang = (language || 'en').toLowerCase().split('-')[0];

    // Try Azure Speech Neural TTS First
    try {
      const ttsData = await this.synthesizeSpeech(cleanText, cleanLang);
      if (ttsData?.audio_base64) {
        const audio = new Audio(`data:audio/mpeg;base64,${ttsData.audio_base64}`);
        currentAudioInstance = audio;

        audio.onplay = () => {
          if (onStart) onStart({ voice: ttsData.voice_name, language: ttsData.language });
        };

        audio.onended = () => {
          currentAudioInstance = null;
          if (onEnd) onEnd();
        };

        audio.onerror = () => {
          currentAudioInstance = null;
          this.fallbackBrowserTTS(cleanText, cleanLang, onStart, onEnd);
        };

        await audio.play();
        return audio;
      }
    } catch (err) {
      console.warn(
        'Azure Speech TTS unavailable, falling back to browser speech:',
        err.message
      );
      return this.fallbackBrowserTTS(cleanText, cleanLang, onStart, onEnd);
    }
  },

  /**
   * Fallback to native Web Speech Synthesis if offline or network error.
   */
  fallbackBrowserTTS(text, language = 'en', onStart = null, onEnd = null) {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      console.warn('SpeechSynthesis is not supported in this browser.');
      if (onEnd) onEnd();
      return null;
    }

    const cleanLang = (language || 'en').toLowerCase().split('-')[0];
    const locale = LOCALE_MAP[cleanLang] || 'en-IN';
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = locale;
    utterance.rate = 0.95;

    // Try to pick a voice matching the locale
    const voices = window.speechSynthesis.getVoices();
    const matchingVoice = voices.find((v) => v.lang === locale || v.lang.startsWith(cleanLang));
    if (matchingVoice) {
      utterance.voice = matchingVoice;
    }

    utterance.onstart = () => {
      if (onStart) onStart({ voice: utterance.voice?.name || 'Browser Voice', language: locale });
    };
    utterance.onend = () => {
      if (onEnd) onEnd();
    };
    utterance.onerror = () => {
      if (onEnd) onEnd();
    };

    window.speechSynthesis.speak(utterance);
    return utterance;
  },
};
