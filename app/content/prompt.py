"""
Rules that both chatbot prompts share (passages/prompt.py, grammar/prompt.py).
"""

from app.content.schemas import LETTERS, MAX_OPTIONS, MIN_OPTIONS

FIRST, LAST = LETTERS[0], LETTERS[MAX_OPTIONS - 1]

OPTION_RULES = f"""\
- options: {MIN_OPTIONS} to {MAX_OPTIONS} different options per question, in the source's order.
- answer: the letter of the correct option, {FIRST} for the first option up to {LAST}. Take it
  from the source's answer key. If there is no key, choose the answer yourself and put the
  comment `# check` after the letter.
"""

YAML_RULES = """\
- Put a value in quotes when YAML would read it as something else: numbers, years, dates,
  yes, no, on, off, and values that contain ": " or start with a symbol.
- Don't use anchors or aliases (& and *).
"""
