"""Starter text for canonical Hydra skills and agents."""

from __future__ import annotations


def skill_metadata_text(name: str, description: str, uid: str, kind: str) -> str:
    hydra_id = "hydra" + "://capability/skill/" + name
    return f"""schema: hydra-framework.skill.v2
hydra_id: {hydra_id}
uid: {uid}
schema_version: 3
hydra_object_kind: skill
kind: {kind}
name: {name}
description: {description}
tags: []
scope: repo-local
maturity: experimental
owners:
  team: hydra
dependencies:
  knowledge: []
  skills: []
  workflows: []
relations: []
provenance:
  sources: []
"""


def skill_body_text(title: str) -> str:
    return f"""# {title} Skill

## Capability

<!-- One sentence: what does this skill do, and when should an agent reach for it? -->

## Procedure

1. <!-- First concrete step. -->
2. <!-- Add as many numbered steps as the real procedure needs. -->

## Output

<!-- What should be reported back when this skill finishes: files changed, findings, validation evidence. -->

## Boundaries

- <!-- A concrete "do not" constraint. Pair it with the approved alternative when there is one. -->
"""


def agent_metadata_text(name: str, description: str, uid: str, capability_class: str, effort: str) -> str:
    hydra_id = "hydra" + "://capability/agent/" + name
    return f"""schema: hydra-framework.agent.v2
hydra_id: {hydra_id}
uid: {uid}
schema_version: 3
hydra_object_kind: agent
name: {name}
description: {description}
scope: repo-local
maturity: experimental
owners:
  team: hydra
capability_class: {capability_class}
effort: {effort}
tools: []
dependencies:
  knowledge: []
  skills: []
  workflows: []
relations: []
provenance:
  sources: []
"""


def agent_body_text(title: str) -> str:
    return f"""# {title} Agent

## Purpose

<!-- One sentence: what decision-making role does this agent own? -->

## Responsibilities

- <!-- A concrete responsibility. -->

## Boundaries

- <!-- A concrete constraint. Pair a "do not" with the approved alternative when there is one. -->
"""
