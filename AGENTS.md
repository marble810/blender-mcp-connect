# Repository Agent Instructions

## Agent-Generated Documentation

Use `docs/agent/` as the default destination for agent-generated Markdown documents, including plans, research notes, architecture proposals, reviews, audits, investigations, and handoff summaries.

Name each document using:

```text
{datetime}_{title}.md
```

Required filename format:

```text
YYYY-MM-DD_HH-mm-ss_<title>.md
```

Rules:

- Use UTC for `datetime`.
- Use a lowercase ASCII kebab-case title.
- Keep the title short and descriptive.
- Do not use characters that are invalid in Windows filenames, including `:`.
- Do not overwrite an existing document; create a new timestamped document.
- Example: `docs/agent/2026-08-07_15-30-22_dynamic-port-discovery-plan.md`.
- Avoid fixed generic names such as `PLAN.md`, `REVIEW.md`, or `NOTES.md` inside `docs/agent/`.

Exceptions:

- Follow an explicit user-requested path or filename when one is provided.
- Keep conventional repository files in their conventional locations, including `README.md`, `CHANGELOG.md`, `LICENSE`, `SECURITY.md`, `NOTICE.md`, `UPSTREAM.md`, and `AGENTS.md`.
- Keep machine-readable specifications such as JSON Schema files in their documented product location.
- Do not move source-code documentation that must live beside the source it documents.
