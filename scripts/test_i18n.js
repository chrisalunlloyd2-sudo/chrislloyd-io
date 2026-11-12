// Tests for the pure parts of assets/i18n.js (translator + money). Run: node scripts/test_i18n.js
const assert = require("assert");
const { norm, makeTranslator, makeMoney } = require("../assets/i18n.js");

function text(v) { return { nodeType: 3, nodeValue: v, get textContent() { return this.nodeValue; } }; }
function el(tag, attrs, kids) {
  const n = {
    nodeType: 1, nodeName: tag.toUpperCase(), attrs: Object.assign({}, attrs), childNodes: kids || [], _html: null,
    hasAttribute(k) { return k in this.attrs; },
    getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; },
    setAttribute(k, v) { this.attrs[k] = v; },
    get textContent() { return this.childNodes.map((c) => c.textContent).join(""); },
    set innerHTML(v) { this._html = v; this.childNodes = []; },
  };
  return n;
}

const P = {
  "Rooms": "Pièces", "Contact": "Contact", "Send": "Envoyer", "Your name": "Votre nom", "Shop": "Boutique",
  "Skip me": "NE PAS", "Hello": "Bonjour",
};
const SENT = "Estimate only — not a quote. Actual price depends on the paint.";
const R = { [SENT]: "Estimation seulement — <strong>pas une soumission.</strong> Le prix réel dépend de la peinture." };
const tr = makeTranslator(P, R);

// 1. norm
assert.strictEqual(norm("  a \n  b\t c "), "a b c");

// 2. text node keeps surrounding whitespace
let t = text("\n  Rooms  ");
tr.walk(t);
assert.strictEqual(t.nodeValue, "\n  Pièces  ");

// 3. attributes and submit value
let inp = el("input", { type: "text", placeholder: "Your name" });
tr.walk(inp);
assert.strictEqual(inp.attrs.placeholder, "Votre nom");
let sub = el("input", { type: "submit", value: "Send" });
tr.walk(sub);
assert.strictEqual(sub.attrs.value, "Envoyer");
let txt = el("input", { type: "text", value: "Send" });
tr.walk(txt);
assert.strictEqual(txt.attrs.value, "Send", "text input values are user data, never translated");

// 4. rich unit (sentence with an inline element) is replaced as a whole
let rich = el("p", {}, [text("Estimate only — "), el("strong", {}, [text("not a quote.")]), text(" Actual price depends on the paint.")]);
tr.walk(rich);
assert.ok(rich._html && rich._html.indexOf("<strong>pas une soumission.</strong>") >= 0);

// 5. label with a form control is NOT replaced wholesale: the input survives, text node is translated
let input = el("input", { id: "est-rooms" });
let label = el("label", {}, [text("Rooms "), input]);
tr.walk(label);
assert.strictEqual(label.childNodes[0].nodeValue, "Pièces ");
assert.strictEqual(label.childNodes[1], input);
assert.strictEqual(label._html, null);

// 6. heading with only an svg icon and one word is plain text
let h = el("h2", {}, [el("svg", {}, []), text(" Shop")]);
tr.walk(h);
assert.strictEqual(h.childNodes[1].nodeValue, " Boutique");

// 7. data-no-i18n and script/style are skipped
let skip = el("div", { "data-no-i18n": "" }, [text("Hello")]);
tr.walk(skip);
assert.strictEqual(skip.childNodes[0].nodeValue, "Hello");
let scr = el("script", {}, [text("Hello")]);
tr.walk(scr);
assert.strictEqual(scr.childNodes[0].nodeValue, "Hello");

// 8. unknown text is left alone, and running twice is harmless
let unk = text("Something not in the catalog");
tr.walk(unk);
assert.strictEqual(unk.nodeValue, "Something not in the catalog");
let again = text("Rooms");
tr.walk(again); tr.walk(again);
assert.strictEqual(again.nodeValue, "Pièces");

// 9. meta description is translated only for the listed names
let meta = el("meta", { name: "description", content: "Hello" });
tr.walk(meta);
assert.strictEqual(meta.attrs.content, "Bonjour");
let other = el("meta", { name: "viewport", content: "Hello" });
tr.walk(other);
assert.strictEqual(other.attrs.content, "Hello");

// 10. prototype keys never match
let proto = text("constructor");
tr.walk(proto);
assert.strictEqual(proto.nodeValue, "constructor");

// 11. money
const strip = (s) => s.replace(/[  ]/g, " ");
const cadEn = makeMoney("CAD", 1.4181, "en-CA", Intl);
assert.strictEqual(strip(cadEn(100, "USD", 2)), "$141.81");
assert.strictEqual(strip(cadEn(100, "CAD", 0)), "$100");
const usdEn = makeMoney("USD", 1.4181, "en-CA", Intl);
assert.strictEqual(strip(usdEn(1418.1, "CAD", 0)), "US$1,000");
assert.strictEqual(strip(usdEn(10, "USD", 2)), "US$10.00");
const cadFr = makeMoney("CAD", 1.4181, "fr-CA", Intl);
assert.ok(/141,81/.test(strip(cadFr(100, "USD", 2))), strip(cadFr(100, "USD", 2)));
const noRate = makeMoney("CAD", 0, "en-CA", Intl);
assert.strictEqual(strip(noRate(10, "USD", 2)), "US$10.00", "without a rate, show the original currency, never a guess");

console.log("i18n.js ok");
