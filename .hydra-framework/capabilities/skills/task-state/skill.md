# Task State Skill

## Capability

Run the Hydra task-state lifecycle through the canonical helper instead of hand-editing Markdown. This is the command surface over `hydra.py task`.

Use the argument to pick the action:

- `start <name>`: create an active record under your owner directory
- `checkpoint <name-or-path>`: write a recovery checkpoint beside the record
- `handoff <name-or-path> --to <owner>`: move the record and reassign it
- `complete <name-or-path> --outcome <path|none>`: delete the record; Git history is the archive
- no argument: show the board

## Procedure

1. Resolve the action from the argument. With no argument, run `python3 .hydra-framework/scripts/hydra.py board` and stop.
2. Before `start`, check the board for a record that already covers this objective. If one exists, update it instead of creating a competing record. If it belongs to someone else, talk to them rather than starting a parallel one.
3. Run the matching command. Each takes the name or path positionally:
   - `python3 .hydra-framework/scripts/hydra.py task start <name> --goal "<goal>"`
   - `python3 .hydra-framework/scripts/hydra.py task checkpoint <name-or-path>`
   - `python3 .hydra-framework/scripts/hydra.py task handoff <name-or-path> --to <owner>`
   - `python3 .hydra-framework/scripts/hydra.py task complete <name-or-path> --outcome <path|none>`

   Check `--help` on any of them before guessing flags.
   An absolute path or path-shaped repository-relative value is resolved
   exactly. A bare name is slugified, then resolves first to one matching task
   under the caller's owner directory and otherwise to one unique global
   match. Multiple matches are refused with their candidate paths; pass one of
   those paths explicitly instead of relying on task dates.
4. The helper writes the skeleton; it does not know the work. Immediately fill in the fields it left blank: readiness, step state, changed files, validation evidence, continuation notes.
5. Before `complete`, make sure the durable outcome exists somewhere else. `--outcome` must name a file that exists, or `none`. The record is about to be deleted; whatever it taught has to be in a knowledge file by then.
6. Run `python3 .hydra-framework/scripts/hydra.py validate` to confirm the record has every required field.

## Output

Report the task record or checkpoint changed, its current state, and validation evidence.

## Boundaries

- Do not create a formal task for trivial one-shot work.
- Do not paste conversation transcripts into the record. Preserve facts and continuation state.
- Do not leave a generated record with template placeholders still in it; an unfilled record is worse than none.
- Edit only your own records. Use `handoff` to take one over.
- Keep credentials, machine paths, planning, and personal notes out of records. Those go in `.hydra-framework.local/`; `hydra.py note "<title>"` creates a named note with no template.
- If the owner slug will not resolve, the command fails on purpose. Set `git config user.email` or `HYDRA_OWNER` rather than working around it.
