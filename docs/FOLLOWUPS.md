# Follow-ups

The only legal home for deferred work. Code carries no deferred-work markers (`just markers`).

Format: `- [ ] <what> — why deferred: <reason> (added YYYY-MM-DD)`

- [ ] guard-gate: chained read-verb prefix (`grep x justfile && rm justfile`) passes — why deferred: pre-push tamper check is the backstop; a full shell parser is out of scope (added 2026-08-24)
- [ ] Cold-setup number excludes the `pyright` Node download — why deferred: the measuring machine had a system `node`, and provisioning a node-less machine to time it is out of scope; the README cites CI's measured `time` lines, which will simply grow if node is absent (added 2026-08-24)
- [ ] `check-links.py` ignores HTML `<img src>`/`<a href>` targets, so `docs/assets/*` referenced from README are unchecked — why deferred: the scanner is at its 100-line cap; a second regex for `src="..."` is a small follow-up (added 2026-08-25)
