// Tier logic unit tests (task 015) — mirrors computeLeadTier() in assets/main.js
function tier(property, timeline, photos, referral, budget) {
  var hasSignal = photos || referral || !!(budget || '').trim();
  if (property === 'own' && timeline !== 'ideas' && hasSignal) return 'hot';
  if (property === 'rent_approved' || property === 'manager') return 'warm';
  if (property === 'own' || property === 'rent_approved' || property === 'manager') return 'warm';
  if (property === 'rent_unapproved') return 'filtered';
  if (timeline === 'ideas') return 'filtered';
  return 'warm';
}
const cases = [
  ['own', 'ready', true, false, '', 'hot'],
  ['own', 'ready', false, true, '', 'hot'],      // referral source
  ['own', 'months', false, false, '2000', 'hot'],// budget given
  ['own', 'ready', false, false, '', 'warm'],    // owner, no extra signal
  ['own', 'ideas', false, false, '', 'warm'],    // gathering ideas but owner
  ['rent_approved', 'ideas', false, false, '', 'warm'],
  ['rent_unapproved', 'ready', true, false, '', 'filtered'], // renter w/o approval dominates
  ['rent_unapproved', 'ready', false, false, '', 'filtered'],
  ['manager', 'ready', false, false, '', 'warm'],
];
let fail = 0;
cases.forEach(c => {
  const got = tier(c[0], c[1], c[2], c[3], c[4]);
  if (got !== c[5]) { console.log('FAIL', c, 'got', got); fail++; }
});
console.log(fail === 0 ? 'ALL TIER TESTS PASS' : 'FAILURES: ' + fail);
process.exit(fail ? 1 : 0);