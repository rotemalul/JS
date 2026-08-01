/* ===== משחקונים =====
   כל משחקון: run(area, country, ctx) — ctx נותן setInstruction ו-onComplete.
   אין כישלון: טעות רק מעמעמת אפשרות, תמיד מגיעים להצלחה. */

function shuffleArray(arr) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    const t = a[i]; a[i] = a[j]; a[j] = t;
  }
  return a;
}

function pickRandom(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

function otherCountries(country, count, mapFn) {
  const others = shuffleArray(COUNTRIES.filter(function (c) { return c.id !== country.id; }));
  return others.slice(0, count).map(mapFn);
}

/* חגיגה קטנה בסיום משחקון */
function celebrate(area, ctx, message) {
  AudioFX.chime();
  const burst = document.createElement('div');
  burst.className = 'celebrate-burst';
  burst.textContent = '🎉 ' + message + ' ⭐';
  area.appendChild(burst);
  AudioFX.speak(message);
  setTimeout(ctx.onComplete, 1800);
}

/* תגובה עדינה לטעות */
function gentleMiss(btn) {
  AudioFX.hmm();
  AudioFX.speak('כמעט! בואו ננסה שוב');
  btn.classList.add('wiggle');
  setTimeout(function () { btn.classList.add('dimmed'); }, 400);
}

const MINIGAMES = {

  /* --- מצאו את הדגל --- */
  'flag-pick': {
    run(area, country, ctx) {
      ctx.setInstruction('איזה דגל הוא הדגל של ' + country.name + '?');
      AudioFX.speak('איזה דגל הוא הדגל של ' + country.name + '?');

      const options = shuffleArray(
        [country.id].concat(otherCountries(country, 2, function (c) { return c.id; }))
      );

      const row = document.createElement('div');
      row.className = 'options-row';
      options.forEach(function (id) {
        const btn = document.createElement('button');
        btn.className = 'option-btn';
        btn.innerHTML = flagSVG(id);
        btn.addEventListener('click', function () {
          if (id === country.id) {
            btn.classList.add('correct');
            celebrate(area, ctx, 'נכון! זה הדגל של ' + country.name);
          } else {
            gentleMiss(btn);
          }
        });
        row.appendChild(btn);
      });
      area.appendChild(row);
    }
  },

  /* --- מי גר כאן? --- */
  'animal-match': {
    run(area, country, ctx) {
      const target = pickRandom(country.animals);
      ctx.setInstruction('איזו חיה פגשנו ב' + country.name + '?');
      AudioFX.speak('איזו חיה פגשנו ב' + country.name + '?');

      const distractors = otherCountries(country, 3, function (c) { return pickRandom(c.animals); });
      const options = shuffleArray([target].concat(distractors));

      const row = document.createElement('div');
      row.className = 'options-row';
      options.forEach(function (animal) {
        const btn = document.createElement('button');
        btn.className = 'option-btn';
        btn.innerHTML = '<span class="opt-emoji">' + animal.emoji + '</span><span>' + animal.name + '</span>';
        btn.addEventListener('click', function () {
          if (animal === target) {
            btn.classList.add('correct');
            celebrate(area, ctx, 'נכון! ה' + target.name + ' גר ב' + country.name);
          } else {
            gentleMiss(btn);
          }
        });
        row.appendChild(btn);
      });
      area.appendChild(row);
    }
  },

  /* --- פאזל דגל: בוחרים חלק ולוחצים על המקום שלו --- */
  'flag-puzzle': {
    run(area, country, ctx) {
      ctx.setInstruction('בואו נרכיב את הדגל של ' + country.name + '! לחצו על חלק, ואז על המקום שלו');
      AudioFX.speak('בואו נרכיב את הדגל של ' + country.name + '. לחצו על חלק, ואחר כך על המקום שלו בלוח');

      const board = document.createElement('div');
      board.className = 'puzzle-board';
      const piecesRow = document.createElement('div');
      piecesRow.className = 'puzzle-pieces';

      let selected = null;
      let placed = 0;

      /* 4 רבעים: 0=ימין-למעלה בערך לפי הסדר בגריד */
      const quarters = [
        { row: 0, col: 0 }, { row: 0, col: 1 },
        { row: 1, col: 0 }, { row: 1, col: 1 }
      ];

      function quarterHTML(q) {
        return '<div class="piece-svg" style="left:' + (-q.col * 100) + '%;top:' + (-q.row * 100) + '%">' +
               flagSVG(country.id) + '</div>';
      }

      quarters.forEach(function (q, i) {
        const slot = document.createElement('div');
        slot.className = 'puzzle-slot';
        slot.dataset.index = i;
        slot.addEventListener('click', function () {
          if (!selected || slot.classList.contains('filled')) return;
          if (Number(selected.dataset.index) === i) {
            slot.innerHTML = quarterHTML(q);
            slot.classList.add('filled');
            selected.remove();
            selected = null;
            placed++;
            AudioFX.sparkle();
            if (placed === 4) {
              celebrate(area, ctx, 'הרכבתם את הדגל של ' + country.name + '!');
            }
          } else {
            AudioFX.hmm();
            slot.classList.add('wiggle');
            setTimeout(function () { slot.classList.remove('wiggle'); }, 500);
          }
        });
        board.appendChild(slot);
      });

      shuffleArray(quarters.map(function (q, i) { return { q: q, i: i }; })).forEach(function (item) {
        const piece = document.createElement('button');
        piece.className = 'puzzle-piece';
        piece.dataset.index = item.i;
        piece.innerHTML = quarterHTML(item.q);
        piece.addEventListener('click', function () {
          if (selected) selected.classList.remove('selected');
          selected = piece;
          piece.classList.add('selected');
          AudioFX.sparkle();
        });
        piecesRow.appendChild(piece);
      });

      area.appendChild(board);
      area.appendChild(piecesRow);
    }
  }
};

const MINIGAME_ORDER = ['flag-pick', 'animal-match', 'flag-puzzle'];
