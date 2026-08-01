/* ===== מסביב לעולם — לוגיקת האפליקציה ===== */

const progress = loadProgress();
AudioFX.init(progress.muted);

const session = {
  countryId: null,
  seen: {},        // קטגוריות שנצפו בביקור הנוכחי
  gamesQueue: [],
  gameIndex: 0
};

/* ---------- ניווט בין מסכים ---------- */

function showScreen(id) {
  document.querySelectorAll('.screen').forEach(function (s) {
    s.classList.remove('active');
  });
  document.getElementById(id).classList.add('active');
  window.scrollTo(0, 0);
}

/* ---------- רקע: כוכבים ועמעום לילה ---------- */

function createStars() {
  const layer = document.getElementById('stars');
  for (let i = 0; i < 40; i++) {
    const star = document.createElement('span');
    star.className = 'star';
    star.textContent = Math.random() > 0.8 ? '✦' : '·';
    star.style.left = Math.random() * 100 + '%';
    star.style.top = Math.random() * 100 + '%';
    star.style.fontSize = (8 + Math.random() * 14) + 'px';
    star.style.animationDelay = (Math.random() * 3) + 's';
    layer.appendChild(star);
  }
}

/* מצב שינה: המסך מתחמם ומתעמעם בהדרגה לאורך הסשן */
function startBedtimeDimming() {
  const overlay = document.getElementById('dim-overlay');
  let level = 0;
  setInterval(function () {
    if (level < 0.32) {
      level += 0.08;
      overlay.style.opacity = level;
    }
  }, 3 * 60 * 1000);
}

/* ---------- מסך המפה ---------- */

function tonightCountryId() {
  const next = COUNTRIES.find(function (c) { return !progress.stamps[c.id]; });
  return next ? next.id : COUNTRIES[0].id;
}

function renderMap() {
  const grid = document.getElementById('country-cards');
  grid.innerHTML = '';
  const tonight = tonightCountryId();

  COUNTRIES.forEach(function (country) {
    const card = document.createElement('button');
    card.className = 'country-card';
    if (country.id === tonight) card.classList.add('tonight');

    card.innerHTML =
      (country.id === tonight ? '<span class="tonight-badge">🌙 המדינה של הלילה</span>' : '') +
      (progress.stamps[country.id] ? '<span class="visited-badge">✅</span>' : '') +
      '<span class="flag-wrap">' + flagSVG(country.id) + '</span>' +
      '<span>' + country.name + '</span>' +
      '<span class="continent">' + country.continent + '</span>';

    card.addEventListener('click', function () { openCountry(country.id); });
    grid.appendChild(card);
  });
}

/* ---------- מסך ביקור במדינה ---------- */

function countryCategories(country) {
  return [
    {
      key: 'flag', title: 'הדגל', iconHTML: flagSVG(country.id),
      fact: country.flagFact
    },
    {
      key: 'capital', title: 'עיר הבירה: ' + country.capital.name, iconHTML: country.capital.emoji,
      fact: country.capital.fact
    },
    {
      key: 'map', title: 'איפה בעולם?', iconHTML: '🗺️',
      fact: country.mapFact
    },
    {
      key: 'foods', title: 'מה אוכלים כאן?', iconHTML: country.foods[0].emoji,
      items: country.foods
    },
    {
      key: 'animals', title: 'מי גר כאן?', iconHTML: country.animals[0].emoji,
      items: country.animals
    },
    {
      key: 'landmarks', title: 'מקום מיוחד', iconHTML: country.landmarks[0].emoji,
      items: country.landmarks
    },
    {
      key: 'language', title: 'איך אומרים שלום?', iconHTML: '👋',
      fact: 'ב' + country.language.name + ' אומרים "' + country.language.hello + '" (' + country.language.helloLatin + ')'
    },
    {
      key: 'people', title: 'אנשים מיוחדים', iconHTML: '⭐',
      items: country.famousPeople
    }
  ];
}

