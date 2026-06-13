# Wiki Schema — Operating Rules

## Purpose
This wiki stores the user's domain knowledge base, distilled from source documents.
It provides context to the deck generation agent for domain-aware slide creation.

## Files

| File | Role |
|------|------|
| `schema.md` | This file. Wiki operating rules. |
| `profile.md` | User / organization profile and domain specialty. |
| `domain.md` | Core domain concepts and knowledge (ingest target). |
| `stack.md` | Technology stack and tools used in the domain. |
| `glossary.md` | Domain-specific terminology and definitions. |

## Rules

1. **Accumulate, never delete** — existing entries are never removed; only extended.
2. **Conflicts** — mark with `[CONFLICT]` tag for the user to resolve manually.
3. **Language** — all wiki content must be in English.
4. **Source** — each section should note the source document it was distilled from.
5. **ingest.py writes here** — never edit these files manually during an active ingest session.
