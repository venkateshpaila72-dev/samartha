import { apiRequest } from './apiClient';

let currentAudioInstance = null;

class VoiceRecorder {
  constructor() {
    this.mediaStream = null;
    this.audioContext = null;
    this.processor = null;
    this.input = null;
    this.audioChunks = [];
    this.sampleRate = 16000;
  }

  async start() {
    this.audioChunks = [];
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error('Audio recording is not supported in this browser.');
    }

    this.mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        sampleRate: 16000,
        echoCancellation: true,
        noiseSuppression: true,
      },
    });

    // Create Web Audio context to capture 16kHz PCM
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    this.audioContext = new AudioContextClass({ sampleRate: 16000 });
    this.input = this.audioContext.createMediaStreamSource(this.mediaStream);
    this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);

    this.processor.onaudioprocess = (e) => {
      const channelData = e.inputBuffer.getChannelData(0);
      this.audioChunks.push(new Float32Array(channelData));
    };

    this.input.connect(this.processor);
    this.processor.connect(this.audioContext.destination);
  }

  async stop() {
    if (this.processor) {
      this.processor.disconnect();
      this.processor = null;
    }
    if (this.input) {
      this.input.disconnect();
      this.input = null;
    }
    if (this.audioContext) {
      await this.audioContext.close();
      this.audioContext = null;
    }
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }

    // Merge Float32Array chunks
    let totalLength = 0;
    for (const chunk of this.audioChunks) {
      totalLength += chunk.length;
    }
    const merged = new Float32Array(totalLength);
    let offset = 0;
    for (const chunk of this.audioChunks) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }

    return this.encodeWAV(merged, 16000);
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
    view.setUint32(28, sampleRate * 2, true); // ByteRate
    view.setUint16(32, 2, true); // BlockAlign
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
  async startRecording() {
    if (activeRecorder) {
      try {
        await activeRecorder.stop();
      } catch {
        /* noop */
      }
    }
    activeRecorder = new VoiceRecorder();
    await activeRecorder.start();
  },

  async stopRecording() {
    if (!activeRecorder) {
      throw new Error('No active voice recording session.');
    }
    const wavBlob = await activeRecorder.stop();
    activeRecorder = null;
    return wavBlob;
  },

  async transcribeAudio(audioBlob, language = 'en') {
    const formData = new FormData();
    formData.append('file', audioBlob, 'recording.wav');

    const token = localStorage.getItem('farmshield_token');
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch('/api/v1/speech/transcribe', {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      throw new Error(errJson.detail || 'Failed to transcribe voice recording.');
    }

    const data = await res.json();
    return data.data; // { transcript, confidence, language }
  },

  async synthesizeSpeech(text, language = 'en', voiceName = null) {
    const res = await apiRequest('/speech/synthesize', {
      method: 'POST',
      body: JSON.stringify({
        text,
        language,
        voice_name: voiceName,
      }),
    });
    return res.data; // { audio_base64, media_type, language, voice_name }
  },

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
    if (window.speechSynthesis) {
      try {
        window.speechSynthesis.cancel();
      } catch {
        /* noop */
      }
    }
  },

  async speakText(text, language = 'en', onStart = null, onEnd = null) {
    this.stopAudio();
    if (!text || !text.trim()) return;

    // Try Azure Speech TTS First
    try {
      const ttsData = await this.synthesizeSpeech(text, language);
      if (ttsData?.audio_base64) {
        const audio = new Audio(`data:audio/mpeg;base64,${ttsData.audio_base64}`);
        currentAudioInstance = audio;

        audio.onplay = () => {
          if (onStart) onStart();
        };

        audio.onended = () => {
          currentAudioInstance = null;
          if (onEnd) onEnd();
        };

        audio.onerror = () => {
          currentAudioInstance = null;
          this.fallbackBrowserTTS(text, language, onStart, onEnd);
        };

        await audio.play();
        return audio;
      }
    } catch (err) {
      console.warn('Azure Speech TTS unavailable, falling back to browser speech:', err.message);
      return this.fallbackBrowserTTS(text, language, onStart, onEnd);
    }
  },

  fallbackBrowserTTS(text, language = 'en', onStart = null, onEnd = null) {
    if (!('speechSynthesis' in window)) {
      console.warn('SpeechSynthesis is not supported in this browser.');
      if (onEnd) onEnd();
      return null;
    }

    const utterance = new SpeechSynthesisUtterance(text);
    const langMap = {
      en: 'en-IN',
      hi: 'hi-IN',
      te: 'te-IN',
      ta: 'ta-IN',
      kn: 'kn-IN',
      mr: 'mr-IN',
      bn: 'bn-IN',
      gu: 'gu-IN',
    };
    utterance.lang = langMap[language] || 'en-IN';
    utterance.rate = 0.95;

    utterance.onstart = () => {
      if (onStart) onStart();
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
