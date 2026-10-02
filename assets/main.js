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
  var ACCENTS = ["#c86e3c", "#3c9482"]; // terracotta, teal (task 031: synced with style.css tokens for 4.5:1 contrast)

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

  // --- testimonial card (customer quote; distinct from product reviews) -------
  function testimonialCard(item) {
    var c = el("blockquote", "card testimonial" + (item.placeholder ? " placeholder" : ""));
    if (item.quote) {
      var q = el("p", "quote", item.quote);
      q.setAttribute("cite", item.id || "testimonial");
      c.appendChild(q);
    }
    var footer = el("footer", null);
    footer.appendChild(el("strong", null, item.author || "Customer"));
    if (item.date) footer.appendChild(el("span", "meta-date", " — " + item.date));
    c.appendChild(footer);
    if (item.rating) {
      var stars = Math.max(1, Math.min(5, Math.round(item.rating)));
      c.appendChild(el("p", "rating", "★★★★★".slice(0, stars) + "☆☆☆☆☆".slice(0, 5 - stars)));
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

  // --- get-ready checklist (task 036 lead magnet) ---------------------------
  // Revealed right after the visitor submits the quote form. Data:
  // data/lead_magnet.json — the same source of truth for
  // scripts/gen_autoreply_email.py (auto-reply email body). PLACEHOLDER-
  // flagged items are shown with an honest "(confirm before we start)" note,
  // never silently. No response-time promises anywhere (tasks 015/030).
  (function setupGetReady() {
    var box = document.getElementById("get-ready");
    var list = document.getElementById("get-ready-list");
    var note = document.getElementById("get-ready-note");
    if (!box || !list) return;
    fetch("data/lead_magnet.json")
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (data) {
        var items = data.checklist || [];
        var els = {};
        items.filter(function (it) { return !it.placeholder; })
             .forEach(function (it, i) {
               var li = el("li");
               var title = el("strong", null, it.title || "");
               li.appendChild(title);
               if (it.detail) {
                 li.appendChild(document.createElement("br"));
                 li.appendChild(el("span", null, it.detail));
               }
               list.appendChild(li);
               els[it.id] = { title: title, detail: it.detail || "" };
             });
        // closing note is the honesty block — always shown, never a promise
        if (note) note.textContent = data.closing_note || "";
        // capture: placeholder items are omitted here but surfaced as
        // "(confirm before we start)" annotations in the email generator.
        window.__getReadyItems = els;
      })
      .catch(function () {
        // data fetch failure: leave block hidden (site stays functional, no
        // broken get-ready shell)
      });
    document.getElementById("contact-form").addEventListener("submit", function () {
      box.hidden = false;
    }, true);
  })();

  // --- FAQ: Q&A list from data/faq.json + FAQPage JSON-LD ---------------------
  function renderFAQ() {
    var list = document.getElementById("faq-list");
    if (!list) return Promise.resolve();
    return fetch("data/faq.json")
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (data) {
        var items = data.faq || [];
        var ld = {
          "@context": "https://schema.org",
          "@type": "FAQPage",
          "mainEntity": items.map(function (item) {
            return {
              "@type": "Question",
              "name": item.q,
              "acceptedAnswer": { "@type": "Answer", "text": item.a }
            };
          })
        };
        var script = document.createElement("script");
        script.type = "application/ld+json";
        script.textContent = JSON.stringify(ld);
        document.head.appendChild(script);
        items.forEach(function (item) {
          var qa = el("div", "faq-item");
          var h = el("h3", null, item.q);
          var p = el("p", null, item.a);
          qa.appendChild(h);
          qa.appendChild(p);
          list.appendChild(qa);
        });
      })
      .catch(function (e) {
        list.appendChild(el("p", "section-note", "Content failed to load (" + e.message + ")."));
      });
  }

  // --- testimonials: quotes from data/testimonials.json + schema.org Review ---
  // JSON-LD policy: only REAL reviews (placeholder !== true) get Review markup.
  // Placeholder star ratings are never emitted as structured data — Google
  // penalises self-serving/placeholder review stars (see task 025).
  function renderTestimonials() {
    var grid = document.getElementById("testimonials-grid");
    if (!grid) return Promise.resolve();
    return fetch("data/testimonials.json")
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (items) {
        (items || []).forEach(function (item) { grid.appendChild(testimonialCard(item)); });
        var ld = {
          "@context": "https://schema.org",
          "@type": "ItemList",
          "itemListElement": (items || []).filter(function (i) { return i.placeholder !== true; })
            .map(function (i, n) {
              var rev = {
                "@type": "Review",
                "author": { "@type": "Person", "name": i.author || "Customer" },
                "reviewBody": i.quote || ""
              };
              if (i.rating) {
                rev.reviewRating = { "@type": "Rating", "ratingValue": String(Math.round(i.rating)), "bestRating": "5", "worstRating": "1" };
              }
              if (i.date) rev.datePublished = i.date;
              return { "@type": "ListItem", "position": n + 1, "item": rev };
            })
        };
        if (ld.itemListElement.length) {
          var script = document.createElement("script");
          script.type = "application/ld+json";
          script.id = "testimonials-jsonld";
          script.textContent = JSON.stringify(ld);
          document.head.appendChild(script);
        }
      })
      .catch(function (e) {
        grid.appendChild(el("p", "section-note", "Testimonials failed to load (" + e.message + ")."));
      });
  }

  // --- before/after gallery: photo pairs from data/gallery.json ----------------
  // Photos arrive later (owner supplies pairs into assets/gallery/). Entries
  // are shown only when both image files actually load: img.onerror removes
  // broken/placeholder entries so the live site never shows broken-image
  // icons, and if nothing renders a single muted note line replaces the grid.
  var GALLERY_SIDES = ["before", "after"];

  // Pure: an entry is displayable only with a src for BOTH sides. (Whether the
  // src file exists is checked at runtime by img.onerror in renderGallery.)
  function galleryRenderable(item) {
    return !!item && GALLERY_SIDES.every(function (w) {
      return !!(item[w] && typeof item[w].src === "string" && item[w].src.length);
    });
  }

  function galleryCard(item) {
    var c = el("article", "card gallery-card" + (item.placeholder ? " placeholder" : ""));
    if (item.title) c.appendChild(el("h3", null, item.title));
    var pair = el("div", "gallery-pair");
    GALLERY_SIDES.forEach(function (which) {
      var fig = el("figure", "gallery-side");
      var img = el("img", "gallery-img");
      img.src = item[which].src;
      img.alt = item[which].alt || "";
      img.loading = "lazy";
      img.onerror = function () {
        img.onerror = null;
        if (c.parentNode) c.parentNode.removeChild(c); // hide broken entry
      };
      fig.appendChild(img);
      fig.appendChild(el("figcaption", "gallery-chip gallery-chip-" + which, which.toUpperCase()));
      pair.appendChild(fig);
    });
    c.appendChild(pair);
    if (item.caption) c.appendChild(el("p", "gallery-caption", item.caption));
    if (item.location || item.year) {
      var meta = el("ul", "meta");
      if (item.location) meta.appendChild(el("li", null, item.location));
      if (item.year) meta.appendChild(el("li", null, String(item.year)));
      c.appendChild(meta);
    }
    return c;
  }

  function renderGallery() {
    var grid = document.getElementById("gallery-grid");
    if (!grid) return Promise.resolve();
    return fetch("data/gallery.json")
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (items) {
        var renderable = (items || []).filter(galleryRenderable);
        renderable.forEach(function (item) { grid.appendChild(galleryCard(item)); });
        // Settle counting: the empty-state note waits until every remaining
        // image has either loaded or errored (broken card removal included).
        var cards = [].slice.call(grid.querySelectorAll(".gallery-card"));
        var pending = cards.length;
        var settled = function () {
          pending -= 1;
          if (pending > 0) return;
          if (!grid.querySelectorAll(".gallery-card").length) {
            grid.appendChild(el("p", "section-note gallery-empty",
              "Before & after photos coming soon — real job pairs will appear here."));
          }
        };
        if (!pending) { settled(); return; }
        cards.forEach(function (c) {
          [].slice.call(c.querySelectorAll("img")).forEach(function (img) {
            img.addEventListener("load", settled);
            img.addEventListener("error", settled);
          });
        });
      })
      .catch(function (e) {
        grid.appendChild(el("p", "section-note", "Before & after failed to load (" + e.message + ")."));
      });
  }

  // --- seasonal promo strip (data/promo-calendar.json, picks current season) --
  function renderPromoStrip() {
    var strip = document.getElementById("promo-strip");
    if (!strip) return Promise.resolve();
    return fetch("data/promo-calendar.json")
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (cal) {
        var m = new Date().getMonth() + 1; // 1-12
        var cur = (cal.seasons || []).filter(function (s) {
          return (s.months || []).indexOf(m) !== -1;
        })[0];
        if (cur && cur.promo_copy) {
          strip.textContent = cur.promo_copy;
          strip.hidden = false;
        }
      })
      .catch(function () { /* silent: promo strip is optional garnish */ });
  }

  // --- paint-quote estimator (task 034 / roadmap 25) --------------------------
  // Customer-facing estimate widget. Formulas MIRROR scripts/quote_estimator.py
  // (single source of truth — do not fork the math); rates come from
  // data/pricing.json (placeholder EDIT-ME until Chris sets real production
  // rates). Deterministic only: no fetches at compute time, no backend.
  // Pure helpers are copied into scripts/test_estimator_logic.js for node-side
  // parity tests against the CLI itself (fixtures generated by
  // scripts/gen_estimator_fixtures.py at test time).
  function parseRoomSize(str) {
    var m = /^(\d+(?:\.\d+)?)\s*[xX]\s*(\d+(?:\.\d+)?)$/.exec((str || "").trim());
    if (!m) return null;
    var w = parseFloat(m[1]), l = parseFloat(m[2]);
    if (!(w > 0) || !(l > 0)) return null;
    return { w: w, l: l };
  }

  function estimatorRates(rates) {
    // clamp every rate to a finite positive number, else fall back to CLI DEFAULTS
    var def = {
      labour_rate: 55.0, coats_standard: 2, roller_sqft_hr: 150.0,
      cutin_hr_per_room: 1.5, prep_hr_per_room: 2.5, repair_hr_per_pop: 0.25,
      height_9ft_factor: 1.3, exterior_sqft_hr: 100.0,
      paint_cost_wall_gal: 75.0, gal_coverage_sqft: 350.0
    };
    var out = {};
    Object.keys(def).forEach(function (k) {
      var v = rates ? rates[k] : undefined;
      out[k] = (typeof v === "number" && isFinite(v) && v > 0) ? v : def[k];
    });
    return out;
  }

  // Same math as quote_estimator.interior().
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

  // Same math as quote_estimator.exterior() (incl. the 1.2 exterior paint premium).
  function estimateExterior(sqft, rates, coats) {
    var r = estimatorRates(rates);
    var area = parseInt(sqft, 10);
    if (!(area > 0)) area = 0;
    var nCoats = parseInt(coats, 10) || r.coats_standard;
    var labourHr = area / r.exterior_sqft_hr * nCoats;
    var gal = area * nCoats / r.gal_coverage_sqft;
    var paintCost = gal * r.paint_cost_wall_gal * 1.2; // exterior typically pricier
    var labourCost = labourHr * r.labour_rate;
    return {
      mode: "exterior", siding_sqft: area,
      labour_hours: round1(labourHr), labour_cost: round2(labourCost),
      paint_gallons: round1(gal), paint_cost: round2(paintCost),
      total_range: [Math.round((labourCost + paintCost) * 0.9),
                    Math.round((labourCost + paintCost) * 1.15)]
    };
  }

  function round1(x) { return Math.round(x * 10) / 10; }
  function round2(x) { return Math.round(x * 100) / 100; }

  function readEstimatorInputs() {
    var mode = document.querySelector('input[name="est-mode"]:checked');
    mode = (mode && mode.value === "exterior") ? "exterior" : "interior";
    var size = parseRoomSize(document.getElementById("est-size").value);
    return {
      mode: mode,
      rooms: document.getElementById("est-rooms").value,
      sizeW: size ? size.w : 12,
      sizeL: size ? size.l : 14,
      height: document.getElementById("est-height").value,
      repairs: document.getElementById("est-repairs").value,
      sqft: document.getElementById("est-sqft").value
    };
  }

  function computeEstimate(inputs, rates) {
    if (inputs.mode === "exterior") return estimateExterior(inputs.sqft, rates);
    return estimateInterior(inputs.rooms, inputs.sizeW, inputs.sizeL,
                            inputs.height, inputs.repairs, rates);
  }

  function renderEstimator() {
    var outBox = document.getElementById("est-out");
    var calcBtn = document.getElementById("est-calc");
    var modeRadios = document.querySelectorAll('input[name="est-mode"]');
    if (!outBox || !calcBtn || !modeRadios.length) return;

    // mode switching: toggle field groups
    function syncMode() {
      var m = document.querySelector('input[name="est-mode"]:checked');
      var ext = !!(m && m.value === "exterior");
      document.getElementById("est-interior-fields").hidden = ext;
      document.getElementById("est-exterior-fields").hidden = !ext;
    }
    [].slice.call(modeRadios).forEach(function (radio) {
      radio.addEventListener("change", syncMode);
    });

    function money(x) { return "$" + Math.round(x).toLocaleString("en-CA"); }
    function run() {
      var inputs = readEstimatorInputs();
      var rates = null; // data/pricing.json is fetched once below and cached
      var result = computeEstimate(inputs, window.__estimatorRates || rates);
      outBox.hidden = false;
      document.getElementById("est-range").innerHTML = "";
      document.getElementById("est-range").appendChild(el("strong", null,
        money(result.total_range[0]) + " – " + money(result.total_range[1])));
      var lines = document.getElementById("est-lines");
      lines.innerHTML = "";
      [["Labour", result.labour_hours + " hrs · " + money(result.labour_cost)],
       ["Paint", result.paint_gallons + " gal · " + money(result.paint_cost)]
      ].forEach(function (pair) {
        var dt = document.createElement("dt"); dt.textContent = pair[0];
        var dd = document.createElement("dd"); dd.textContent = pair[1];
        lines.appendChild(dt); lines.appendChild(dd);
      });
      var range = outBox.querySelector(".est-range");
      if (range) {
        var note = el("span", "est-range-note",
          " labour + paint, typical range");
        range.appendChild(note);
      }
      // hard guard: estimate language must always be present
      document.getElementById("est-disclaimer").hidden = false;
    }
    calcBtn.addEventListener("click", run);

    // rates: fetch once up front (NOT at compute time — still deterministic),
    // cached on window for the test harness and reused for every run().
    fetch("data/pricing.json")
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) { window.__estimatorRates = (d && d.rates) || null; })
      .catch(function () { window.__estimatorRates = null; });
  }
  // expose estimator pure helpers for scripts/test_estimator_logic.js (mirror test)
  window.__estimatorPure = {
    parseRoomSize: parseRoomSize,
    estimatorRates: estimatorRates,
    estimateInterior: estimateInterior,
    estimateExterior: estimateExterior
  };

  renderJSON("data/shop.json", "shop-grid");
  renderJSON("data/opensource.json", "opensource-grid");
  renderJSON("data/reviews.json", "reviews-grid", reviewCard);
  renderTestimonials();
  renderGallery();
  renderEstimator();
  renderServices();
  renderAbout();
  renderFAQ();
  renderPromoStrip();
  mountRosettes();

  document.getElementById("year").textContent = new Date().getFullYear();
})();