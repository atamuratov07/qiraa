# How content files are read

`parse(text)` in `app/content/loader.py` turns a content file into a validated `ContentFile`,
or raises `ContentError` listing every problem with its line. It doesn't use the database;
the CLI, the import page and the tests all call it.

## How PyYAML reads a file

`yaml.safe_load()` runs five stages and returns only the last result. `yaml.SafeLoader`
inherits all of them, so the loader drives one loader object a stage at a time and keeps what
it needs on the way.

| Stage       | Turns      | Into                               | Call                              |
| ----------- | ---------- | ---------------------------------- | --------------------------------- |
| Reader      | text       | characters, refusing control ones  | `yaml.SafeLoader(text)`           |
| Scanner     | characters | tokens (`-`, `:`, indentation)     | `yaml.scan()`                     |
| Parser      | tokens     | a flat stream of events            | `yaml.parse()`                    |
| Composer    | events     | a tree of nodes, with positions    | `loader.get_single_node()`        |
| Constructor | nodes      | dicts, lists, str, int, no positions | `loader.construct_document(root)` |

For this file:

```yaml
passages:
  - slug: b1-media
    options: [أ, ب]
```

the parser gives events, still flat but with start and end markers:

```
MappingStartEvent   line 0
ScalarEvent         line 0 'passages'
SequenceStartEvent  line 1
MappingStartEvent   line 1
ScalarEvent         line 1 'slug'
ScalarEvent         line 1 'b1-media'
ScalarEvent         line 2 'options'
SequenceStartEvent  line 2
ScalarEvent         line 2 'أ'
ScalarEvent         line 2 'ب'
SequenceEndEvent    line 2
MappingEndEvent     line 3
...
```

The composer nests them into a tree:

```
MappingNode([
  (ScalarNode('passages'), SequenceNode([
      MappingNode([
        (ScalarNode('slug'), ScalarNode('b1-media')),
        (ScalarNode('options'), SequenceNode([ScalarNode('أ'), ScalarNode('ب')])),
      ])
  ]))
])
```

and the constructor builds `{'passages': [{'slug': 'b1-media', 'options': ['أ', 'ب']}]}`.

Things worth knowing about the stages:

- The parser keeps a stack of states, so any nesting depth is safe there. The composer calls
  itself once per level and crashes with `RecursionError` at a few hundred levels.
- An `&name` anchor shows up as an event attribute and `*name` as an `AliasEvent`. The composer
  resolves an alias by reusing the same node, so a few bytes can repeat a large value many
  times.
- The constructor puts two equal keys into one dict, and the last one silently wins.
- `SafeConstructor` builds only plain types. The full constructor can run code from tags such
  as `!!python/object/apply:os.system`.

## Nodes and marks

| Node           | `value`                                              |
| -------------- | ---------------------------------------------------- |
| `ScalarNode`   | the text as written, always a `str`                  |
| `SequenceNode` | a list of child nodes                                |
| `MappingNode`  | a list of `(key node, value node)` pairs, in file order |

A mapping is a list instead of a dict because its keys are nodes and may repeat.

A node's `tag` says what it will become. The resolver picks it from patterns: `2010` gets
`int`, `'2010'` gets `str`, `no` gets `bool`. The node keeps the text either way; only the
constructor converts it.

`start_mark` is where a node begins and `end_mark` is just after it ends. A mark has `line`,
`column` and `index` (characters from the start of the file), all counted from 0. The loader
only reads `start_mark.line` and adds 1.

## The code

| Module         | Holds                                                                         |
| -------------- | ----------------------------------------------------------------------------- |
| `errors.py`    | `LineError`, `ContentError`, `MESSAGES`, `describe()`, `format_path()`        |
| `yaml_tree.py` | `read_yaml()`, `check_events()`, `duplicate_keys()`, `line_of()`, `from_yaml()` |
| `loader.py`    | `parse()`, `from_pydantic()`                                                  |

`yaml_tree.py` knows PyYAML and nothing about the schemas; `loader.py` joins the two.

### `read_yaml(text)`

1. `check_events()` reads the events once. It refuses any anchor or alias (`yaml_alias`) and
   nesting deeper than `MAX_DEPTH` (`too_deep`). A valid file nests 6 levels. 20 leaves room
   for a file one level too deep to get Pydantic's exact error, and stays far below the depth
   where the composer crashes.
2. `get_single_node()` builds the tree, or returns `None` for an empty file.
3. `construct_document(root)` builds the data from the same tree.
4. `loader.dispose()` runs in `finally`. The parser stores its next step as a bound method,
   which refers back to the loader. After a parse stopped by an error, that cycle keeps the
   loader and the whole text in memory until the garbage collector runs. `dispose()` breaks
   it, as `yaml.load()` does.

A PyYAML error becomes one `LineError` through `from_yaml()`: a `ReaderError` gives a
character position, so its line is counted from the newlines before it; a syntax error has
`problem_mark.line`. Then `duplicate_keys()` walks the tree and reports keys repeated in one
mapping.

### `parse(text)`

Validates the data with `ContentFile.model_validate()`. On a `ValidationError`, each error
becomes a `LineError` through `from_pydantic()`, the list is sorted by line (Pydantic reports
in field order), and one `ContentError` is raised.

### `line_of(root, loc)`

Follows a Pydantic `loc` such as `('passages', 0, 'questions', 2, 'answer')` down the tree:

- a string part finds the mapping pair with that key and takes the key's line;
- an int part takes that sequence item's line;
- a part that doesn't match stops the walk, so a missing field reports the line of the block
  that lacks it.

Finding a key is a scan, `next((pair for pair in pairs if key matches), None)`, which returns
the first match or `None`. Repeated keys were already refused, so the first match is the only
one.

### Messages

Pydantic's `errors()` gives each error's `type`, `loc`, `msg` and `ctx`, but not its message
template. `describe(error)` therefore looks the type up in `MESSAGES` and calls `_()` with
`ctx`, which translates it and fills its placeholders. Unknown types fall back to the English
`msg`. Checks of our own raise `PydanticCustomError` with their own type (`bad_answer`,
`bad_slug`, `answer_out_of_range`, `duplicate_option`, `duplicate_slug`).

The small `cast()` helpers at the end of `yaml_tree.py` only give the type checker the types
that PyYAML's stubs leave as `Any`.
