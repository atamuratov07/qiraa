// attempt.js: timer, pause/resume, autosave and the submit check for an unfinished attempt.
//
// Server endpoints it calls:
//   POST /api/attempts/{id}/heartbeat               -> 200 {"elapsed_seconds": 192}
//   PUT  /api/attempts/{id}/answers/{question_id}   body {"option_id": 45} -> 204
// Both should answer 409 if the attempt is already submitted and 404 if it was discarded
// (or belongs to someone else). This script then reloads / leaves the page.
//
// Timer rule, which the server must apply on every heartbeat (and once more on submit):
//   gap = now - last_seen_at
//   if gap <= 30 s: elapsed_seconds += gap      (the user was here)
//   last_seen_at = now                          (a longer gap = they were away: add nothing)
// So the server owns the time; this script only displays it and sends the beats.

(() => {
  const root = document.getElementById("attempt-root");
  if (!root) return;

  const id = root.dataset.attemptId;
  const total = Number(root.dataset.total);
  const HEARTBEAT_MS = 15_000; // must be well under the server's 30 s gap limit
  const AWAY_MS = 30_000; // tab hidden longer than this -> show the paused card

  const content = document.getElementById("attempt-content");
  const overlay = document.getElementById("pause-overlay");
  const resumeBtn = overlay.querySelector("[data-resume]");
  const form = document.getElementById("answers-form");
  const statusEl = form.querySelector("[data-save-status]");
  const submitBtn = form.querySelector("[data-submit]");
  const timerBox = document.getElementById("timer");
  const timeEl = timerBox.querySelector("[data-time]");
  const toggleBtn = timerBox.querySelector("[data-toggle]");
  const heartbeatUrl = `/api/attempts/${id}/heartbeat`;

  // ---- timer ----------------------------------------------------------------------
  let base = Number(root.dataset.elapsed) || 0; // seconds last confirmed by the server
  let runningSince = null; // performance.now() when the clock last started, null if stopped
  let beat = null;

  const fmt = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
  const seconds = () =>
    Math.floor(
      base +
        (runningSince === null ? 0 : (performance.now() - runningSince) / 1000),
    );

  function render() {
    const text = fmt(seconds());
    timeEl.textContent = text;
    overlay.querySelector("[data-pause-time]").textContent = text;
  }
  setInterval(render, 1000);

  async function heartbeat() {
    try {
      const res = await fetch(heartbeatUrl, { method: "POST" });
      if (handleGone(res) || !res.ok) return;
      const data = await res.json();
      base = data.elapsed_seconds;
      if (runningSince !== null) runningSince = performance.now();
      render();
    } catch {
      // offline: keep counting locally; the server only counts gaps <= 30 s anyway
    }
  }

  function start() {
    if (runningSince !== null) return;
    runningSince = performance.now();
    heartbeat(); // after a long absence this beat adds nothing; it marks "I'm back"
    beat = setInterval(heartbeat, HEARTBEAT_MS);
  }

  function stop() {
    if (runningSince === null) return false;
    base = seconds();
    runningSince = null;
    clearInterval(beat);
    // one last beat so the seconds since the previous one are counted.
    // sendBeacon still gets delivered while the tab is being hidden or closed.
    navigator.sendBeacon(heartbeatUrl);
    render();
    return true;
  }

  // ---- pause / resume -------------------------------------------------------------
  function pause() {
    stop();
    content.inert = true; // nothing behind the blur can be clicked or focused
    overlay.hidden = false;
    document.getElementById("tr-pop")?.setAttribute("hidden", "");
    resumeBtn.focus();
  }

  function resume() {
    overlay.hidden = true;
    content.inert = false;
    start();
  }
  resumeBtn.addEventListener("click", resume);

  let hiddenAt = null;
  let wasRunning = false;
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") {
      hiddenAt = performance.now();
      wasRunning = stop();
    } else if (hiddenAt !== null) {
      const away = performance.now() - hiddenAt;
      hiddenAt = null;
      if (!wasRunning) return;
      if (away > AWAY_MS) pause();
      else start();
    }
  });

  // ---- hide/show the timer ----
  const STORAGE_KEY = "qiraa.timerHidden";
  function setTimerHidden(hidden) {
    timeEl.hidden = hidden;
    toggleBtn.textContent = hidden ? "show" : "hide";
    toggleBtn.title = hidden ? "Show timer" : "Hide timer";
    try {
      localStorage.setItem(STORAGE_KEY, hidden ? "1" : "0");
    } catch {}
  }
  toggleBtn.addEventListener("click", () => setTimerHidden(!timeEl.hidden));
  try {
    if (localStorage.getItem(STORAGE_KEY) === "1") setTimerHidden(true);
  } catch {}

  // ---- autosave every pick ----------------------------------------------------------
  const answered = () =>
    form.querySelectorAll("input[type=radio]:checked").length;
  function setStatus(text, bad = false) {
    statusEl.textContent = `${answered()} of ${total} answered · ${text}`;
    statusEl.classList.toggle("text-bad", bad);
    statusEl.classList.toggle("text-muted", !bad);
    overlay.querySelector("[data-answered]").textContent = answered();
  }

  let saveId = 0;
  form.addEventListener("change", async (e) => {
    const input = e.target;
    if (input.type !== "radio") return;
    const questionId = input.closest("[data-question-id]").dataset.questionId;
    const mine = ++saveId;
    setStatus("saving…");
    try {
      const res = await fetch(`/api/attempts/${id}/answers/${questionId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ option_id: Number(input.value) }),
      });
      if (handleGone(res) || mine !== saveId) return;
      if (res.ok) setStatus("saved");
      else
        setStatus(
          `not saved (${res.status}); it will be sent when you submit`,
          true,
        );
    } catch {
      if (mine === saveId)
        setStatus("offline: not saved; it will be sent when you submit", true);
    }
  });

  // ---- submit -------------------------------------------------------------------------
  form.addEventListener("submit", (e) => {
    const missing = total - answered();
    if (missing > 0) {
      const ok = confirm(
        `${missing} question${missing === 1 ? " is" : "s are"} not answered. Submit anyway?`,
      );
      if (!ok) return e.preventDefault();
    }
    clearInterval(beat); // the submit route does the final time calculation itself
    submitBtn.disabled = true; // no double submit
    submitBtn.textContent = "Checking…";
  });

  // ---- the attempt changed elsewhere (another tab, another device) --------------------
  function handleGone(res) {
    if (res.status === 409)
      location.reload(); // submitted: reloading shows the result
    else if (res.status === 404)
      location.href = "/passages"; // discarded
    else if (res.status === 401) location.href = "/login";
    else return false;
    return true;
  }

  // ---- go ---------------------------------------------------------------------------------
  if (root.dataset.paused === "true") resumeBtn.focus();
  else start();
})();
