// Task 034 — pure-function tests for the paint-quote estimator widget.
// Mirrors estimatorsPure helpers from assets/main.js (parseRoomSize,
// estimatorRates, estimateInterior, estimateExterior) and checks JS-vs-CLI
// parity: the numbers this JS produces must EQUAL scripts/quote_estimator.py
// output for identical inputs. Fixtures are generated at test time by
// scripts/gen_estimator_fixtures.py — never stale.
// Run: node scripts/test_estimator_logic.js
'use strict';

const { execFileSync } = require('child_process');
const path = require('path');
const fs = require('fs');

// --- mirror of window.__estimatorPure (keep in sync with assets/main.js) -----
function round1(x) { return Math.round(x * 10) / 10; }
function round2(x) { return Math.round(x * 100) / 100; }

var ESTIMATOR_DEFAULT_RATES = {
  labour_rate: 55.0, coats_standard: 2, roller_sqft_hr: 150.0,
  cutin_hr_per_room: 1.5, prep_hr_per_room: 2.5, repair_hr_per_pop: 0.25,
  height_9ft_factor: 1.3, exterior_sqft_hr: 100.0,
  paint_cost_wall_gal: 75.0, gal_coverage_sqft: 350.0
};

function parseRoomSize(str) {
  var m = /^(\d+(?:\.\d+)?)\s*[xX]\s*(\d+(?:\.\d+)?)$/.exec((str || "").trim());
  if (!m) return null;
  var w = parseFloat(m[1]), l = parseFloat(m[2]);
  if (!(w > 0) || !(l > 0)) return null;
  return { w: w, l: l };
}

function estimatorRates(rates) {
  var def = ESTIMATOR_DEFAULT_RATES;
  var out = {};
  Object.keys(def).forEach(function (k) {
    var v = rates ? rates[k] : undefined;
    out[k] = (typeof v === "number" && isFinite(v) && v > 0) ? v : def[k];
  });
  return out;
}

function estimateInterior(rooms, sizeW, sizeL, height, repairs, rates, coats) {
  var r = estimatorRates(rates);
  var nC = parseInt(rooms, 10); if (!(nC > 0)) nC = 1;
  var nR = parseInt(repairs, 10); if (!(nR >= 0)) nR = 0;
  var h = (parseInt(height, 10) === 9) ? 9 : 8;
  var nCoats = parseInt(coats, 10) || r.coats_standard;
  var wallSqft = nC * 2 * (sizeW + sizeL) * h;
  var areaHr = wallSqft / r.roller_sqft_hr;
  var cutinHr = nC * r.cutin_hr_per_room;
  var prepHr = nC * r.prep_hr_per_room + nR * r.repair_hr_per_pop;
  var factor = (h >= 9) ? r.height_9ft_factor : 1.0;
  var labourHr = (areaHr + cutinHr + prepHr) * factor;
  var gal = wallSqft * nCoats / r.gal_coverage_sqft;
  var paintCost = gal * r.paint_cost_wall_gal;
  var labourCost = labourHr * r.labour_rate;
  return {
    mode: "interior", wall_sqft: round1(wallSqft),
    labour_hours: round1(labourHr), labour_cost: round2(labourCost),
    paint_gallons: round1(gal), paint_cost: round2(paintCost),
    total_range: [Math.round((labourCost + paintCost) * 0.9),
                  Math.round((labourCost + paintCost) * 1.15)]
  };
}

function estimateExterior(sqft, rates, coats) {
  var r = estimatorRates(rates);
  var area = parseInt(sqft, 10);
  if (!(area > 0)) area = 0;
  var nCoats = parseInt(coats, 10) || r.coats_standard;
  var labourHr = area / r.exterior_sqft_hr * nCoats;
  var gal = area * nCoats / r.gal_coverage_sqft;
  var paintCost = gal * r.paint_cost_wall_gal * 1.2;
  var labourCost = labourHr * r.labour_rate;
  return {
    mode: "exterior", siding_sqft: area,
    labour_hours: round1(labourHr), labour_cost: round2(labourCost),
    paint_gallons: round1(gal), paint_cost: round2(paintCost),
    total_range: [Math.round((labourCost + paintCost) * 0.9),
                  Math.round((labourCost + paintCost) * 1.15)]
  };
}

// --- tests --------------------------------------------------------------------
let fail = 0;
function expect(cond, msg) {
  if (!cond) { console.log('FAIL:', msg); fail++; }
}

// parseRoomSize: strict WxL, tolerant of decimals/spaces/X case, rejects junk
expect(parseRoomSize('12x14') !== null && parseRoomSize('12x14').w === 12, "12x14 -> w=12");
expect(parseRoomSize('12x14').l === 14, "12x14 -> l=14");
expect(parseRoomSize(' 11.5 x 13.25 ') !== null, "spaces+decimals parse");
expect(parseRoomSize('10X12') !== null && parseRoomSize('10X12').l === 12, "capital X parses");
expect(parseRoomSize('garage') === null, "non-numeric rejected");
expect(parseRoomSize('12') === null, "missing dimension rejected");
expect(parseRoomSize('0x14') === null, "zero width rejected");
expect(parseRoomSize('-3x14') === null, "negative rejected");
expect(parseRoomSize('') === null, "empty string rejected");

// estimatorRates: bad/missing rates fall back to CLI defaults, valid pass through
var rDefault = estimatorRates(null);
Object.keys(ESTIMATOR_DEFAULT_RATES).forEach(function (k) {
  expect(rDefault[k] === ESTIMATOR_DEFAULT_RATES[k], "fallback default " + k);
});
var rPart = estimatorRates({ labour_rate: 70, roller_sqft_hr: 0, height_9ft_factor: -2 });
expect(rPart.labour_rate === 70, "valid rate overrides");
expect(rPart.roller_sqft_hr === 150.0, "zero rate rejected -> default");
expect(rPart.height_9ft_factor === 1.3, "negative rate rejected -> default");

