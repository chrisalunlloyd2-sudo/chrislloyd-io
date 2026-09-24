// Blog renderer — data-driven from data/posts.json, styled by the 013 design system.
(function () {
  "use strict";

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }

  // Same rosette motif as the main site (main.js), local copy so blog.js stays standalone.
  var SVG_NS = "http://www.w3.org/2000/svg";
  var ACCENTS = ["#c1613c", "#3c8f82"];
  function rosette() {
    var svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("viewBox", "0 0 200 200");
    var cx = 100, cy = 100, r = 96;
    for (var i = 0; i < 8; i++) {
      var a1 = (i * 45) * Math.PI / 180;
      var a2 = ((i + 1) * 45) * Math.PI / 180;
      var pts = cx + "," + cy + " " +
        (cx + r * Math.cos(a1)).toFixed(1) + "," + (cy + r * Math.sin(a1)).toFixed(1) + " " +
        (cx + r * Math.cos(a2)).toFixed(1) + "," + (cy + r * Math.sin(a2)).toFixed(1);
      var poly = document.createElementNS(SVG_NS, "polygon");
      poly.setAttribute("points", pts);
      poly.setAttribute("fill", ACCENTS[i % 2]);
      poly.setAttribute("fill-opacity", (0.25 + 0.45 * ((i % 3) / 2)).toFixed(2));
      poly.setAttribute("stroke", "#14171c");
      poly.setAttribute("stroke-width", "1.5");
      svg.appendChild(poly);
    }
    var wrap = el("div");
    wrap.style.position = "absolute";
    wrap.style.inset = "0";
    wrap.appendChild(svg);
    return wrap;
  }
  var heroSlot = document.querySelector(".rosette-hero");
  if (heroSlot) heroSlot.appendChild(rosette());

  function fmtDate(iso) {
    var d = new Date(iso + "T00:00:00");
    return isNaN(d) ? iso : d.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
  }

  function renderIndex(posts) {
    var list = document.getElementById("post-list");
    if (!posts.length) {
      list.appendChild(el("p", "section-note", "No posts yet."));
      return;
    }
    posts.forEach(function (p) {
      var art = el("article", "card blog-card" + (/\[?\s*PLACEHOLDER/i.test(p.excerpt || "") ? " placeholder" : ""));
      art.appendChild(el("p", "blog-date", fmtDate(p.date)));
      art.appendChild(el("h3", null, p.title));
      art.appendChild(el("p", null, p.excerpt));
      var a = el("a", null, "Read post →");
      a.href = "?post=" + encodeURIComponent(p.id);
      art.appendChild(a);
      list.appendChild(art);
    });
  }

  // SEO: per-post head tags. base comes from site.canonicalBase when set,
  // falling back to the deployed GitHub Pages URL.
  function seoBase() {
    var c = document.querySelector('link[rel="canonical"]');
    if (c) {
      var u = new URL(c.href);
      return u.origin + u.pathname.replace(/blog\.html$/, "");
    }
    return window.location.origin + window.location.pathname.replace(/blog\.html$/, "");
  }
  function setMeta(attr, key, content) {
    var m = document.querySelector("meta[" + attr + '="' + key + '"]');
    if (m) m.setAttribute("content", content);
  }
  function applyPostSeo(p) {
    var url = seoBase() + "blog.html?post=" + encodeURIComponent(p.id);
    document.title = p.title + " — Chris Lloyd Ltd";
    var c = document.getElementById("canonical-link");
    if (c) c.href = url;
    var desc = (p.excerpt || "").replace(/\[?\s*PLACEHOLDER[^\]]*\]?/i, "").trim() || p.title;
    var d = document.querySelector('meta[name="description"]');
    if (d) d.setAttribute("content", desc);
    setMeta("property", "og:title", p.title + " — Chris Lloyd Ltd");
    setMeta("property", "og:description", desc);
    setMeta("property", "og:type", "article");
    setMeta("property", "og:url", url);
    setMeta("name", "twitter:title", p.title + " — Chris Lloyd Ltd");
    setMeta("name", "twitter:description", desc);
  }

  function renderPost(p) {
    var view = document.getElementById("post-view");
    var list = document.getElementById("post-list");
    if (list) list.hidden = true;
    document.getElementById("blog-title").textContent = p.title;
    view.hidden = false;
    view.appendChild(el("p", "blog-date", fmtDate(p.date)));
    var paras = typeof p.body === "string" ? [p.body] : (p.body || []);
    paras.forEach(function (t) { view.appendChild(el("p", null, t)); });
    var back = el("a", "back-link", "← All posts");
    back.href = "blog.html";
    view.appendChild(back);
    applyPostSeo(p);
  }

  fetch("data/posts.json")
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (posts) {
      posts = (posts || []).slice().sort(function (a, b) { return (b.date || "").localeCompare(a.date || ""); });
      var wanted = new URLSearchParams(window.location.search).get("post");
      if (wanted) {
        var found = posts.filter(function (p) { return p.id === wanted; })[0];
        if (found) { renderPost(found); return; }
        // unknown id: fall through to index
      }
      renderIndex(posts);
    })
    .catch(function (e) {
      var list = document.getElementById("post-list");
      if (list) list.appendChild(el("p", "section-note", "Posts failed to load (" + e.message + ")."));
    });

  fetch("data/site.json").then(function (r) { return r.json(); }).then(function (s) {
    var site = s.site || {};
    document.getElementById("footer-name").textContent = site.legalName || site.name || "";
  }).catch(function () {});

  document.getElementById("year").textContent = new Date().getFullYear();
})();