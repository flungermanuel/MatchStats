# 0002: Agententeam, Skills und Commit-Hook

Datum: 2026-11-13

## Was
- Hauptsitzung = Lead (Tech Lead/CTO). Sieben Subagents in `.claude/agents/`: architect,
  backend-engineer, frontend-engineer (inaktiv), test-engineer, code-reviewer, product-owner,
  doc-keeper.
- Zwei Skills: `/aufgabe-start` und `/aufgabe-abschluss` bilden den Ablauf pro Aufgabe ab.
- Ein Hook (`.claude/hooks/pre_commit_check.py`) blockiert `git commit` bei rotem `pytest` oder
  `ruff check .`.
- Berechtigungen pro Rolle: Prüfer (architect, code-reviewer) nur lesend; test-engineer nur
  `tests/`; doc-keeper nur `docs/`; product-owner nur `docs/ideen.md`.

## Warum
- Der Entwickler liest den Code nicht Zeile für Zeile. Unabhängige Prüfrollen und Automatik
  ersetzen das Diff-Review und trennen Schreiben von Prüfen.
- Rollen mit engen Rechten verhindern Scope-Creep (z. B. Produktideen ändern keine Spezifikation).
- Lernziel: sauberes agentisches Arbeiten.

## Alternativen
- Nur CLAUDE.md und eine Sitzung: einfacher, aber kein unabhängiges Review.
- Mehr Agenten (z. B. DevOps, Daten): nicht nötig, bei Bedarf später.
- Kosten: Jeder Aufruf verbraucht Kontingent (Claude Pro). Deshalb nur so viele Agenten wie nötig,
  Haiku für Doku, Sonnet als Standard.
