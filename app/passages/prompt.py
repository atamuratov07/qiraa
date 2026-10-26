"""Instructions for a chatbot that turns reading material into a passages file."""

from app.content.prompt import OPTION_RULES, YAML_RULES
from app.content.schemas import MAX_SLUG
from app.passages.schemas import MAX_LEVEL, MAX_TITLE

EXAMPLE = """\
passages:
  - slug: a2-market
    title: فِي السُّوقِ
    level: A2
    text: |
      ذَهَبَ أَحْمَدُ إِلَى السُّوقِ يَوْمَ الْجُمُعَةِ مَعَ أُمِّهِ.

      كَانَ السُّوقُ مُزْدَحِمًا، فَرَجَعَا إِلَى الْبَيْتِ قَبْلَ الظُّهْرِ.
    translation_ru: |
      В пятницу Ахмад пошёл на рынок с мамой.

      На рынке было много людей, поэтому они вернулись домой до полудня.
    questions:
      - prompt: مَتَى ذَهَبَ أَحْمَدُ إِلَى السُّوقِ؟
        options:
          - يَوْمَ السَّبْتِ
          - يَوْمَ الْجُمُعَةِ
          - يَوْمَ الْأَحَدِ
        answer: B
        explanation: |
          В тексте сказано «يَوْمَ الْجُمُعَةِ», то есть в пятницу.
"""


def passage_prompt() -> str:
    return f"""\
Convert the material I give you into a YAML file for an Arabic reading practice app.
Reply with the YAML only, in one code block.

The format, with one passage:

{EXAMPLE}
Rules:
- The file has one key, `passages`: a list with one entry per passage in the material.
  A passage has only these keys: slug, title, level, text, translation_ru, questions. A
  question has only these keys: prompt, options, answer, explanation.
- slug (required): lowercase Latin words joined by single hyphens, such as a2-market, at
  most {MAX_SLUG} characters, different for every passage in the file. Build it from the
  level and the topic.
- title (optional): at most {MAX_TITLE} characters. level (optional): such as A2 or B1, at
  most {MAX_LEVEL} characters.
- text (required): the Arabic passage exactly as in the source, keeping its vowel marks, in
  a `|` block. Separate paragraphs with one blank line.
- translation_ru (optional): a Russian translation, also in a `|` block.
- questions (at least one): keep the source's questions in their order. If the source has
  none, write 4 to 6 comprehension questions in Arabic.
{OPTION_RULES}\
- explanation (optional): one or two Russian sentences on why the answer is right, quoting
  the text.
{YAML_RULES}"""