function openCountry(id) {
  const country = getCountry(id);
  session.countryId = id;
  session.seen = {};

  document.getElementById('country-title').textContent = country.name + ' ' + '🛬';
  document.getElementById('btn-play-games').classList.add('hidden');
  document.getElementById('country-hint').textContent = 'לחצו על הבועות כדי לגלות דברים מעניינים!';

  const scene = document.getElementById('country-scene');
  scene.innerHTML = '';

  countryCategories(country).forEach(function (cat, i) {
    const spot = document.createElement('button');
    spot.className = 'hotspot';
    spot.style.animationDelay = (i * 0.35) + 's';
    spot.innerHTML =
      '<span class="hotspot-icon">' + cat.iconHTML + '</span>' +
      '<span>' + cat.title + '</span>';
    spot.addEventListener('click', function () {
      openFactModal(cat);
      if (!session.seen[cat.key]) {
        session.seen[cat.key] = true;
        spot.classList.add('seen');
        checkAllSeen(country);
      }
    });
    scene.appendChild(spot);
  });

  showScreen('screen-country');
  AudioFX.speak('הגענו ל' + country.name + '! לחצו על הבועות כדי לגלות דברים מעניינים');
}

function checkAllSeen(country) {
  const total = countryCategories(country).length;
  if (Object.keys(session.seen).length === total) {
    const btn = document.getElementById('btn-play-games');
    btn.classList.remove('hidden');
    document.getElementById('country-hint').textContent = 'גיליתם הכול! עכשיו בואו נשחק 🎲';
  }
}

/* ---------- מודאל עובדה ---------- */

function openFactModal(cat) {
  AudioFX.sparkle();
  const modal = document.getElementById('fact-modal');
  document.getElementById('modal-icon').innerHTML = cat.iconHTML;
  document.getElementById('modal-title').textContent = cat.title;

  const itemsEl = document.getElementById('modal-items');
  let factText;

  if (cat.items) {
    itemsEl.innerHTML = cat.items.map(function (it) {
      return '<span title="' + it.name + '">' + it.emoji + '</span>';
    }).join('');
    factText = cat.items.map(function (it) { return it.fact; }).join('. ');
  } else {
    itemsEl.innerHTML = '';
    factText = cat.fact;
  }

  document.getElementById('modal-fact').textContent = factText;
  modal.classList.remove('hidden');
  AudioFX.speak(factText);
}

function closeFactModal() {
  document.getElementById('fact-modal').classList.add('hidden');
  AudioFX.stopSpeech();
}

/* ---------- משחקונים ---------- */

function startMinigames() {
  session.gamesQueue = shuffleArray(MINIGAME_ORDER);
  session.gameIndex = 0;
  showScreen('screen-minigame');
  runCurrentGame();
}

function runCurrentGame() {
  const country = getCountry(session.countryId);
  const area = document.getElementById('game-area');
  area.innerHTML = '';

  /* נקודות התקדמות */
  const dots = document.getElementById('game-progress');
  dots.innerHTML = session.gamesQueue.map(function (_, i) {
    const cls = i < session.gameIndex ? 'done' : (i === session.gameIndex ? 'now' : '');
    return '<span class="game-dot ' + cls + '"></span>';
  }).join('');

  const gameId = session.gamesQueue[session.gameIndex];
  MINIGAMES[gameId].run(area, country, {
    setInstruction: function (text) {
      document.getElementById('game-instruction').textContent = text;
    },
    onComplete: function () {
      session.gameIndex++;
      if (session.gameIndex < session.gamesQueue.length) {
        runCurrentGame();
      } else {
        showStampScreen();
      }
    }
  });
}

/* ---------- חותמת בדרכון ---------- */

function randomSummaryFact(country) {
  const pool = [country.flagFact, country.capital.fact, country.mapFact]
    .concat(country.foods.map(function (f) { return f.fact; }))
    .concat(country.animals.map(function (a) { return a.fact; }));
  return pickRandom(pool);
}

