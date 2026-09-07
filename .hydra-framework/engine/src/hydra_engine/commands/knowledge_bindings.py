"""Knowledge v3 logical binding inspection and reviewed acceptance."""

from __future__ import annotations

import sys

from hydra_engine.commands import CommandResult
from hydra_engine.knowledge import bindings as bindings_module
from hydra_engine.knowledge.packages import ContextCompilerPaths


def _statuses(paths: ContextCompilerPaths, selector: str | None):
    manifest = bindings_module.bindings_root(paths) / "manifest.yaml"
    if not manifest.is_file():
        return None, []
    loaded = bindings_module.load_bindings(paths)
    chosen = [
        binding for name, binding in sorted(loaded.items())
        if selector is None or name == selector or binding.namespace == selector
    ]
    if selector is not None and not chosen:
        raise bindings_module.BindingResolutionError(f"no binding matches `{selector}`")
    return loaded, [bindings_module.verify_binding(binding, paths) for binding in chosen]


def command_bindings_list(args, paths: ContextCompilerPaths) -> CommandResult:
    try:
        loaded, statuses = _statuses(paths, getattr(args, "name", None))
    except ValueError as error:
        print(f"Hydra bindings: {error}", file=sys.stderr)
        return CommandResult(1)
    if loaded is None:
        print("Hydra bindings: no bindings manifest")
        return CommandResult(0)
    if not statuses:
        print("Hydra bindings: none declared")
        return CommandResult(0)
    for status in statuses:
        binding = status.binding
        print(f"- {binding.logical_name} [{status.state}] {binding.kind} -> {binding.target}")
    return CommandResult(0)


def command_bindings_verify(args, paths: ContextCompilerPaths) -> CommandResult:
    try:
        loaded, statuses = _statuses(paths, getattr(args, "name", None))
    except ValueError as error:
        print(f"Hydra bindings verify: {error}", file=sys.stderr)
        return CommandResult(1)
    if loaded is None:
        print("Hydra bindings verify: no bindings manifest")
        return CommandResult(0)
    if not statuses:
        print("Hydra bindings verify: none declared")
        return CommandResult(0)

    accept = bool(getattr(args, "accept", False))
    accepted: list[str] = []
    failed: list[str] = []
    for status in statuses:
        name = status.binding.logical_name
        # Only an otherwise-clean binding may be accepted. A failed assertion or
        # a missing target is not reviewable, and accepting it would launder a
        # real defect. `awaiting_review` is set by the verifier itself, so this
        # never depends on the wording of an error message.
        if accept and status.awaiting_review:
            try:
                bindings_module.record_accepted_fingerprint(status.binding, status.fingerprint, paths)
            except ValueError as error:
                print(f"- {name} [not accepted] {error}")
                failed.append(name)
                continue
            accepted.append(name)
            print(f"- {name} [accepted] {status.fingerprint}")
            continue
        print(f"- {name} [{status.state}]")
        for item in status.errors:
            print(f"  - {item}")
        if status.state != "verified":
            failed.append(name)
    if accepted:
        print(f"Hydra bindings verify: accepted {len(accepted)} reviewed fingerprint(s)")
    if failed:
        print("Hydra bindings verify: failed")
        return CommandResult(1)
    print("Hydra bindings verify: ok")
    return CommandResult(0)


def register(subparsers) -> None:
    bindings = subparsers.add_parser("bindings", help="Inspect and accept Knowledge v3 logical bindings")
    sub = bindings.add_subparsers(dest="bindings_command", required=True)
    listing = sub.add_parser("list", help="List logical bindings with their verified state")
    listing.add_argument("--name", help="One `@namespace/key` logical name, or a namespace")
    listing.set_defaults(func=_dispatch_list)
    verify = sub.add_parser("verify", help="Verify binding assertions against their targets")
    verify.add_argument("--name", help="One `@namespace/key` logical name, or a namespace")
    verify.add_argument(
        "--accept", action="store_true",
        help="Record the reviewed assertion fingerprint; this writes to the fragment",
    )
    verify.set_defaults(func=_dispatch_verify)


def _dispatch_list(args, ctx) -> int:
    return command_bindings_list(args, ctx.context_compiler_paths()).exit_code


def _dispatch_verify(args, ctx) -> int:
    return command_bindings_verify(args, ctx.context_compiler_paths()).exit_code
