// reader.js: tap an Arabic word (or select a phrase) to see its translation.
//
// 1. Wraps every Arabic word inside elements marked [data-tappable] in <span class="w">.
// 2. On tap/selection, asks MyMemory from the browser:
//      GET https://api.mymemory.translated.net/get?q=<text>&langpair=ar|<language>
//    and keeps the answers for the browser session. The popup also links to Google
//    Translate. The language is the interface's until one is picked in the popup; the
//    pick stays in localStorage.

(() => {
  const pop = document.getElementById("tr-pop");
  if (!pop) return;
  const messages = JSON.parse(document.getElementById("i18n").textContent);
  const t = (key, values = {}) =>
    messages[key].replace(/\{(\w+)\}/g, (_, name) => values[name]);
  const qEl = pop.querySelector("[data-q]");
  const aEl = pop.querySelector("[data-a]");
  const gLink = pop.querySelector("[data-g]");
  const ARABIC = /[؀-ۿݐ-ݿ]/;
  // splits "«الكتابُ،" into ["«", "الكتابُ", "،"]: letters + vowel marks in the middle
  const EDGES = /^([^\p{L}\p{M}]*)(.*?)([^\p{L}\p{M}]*)$/su;
  const MYMEMORY = "https://api.mymemory.translated.net/get";
  const LANGUAGE_KEY = "qiraa.translateTo";
  const languageButtons = [...pop.querySelectorAll("[data-lang]")];
  let language = document.documentElement.lang;
  try {
    const saved = localStorage.getItem(LANGUAGE_KEY);
    if (languageButtons.some((b) => b.dataset.lang === saved)) language = saved;
  } catch {} // storage can be blocked, e.g. in a private window
  let active = null;
  let shown = null; // { text, anchor }: the text, and the word or range it came from
  let requestId = 0;

  // ---- 1. wrap words ------------------------------------------------------------
  for (const root of document.querySelectorAll("[data-tappable]")) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const textNodes = [];
    while (walker.nextNode()) textNodes.push(walker.currentNode);

    for (const node of textNodes) {
      if (!ARABIC.test(node.nodeValue)) continue;
      const frag = document.createDocumentFragment();
      for (const piece of node.nodeValue.split(/(\s+)/)) {
        if (!ARABIC.test(piece)) {
          if (piece) frag.append(piece);
          continue;
        }
        const [, before, word, after] = piece.match(EDGES);
        if (before) frag.append(before);
        const span = document.createElement("span");
        span.className = "w";
        span.textContent = word;
        frag.append(span);
        if (after) frag.append(after);
      }
      node.replaceWith(frag);
    }
  }

  // ---- 2. translation ---------------------------------------------------------------
  class QuotaSpent extends Error {}
  class Refused extends Error {} // message: MyMemory's status code

  // MyMemory answers errors with HTTP 200 too: only responseStatus tells them apart.
  // Its text comes HTML-escaped ("Sog&#39;lom").
  function answerOf(data, text) {
    const status = String(data?.responseStatus);
    if (status === "429" || data?.quotaFinished) throw new QuotaSpent();
    if (status !== "200") throw new Refused(status);
    const escaped = String(data.responseData?.translatedText ?? "");
    const answer = new DOMParser()
      .parseFromString(escaped, "text/html")
      .documentElement.textContent.trim()
      .replace(/\s*:$/, "");
    return answer && answer !== text ? answer : null;
  }

  async function translate(text, target) {
    const key = `qiraa.tr.${target}.${text}`;
    try {
      const saved = sessionStorage.getItem(key);
      if (saved !== null) return JSON.parse(saved);
    } catch {}

    const params = new URLSearchParams({ q: text, langpair: `ar|${target}` });
    const res = await fetch(`${MYMEMORY}?${params}`, {
      referrerPolicy: "no-referrer",
    });
    if (res.status === 429) throw new QuotaSpent();
    if (!res.ok) throw new Refused(String(res.status));
    const answer = answerOf(await res.json(), text);
    try {
      sessionStorage.setItem(key, JSON.stringify(answer));
    } catch {}
    return answer;
  }

  // ---- 3. popup -------------------------------------------------------------------
  function place(rect) {
    pop.hidden = false;
    const m = 8;
    const w = pop.offsetWidth;
    const h = pop.offsetHeight;
    const maxLeft =
      window.scrollX + document.documentElement.clientWidth - w - m;
    const left = Math.max(
      window.scrollX + m,
      Math.min(rect.left + rect.width / 2 - w / 2 + window.scrollX, maxLeft),
    );
    const below = rect.bottom + h + m <= window.innerHeight || rect.top < h + m;
    const top = below ? rect.bottom + m : rect.top - h - m;
    pop.style.left = `${left}px`;
    pop.style.top = `${top + window.scrollY}px`;
  }

  function show(answer, missing) {
    aEl.textContent = answer;
    aEl.classList.toggle("text-muted", missing);
  }

  async function lookup(text, anchor) {
    const id = ++requestId;
    shown = { text, anchor };
    qEl.textContent = text;
    aEl.lang = language;
    for (const b of languageButtons)
      b.setAttribute("aria-pressed", String(b.dataset.lang === language));
    show("…", true);
    const google = { sl: "ar", tl: language, op: "translate", text };
    gLink.href = `https://translate.google.com/?${new URLSearchParams(google)}`;
    place(anchor.getBoundingClientRect());

    let answer = null;
    let problem = null;
    try {
      answer = await translate(text, language);
    } catch (e) {
      if (e instanceof QuotaSpent) problem = t("quotaSpent");
      else if (e instanceof Refused)
        problem = t("serverError", { code: e.message });
      else problem = t("networkError");
    }
    if (id !== requestId) return; // the user already tapped something else
    if (problem) show(problem, true);
    else if (answer) show(answer, false);
    else show(t("noTranslation"), true);
    place(anchor.getBoundingClientRect());
  }

  function close() {
    pop.hidden = true;
    active?.classList.remove("on");
    active = null;
  }

  pop.addEventListener("click", (e) => {
    const button = e.target.closest("[data-lang]");
    if (!button || button.dataset.lang === language) return;
    language = button.dataset.lang;
    try {
      localStorage.setItem(LANGUAGE_KEY, language);
    } catch {}
    lookup(shown.text, shown.anchor);
  });

  // tap one word
  document.addEventListener("click", (e) => {
    if (pop.contains(e.target)) return;
    const word = e.target.closest(".w");
    const sel = window.getSelection();
    if (word && sel.isCollapsed) {
      active?.classList.remove("on");
      active = word;
      word.classList.add("on");
      lookup(word.textContent, word);
    } else if (sel.isCollapsed) {
      close();
    }
  });

  // select several words (mouse drag, or long-press on a phone)
  let timer;
  document.addEventListener("selectionchange", () => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      const sel = window.getSelection();
      if (sel.isCollapsed || !sel.rangeCount) return;
      const text = sel.toString().trim().replace(/\s+/g, " ");
      if (!text || text.length > 120 || !ARABIC.test(text)) return;
      active?.classList.remove("on");
      active = null;
      lookup(text, sel.getRangeAt(0).cloneRange());
    }, 350);
  });

  // Escape, and the navigator's ←/→, which show another question
  document.addEventListener("keydown", (e) => {
    if (["Escape", "ArrowLeft", "ArrowRight"].includes(e.key)) close();
  });
  window.addEventListener("resize", close);
})();
