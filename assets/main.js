// Renders all page content from /data/*.json — edit the JSON files, not this HTML.
(function () {
  "use strict";

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }

  function setMeta(attr, key, content) {
    var m = document.querySelector("meta[" + attr + '="' + key + '"]');
    if (m) m.setAttribute("content", content);
  }

  // --- signature motif: 8-facet radial rosette -------------------------------
  // 8 triangular SVG polygons fanning from center, alternating terracotta/teal
  // fills at varying opacity, thin ink strokes between facets.
  var SVG_NS = "http://www.w3.org/2000/svg";
  var ACCENTS = ["#c1613c", "#3c8f82"]; // terracotta, teal

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
    var wrap = el("div", "rosette-inner");
    wrap.style.position = "absolute";
    wrap.style.inset = "0";
    wrap.appendChild(svg);
    return wrap;
  }

  function mountRosettes() {
    document.querySelectorAll(".rosette").forEach(function (slot) {
      if (slot.querySelector("svg")) return; // idempotent
      slot.appendChild(rosette());
    });
    // footer echo (lower opacity)
    var footer = document.querySelector("footer");
    if (footer && !footer.querySelector(".rosette-echo")) {
      var echo = rosette();
      echo.classList.add("rosette-echo");
      echo.classList.remove("rosette-inner");
      echo.className = "rosette rosette-echo rosette-footer";
      footer.appendChild(echo);
    }
  }

  // --- generic card (shop / opensource) --------------------------------------
  function card(item) {
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

  // --- review card (rating stars + category chip) -----------------------------
  function reviewCard(item) {
    var c = el("article", "card" + (item.placeholder ? " placeholder" : ""));
    if (item.title) c.appendChild(el("h3", null, item.title));
    if (item.rating) {
      var stars = Math.max(1, Math.min(5, Math.round(item.rating)));
      c.appendChild(el("p", "rating", "★★★★★".slice(0, stars) + "☆☆☆☆☆".slice(0, 5 - stars)));
    }
    if (item.desc) c.appendChild(el("p", null, item.desc));
    if (item.category) {
      var meta = el("ul", "meta");
      meta.appendChild(el("li", null, item.category));
      c.appendChild(meta);
    }
    return c;
  }

  function renderJSON(url, gridId, make) {
    var grid = document.getElementById(gridId);
    if (!grid) return Promise.resolve();
    return fetch(url)
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (items) {
        (items || []).forEach(function (item) { grid.appendChild((make || card)(item)); });
      })
      .catch(function (e) {
        grid.appendChild(el("p", "section-note", "Content failed to load (" + e.message + ")."));
      });
  }

  // --- services: split by category into two columns ---------------------------
  function renderServices() {
    return fetch("data/services.json")
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (items) {
        (items || []).forEach(function (item) {
          var cat = (item.category || "painting").toLowerCase() === "labour" ? "services-labour" : "services-painting";
          var grid = document.getElementById(cat);
          if (!grid) return;
          var c = el("article", "svc" + (item.placeholder ? " placeholder" : ""));
          c.appendChild(el("h4", null, item.title));
          c.appendChild(el("p", null, item.desc));
          grid.appendChild(c);
        });
      })
      .catch(function (e) {
        var grid = document.getElementById("services-painting");
        if (grid) grid.appendChild(el("p", "section-note", "Services failed to load (" + e.message + ")."));
      });
  }

  // --- about -------------------------------------------------------------------
  function renderAbout() {
    return fetch("data/about.json")
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (d) {
        var about = d.about || {};
        var copy = document.getElementById("about-copy");
        var photo = document.getElementById("about-photo");
        if (!copy) return;
        (about.paragraphs || []).forEach(function (t) { copy.appendChild(el("p", null, t)); });
        if (photo) {
          if (about.photo) {
            var img = el("img");
            img.src = about.photo; img.alt = about.photoAlt || "";
            photo.textContent = ""; photo.appendChild(img);
          } else {
            photo.textContent = about.photoAlt || "[OWNER PHOTO]";
          }
        }
      })
      .catch(function () {
        var copy = document.getElementById("about-copy");
        if (copy) copy.appendChild(el("p", "section-note", "About content failed to load."));
      });
  }

  // --- site meta -----------------------------------------------------------------
  window.__siteEmail = "";
  fetch("data/site.json").then(function (r) { return r.json(); }).then(function (s) {
    var site = s.site || {};
    // --- SEO plumbing (task 016): keep canonical/og:url aligned with the
    // configured base URL (site.canonicalBase) or the URL the page is
    // actually served from. Static head defaults to the GitHub Pages URL.
    (function () {
      var here = window.location.origin + window.location.pathname;
      var base = (site.canonicalBase ? site.canonicalBase.replace(/\/$/, "") + "/" : here);
      var canon = document.getElementById("canonical-link");
      if (canon) canon.href = base.replace(/\/$/, "") + "/index.html";
      setMeta("property", "og:url", base);
      // If site.json gains a real metaDescription, mirror it into the head.
      if (site.metaDescription) setMeta("name", "description", site.metaDescription);
    })();
    if (site.email && !/^placeholder/.test(site.email)) window.__siteEmail = site.email;
    if (site.legalName) document.getElementById("site-kicker").textContent = site.legalName;
    if (site.tagline) document.getElementById("site-tagline").textContent = site.tagline;
    if (site.blurb) document.getElementById("site-blurb").textContent = site.blurb;
    var em = document.getElementById("contact-email");
    if (site.email && !/^placeholder/.test(site.email)) {
      var a = el("a", null, site.email); a.href = "mailto:" + site.email;
      em.textContent = "Email: "; em.appendChild(a);
    } else {
      em.textContent = "Email: coming soon (set 'email' in data/site.json).";
    }
    var ph = document.getElementById("contact-phone");
    if (ph) {
      if (site.phone) {
        var pa = el("a", null, site.phone);
        pa.href = "tel:" + String(site.phone).replace(/[^+\\d]/g, "");
        ph.textContent = ""; ph.appendChild(pa);
        if (site.phoneNote) {
          var note = el("span", "phone-note", "(" + site.phoneNote + ")");
          ph.appendChild(note);
        }
      } else {
        ph.textContent = "";
      }
    }
    var ad = document.getElementById("contact-address");
    if (ad) {
      if (site.address && site.address.street) {
        ad.textContent = site.address.street + ", " + site.address.city + ", "
          + site.address.region + (site.address.postalCode ? " " + site.address.postalCode : "")
          + ", " + site.address.country;
      } else {
        ad.textContent = "";
      }
    }
    var ul = document.getElementById("socials-list");
    (s.socials || []).forEach(function (soc) {
      var li = el("li");
      if (soc.url) {
        var link = el("a", null, soc.label);
        link.href = soc.url; link.target = "_blank"; link.rel = "noopener noreferrer";
        li.appendChild(link);
      } else {
        li.appendChild(el("span", null, soc.label + " — placeholder"));
      }
      ul.appendChild(li);
    });
    document.getElementById("footer-name").textContent = site.legalName || site.name || "";
  }).catch(function () {});

  // --- contact form: real backend if configured, else mailto fallback -------------
  (function setupForm() {
    var form = document.getElementById("contact-form");
    var note = document.getElementById("contact-form-note");
    if (!form) return;

    // Client-side lead tier (task 015). Computed from qualifying-flow answers and
    // submitted as a hidden field so it arrives in the owner's inbox for triage.
    // Never surfaced in the UI.
    function computeLeadTier() {
      var fd = new FormData(form);
      var property = fd.get("property_status") || "";
      var timeline = fd.get("timeline") || "";
      var hasSignal =
        (form.elements["photos"] && form.elements["photos"].files && form.elements["photos"].files.length > 0) ||
        fd.get("heard_about") === "referral" ||
        !!(fd.get("budget") || "").trim();
      if (property === "own" && timeline !== "ideas" && hasSignal) return "hot";
      if (property === "rent_approved" || property === "manager") return "warm";
      if (property === "own" || property === "rent_approved" || property === "manager") return "warm"; // e.g. "gathering ideas" but real answers
      if (property === "rent_unapproved") return "filtered";
      if (timeline === "ideas") return "filtered";
      return "warm";
    }

    function stampTier() {
      var hidden = document.getElementById("lead-tier");
      if (hidden) hidden.value = computeLeadTier();
    }
    // capture-phase listener: stamps the tier before the mailto/POST handlers run.
    form.addEventListener("submit", stampTier, true);

    var configured = form.getAttribute("action") || "";
    if (/OWNER_FORM_ID/.test(configured)) {
      // No form backend configured: intercept submit and hand off to mail client.
      form.addEventListener("submit", function (ev) {
        ev.preventDefault();
        var site = window.__siteEmail || "";
        var fd = new FormData(form);
        var lines = [
          "Name: " + (fd.get("name") || ""),
          "Heard about us: " + (fd.get("heard_about") || "(not said)"),
          "",
          "Project: " + (fd.get("project") || ""),
          "",
          "Property: " + (fd.get("property_status") || ""),
          "Timeline: " + (fd.get("timeline") || ""),
          "Budget: " + (fd.get("budget") || "(not said)"),
          "Contact via: " + (fd.get("contact_preference") || "email") + (fd.get("phone") ? " — " + fd.get("phone") : ""),
          "Lead tier: " + (document.getElementById("lead-tier") || {}).value || "",
          ""
        ];
        var body = encodeURIComponent(lines.join("\n"));
        var subject = encodeURIComponent("Website enquiry from " + (fd.get("name") || "someone"));
        window.location.href = site
          ? "mailto:" + site + "?subject=" + subject + "&body=" + body
          : "mailto:?subject=" + subject + "&body=" + body;
        var status = document.getElementById("form-status");
        if (status) {
          status.hidden = false;
          status.textContent = site
            ? "Thanks — I'll be in touch soon. (Owner: no form backend configured yet, so this opened your email client.)"
            : "Thanks — I'll be in touch soon. (Owner: set 'email' in data/site.json and/or add a Formspree form id.)";
        }
      });
      if (note) note.textContent = "Form backend not configured yet — this form opens your email client instead. (Owner: create a free Formspree form and put its id into the form action in index.html.)";
    } else {
      if (note) note.hidden = true;
      form.addEventListener("submit", function (ev) {
        ev.preventDefault();
        var status = document.getElementById("form-status");
        fetch(form.action, {
          method: "POST", body: new FormData(form),
          headers: { "Accept": "application/json" }
        }).then(function (r) {
          if (status) { status.hidden = false; status.textContent = r.ok ? "Thanks — I'll be in touch soon." : "Sending failed (" + r.status + ") — please email directly."; }
          if (r.ok) form.reset();
        }).catch(function () {
          if (status) { status.hidden = false; status.textContent = "Network error — please email directly."; }
        });
      });
    }
  })();

  renderJSON("data/shop.json", "shop-grid");
  renderJSON("data/opensource.json", "opensource-grid");
  renderJSON("data/reviews.json", "reviews-grid", reviewCard);
  renderServices();
  renderAbout();
  mountRosettes();

  document.getElementById("year").textContent = new Date().getFullYear();
})();