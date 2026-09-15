# Operations

For canonical ownership and maintainer evidence, see the [Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence).

Status: orientation

Choose the smallest gate that covers your change. A wiki link or page move uses
the focused wiki gate. A change to shared Hydra state uses full validation. If a
gate fails, keep the command, exit result, and finding path, then follow the
owning route in [Troubleshooting](/project-wiki/hydra-framework/operations/troubleshooting.md).

Operations is the route for proving that a Hydra repository is healthy and
narrowing a failure to the owning surface. Start with
[Validation](/project-wiki/hydra-framework/operations/validation.md) to choose the gate. Use
[Evidence and Telemetry](/project-wiki/hydra-framework/operations/evidence-and-telemetry.md) to understand what can
be retained for review and what remains local or deferred.

## A concrete situation

You update a Markdown link under `project-wiki/`. Run the focused wiki check:

```bash
python3 .hydra-framework/scripts/hydra.py validate-wiki --path project-wiki/hydra-framework
```

If the same change also modifies `.hydra-framework/`, run the full repository
check:

```bash
python3 .hydra-framework/scripts/hydra.py validate
```

The wiki check covers Markdown and double-bracket links. Full validation covers
the framework contracts listed in the [validation contract](/.hydra-framework/validation/README.md).

For exact command forms, use the [Command Surface](/project-wiki/hydra-framework/reference/command-surface.md).

## Operator Route

1. If the change is a wiki move or link edit, run the focused wiki gate.
2. If shared Hydra state changed, run the full validation gate.
3. If the failure names a package, provider surface, or engine behavior, run
   the corresponding focused check from [Troubleshooting](/project-wiki/hydra-framework/operations/troubleshooting.md).
4. Preserve the command, exit result, and finding path as review evidence.
5. Use [Evidence and Telemetry](/project-wiki/hydra-framework/operations/evidence-and-telemetry.md) when the evidence
   concerns measurements, redaction, or a future capture integration.

## Next action

Open [Validation](/project-wiki/hydra-framework/operations/validation.md) and match your change to a gate. If it
fails, use [Troubleshooting](/project-wiki/hydra-framework/operations/troubleshooting.md) to choose the next
diagnostic.

## Sources

- [Scripts README](/.hydra-framework/scripts/README.md)
- [Wiki command](/.hydra-framework/engine/src/hydra_engine/commands/wiki.py) and [link validator](/.hydra-framework/engine/src/hydra_engine/wiki/links.py)
- [Validation contract](/.hydra-framework/validation/README.md)
- [Knowledge surface contract](/.hydra-framework/surfaces/README.md)