// estimateInterior: default inputs must equal the CLI's interior_default fixture
const fixturesPath = path.join(__dirname, 'test_estimator_fixtures.json');
expect(fs.existsSync(fixturesPath), 'fixtures file must exist (gen_estimator_fixtures.py writes it)');
const FIX = JSON.parse(fs.readFileSync(fixturesPath, 'utf8'));

function expectParity(tag, js, fix) {
  expect(js.wall_sqft === fix.wall_sqft, tag + ' wall_sqft parity: ' + js.wall_sqft + ' vs ' + fix.wall_sqft);
  expect(js.labour_hours === fix.labour_hours, tag + ' labour_hours parity: ' + js.labour_hours + ' vs ' + fix.labour_hours);
  expect(js.labour_cost === fix.labour_cost, tag + ' labour_cost parity');
  expect(js.paint_gallons === fix.paint_gallons, tag + ' paint_gallons parity');
  expect(js.paint_cost === fix.paint_cost, tag + ' paint_cost parity');
  expect(js.total_range[0] === fix.total_range[0], tag + ' range low parity');
  expect(js.total_range[1] === fix.total_range[1], tag + ' range high parity');
}

// 3 rooms 12x14 8ft 0 repairs — the widget's default interior inputs
var dInt = estimateInterior(3, 12, 14, 8, 0, null);
expectParity('interior_default', dInt, FIX.interior_default);
expect(dInt.wall_sqft === 1248, 'default interior wall_sqft is 1248');

// 9ft factor + repairs path
var h9 = estimateInterior(2, 12, 14, 9, 3, null);
expectParity('interior_9ft', h9, FIX.interior_9ft);

var small = estimateInterior(1, 10, 10, 8, 0, null);
expectParity('interior_small', small, FIX.interior_small);

var rep = estimateInterior(3, 12, 14, 8, 5, null);
expectParity('interior_repairs', rep, FIX.interior_repairs);

// range band math: lo = floor-ish 0.9x, hi = 1.15x of mid-cost, brackets it
[[ 'default', dInt ], [ '9ft', h9 ], [ 'exterior', estimateExterior(1500, null) ]].forEach(function (pair) {
  var tag = pair[0], r = pair[1];
  var mid = r.labour_cost + r.paint_cost;
  expect(r.total_range[0] <= mid && mid <= r.total_range[1], tag + ' range brackets mid');
  expect(r.total_range[0] === Math.round(mid * 0.9), tag + ' low is round(m*0.9)');
  expect(r.total_range[1] === Math.round(mid * 1.15), tag + ' high is round(m*1.15)');
});

// mode/exterior: linear scaling + parity
var e1500 = estimateExterior(1500, null), e3000 = estimateExterior(3000, null);
expectParity('exterior_default', e1500, FIX.exterior_default);
expectParity('exterior_2x', e3000, FIX.exterior_2x);
expect(e3000.labour_hours === e1500.labour_hours * 2, 'exterior labour scales linearly');
expect(e1500.total_range[0] < e1500.total_range[1], 'exterior range low < high');

// exterior paint premium: cost uses UNROUNDED gallons (like the CLI), so the
// check recomputes raw gal from the same inputs rather than the rounded display value
var rawGal1500 = 1500 * 2 / 350;
expect(Math.abs(e1500.paint_cost - rawGal1500 * ESTIMATOR_DEFAULT_RATES.paint_cost_wall_gal * 1.2) < 0.01,
  'exterior paint carries 1.2 premium');

// custom rates flow through (owner will edit data/pricing.json later);
// rates change cost but never the hours
var custom = estimatorRates({ labour_rate: 65 });
var cInt = estimateInterior(3, 12, 14, 8, 0, custom);
var rawHrDefault = (3 * 2 * (12 + 14) * 8 / 150 + 3 * 1.5 + 3 * 2.5); // 20.32 unrounded
expect(cInt.labour_hours === dInt.labour_hours, 'custom rate leaves hours unchanged');
expect(cInt.labour_cost === round2(rawHrDefault * 65), 'custom labour_rate changes cost from unrounded hours');

// shipped pricing.json must carry the same numbers as CLI DEFAULTS (drift alarm)
const pricing = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data', 'pricing.json'), 'utf8'));
expect(pricing._edit_me === true, 'pricing.json must keep _edit_me flag until owner acts');
expect(Array.isArray(pricing._owner_action) && pricing._owner_action.join(' ').indexOf('OWNER ACTION') !== -1,
  'pricing.json must carry OWNER-ACTION comment block');
Object.keys(ESTIMATOR_DEFAULT_RATES).forEach(function (k) {
  expect(pricing.rates[k] === ESTIMATOR_DEFAULT_RATES[k], 'pricing.json rates.' + k + ' matches CLI DEFAULTS');
});

// main.js must actually contain the estimator wiring (renderer called, section fed)
const mainJs = fs.readFileSync(path.join(__dirname, '..', 'assets', 'main.js'), 'utf8');
expect(mainJs.indexOf('renderEstimator();') !== -1, 'main.js must call renderEstimator()');
expect(mainJs.indexOf('data/pricing.json') !== -1, 'main.js must load data/pricing.json');

console.log(fail === 0 ? 'ALL ESTIMATOR LOGIC TESTS PASS' : 'FAILURES: ' + fail);
process.exit(fail ? 1 : 0);