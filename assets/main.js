// Renders all page content from /data/*.json — edit the JSON files, not this HTML.
(function () {
  "use strict";

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }

  function card(item, opts) {
    opts = opts || {};
    var c = el("article", "card" + (item.placeholder ? " placeholder" : ""));
    if (item.title) c.appendChild(el("h3", null, item.title));
    if (item.desc) c.appendChild(el("p", null, item.desc));
    if (item.category) c.appendChild(el("p", null, item.category));
    if (item.tags && item.tags.length) {
      var meta = el("ul", "meta");
      item.tags.forEach(function (t) { meta.appendChild(el("li", null, t)); });
      c.appendChild(meta);
    }
    if (item.url) {
      var a = el("a", null, item.url_label || "Visit");
      a.href = item.url;
      if (/^https?:/.test(item.url)) { a.target = "_blank"; a.rel = "noopener noreferrer"; }
      c.appendChild(a);
    } else if (item.placeholder) {
      c.appendChild(el("span", "meta", "Link to be added"));
    }
    return c;
  }

  function renderJSON(url, gridId, opts) {
    var grid = document.getElementById(gridId);
    if (!grid) return Promise.resolve();
    return fetch(url)
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (items) {
        (items || []).forEach(function (item) { grid.appendChild(card(item, opts)); });
      })
      .catch(function (e) {
        grid.appendChild(el("p", "section-note", "Content failed to load (" + e.message + ")."));
      });
  }

  // Site meta
  fetch("data/site.json").then(function (r) { return r.json(); }).then(function (s) {
    var site = s.site || {};
    if (site.legalName) document.getElementById("site-kicker").textContent = site.legalName;
    if (site.tagline) document.getElementById("site-tagline").textContent = site.tagline;
    if (site.blurb) document.getElementById("site-blurb").textContent = site.blurb;
    if (site.email && !/^placeholder/.test(site.email)) {
      var em = document.getElementById("contact-email");
      var a = el("a", null, site.email); a.href = "mailto:" + site.email;
      em.textContent = ""; em.appendChild(a);
    } else {
      document.getElementById("contact-email").textContent = "Email: coming soon (set 'email' in data/site.json).";
    }
    var ul = document.getElementById("socials-list");
    (s.socials || []).forEach(function (soc) {
      var li = el("li");
      if (soc.url) {
        var a = el("a", null, soc.label);
        a.href = soc.url; a.target = "_blank"; a.rel = "noopener noreferrer";
        li.appendChild(a);
      } else {
        li.appendChild(el("span", null, soc.label + " — placeholder"));
      }
      ul.appendChild(li);
    });
    document.getElementById("footer-name").textContent = site.legalName || site.name || "";
  }).catch(function () {});

  renderJSON("data/services.json", "services-grid");
  renderJSON("data/shop.json", "shop-grid");
  renderJSON("data/opensource.json", "opensource-grid");

  document.getElementById("year").textContent = new Date().getFullYear();
})();