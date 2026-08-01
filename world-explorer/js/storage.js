/* ===== שמירת התקדמות ב-localStorage ===== */

const STORAGE_KEY = 'world-explorer-progress';

function loadProgress() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch (e) { /* אחסון לא זמין — ממשיכים בלי שמירה */ }
  return { stamps: {}, stickers: [], muted: false };
}

function saveProgress(progress) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
  } catch (e) { /* אחסון לא זמין */ }
}

function addStamp(progress, countryId) {
  if (!progress.stamps[countryId]) {
    progress.stamps[countryId] = new Date().toISOString().slice(0, 10);
  }
  saveProgress(progress);
}

function addSticker(progress, sticker) {
  if (progress.stickers.indexOf(sticker) === -1) {
    progress.stickers.push(sticker);
  }
  saveProgress(progress);
}
