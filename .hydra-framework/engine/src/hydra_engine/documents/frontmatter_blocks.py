"""Where the metadata block sits in each document form.

One function per document form, all with the same `(path, root) -> mapping`
shape, so `objects.object_handlers` can hold a uniform reader per registered
form instead of a suffix switch:

- Markdown: the leading `---` block.
- Python: the leading `---` block of the module docstring.
- YAML: the whole file.

`yaml_document_frontmatter` is a thin call on `parse_yaml`. It is named here
rather than left as a bare `parse_yaml` call at the objects layer so that all
three answers to "where is the envelope in this document form" are readable in
one place, and so the objects-layer registry holds three references of one
shape rather than two of one shape and one special case.
"""

from __future__ import annotations

import ast
from pathlib import Path

from hydra_engine.documents.tokens import HydraYamlError, display_path, read_text
from hydra_engine.documents.yaml_documents import parse_yaml, parse_yaml_text, yaml_int, yaml_list, yaml_map, yaml_str  # noqa: F401 -- YAML helpers are re-exported for Knowledge modules, which would otherwise push yaml_documents past the architecture in-degree cap


def _leading_block(text: str, path: Path, root: Path, *, what: str) -> dict:
    """The `---`-delimited block at the top of `text`, or `{}` if there is none.

    An absent block is a real answer (most documents are not Hydra objects);
    an opened-but-unterminated one is an error, because the author plainly
    meant to write metadata and the parser cannot tell how much of the
    document they meant.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return parse_yaml_text("\n".join(lines[1:index]), path, root)
    raise HydraYamlError(f"{display_path(path, root)}: unterminated {what}")


def markdown_frontmatter(path: Path, root: Path) -> dict:
    return _leading_block(read_text(path), path, root, what="frontmatter")


def python_docstring_frontmatter(path: Path, root: Path) -> dict:
    """The frontmatter block at the top of a module docstring.

    Read through `ast` rather than by looking at the first line of the file,
    so a shebang, a leading comment, or a raw/single-quoted docstring are all
    handled by Python's own parser instead of a second guess at Python syntax.
    `clean=False` keeps the docstring's lines byte-identical to the file's,
    which is what lets `objects.envelopes`' line-based field surgery -
    `schema upgrade`, `move-object` - rewrite a Python envelope with no
    special case of its own.

    A module with no docstring, or one that does not open with `---`, is not
    a Hydra object and produces `{}`. That is the normal case: engine modules
    are objects only by declaring an envelope, exactly as Markdown files are.
    """
    try:
        tree = ast.parse(read_text(path), filename=str(path))
    except SyntaxError as error:
        raise HydraYamlError(f"{display_path(path, root)}: {error}") from error
    docstring = ast.get_docstring(tree, clean=False)
    if not docstring:
        return {}
    return _leading_block(docstring, path, root, what="docstring frontmatter")


def yaml_document_frontmatter(path: Path, root: Path) -> dict:
    return parse_yaml(path, root)


def first_declared_string(data: dict, keys: tuple[str, ...]) -> str:
    """The first key in `keys` this document actually declares as a string.

    `keys` is an ordered list of the spellings a human genuinely writes for
    one envelope field - a YAML manifest calls its kind `hydra_object_kind`
    and its title `name`. Reading an alternate authored spelling is not
    defaulting, which is why this returns `""` rather than inventing anything
    when none of them is present (see `objects.envelopes.missing_envelope_fields`).
    """
    for key in keys:
        value = yaml_str(data.get(key))
        if value:
            return value
    return ""
