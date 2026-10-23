// The passage editor (passages/editor.html). Alpine keeps the passage while it is edited;
// on submit it goes into the hidden "passage" field as JSON in the shape PassageIn reads.
// Questions, options and glossary rows carry a key, so x-for keeps each input in its
// place, and the correct option is remembered by key: removing option A must not move
// the answer from B to C.
const LETTERS = "ABCDEF";

document.addEventListener("alpine:init", () => {
  Alpine.data("passageEditor", () => {
    const page = JSON.parse(document.getElementById("editor-data").textContent);
    const i18n = JSON.parse(document.getElementById("i18n").textContent);
    const list = (value) => (Array.isArray(value) ? value : []);

    let last = 0;
    const key = () => `k${++last}`;
    const option = (text = "") => ({ key: key(), text });
    const question = (q = {}) => {
      const options = list(q.options).map((text) => option(text));
      while (options.length < page.limits.min_options) options.push(option());
      const index = q.answer ? LETTERS.indexOf(q.answer) : -1;
      return {
        key: key(),
        prompt: q.prompt ?? "",
        options,
        correct: options[index]?.key ?? null,
        explanation: q.explanation ?? "",
      };
    };

    const p = page.data ?? {};
    const questions = list(p.questions);

    return {
      title: p.title ?? "",
      level: p.level ?? "",
      text: p.text ?? "",
      translation: p.translation_ru ?? "",
      glossary: Object.entries(p.glossary ?? {}).map(([word, meaning]) => ({
        key: key(),
        word,
        meaning,
      })),
      questions: (questions.length ? questions : [{}]).map(question),
      limits: page.limits,
      // Paths shift when items are added or removed, so any change of shape drops them.
      errors: page.errors,

      error(path) {
        return this.errors[path] ?? "";
      },
      glossaryError() {
        const path = Object.keys(this.errors).find((p) =>
          p.startsWith("glossary"),
        );
        return path ? this.errors[path] : "";
      },
      questionLabel(index) {
        return i18n.question.replace("{num}", index + 1);
      },

      addQuestion() {
        this.questions.push(question());
        this.errors = {};
      },
      removeQuestion(index) {
        this.questions.splice(index, 1);
        this.errors = {};
      },
      addOption(q) {
        q.options.push(option());
        this.errors = {};
      },
      removeOption(q, index) {
        const [removed] = q.options.splice(index, 1);
        if (removed.key === q.correct) q.correct = null;
        this.errors = {};
      },
      addWord() {
        this.glossary.push({ key: key(), word: "", meaning: "" });
        this.errors = {};
      },
      removeWord(index) {
        this.glossary.splice(index, 1);
        this.errors = {};
      },

      payload() {
        return {
          title: this.title,
          level: this.level,
          text: this.text,
          translation_ru: this.translation,
          glossary: Object.fromEntries(
            this.glossary
              .filter((row) => row.word.trim() || row.meaning.trim())
              .map((row) => [row.word, row.meaning]),
          ),
          questions: this.questions.map((q) => {
            const index = q.options.findIndex((o) => o.key === q.correct);
            return {
              prompt: q.prompt,
              options: q.options.map((o) => o.text),
              answer: index >= 0 ? LETTERS[index] : null,
              explanation: q.explanation,
            };
          }),
        };
      },
      save() {
        this.$refs.passage.value = JSON.stringify(this.payload());
      },
    };
  });
});
