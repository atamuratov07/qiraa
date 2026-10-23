"""Instructions for a chatbot that turns grammar exercises into a grammar file."""

from app.content.prompt import OPTION_RULES, YAML_RULES
from app.content.schemas import MAX_SLUG

EXAMPLE = """\
grammar:
  - slug: verb-prepositions-01
    prompt: ذَهَبَ الطُّلَّابُ ___ الْمَدْرَسَةِ.
    options:
      - إِلَى
      - عَلَى
      - عَنْ
    answer: A
    explanation: |
      Глагол ذَهَبَ «идти» требует предлога إِلَى «к, в».
  - slug: subject-case-01
    prompt: كَتَبَ ___ الدَّرْسَ.
    options:
      - الطَّالِبُ
      - الطَّالِبَ
      - الطَّالِبِ
    answer: A
    explanation: |
      Подлежащее (فَاعِل) стоит в именительном падеже: الطَّالِبُ.
"""


def grammar_prompt() -> str:
    return f"""\
Convert the material I give you into a YAML file for an Arabic grammar practice app.
Reply with the YAML only, in one code block.

The format, with two questions:

{EXAMPLE}
Rules:
- The file has one key, `grammar`: a list with one entry per exercise item in the
  material. An entry has only these keys: slug, prompt, options, answer, explanation.
- slug (required): lowercase Latin words joined by single hyphens, ending in a number, such
  as subject-case-01, at most {MAX_SLUG} characters, different for every entry in the file.
  Build it from the topic.
- prompt (required): the Arabic sentence exactly as in the source, keeping its vowel marks,
  with ___ in place of the gap, or the source's question.
- If the material explains a rule and has no exercises, write 5 to 10 entries that
  practise it.
{OPTION_RULES}\
- explanation (optional): one or two Russian sentences naming the rule.
{YAML_RULES}"""
