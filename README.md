# Football Helper

A local-first football development MVP built from the [shared product plan](https://chatgpt.com/share/6aceb874-6b44-83e8-a53d-8a018c99b456). No account, API key, package install, or cloud backend is required. Python 3.11+ and a modern browser are enough. An optional local ball detector can be installed with one command (see Phase 2).

## Run

```powershell
python app.py
```

Open **http://127.0.0.1:8765**. The server must use this address, not `localhost`, because the Host check is intentionally strict. Stop it with Ctrl+C. Change the port or data location with `python app.py --port 8766 --data-dir D:\my-football-data` (quote paths containing spaces).

## Implemented workflows

- Player onboarding: position, skill goal, time, equipment, local processing consent, and guardian confirmation for ages 16–17. This pilot excludes under-16 profiles.
- Five repeatable protocols: juggling, alternating-foot wall passing, first touch, slalom, and gate passing. Counts are manually entered; observations with invalid setup, poor visibility, moving camera or missed slalom cones become `UNMEASURABLE`.
- Local video uploads (MP4/WebM/MOV, up to 64 MB), phone capture through the file chooser where supported, playback, seeking, and side-by-side reference previews. Reference clips are not saved; evidence clips are.
- A skill passport with raw metrics, measurement provenance, all original observations, and comparisons restricted to matching setup and protocol versions. These are personal trends, not calibrated ratings or statistical claims about ability.
- An adaptive planner prioritizing goals and position, filtering equipment, recording session completion and effort, and reducing workload for tiredness or hard recent sessions. Rest generates no assignments. Progression requires comparable reviewed evidence and comfortable completed practice.
- Twenty-five original starter drills with objectives, equipment, instructions, observable outcomes, cues, progressions, regressions and versioned source metadata. They are labelled **draft**, not expert-approved. Local qualified-coach reviews change the label for that version.
- A trusted local review workspace with reviewer notes, clip timestamps and optional metric corrections. Append-only corrections preserve original measurements. Reviewer identity/qualification is self-declared, not verified by an account system.
- Offline rule-based coaching and optional Gemma 4 via local Ollama. Retrieval supplies eligible starter guidance; LLM responses cannot modify scores or plans. Only referenced local drills are accepted.
- Local AI availability, installed-model checks, RAM detection and a conservative starting-model suggestion; no automatic downloads or performance guarantees.
- ZIP export of all records and evidence videos, plus deletion of the active workspace's records and videos.

## Phase 2: local video feedback

Open **Video feedback** under Your Workspace after uploading a clip on Record. Choose a saved video and assessment type, then a window of up to 60 seconds. Use slow playback, 0.1-second stepping and the paused frame to inspect the evidence.

For experimental ball tracking, pause on a clear frame, click the ball (or enter normalized centre coordinates) and choose **Select ball**, then **Track selected ball**. Tracking samples at 10 fps and runs forward and backward from that frame. A bounded motion prediction helps follow fast balls; ambiguous candidates and abrupt size changes are rejected. After **two consecutive missed samples**, **one miss near a frame edge**, or a widespread scene change, automatic tracking stops. The scene-change alarm is conservative and uncalibrated; camera movement or lighting changes can also trigger it. The window pauses: scrub to a visible ball in the remaining direction and click to re-confirm it, or choose **Skip remaining track in this direction**. Each confirmation starts a new saved segment; gaps are never backfilled and contact logic never bridges segments. Cancel also works while awaiting a confirmation.

**Correctness gate.** Coverage alone cannot pass a new run: with confidence, motion and stationary-duration limits unset, it is marked **SUSPECT**. Minimum/mean detection score, maximum motion in frame widths per second and the longest interval within one native pixel are saved and shown. Optional API limits can suppress proposals for low/missing confidence, implausible motion or a stationary track; all three must be deliberately supplied. No thresholds have been chosen from the small screenings, and configured runs remain unvalidated and require manual review. See [independent evaluation collection](evaluation/README.md).

Juggling trajectories can propose downward-to-upward turns across up to two missing samples, with a shorter neighbourhood near a window boundary. All trajectory proposals are marked uncertain and never become scores automatically. The seed, confirmations, segment IDs, loss reasons, algorithm version, per-detection confidence and raw observations are retained. New uploads and their analyses include a video SHA-256 for matching evaluation labels.

**Optional local ball detector.** Run `python tools/fetch_detector.py` once (needs internet; installs a 3.7 MB YOLOX-nano model and the 14 MB ONNX Runtime Web WebAssembly runtime, hash-pinned, see [THIRD_PARTY.md](THIRD_PARTY.md)). With it installed, **Select ball** finds the ball with a general-purpose detector running on this machine, fits its radius, and the tracker follows detections instead of a colour patch. If the detector is not installed, the app uses a colour patch and says so (the patch must still sit on a ball-shaped region of one colour or selection is refused). If the detector is installed and sees no ball at your click, selection is refused instead of falling back, because a colour patch will happily track a round logo for the whole window. The detector was not trained or validated on football footage. On three real clips it tracked two lit conditions well and still failed to produce usable contact proposals, a second screening on six other clips found no wrong detections after one fix but showed it gives up on balls under about 25 px across, and a third on six clips in other conditions (sand, indoor floor, night smoke, broadcast) found it can adopt a ball-like object after the real ball leaves the view; see [evaluation/real-footage/REPORT-detector.md](evaluation/real-footage/REPORT-detector.md) and [evaluation/other-footage/REPORT.md](evaluation/other-footage/REPORT.md) and [evaluation/conditions-footage/REPORT.md](evaluation/conditions-footage/REPORT.md) before relying on it. Those reports describe frozen earlier algorithms. A tighter native crop is now tried for small balls, with fallback to the wider motion crop, and ball selection retries a smaller crop when normal views fail. These changes have software regression checks but no independently measured accuracy or speed improvement. Tracking a 30-second window can still take on the order of a minute.

**Optional foot evidence.** Run `python tools/fetch_pose.py`, then enable **Add experimental foot evidence** before tracking. MediaPipe Pose Landmarker Lite runs locally in a cancellable worker. It records ankle, heel and toe landmarks and suggests left/right only when one visible person has one unambiguous nearby foot at a trajectory turn. With this option enabled, unsupported turns are suppressed. Every suggestion remains uncertain: proximity is not proof of contact. Left/right is saved separately from stronger/weaker foot; foot dominance is never guessed. Multiple people, hidden feet, body contacts and missed ball positions require manual review.

Use **Use manual timeline** when tracking is unsuitable. Mark contacts and drops for juggling; pass outcomes and stronger/weaker-foot labels for passing tests; or start, finish and missed-cone events for slalom. Remove mistaken proposals and add missed events, then confirm you checked the entire window and save a reviewed timeline. Each edit creates a new immutable revision.

**Create video assessment** derives counts from that reviewed revision. It requires the complete protocol observation window, and wall passing requires every foot label. Short clips remain useful for review but cannot silently replace a full assessment. An unchanged timeline can create only one assessment. Existing progress records link to their original annotation revision even if the timeline is later edited. All original counts and normal coach corrections remain available.

Feedback states observable labelled outcomes (off-target passes, weaker-foot usage, ball drops or missed cones), connects one or two coaching cues to their source drills, and opens the relevant timestamps. It does not infer a technique diagnosis or biomechanics. The starter coaching guidance retains its draft/review labels. Video runs, labels, provenance and media are included in export and deletion.

This is a **video-assisted Phase 2 prototype**. Colour tracking works best with a distinct ball patch, stable lighting, a fixed camera and little occlusion; similar clothing, pitch markings, blur and camera movement can make it unusable. The detector copes much better with clothing and lighting, but it can lock onto a different, stationary ball, drops out when the ball is dark or blurred, and remains suspect until the correctness limits are calibrated and the full window is reviewed. Coverage measures how often a ball was found, not whether it was the correct ball. Foot side suggestions and pass outcomes require human review. The synthetic regression fixture verifies software behavior, not accuracy on football players. Representative, independently labelled grassroots data and calibrated pose/contact rules are still needed before the automatic-analysis accuracy gate can pass.

**Evaluation labels.** Open the blind labelling tool from Video feedback. Select the original local clip, label visible/absent/occluded ball samples and clear contacts, record conditions and annotator provenance, and export JSON. No predictions are shown. Resume with the exported labels and matching video. Use **Export analysis JSON** to compare a run with these labels; [evaluation/README.md](evaluation/README.md) describes the collection plan and evaluator. The additional public evaluation pack contains 12 downloaded clips and 336 published frame labels; its blind independence, condition coverage and alignment have not been established. It does not calibrate the gate. See [downloaded evaluation material](evaluation/public-football-2026-10-17/README.md).

**Slow or irregular video.** Progress shows sample count, phase and elapsed time; cancellation and navigation stop active tracking. Decode errors explain timestamp/keyframe problems and suggest a constant-frame-rate MP4. With FFmpeg installed, create a separate seek-friendly copy (the original is preserved):

```powershell
python tools/normalize_video.py input.webm normalized.mp4
```

Upload the copy and label it separately: re-encoding changes the video hash. The helper refuses existing output paths, preserves the original and removes partial output on cancellation. FFmpeg shows encoding progress; use Ctrl+C to cancel. Re-encoding is a separate preprocessing step, not a measured general decoding speedup.

## Local Gemma 4 (optional)

Install [Ollama](https://ollama.com/) separately. Quit an already running Ollama server first. In PowerShell:

```powershell
$env:OLLAMA_NO_CLOUD = "1"
ollama serve
```

In another terminal, download one model:

```powershell
ollama pull gemma4:e4b
# Alternatives: gemma4:e2b or gemma4:12b
```

Then choose Ollama in Settings, confirm local-only mode, and save. Downloads require internet; installed local models can run offline. Cloud model tags and remote-backed aliases are rejected. The app sends questions, eligible guidance and recent valid measurements to `127.0.0.1:11434`; it excludes names, videos and authentication credentials. It does not manage Ollama's configuration, so **you must disable its cloud features**. See the [official cloud-disable instructions](https://docs.ollama.com/faq) and [chat API](https://docs.ollama.com/api/chat). The [official model listing](https://ollama.com/library/gemma4) documents the supported tags.

## Architecture and data

`football/domain.py` owns deterministic assessments, comparable progress and adaptation. `knowledge.py` is the original, versioned starter knowledge pack. `store.py` persists settings and append-only events in SQLite. `ai.py` retrieves guidance and invokes a fixed loopback-only Ollama endpoint. `server.py` serves the browser UI and local API using Python's standard library. No external JavaScript, fonts, analytics or CDN assets are required. The optional detector's files are served from an exact allowlist of paths; the Content-Security-Policy adds `'wasm-unsafe-eval'` (WebAssembly only; `eval` stays blocked) so the runtime can start. `web/tracker.js` and `web/detector.js` hold tracking and detection logic, `web/label.html` provides blind frame/contact labelling, `tools/evaluate_tracks.py` checks labelled correctness, and `tools/fetch_detector.py` installs the optional detector.

By default, runtime data is in `.data/football.sqlite3` and `.data/videos/`, excluded from source control. No credentials are collected. The service binds only to loopback, validates Host/Origin, rejects requests that are not same-origin (including `same-site` requests from other local ports), uses an HttpOnly SameSite session cookie named for its own port (so several local instances do not overwrite each other's session) and requires a custom header for mutations. Malformed or pathologically nested JSON is answered with HTTP 400. Static paths are allowlisted. Video filenames are generated; upload types, size and container signatures are checked. These checks are not a full media decoder or malware scanner.

This is a single-player, trusted-device application. The database and exports are not encrypted by the app. Use device login protection and disk encryption. Deleting the workspace cannot erase separately downloaded backups or promise forensic erasure on SSDs. Do not expose this development server to the internet or use it as a hosted multi-user coach portal.

## Tests

```powershell
python -m unittest discover -s tests -v
node --check web/app.js
node --test tests/test_tracker.js tests/test_detector.js tests/test_video_lab.js
```

Tests use temporary directories and an ephemeral local HTTP server. They cover protocol validation, invalid measurements, matching comparisons, immutable review history, eligibility, readiness, progression, duplicate feedback, persistence/deletion, local AI contracts/error handling, cookie/Origin/Host protection, uploads, ranges, exports and malformed requests. Ollama tests mock the provider; a real model download and hardware benchmark are separate checks.

## MVP boundaries

The shared conversation includes later-stage research and deployment proposals. This version implements the local training system and video-assisted feedback prototype. It ships optional general-purpose ball and pose models (not validated on football) and does **not** ship validated automatic rep counts, technique diagnoses, benchmark cohorts, mobile native apps, remote coach accounts, full-match tactics, subscriptions, commercial dataset ingestion, fine-tuning, cloud OAuth/CLI authentication or API billing. These require validated models, rights-cleared/coach-reviewed resources, supported provider integration and further product work. No fabricated output stands in for them.

FIFA and England Football links in the knowledge pack are research references only. Their content and media have not been scraped, imported, or presented as licensed training material.

## Development lifecycle

The project-specific [SDLC integration](sdlc/README.md) uses an isolated copy of `D:\SDLC`. Its records, preview data and worktrees stay separate from the original tool and the player's workspace. See the [validation readiness workflow](evaluation/phase-2026-10-18/README.md) before calibrating correctness thresholds.
