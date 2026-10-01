// Task 027 — pure-function tests for the gallery renderer helpers.
// Mirrors galleryRenderable() / galleryPlaceholderPolicy() from assets/main.js;
// the DOM side (img.onerror removal, empty-state note) is structural-tested in
// test_site_scripts.py (TestGallery). Run: node scripts/test_gallery_logic.js
'use strict';

// --- copies of the pure helpers (keep in sync with assets/main.js) -----------
var GALLERY_SIDES = ['before', 'after'];

function galleryRenderable(item) {
  return !!item && GALLERY_SIDES.every(function (w) {
    return !!(item[w] && typeof item[w].src === 'string' && item[w].src.length);
  });
}

// Placeholder policy: a placeholder entry must be visibly marked in both the
// title and both alts, and must NOT point at a real photo that exists yet.
function galleryPlaceholderOk(item) {
  if (item.placeholder !== true) return true; // real entries: no policy
  var markedOk = item.title.indexOf('PLACEHOLDER') !== -1
    && GALLERY_SIDES.every(function (w) {
      return (item[w].alt || '').indexOf('PLACEHOLDER') !== -1;
    });
  var livePhoto = GALLERY_SIDES.some(function (w) {
    return /^(https?:|\/|data:)/.test(item[w].src);
  });
  return markedOk && !livePhoto;
}

// --- tests --------------------------------------------------------------------
let fail = 0;
function expect(cond, msg) {
  if (!cond) { console.log('FAIL:', msg); fail++; }
}

// galleryRenderable: needs a src string on BOTH sides
expect(galleryRenderable(null) === false, 'null entry not renderable');
expect(galleryRenderable({}) === false, 'empty entry not renderable');
expect(galleryRenderable({
  before: { src: 'assets/gallery/a.jpg' },
}) === false, 'missing after side not renderable');
expect(galleryRenderable({
  before: { src: 'assets/gallery/a.jpg', alt: 'x' },
  after: { src: '' },                       // empty string src
}) === false, 'empty-string src not renderable');
expect(galleryRenderable({
  before: { src: 'assets/gallery/a.jpg', alt: 'b' },
  after: { src: 'assets/gallery/b.jpg', alt: 'a' },
}) === true, 'both srcs present -> renderable');

// placeholder policy: marked + no live photos
expect(galleryPlaceholderOk({
  title: 'PLACEHOLDER — Before & After Entry',
  before: { src: 'assets/gallery/placeholder-before.jpg', alt: 'PLACEHOLDER — before' },
  after: { src: 'assets/gallery/placeholder-after.jpg', alt: 'PLACEHOLDER — after' },
  placeholder: true,
}) === true, 'marked placeholder entry passes policy');

expect(galleryPlaceholderOk({
  title: 'Real Job — Kitchen',      // UNMARKED title
  before: { src: 'assets/gallery/x.jpg', alt: 'x' },
  after: { src: 'assets/gallery/y.jpg', alt: 'y' },
  placeholder: true,
}) === false, 'unmarked title fails policy');

expect(galleryPlaceholderOk({
  title: 'PLACEHOLDER — Kitchen',
  before: { src: '/photos/kitchen-before.jpg', alt: 'PLACEHOLDER — before' },
  after: { src: 'assets/gallery/y.jpg', alt: 'PLACEHOLDER — after' },
  placeholder: true,
}) === false, 'placeholder pointing at a live photo path fails policy');

expect(galleryPlaceholderOk({
  title: 'Real Job — Kitchen',
  before: { src: 'assets/gallery/x.jpg', alt: 'kitchen before' },
  after: { src: 'assets/gallery/y.jpg', alt: 'kitchen after' },
  placeholder: false,
}) === true, 'real entry has no placeholder policy');

// shipped data file must satisfy both helpers (fixtures, not assumptions)
const items = require('../data/gallery.json');
expect(Array.isArray(items) && items.length >= 1, 'data/gallery.json must be a non-empty array');
items.forEach((item, i) => {
  expect(galleryRenderable(item), `entry ${i} (${item.id}) must be renderable (src on both sides)`);
  expect(galleryPlaceholderOk(item), `entry ${i} (${item.id}) must satisfy placeholder policy`);
});

console.log(fail === 0 ? 'ALL GALLERY LOGIC TESTS PASS' : 'FAILURES: ' + fail);
process.exit(fail ? 1 : 0);