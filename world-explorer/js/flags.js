/* ===== דגלי SVG מצוירים (מפושטים לילדים) ===== */

const FLAGS = {

  israel: `
    <svg viewBox="0 0 300 200" xmlns="http://www.w3.org/2000/svg">
      <rect width="300" height="200" fill="#ffffff"/>
      <rect y="18" width="300" height="26" fill="#0038b8"/>
      <rect y="156" width="300" height="26" fill="#0038b8"/>
      <g stroke="#0038b8" stroke-width="9" fill="none">
        <polygon points="150,58 187,122 113,122"/>
        <polygon points="150,142 113,78 187,78"/>
      </g>
    </svg>`,

  italy: `
    <svg viewBox="0 0 300 200" xmlns="http://www.w3.org/2000/svg">
      <rect width="100" height="200" fill="#009246"/>
      <rect x="100" width="100" height="200" fill="#ffffff"/>
      <rect x="200" width="100" height="200" fill="#ce2b37"/>
    </svg>`,

  japan: `
    <svg viewBox="0 0 300 200" xmlns="http://www.w3.org/2000/svg">
      <rect width="300" height="200" fill="#ffffff"/>
      <circle cx="150" cy="100" r="58" fill="#bc002d"/>
    </svg>`,

  brazil: `
    <svg viewBox="0 0 300 200" xmlns="http://www.w3.org/2000/svg">
      <rect width="300" height="200" fill="#009b3a"/>
      <polygon points="150,26 274,100 150,174 26,100" fill="#fedf00"/>
      <circle cx="150" cy="100" r="48" fill="#002776"/>
      <path d="M106 94 Q150 76 194 94" stroke="#ffffff" stroke-width="9" fill="none"/>
    </svg>`,

  kenya: `
    <svg viewBox="0 0 300 200" xmlns="http://www.w3.org/2000/svg">
      <rect width="300" height="56" fill="#000000"/>
      <rect y="56" width="300" height="10" fill="#ffffff"/>
      <rect y="66" width="300" height="68" fill="#922529"/>
      <rect y="134" width="300" height="10" fill="#ffffff"/>
      <rect y="144" width="300" height="56" fill="#008c51"/>
      <line x1="118" y1="30" x2="182" y2="170" stroke="#ffffff" stroke-width="7"/>
      <line x1="182" y1="30" x2="118" y2="170" stroke="#ffffff" stroke-width="7"/>
      <ellipse cx="150" cy="100" rx="34" ry="58" fill="#ffffff"/>
      <ellipse cx="150" cy="100" rx="27" ry="50" fill="#922529"/>
      <ellipse cx="150" cy="100" rx="10" ry="24" fill="#000000"/>
      <circle cx="150" cy="100" r="5" fill="#ffffff"/>
    </svg>`
};

function flagSVG(countryId) {
  return FLAGS[countryId] || '';
}
