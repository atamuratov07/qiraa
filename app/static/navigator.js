// navigator.js: one question at a time on the attempt page (practice/_attempt.html).
//
// Without scripts the page is a plain list and the grid's links scroll to #q1, #q2...
// This Alpine component shows the question named in the URL, flags questions, and runs
// the bar at the bottom of the screen: previous/next, the grid it opens, "Check answers".
// It keeps the grid's answered numbers current. attempt.js saves the answers; the two
// share nothing but the radios and the form.
//
// Keys (not while typing in a text field, nor with Ctrl, Alt or Meta):
//   ←/→   previous/next question, in the interface's direction
//   1–6   pick that option. click(), not checked = true: only a click fires "change",
//         which attempt.js saves on.
//   F     flag the question
// On a focused radio the browser's own arrow keys would pick another option (in a
// right-to-left question, the previous one), so ←/→ cancel that.
//
// Flags stay in this browser (localStorage, per attempt); the forms that submit or
// discard the attempt remove them (data-forget, forms.js).
//
// "Check answers", and → on the last question, open a review (the grid and the unanswered
// count) instead of submitting; the review's own button submits. Cancelling the first button's click means
// no submit event at all, so attempt.js only sees the real one.
document.addEventListener("alpine:init", () => {
  Alpine.data("attemptNavigator", () => ({
    current: 0,
    total: 0,
    answered: [], // question ids
    flagged: [], // question ids
    reviewing: false,
    gridOpen: false,
    submitting: false,

    init() {
      this.flagsKey = `qiraa.flags.${document.getElementById("attempt-root").dataset.attemptId}`;
      const steps = this.steps();
      this.total = steps.length;
      this.answered = steps
        .filter((step) => step.querySelector("input[type=radio]:checked"))
        .map((step) => Number(step.dataset.questionId));
      this.current = this.fromHash() ?? 0;
      try {
        const ids = steps.map((step) => Number(step.dataset.questionId));
        const saved = JSON.parse(localStorage.getItem(this.flagsKey) ?? "[]");
        this.flagged = saved.filter((id) => ids.includes(id));
      } catch {} // storage can be blocked, e.g. in a private window

      this.$el.addEventListener("change", (e) => {
        if (e.target.type !== "radio") return;
        const id = Number(e.target.closest("[data-step]").dataset.questionId);
        if (!this.answered.includes(id)) this.answered.push(id);
      });
      this.$el.addEventListener("submit", (e) => {
        if (!e.defaultPrevented) this.submitting = true;
      });
      window.addEventListener("hashchange", () => {
        const index = this.fromHash();
        if (index !== null) this.current = index;
      });
    },

    steps() {
      return [...this.$root.querySelectorAll("[data-step]")];
    },
    fromHash() {
      const match = location.hash.match(/^#q(\d+)$/);
      const index = match ? Number(match[1]) - 1 : -1;
      return index >= 0 && index < this.total ? index : null;
    },

    currentId() {
      return Number(this.steps()[this.current].dataset.questionId);
    },
    toggleFlag(id = this.currentId()) {
      this.flagged = this.flagged.includes(id)
        ? this.flagged.filter((other) => other !== id)
        : [...this.flagged, id];
      try {
        localStorage.setItem(this.flagsKey, JSON.stringify(this.flagged));
      } catch {}
    },

    go(index) {
      if (index < 0 || index >= this.total) return;
      this.reviewing = false;
      this.gridOpen = false;
      this.current = index;
      history.replaceState(null, "", `#q${index + 1}`);
      this.$nextTick(() => {
        if (this.$root.getBoundingClientRect().top < 0)
          this.$root.scrollIntoView();
      });
    },
    next() {
      if (this.current === this.total - 1) this.openReview();
      else this.go(this.current + 1);
    },
    prev() {
      this.go(this.current - 1);
    },

    review(e) {
      e.preventDefault(); // a submit button's click would submit
      this.openReview();
    },
    openReview() {
      this.gridOpen = false;
      this.reviewing = true;
      this.$nextTick(() => this.$refs.confirm.focus());
    },

    key(e) {
      if (this.reviewing || e.ctrlKey || e.altKey || e.metaKey) return;
      if (e.target.matches("textarea, select, input:not([type=radio])")) return;
      if (document.getElementById("attempt-content").inert) return; // paused

      if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
        e.preventDefault();
        if (e.key === "ArrowRight") this.next();
        else this.prev();
        return;
      }
      if (e.code === "KeyF") {
        this.toggleFlag();
        return;
      }
      const digit = e.code.match(/^(?:Digit|Numpad)([1-9])$/);
      if (digit) {
        const options =
          this.steps()[this.current].querySelectorAll("input[type=radio]");
        options[Number(digit[1]) - 1]?.click();
      }
    },
  }));
});
