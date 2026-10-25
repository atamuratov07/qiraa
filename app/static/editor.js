// The editors (passages/editor.html, grammar/editor.html). Alpine keeps the content while
// it is edited; on submit it goes into one hidden field as JSON in the shape PassageIn or
// QuestionIn reads. Questions, options and glossary rows carry a key, so x-for keeps each
// input in its place, and the correct option is remembered by key: removing option A
// must not move the answer from B to C.
//
// Both components render the question card from _editor.html, which asks path(qi, field)
// for the error key: "questions[0].prompt" in a passage, "prompt" for one question.
const LETTERS = "ABCDEF";

const readJson = (id) => JSON.parse(document.getElementById(id).textContent);
const list = (value) => (Array.isArray(value) ? value : []);

// What both editors share: building questions from the server's JSON, reading them back,
// and the methods the question card calls.
function questionKit(limits) {
  let last = 0;
  const key = () => `k${++last}`;
  const option = (text = "") => ({ key: key(), text });

  const question = (q = {}) => {
    const options = list(q.options).map((text) => option(text));
    while (options.length < limits.min_options) options.push(option());
    const index = q.answer ? LETTERS.indexOf(q.answer) : -1;
    return {
      key: key(),
      prompt: q.prompt ?? "",
      options,
      correct: options[index]?.key ?? null,
      explanation: q.explanation ?? "",
    };
  };

  const payload = (q) => {
    const index = q.options.findIndex((o) => o.key === q.correct);
    return {
      prompt: q.prompt,
      options: q.options.map((o) => o.text),
      answer: index >= 0 ? LETTERS[index] : null,
      explanation: q.explanation,
    };
  };

  // Paths shift when items are added or removed, so any change of shape drops the errors.
  const methods = {
    error(path) {
      return this.errors[path] ?? "";
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
  };

  return { key, question, payload, methods };
}

document.addEventListener("alpine:init", () => {
  Alpine.data("passageEditor", () => {
    const page = readJson("editor-data");
    const i18n = readJson("i18n");
    const kit = questionKit(page.limits);
    const p = page.data ?? {};
    const questions = list(p.questions);

    return {
      ...kit.methods,
      title: p.title ?? "",
      level: p.level ?? "",
      text: p.text ?? "",
      translation: p.translation_ru ?? "",
      glossary: Object.entries(p.glossary ?? {}).map(([word, meaning]) => ({
        key: kit.key(),
        word,
        meaning,
      })),
      questions: (questions.length ? questions : [{}]).map(kit.question),
      limits: page.limits,
      errors: page.errors,

      path(qi, field) {
        return `questions[${qi}].${field}`;
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
        this.questions.push(kit.question());
        this.errors = {};
      },
      removeQuestion(index) {
        this.questions.splice(index, 1);
        this.errors = {};
      },
      addWord() {
        this.glossary.push({ key: kit.key(), word: "", meaning: "" });
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
          questions: this.questions.map(kit.payload),
        };
      },
      save() {
        this.$refs.json.value = JSON.stringify(this.payload());
      },
    };
  });

  // One grammar question. It sits in a one-item list so the card's x-for serves it too.
  Alpine.data("questionEditor", () => {
    const page = readJson("editor-data");
    const kit = questionKit(page.limits);

    return {
      ...kit.methods,
      questions: [kit.question(page.data ?? {})],
      limits: page.limits,
      errors: page.errors,

      path(_qi, field) {
        return field;
      },
      payload() {
        return kit.payload(this.questions[0]);
      },
      save() {
        this.$refs.json.value = JSON.stringify(this.payload());
      },
    };
  });
});
