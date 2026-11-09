// Optional polish shared by every page: reveals, sticky-nav shadow, scrollspy, hero parallax.
(function () {
  "use strict";
  // --- motion: scroll reveals, sticky-nav shadow, scrollspy, hero parallax ------------------
  // Everything here is optional polish: if IntersectionObserver is missing or the visitor asks for
  // reduced motion, nothing is hidden and nothing moves.
  (function setupMotion() {
    var root = document.documentElement;
    var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var nav = document.querySelector(".nav");
    if (nav && window.addEventListener) {
      var onScroll = function () { nav.classList.toggle("scrolled", window.scrollY > 8); };
      window.addEventListener("scroll", onScroll, { passive: true });
      onScroll();
    }
    if (reduce || !root || typeof IntersectionObserver === "undefined" || !document.body.querySelectorAll) return;

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        var t = en.target;
        t.classList.add("in");
        io.unobserve(t);
        var done = function (ev) {
          if (ev.propertyName !== "opacity") return;
          t.removeEventListener("transitionend", done);
          t.classList.remove("reveal", "in");
          t.style.removeProperty("--d");
        };
        t.addEventListener("transitionend", done);
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });

    var SEL = ".section > .eyebrow, .section > h2, .section > p, .svc-card, .steps li, .card, .store-more, .faq-item, .about, .find-card, .map-frame, .contact-form, .contact-tile, .estimator > *";
    function watch(scope) {
      var nodes = scope.querySelectorAll(SEL);
      var seen = new Map();
      [].forEach.call(nodes, function (n) {
        if (n.dataset.rv) return;
        n.dataset.rv = "1";
        var par = n.parentNode, k = seen.get(par) || 0;
        seen.set(par, k + 1);
        n.style.setProperty("--d", Math.min(k, 6) * 70 + "ms");
        n.classList.add("reveal");
        io.observe(n);
      });
    }
    root.classList.add("js-reveal");
    var main = document.querySelector("main");
    if (main) {
      watch(main);
      if (typeof MutationObserver !== "undefined") {
        new MutationObserver(function () { watch(main); }).observe(main, { childList: true, subtree: true });
      }
    }

    var links = [].slice.call(document.querySelectorAll('.nav-links a[href^="#"]'));
    if (links.length) {
      var spy = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (!en.isIntersecting) return;
          links.forEach(function (a) { a.setAttribute("aria-current", a.getAttribute("href") === "#" + en.target.id ? "true" : "false"); });
        });
      }, { rootMargin: "-45% 0px -50% 0px" });
      links.forEach(function (a) {
        var sec = document.getElementById(a.getAttribute("href").slice(1));
        if (sec) spy.observe(sec);
      });
    }

    var photo = document.querySelector(".hero-photo img");
    if (photo && window.requestAnimationFrame) {
      var ticking = false;
      window.addEventListener("scroll", function () {
        if (ticking || window.scrollY > 900) return;
        ticking = true;
        window.requestAnimationFrame(function () {
          photo.style.setProperty("--par", Math.round(window.scrollY * 0.08) + "px");
          ticking = false;
        });
      }, { passive: true });
    }
  })();
})();
