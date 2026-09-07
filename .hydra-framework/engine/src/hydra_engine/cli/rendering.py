"""Output rendering for CLI-layer composition.

`route-prompt` is the one command whose presentation was never given a
`commands/*.py` home: it composes across two domains (`knowledge.routing`'s
package pointers and `work.board`'s state-pointer lines). The print
composition below -- pure formatting, no root-derived paths -- lives in this
permanent CLI-layer home; its domain calls live in `cli.route_prompt`.
"""

from __future__ import annotations

import sys


def render_route_prompt(matches, warnings: list[str], state_lines: list[str], references=()) -> None:
    for warning in warnings:
        # Routing is a convenience surface; a broken file must not break the
        # prompt. Say so on stderr instead of silently skipping it.
        print(f"Hydra routing skipped: {warning}", file=sys.stderr)

    if matches:
        print("Hydra Knowledge v3 routing (pointers only):")
        for match in matches:
            print(f"- {match.title}: read `{match.state}` then `{match.overview}` first. {match.note}")

    if references:
        print("Hydra exact references:")
        for reference in references:
            doc = reference.document
            label = doc.hydra_id or doc.title
            suffix = f" ({doc.title})" if doc.hydra_id and doc.title else ""
            print(f"- {label}{suffix}: `{doc.path}`")

    for line in state_lines:
        print(line)
