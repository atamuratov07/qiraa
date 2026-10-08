// reader.js: tap an Arabic word (or select a phrase) to see its Russian translation.
//
// 1. Wraps every Arabic word inside elements marked [data-tappable] in <span class="w">.
// 2. On tap/selection, calls your backend:
//      GET /api/translate?q=<word>&passage_id=<id>
//    and expects JSON like:
//      {"translation": "автобус", "source": "glossary"}     (translation may be null)
//    Until that endpoint exists, the popup says so and still offers a Google Translate link.

(() => {
  const pop = document.getElementById("tr-pop");
  if (!pop) return;
  const qEl = pop.querySelector("[data-q]");
  const aEl = pop.querySelector("[data-a]");
  const srcEl = pop.querySelector("[data-src]");
  const gLink = pop.querySelector("[data-g]");
  const ARABIC = /[؀-ۿݐ-ݿ]/;
  // splits "«الكتابُ،" into ["«", "الكتابُ", "،"]: letters + vowel marks in the middle
  const EDGES = /^([^\p{L}\p{M}]*)(.*?)([^\p{L}\p{M}]*)$/su;
  let active = null;
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

  // ---- 2. popup -------------------------------------------------------------------
  function passageIdOf(el) {
    const holder = el && el.closest("[data-passage-id]");
    return holder ? holder.dataset.passageId : "";
  }

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

  function show(answer, source, missing) {
    aEl.textContent = answer;
    aEl.classList.toggle("text-muted", missing);
    srcEl.textContent = source || "";
  }

  async function lookup(text, rect, passageId) {
    const id = ++requestId;
    qEl.textContent = text;
    show("…", "", true);
    gLink.href =
      "https://translate.google.com/?sl=ar&tl=ru&op=translate&text=" +
      encodeURIComponent(text);
    place(rect);

    try {
      const params = new URLSearchParams({ q: text });
      if (passageId) params.set("passage_id", passageId);
      const res = await fetch(`/api/translate?${params}`);
      if (id !== requestId) return; // the user already tapped something else
      if (res.status === 401) return void (location.href = "/login");
      if (res.status === 404)
        return void show("Перевод пока недоступен.", "", true);
      if (!res.ok) return void show(`Ошибка сервера (${res.status}).`, "", true);
      const data = await res.json();
      if (id !== requestId) return;
      if (data.translation) show(data.translation, data.source, false);
      else show("Перевод не найден.", "", true);
    } catch {
      if (id === requestId)
        show("Ошибка сети. Попробуйте ссылку ниже.", "", true);
    }
    place(rect);
  }

  function close() {
    pop.hidden = true;
    active?.classList.remove("on");
    active = null;
  }

  // tap one word
  document.addEventListener("click", (e) => {
    if (pop.contains(e.target)) return;
    const word = e.target.closest(".w");
    const sel = window.getSelection();
    if (word && sel.isCollapsed) {
      active?.classList.remove("on");
      active = word;
      word.classList.add("on");
      lookup(word.textContent, word.getBoundingClientRect(), passageIdOf(word));
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
      const range = sel.getRangeAt(0);
      const container = range.commonAncestorContainer;
      const el =
        container.nodeType === Node.ELEMENT_NODE
          ? container
          : container.parentElement;
      active?.classList.remove("on");
      active = null;
      lookup(text, range.getBoundingClientRect(), passageIdOf(el));
    }, 350);
  });

  document.addEventListener("keydown", (e) => e.key === "Escape" && close());
  window.addEventListener("resize", close);
})();
