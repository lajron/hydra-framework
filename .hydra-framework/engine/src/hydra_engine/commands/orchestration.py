"""CLI for explicit, provider-neutral orchestration control-plane actions."""

from __future__ import annotations

import argparse
import json
import sys

from hydra_engine.commands import CommandResult
from hydra_engine.documents.tokens import display_path
from hydra_engine.orchestration import control
from hydra_engine.work import task_records
from hydra_engine.work.owners import HydraOwnerError, resolve_owner


def _payload(raw: str, label: str):
    try:
        return json.loads(raw)
    except json.JSONDecodeError as error:
        raise control.OrchestrationError(f"{label} must be valid JSON") from error


def _owner(args, ctx) -> str:
    return resolve_owner(args.owner, ctx.env_owner(), ctx.git_email())


def _task_reference(args, ctx, owner: str) -> str:
    task, lines = task_records.resolve_task_record(args.task, ctx.work_paths(), owner)
    if task is None:
        raise control.OrchestrationError("\n".join(lines))
    return display_path(task, ctx.root)


def _control(ctx):
    def task_exists(reference: str) -> bool:
        return (ctx.root / reference).is_file()

    return control.for_repository(ctx.root, ctx.hydra, ctx.local, task_exists)


def _emit(value) -> CommandResult:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2))
    return CommandResult(0)


def command_orchestration(args, ctx) -> CommandResult:
    try:
        if args.orchestration_command == "status":
            return _emit(_control(ctx).snapshot(args.run_id))
        owner = _owner(args, ctx)
        runner = _control(ctx)
        command = args.orchestration_command
        if command == "start":
            task_id = _task_reference(args, ctx, owner)
            return _emit(runner.start_run(args.run_id, task_id, owner))
        if command == "spawn":
            return _emit(runner.spawn(
                args.run_id, args.request_id, args.worker_id, args.worker_owner,
                owner, args.parent_worker_id, args.role, args.task, args.reason,
                args.capability_class, args.effort, args.provider,
                _payload(args.payload, "spawn payload"),
            ))
        if command == "message":
            return _emit(runner.message(
                args.run_id, args.worker_id, args.request_id, args.message_id,
                owner, args.provider, _payload(args.payload, "message payload"),
            ))
        if command == "collect":
            return _emit(runner.collect(
                args.run_id, args.worker_id, args.request_id, args.result_id,
                owner, args.provider, _payload(args.payload, "result payload"), args.complete,
            ))
        if command == "transition":
            return _emit(runner.transition(args.kind, args.target_id, owner, args.status))
        if command == "handoff":
            return _emit(runner.handoff(args.kind, args.target_id, owner, args.to))
        if command == "recover":
            return _emit(runner.recover(args.kind, args.target_id, owner, args.from_owner))
        if command == "review":
            return _emit(runner.review(args.kind, args.target_id, owner, args.status, args.note))
        if command == "validate":
            return _emit(runner.validate(args.kind, args.target_id, owner, args.status, args.evidence))
        raise control.OrchestrationError(f"unknown orchestration command `{command}`")
    except (control.OrchestrationError, HydraOwnerError, ValueError) as error:
        print(f"Hydra orchestration: {error}", file=sys.stderr)
        return CommandResult(1)


def _owner_arg(parser) -> None:
    parser.add_argument("--owner", default="", help="Explicit actor owner; otherwise use Hydra owner resolution")


def _target_args(parser) -> None:
    parser.add_argument("--kind", required=True, choices=("run", "worker"))
    parser.add_argument("--target-id", required=True)
    _owner_arg(parser)


def register(subparsers) -> None:
    root = subparsers.add_parser(
        "orchestration",
        help="Record bounded provider-neutral runs, workers, requests, results, review, and recovery",
    )
    commands = root.add_subparsers(dest="orchestration_command", required=True)

    start = commands.add_parser("start", help="Start a run anchored to an existing task record")
    start.add_argument("--run-id", required=True)
    start.add_argument("--task", required=True, help="Task name or repository-relative task-record path")
    _owner_arg(start)
    start.set_defaults(func=command_orchestration)

    spawn = commands.add_parser("spawn", help="Record one bounded worker spawn request")
    for name in ("run-id", "request-id", "worker-id"):
        spawn.add_argument(f"--{name}", required=True)
    spawn.add_argument("--worker-owner", required=True)
    spawn.add_argument("--parent-worker-id", default="", help="Parent worker ID; omit only for a run-root worker")
    spawn.add_argument("--role", required=True)
    spawn.add_argument("--task", required=True)
    spawn.add_argument("--reason", required=True)
    spawn.add_argument("--capability-class", default="fast-default")
    spawn.add_argument("--effort", default="standard")
    spawn.add_argument("--provider", default="unconfigured")
    spawn.add_argument("--payload", default="{}", help="Bounded structured JSON request payload")
    _owner_arg(spawn)
    spawn.set_defaults(func=command_orchestration)

    message = commands.add_parser("message", help="Record one bounded worker message request")
    for name in ("run-id", "worker-id", "request-id", "message-id"):
        message.add_argument(f"--{name}", required=True)
    message.add_argument("--provider", default="unconfigured")
    message.add_argument("--payload", required=True, help="Bounded structured JSON message payload")
    _owner_arg(message)
    message.set_defaults(func=command_orchestration)

    collect = commands.add_parser("collect", help="Record a bounded result supplied for a worker")
    for name in ("run-id", "worker-id", "request-id", "result-id"):
        collect.add_argument(f"--{name}", required=True)
    collect.add_argument("--provider", default="unconfigured")
    collect.add_argument("--payload", required=True, help="Bounded structured JSON result payload")
    collect.add_argument("--complete", action="store_true", help="Mark the supplied result as provider-reported complete")
    _owner_arg(collect)
    collect.set_defaults(func=command_orchestration)

    transition = commands.add_parser("transition", help="Apply one explicit run or worker lifecycle transition")
    _target_args(transition)
    transition.add_argument("--status", required=True)
    transition.set_defaults(func=command_orchestration)

    handoff = commands.add_parser("handoff", help="Transfer one run or worker to an explicit new owner")
    _target_args(handoff)
    handoff.add_argument("--to", required=True)
    handoff.set_defaults(func=command_orchestration)

    recover = commands.add_parser("recover", help="Recover one explicitly named handed-off or recovery-required record")
    _target_args(recover)
    recover.add_argument("--from-owner", required=True)
    recover.set_defaults(func=command_orchestration)

    review = commands.add_parser("review", help="Record an owner request or independent review decision")
    _target_args(review)
    review.add_argument("--status", required=True)
    review.add_argument("--note", default="")
    review.set_defaults(func=command_orchestration)

    validate = commands.add_parser("validate", help="Record independent validation state and bounded evidence")
    _target_args(validate)
    validate.add_argument("--status", required=True)
    validate.add_argument("--evidence", action="append", default=[])
    validate.set_defaults(func=command_orchestration)

    status = commands.add_parser("status", help="Read one run or the private ledger without changing it")
    status.add_argument("--run-id", default="")
    status.set_defaults(func=command_orchestration)
