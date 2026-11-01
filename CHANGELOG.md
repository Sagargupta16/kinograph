# Changelog

Every change, newest first, under the version that shipped it.

## 0.1.0 - 2026-10-31

First public release.

- **One skill, `/praxinoscope:praxinoscope`.** The main chat takes a brief, offers styles, writes a storyboard that `qa.py holds` checks for reading time, and builds nothing until the user approves it. A proof, a fresh-eyes review and a render follow, then a final review whose verdict `qa.py approve` binds to the file's content hashes.
- **Two agents.** `praxinoscope:builder` writes, renders and checks one video in its own context. `praxinoscope:reviewer` reads only the scenario and the working folder, never the builder's report.
- **Six original styles:** signal (product launch), ledger (data story), blueprint (technical explainer), marquee (logo sting or title card), pulse (beat-locked kinetic type for reels) and cartridge (retro 8-bit parody).
- **The engine.** Every frame is a pure function of time on one integer frame clock. Frames pass from worker processes through a shared-memory ring into a single H.264 encode, tagged BT.709. Sound comes from numpy instruments placed by their perceptual landmark and a 4x oversampled true-peak master to -14 LUFS. Offline narration has word cues.
- **58 coded QA checks** (`qa.py check`), each proven by planted-fault fixtures in `qa.py selftest`.
- **One Python version per build.** `engine/.python-version` (3.15) travels with every copy of the engine, so a proof and its render run on the same interpreter; CI reads the same file.
- **The README flow diagram**, `docs/praxinoscope-flow.svg`: a dual-theme SVG with no scripts or external links. Its archify source, `docs/praxinoscope-flow.workflow.json`, cites the file and lines behind every box.
