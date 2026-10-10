import { apiRequest } from './apiClient';

const BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

let currentAudioInstance = null;

class VoiceRecorder {
  constructor() {
    this.mediaStream = null;
    this.mediaRecorder = null;
    this.chunks = [];
  }

  async start() {
    this.chunks = [];
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error('Audio recording is not supported in this browser.');
    }

    this.mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
      },
    });

    let mimeType = '';
    if (typeof MediaRecorder !== 'undefined') {
      if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
        mimeType = 'audio/webm;codecs=opus';
      } else if (MediaRecorder.isTypeSupported('audio/webm')) {
        mimeType = 'audio/webm';
      } else if (MediaRecorder.isTypeSupported('audio/ogg;codecs=opus')) {
        mimeType = 'audio/ogg;codecs=opus';
      } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
        mimeType = 'audio/mp4';
      }
    }

    this.mediaRecorder = new MediaRecorder(
      this.mediaStream,
      mimeType ? { mimeType } : undefined
    );

    this.mediaRecorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) {
        this.chunks.push(e.data);
      }
    };

    this.mediaRecorder.start(200);
  }

  async stop() {
    return new Promise((resolve, reject) => {
      if (!this.mediaRecorder || this.mediaRecorder.state === 'inactive') {
        reject(new Error('No active recorder to stop.'));
        return;
      }

      this.mediaRecorder.onstop = async () => {
        try {
          if (this.mediaStream) {
            this.mediaStream.getTracks().forEach((track) => track.stop());
            this.mediaStream = null;
          }

          const rawBlob = new Blob(this.chunks, {
            type: this.mediaRecorder.mimeType || 'audio/webm',
          });
          const wavBlob = await this.convertTo16kHzWAV(rawBlob);
          resolve(wavBlob);
        } catch (err) {
          reject(err);
        }
      };

      this.mediaRecorder.stop();
    });
  }

  async convertTo16kHzWAV(blob) {
    const arrayBuffer = await blob.arrayBuffer();
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    const audioCtx = new AudioContextClass();

    try {
      const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer);

      // Resample to 16,000 Hz Mono using OfflineAudioContext
      const targetSampleRate = 16000;
      const numChannels = 1;
      const offlineCtx = new (window.OfflineAudioContext ||
        window.webkitOfflineAudioContext)(
        numChannels,
        Math.max(1, Math.ceil(audioBuffer.duration * targetSampleRate)),
        targetSampleRate
      );

      const source = offlineCtx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(offlineCtx.destination);
      source.start(0);

      const renderedBuffer = await offlineCtx.startRendering();
      const pcmData = renderedBuffer.getChannelData(0);

      return this.encodeWAV(pcmData, targetSampleRate);
    } finally {
      if (audioCtx.state !== 'closed') {
        await audioCtx.close();
      }
    }
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

    const url = `${BASE_URL}/speech/transcribe`;
    const res = await fetch(url, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      throw new Error(
        errJson.detail || 'Failed to transcribe voice recording.'
      );
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
        const audio = new Audio(
          `data:audio/mpeg;base64,${ttsData.audio_base64}`
        );
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
      console.warn(
        'Azure Speech TTS unavailable, falling back to browser speech:',
        err.message
      );
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