function showStampScreen() {
  const country = getCountry(session.countryId);
  addStamp(progress, country.id);

  /* מדבקה אקראית מהמדינה */
  const stickerPool = country.foods.concat(country.animals, country.landmarks);
  const sticker = pickRandom(stickerPool);
  addSticker(progress, sticker.emoji);

  const circle = document.getElementById('stamp-circle');
  circle.innerHTML = flagSVG(country.id);
  circle.classList.remove('stamp-in');
  void circle.offsetWidth;   // הפעלת האנימציה מחדש
  circle.classList.add('stamp-in');

  document.getElementById('stamp-country-name').textContent = country.name;
  const summary = randomSummaryFact(country);
  document.getElementById('stamp-summary').textContent = '🦉 הלילה למדנו: ' + summary;
  document.getElementById('sticker-award').textContent = 'קיבלתם מדבקה חדשה: ' + sticker.emoji + ' ' + sticker.name + '!';

  showScreen('screen-stamp');
  AudioFX.chime();
  AudioFX.speak('כל הכבוד! קיבלתם חותמת מ' + country.name + '. הלילה למדנו: ' + summary);
}

/* ---------- הדרכון ---------- */

function renderPassport() {
  const grid = document.getElementById('passport-stamps');
  grid.innerHTML = '';

  const visited = COUNTRIES.filter(function (c) { return progress.stamps[c.id]; });

  if (visited.length === 0) {
    grid.innerHTML = '<p class="empty-note">עוד אין חותמות... בואו נטוס למדינה הראשונה! ✈️</p>';
  }

  visited.forEach(function (country) {
    const card = document.createElement('button');
    card.className = 'stamp-card';
    card.innerHTML =
      '<span class="stamp-circle">' + flagSVG(country.id) + '</span>' +
      '<span>' + country.name + '</span>' +
      '<span class="continent">' + progress.stamps[country.id] + '</span>';
    card.addEventListener('click', function () {
      AudioFX.speak(country.name + '. ' + randomSummaryFact(country));
    });
    grid.appendChild(card);
  });

  const album = document.getElementById('sticker-album');
  album.innerHTML = progress.stickers.length
    ? progress.stickers.map(function (s) { return '<span>' + s + '</span>'; }).join('')
    : '<p class="empty-note">המדבקות שתאספו יופיעו כאן</p>';
}

/* ---------- לילה טוב ---------- */

function showGoodnight() {
  showScreen('screen-goodnight');
  document.getElementById('btn-finish').classList.add('hidden');
  AudioFX.speak('לילה טוב... ניפגש מחר במדינה חדשה');
  setTimeout(function () {
    document.getElementById('btn-finish').classList.remove('hidden');
  }, 4000);
}

/* ---------- חיבור אירועים ---------- */

function init() {
  createStars();
  startBedtimeDimming();

  document.getElementById('btn-start').addEventListener('click', function () {
    renderMap();
    showScreen('screen-map');
    AudioFX.speak('לאן טסים הלילה? בחרו מדינה!');
  });

  document.getElementById('btn-passport').addEventListener('click', function () {
    renderPassport();
    showScreen('screen-passport');
  });

  document.getElementById('btn-play-games').addEventListener('click', startMinigames);
  document.getElementById('modal-close').addEventListener('click', closeFactModal);
  document.getElementById('btn-goodnight').addEventListener('click', showGoodnight);

  document.getElementById('btn-another').addEventListener('click', function () {
    renderMap();
    showScreen('screen-map');
  });

  document.getElementById('btn-finish').addEventListener('click', function () {
    showScreen('screen-home');
  });

  document.querySelectorAll('.back-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      AudioFX.stopSpeech();
      if (btn.dataset.back === 'screen-map') renderMap();
      showScreen(btn.dataset.back);
    });
  });

  const muteBtn = document.getElementById('mute-btn');
  muteBtn.textContent = progress.muted ? '🔇' : '🔊';
  muteBtn.addEventListener('click', function () {
    const muted = AudioFX.toggleMute();
    progress.muted = muted;
    saveProgress(progress);
    muteBtn.textContent = muted ? '🔇' : '🔊';
  });
}

init();
