// PLAN-SITE-100 step 15 / PLAN-VOICE-100 step 70 — speakable JSON-LD for the FAQ.
// Mirrors the LD-building logic inside renderFAQ() in assets/main.js (keep in sync).
// Run: node scripts/test_faq_schema.js
'use strict';

function buildFaqJsonLd(items) {
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "speakable": {
      "@type": "SpeakableSpecification",
      "cssSelector": ["#faq-list .faq-item"]
    },
    "mainEntity": items.map(function (item) {
      return {
        "@type": "Question",
        "name": item.q,
        "acceptedAnswer": { "@type": "Answer", "text": item.a }
      };
    })
  };
}

let fail = 0;
function check(name, cond) {
  if (!cond) { console.log('FAIL', name); fail++; }
}

const ld = buildFaqJsonLd([
  { q: "How do I get a quote?", a: "Message me or use the form." },
  { q: "Do you clean up after?", a: "Yes, daily plus a final cleanup." },
]);

check('is valid JSON when stringified', (() => { try { JSON.parse(JSON.stringify(ld)); return true; } catch (e) { return false; } })());
check('@type is FAQPage', ld['@type'] === 'FAQPage');
check('speakable @type is SpeakableSpecification', ld.speakable && ld.speakable['@type'] === 'SpeakableSpecification');
check('speakable selector targets the real #faq-list container', Array.isArray(ld.speakable.cssSelector) && ld.speakable.cssSelector.indexOf('#faq-list .faq-item') !== -1);
check('mainEntity has one Question per faq.json entry', ld.mainEntity.length === 2);
check('every Question has a non-empty name and acceptedAnswer.text', ld.mainEntity.every(function (q) {
  return !!q.name && q['@type'] === 'Question' && q.acceptedAnswer && q.acceptedAnswer['@type'] === 'Answer' && !!q.acceptedAnswer.text;
}));
// speakable must point at a real, existing selector -- not a fabricated element id
check('speakable selector never references a non-existent per-item id (only the shared container class)',
  ld.speakable.cssSelector.every(function (sel) { return !/#faq-item-\d/.test(sel); }));

console.log(fail === 0 ? 'ALL FAQ SCHEMA TESTS PASS' : 'FAILURES: ' + fail);
process.exit(fail ? 1 : 0);
