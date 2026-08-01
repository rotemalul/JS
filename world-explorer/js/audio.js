/* ===== קריינות וצלילים ===== */

const AudioFX = {
  muted: false,
  ctx: null,

  init(muted) {
    this.muted = !!muted;
  },

  toggleMute() {
    this.muted = !this.muted;
    if (this.muted) this.stopSpeech();
    return this.muted;
  },

  /* --- קריינות בעברית (Web Speech API — placeholder עד הקלטות) --- */
  speak(text) {
    if (this.muted || !('speechSynthesis' in window)) return;
    this.stopSpeech();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = 'he-IL';
    u.rate = 0.9;   // איטי ורגוע — קול של סיפור לפני שינה
    u.pitch = 1.05;
    const voices = speechSynthesis.getVoices();
    const hebrew = voices.find(function (v) { return v.lang && v.lang.indexOf('he') === 0; });
    if (hebrew) u.voice = hebrew;
    speechSynthesis.speak(u);
  },

  stopSpeech() {
    if ('speechSynthesis' in window) speechSynthesis.cancel();
  },

  /* --- צלילי משוב רכים (WebAudio) --- */
  _audioCtx() {
    if (!this.ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (AC) this.ctx = new AC();
    }
    return this.ctx;
  },

  _tone(freq, start, duration, volume) {
    const ctx = this._audioCtx();
    if (!ctx) return;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(0, ctx.currentTime + start);
    gain.gain.linearRampToValueAtTime(volume, ctx.currentTime + start + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + start + duration);
    osc.connect(gain).connect(ctx.destination);
    osc.start(ctx.currentTime + start);
    osc.stop(ctx.currentTime + start + duration + 0.05);
  },

  /* פעמון קטן — תשובה נכונה */
  chime() {
    if (this.muted) return;
    this._tone(660, 0, 0.35, 0.12);
    this._tone(880, 0.12, 0.4, 0.12);
    this._tone(1320, 0.24, 0.5, 0.08);
  },

  /* "הממ?" סקרן — ניסיון שגוי (רך, לא באזר) */
  hmm() {
    if (this.muted) return;
    this._tone(330, 0, 0.25, 0.08);
    this._tone(392, 0.18, 0.3, 0.08);
  },

  /* נצנוץ קטן — פתיחת בועה */
  sparkle() {
    if (this.muted) return;
    this._tone(1046, 0, 0.18, 0.06);
    this._tone(1568, 0.08, 0.22, 0.05);
  }
};

/* חלק מהדפדפנים טוענים קולות באיחור */
if ('speechSynthesis' in window) {
  speechSynthesis.onvoiceschanged = function () { speechSynthesis.getVoices(); };
}
