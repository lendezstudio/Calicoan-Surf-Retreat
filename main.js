/* Calicoan Surf Retreat: progressive enhancements. The page is fully readable without this file. */
(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const data = JSON.parse($("#site-data").textContent);
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const focusable = 'a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])';

  /* Year */
  $$("[data-year]").forEach((el) => { el.textContent = String(new Date().getFullYear()); });

  /* Hero focal point: on wide screens, crop so the surfer stays in frame above the text */
  const heroImg = $(".hero__media img[data-focal-y]");
  const heroBox = $(".hero__media");
  const placeHero = () => {
    if (!heroImg || window.innerWidth < 700) { if (heroImg) heroImg.style.objectPosition = ""; return; }
    const w = heroBox.clientWidth;
    const h = heroBox.clientHeight;
    const ratio = heroImg.naturalWidth / heroImg.naturalHeight || 1.5;
    const rendered = w / ratio;
    const overflow = rendered - h;
    if (overflow <= 0) { heroImg.style.objectPosition = ""; return; }
    const offset = Number(heroImg.dataset.focalY) * rendered - 0.04 * h;
    const y = Math.min(1, Math.max(0, offset / overflow));
    heroImg.style.objectPosition = `62% ${(y * 100).toFixed(1)}%`;
  };
  placeHero();
  heroImg && heroImg.addEventListener("load", placeHero);
  window.addEventListener("resize", placeHero, { passive: true });

  /* Header state */
  const header = $("[data-header]");
  const onScroll = () => header.classList.toggle("is-scrolled", window.scrollY > 8);
  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });

  /* Mobile menu */
  const menu = $("[data-menu]");
  const menuOpen = $("[data-menu-open]");
  let menuReturn = null;

  function openMenu() {
    menuReturn = document.activeElement;
    menu.hidden = false;
    menuOpen.setAttribute("aria-expanded", "true");
    document.documentElement.style.overflow = "hidden";
    $("a", menu).focus();
    document.addEventListener("keydown", menuKeys);
    mobileCta.update();
  }
  function closeMenu(restoreFocus = true) {
    if (menu.hidden) return;
    menu.hidden = true;
    menuOpen.setAttribute("aria-expanded", "false");
    document.documentElement.style.overflow = "";
    document.removeEventListener("keydown", menuKeys);
    if (restoreFocus && menuReturn) menuReturn.focus();
    mobileCta.update();
  }
  function menuKeys(e) {
    if (e.key === "Escape") { e.preventDefault(); closeMenu(); return; }
    if (e.key !== "Tab") return;
    const items = $$(focusable, menu);
    const first = items[0];
    const last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }
  menuOpen.addEventListener("click", openMenu);
  $("[data-menu-close]").addEventListener("click", () => closeMenu());
  $$("a", menu).forEach((a) => a.addEventListener("click", () => closeMenu(false)));
  window.matchMedia("(min-width: 920.02px)").addEventListener("change", (e) => { if (e.matches) closeMenu(false); });

  /* Current section in the nav */
  const navLinks = $$(".site-nav a");
  if ("IntersectionObserver" in window) {
    const sections = navLinks.map((a) => $(a.getAttribute("href"))).filter(Boolean);
    const seen = new Map();
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => seen.set(en.target.id, en.isIntersecting));
      const current = sections.find((s) => seen.get(s.id));
      navLinks.forEach((a) => {
        if (current && a.getAttribute("href") === "#" + current.id) a.setAttribute("aria-current", "true");
        else a.removeAttribute("aria-current");
      });
    }, { rootMargin: "-45% 0px -50% 0px" });
    sections.forEach((s) => io.observe(s));
  }

  /* Reveal on scroll, only for elements below the first screen and only when motion is welcome */
  if (!reduceMotion.matches && "IntersectionObserver" in window) {
    const targets = $$(".section-head, .statement > *, .stay, .island__surf-copy, .island__item, .gallery__item, .film, .films__note, .about__inner > *, .plan__copy, .plan__media, .plan__tips li, .faq__list, .inquiry__intro, .composer");
    const fold = window.innerHeight;
    const below = targets.filter((el) => el.getBoundingClientRect().top > fold);
    below.forEach((el) => el.setAttribute("data-reveal", ""));
    document.documentElement.classList.add("motion-ok");
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => {
        if (!en.isIntersecting) return;
        en.target.classList.add("is-visible");
        io.unobserve(en.target);
      });
    }, { rootMargin: "0px 0px -8% 0px" });
    below.forEach((el) => io.observe(el));
  }

  /* Lightbox */
  const box = $("[data-lightbox]");
  const boxImg = $("[data-lightbox-picture] img", box);
  const boxSource = $("[data-lightbox-picture] source", box);
  const boxCaption = $("[data-lightbox-caption]", box);
  const boxCount = $("[data-lightbox-count]", box);
  const boxPrev = $("[data-lightbox-prev]", box);
  const boxNext = $("[data-lightbox-next]", box);
  let boxItems = [];
  let boxIndex = 0;
  let boxReturn = null;

  function showItem(i) {
    boxIndex = (i + boxItems.length) % boxItems.length;
    const item = boxItems[boxIndex];
    boxSource.srcset = item.avif;
    boxSource.sizes = "100vw";
    boxImg.srcset = item.jpg;
    boxImg.sizes = "100vw";
    boxImg.src = item.src;
    boxImg.width = item.width;
    boxImg.height = item.height;
    boxImg.alt = item.alt;
    boxCaption.textContent = item.caption;
    boxCount.textContent = boxItems.length > 1 ? `${boxIndex + 1} / ${boxItems.length}` : "";
  }
  function openBox(items, index, trigger) {
    if (typeof box.showModal !== "function") return;
    boxItems = items;
    boxReturn = trigger;
    boxPrev.hidden = boxNext.hidden = items.length < 2;
    showItem(index);
    box.showModal();
    document.documentElement.style.overflow = "hidden";
    $("[data-lightbox-close]", box).focus();
  }
  box.addEventListener("close", () => {
    document.documentElement.style.overflow = "";
    if (boxReturn) boxReturn.focus();
  });
  $("[data-lightbox-close]", box).addEventListener("click", () => box.close());
  boxPrev.addEventListener("click", () => showItem(boxIndex - 1));
  boxNext.addEventListener("click", () => showItem(boxIndex + 1));
  box.addEventListener("keydown", (e) => {
    if (boxItems.length < 2) return;
    if (e.key === "ArrowLeft") { e.preventDefault(); showItem(boxIndex - 1); }
    if (e.key === "ArrowRight") { e.preventDefault(); showItem(boxIndex + 1); }
  });
  box.addEventListener("click", (e) => { if (e.target === box) box.close(); });

  let touchX = null;
  const figure = $(".lightbox__figure", box);
  figure.addEventListener("pointerdown", (e) => { if (e.pointerType !== "mouse") touchX = e.clientX; });
  figure.addEventListener("pointerup", (e) => {
    if (touchX === null || boxItems.length < 2) return;
    const dx = e.clientX - touchX;
    touchX = null;
    if (Math.abs(dx) > 45) showItem(boxIndex + (dx < 0 ? 1 : -1));
  });
  figure.addEventListener("pointercancel", () => { touchX = null; });

  $$("[data-lightbox-set]").forEach((btn) => {
    btn.addEventListener("click", () => openBox(data.stays[btn.dataset.lightboxSet].photos, 0, btn));
  });

  /* Gallery filters */
  const tiles = $$(".gallery__item");
  const filterStatus = $("[data-filter-status]");
  $$("[data-filter]").forEach((btn) => {
    btn.addEventListener("click", () => {
      $$("[data-filter]").forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
      const f = btn.dataset.filter;
      let shown = 0;
      tiles.forEach((t) => {
        const match = f === "all" || t.dataset.group === f;
        t.hidden = !match;
        if (match) { shown += 1; t.classList.add("is-visible"); }
      });
      filterStatus.textContent = `Showing ${shown} photos`;
    });
  });
  $$("[data-lightbox-index]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const visible = tiles.filter((t) => !t.hidden);
      const items = visible.map((t) => data.gallery[Number($("[data-lightbox-index]", t).dataset.lightboxIndex)]);
      openBox(items, visible.indexOf(btn.closest(".gallery__item")), btn);
    });
  });

  /* Videos: open enlarged in a player when asked; never autoplay */
  const player = $("[data-player]");
  const playerVideo = $("[data-player-video]", player);
  const playerToggle = $("[data-player-toggle]", player);
  const playerLabel = $("[data-player-label]", player);
  let playerReturn = null;

  const setPlaying = (playing) => {
    playerToggle.setAttribute("aria-pressed", String(playing));
    playerLabel.textContent = playing ? "Pause video" : "Play video";
  };
  const playerMute = $("[data-player-mute]", player);
  const setMuted = (muted) => {
    playerVideo.muted = muted;
    playerMute.setAttribute("aria-pressed", String(muted));
    playerMute.textContent = muted ? "Unmute" : "Mute";
  };
  playerMute.addEventListener("click", () => setMuted(!playerVideo.muted));
  function startPlayer() {
    playerVideo.play().catch(() => {
      // Some browsers refuse sound without a fresh tap; fall back to muted playback.
      setMuted(true);
      playerVideo.play().catch(() => { playerLabel.textContent = "Video unavailable"; });
    });
  }
  function openPlayer(fig, trigger) {
    if (typeof player.showModal !== "function") return false;
    playerReturn = trigger;
    if (playerVideo.dataset.src !== fig.dataset.src) {
      playerVideo.dataset.src = fig.dataset.src;
      playerVideo.poster = fig.dataset.poster;
      playerVideo.src = fig.dataset.src;
      playerVideo.setAttribute("aria-label", fig.dataset.label);
    }
    $("[data-player-title]", player).textContent = fig.dataset.title;
    $("[data-player-caption]", player).textContent = fig.dataset.caption;
    setMuted(false);
    player.showModal();
    document.documentElement.style.overflow = "hidden";
    playerToggle.focus();
    startPlayer();
    return true;
  }
  playerToggle.addEventListener("click", () => { if (playerVideo.paused) startPlayer(); else playerVideo.pause(); });
  playerVideo.addEventListener("play", () => setPlaying(true));
  playerVideo.addEventListener("pause", () => setPlaying(false));
  playerVideo.addEventListener("click", () => playerToggle.click());
  $("[data-player-close]", player).addEventListener("click", () => player.close());
  player.addEventListener("click", (e) => { if (e.target === player) player.close(); });
  player.addEventListener("close", () => {
    playerVideo.pause();
    document.documentElement.style.overflow = "";
    if (playerReturn) playerReturn.focus();
  });

  $$("[data-film]").forEach((fig) => {
    const video = $("video", fig);
    const toggle = $("[data-film-toggle]", fig);
    video.addEventListener("click", () => toggle.click());
    toggle.addEventListener("click", () => {
      if (openPlayer(fig, toggle)) return;
      // Fallback for browsers without <dialog>: play in place.
      if (video.paused) video.play().catch(() => {}); else video.pause();
    });
  });

  /* Inquiry composer: builds a message locally. Nothing is sent or stored. */
  const form = $("[data-composer]");
  const fields = {
    arrival: $("#arrival"),
    departure: $("#departure"),
    guests: $("#guests"),
    stay: $("#stay"),
    note: $("#note"),
  };
  const messageBox = $("[data-message]");
  const status = $("[data-status]");

  const pad = (n) => String(n).padStart(2, "0");
  const localISO = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  const todayISO = () => localISO(new Date());
  const parseISO = (s) => {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
    if (!m) return null;
    const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
    return localISO(d) === s ? d : null;
  };
  const nextDayISO = (s) => {
    const d = parseISO(s);
    if (!d) return "";
    d.setDate(d.getDate() + 1);
    return localISO(d);
  };
  const dateFormat = new Intl.DateTimeFormat("en-GB", { weekday: "short", day: "numeric", month: "short", year: "numeric" });
  const friendly = (s) => { const d = parseISO(s); return d ? dateFormat.format(d) : ""; };

  function syncMins() {
    const today = todayISO();
    fields.arrival.min = today;
    fields.departure.min = nextDayISO(fields.arrival.value) || nextDayISO(today);
  }

  function message() {
    const stayName = data.stayNames[fields.stay.value] || "No preference";
    const note = fields.note.value.trim().replace(/\s+\n/g, "\n");
    const lines = [
      `Hi ${data.businessName}! I’d like to ask about a stay.`,
      `Arrival: ${friendly(fields.arrival.value)}`,
      `Departure: ${friendly(fields.departure.value)}`,
      `Guests: ${fields.guests.value.trim()}`,
      `Preferred stay: ${stayName}`,
    ];
    if (note) lines.push(`Question: ${note}`);
    lines.push("Could you share the available options, rates, inclusions and reservation terms? Thank you!");
    return lines.join("\n");
  }

  function setError(name, text) {
    const el = $(`[data-error-for="${name}"]`);
    el.textContent = text;
    if (text) fields[name].setAttribute("aria-invalid", "true");
    else fields[name].removeAttribute("aria-invalid");
  }

  function validate() {
    const today = todayISO();
    const a = fields.arrival.value;
    const d = fields.departure.value;
    const g = fields.guests.value.trim();
    const errors = {};
    if (!parseISO(a)) errors.arrival = "Choose your arrival date.";
    else if (a < today) errors.arrival = "Choose an arrival date from today onward.";
    if (!parseISO(d)) errors.departure = "Choose your departure date.";
    else if (parseISO(a) && d <= a) errors.departure = "Choose a departure date after your arrival date.";
    if (!/^\d+$/.test(g) || Number(g) < 1) errors.guests = "Enter how many guests are coming (1 or more).";
    else if (Number(g) > 30) errors.guests = "For more than 30 guests, enter 30 and mention your group size in your question.";
    ["arrival", "departure", "guests"].forEach((k) => setError(k, errors[k] || ""));
    return errors;
  }

  function refresh() {
    syncMins();
    messageBox.value = message();
    status.textContent = "";
    status.className = "composer__status";
  }

  Object.values(fields).forEach((el) => el.addEventListener("input", () => {
    refresh();
    if (el.getAttribute("aria-invalid") === "true") validate();
  }));
  fields.arrival.addEventListener("change", () => {
    if (fields.departure.value && fields.departure.value <= fields.arrival.value) validate();
  });

  async function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      try { await navigator.clipboard.writeText(text); return true; } catch (_) { /* fall through */ }
    }
    try {
      messageBox.focus();
      messageBox.select();
      return document.execCommand("copy");
    } catch (_) {
      return false;
    }
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const errors = validate();
    const firstBad = ["arrival", "departure", "guests"].find((k) => errors[k]);
    if (firstBad) {
      status.textContent = "";
      fields[firstBad].focus();
      return;
    }
    messageBox.value = message();
    const ok = await copyText(messageBox.value);
    if (ok) {
      status.textContent = "Inquiry copied. Open Facebook and paste it into your message.";
      status.className = "composer__status is-success";
    } else {
      status.textContent = "Select and copy the message below.";
      status.className = "composer__status is-error";
      messageBox.focus();
      messageBox.select();
    }
  });

  $$("a[data-stay]").forEach((a) => {
    a.addEventListener("click", () => {
      fields.stay.value = a.dataset.stay;
      refresh();
    });
  });

  refresh();

  /* Small mobile contact button: after the hero, never over the form, footer or menu */
  const mobileCta = (() => {
    const btn = $("[data-mobile-cta]");
    let pastHero = false;
    let nearForm = false;
    let typing = false;
    const update = () => btn.classList.toggle("is-shown", pastHero && !nearForm && !typing && menu.hidden);
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(([en]) => { pastHero = !en.isIntersecting; update(); }).observe($(".hero"));
      const seen = new Map();
      const io = new IntersectionObserver((entries) => {
        entries.forEach((en) => seen.set(en.target, en.isIntersecting));
        nearForm = Array.from(seen.values()).some(Boolean);
        update();
      });
      io.observe($("#inquiry"));
      io.observe($(".site-footer"));
    }
    document.addEventListener("focusin", (e) => { typing = e.target.matches("input, select, textarea"); update(); });
    document.addEventListener("focusout", () => { typing = false; update(); });
    return { update };
  })();
})();
