# 60-Second Demo Film — Production Script

A shot-by-shot script for a ~60s AI-generated demo video of the Agentic On-Call
Incident Response System. Built for **100% AI text-to-video** (Runway / Sora /
Kling / Pika), stylized (no real screen capture), calm AI narrator, **16:9** for
LinkedIn and the portfolio.

> **The one hard constraint:** AI text-to-video cannot render readable text.
> Every number, label, and title in this script is added afterwards in your
> editor (CapCut, Premiere, After Effects) as an overlay. The AI generates the
> *imagery* only — which is why every prompt below ends with "no text".

---

## Structure

| Act | Time | Beat | Color |
|-----|------|------|-------|
| I | 0:00–0:17 | The 3 AM reality — alert, exhaustion, manual grind | amber → red |
| II | 0:17–0:44 | The agent — diagnosis, root cause, the confidence gate, auto-fix | cyan → green |
| III | 0:44–0:56 | Why you can trust it — resilience, honest escalation, audit trail | cyan/amber |
| IV | 0:56–1:00 | Title card | neutral |

The turn at **0:17** is the whole video. Act I should feel cluttered, noisy and
handheld; Act II onward is calm, geometric and locked-off. Let the sound drop to
near-silence for a half-beat at 0:17 — that contrast is what creates curiosity.

---

## Full voiceover (127 words · ~60s at a calm 2.1 words/sec)

Paste this whole block into ElevenLabs or your TTS of choice. Voice direction:
**calm technical documentary narrator, measured, unhurried, quietly confident.
Not a hype promo read.** Slight warmth. Pause where the line breaks are.

```
Three forty-seven AM. Production breaks.

An alert fires. Somebody's night is over.

Now the hunt starts. Logs. Metrics. Runbooks. What shipped today.

Forty-five minutes of pattern-matching — at four in the morning.

So I built an agent that gets there first.

Stage one reads logs and metrics together, and scores severity.

Stage two matches runbooks against the deploy timeline, and commits to a
confidence score.

Above eighty-five percent, it fixes it. In between, it asks a human. Below,
it escalates.

It applied the fix, verified it, closed the incident. Twenty seconds.

When a tool dies mid-investigation, it retries, then continues on partial data.

When it isn't confident, it escalates — with the entire investigation attached.

Every decision it made, logged for the post-mortem.

Not a chatbot. A first responder.
```

---

## Style block — paste into EVERY prompt

Appending the same block to every shot is what keeps 13 separately-generated
clips looking like one film.

```
Cinematic 16:9, photoreal 3D render, dark moody tech aesthetic, deep blue-black
environment, volumetric light shafts, shallow depth of field, subtle film grain,
anamorphic lens flare, 24fps motion blur, high contrast, no text, no letters,
no numbers, no logos, no watermark.
```

**Negative prompt** (where your tool supports one):

```
text, letters, words, numbers, UI screenshots, readable writing, watermark,
logo, subtitles, distorted hands, extra fingers, deformed face, cartoon, anime,
oversaturated, low contrast
```

---

## Shot list

Each shot: generate 3–4 variations, keep the best, trim to the stated duration.

### ACT I — THE 3 AM REALITY

**S01 · 0:00–0:04 · 4s**
- **VO:** "Three forty-seven AM. Production breaks."
- **On-screen text:** `03:47` (mono, small, bottom-left, fades in at 0:01)
- **SFX:** phone buzz against wood; low sub-bass drone begins
- **Prompt:**
  > Extreme close-up of a smartphone lying face-up on a wooden nightstand in a
  > pitch-dark bedroom. The screen ignites with harsh amber-red alert light,
  > spilling across the wood grain and washing up onto the ceiling. Slow push-in
  > with subtle handheld micro-shake. The phone is the only light source in
  > frame. Cold blue ambient moonlight from a window far behind.

**S02 · 0:04–0:08 · 4s**
- **VO:** "An alert fires. Somebody's night is over."
- **On-screen text:** none — let the image breathe
- **SFX:** sheets, a laptop lid opening, a single keystroke
- **Prompt:**
  > Silhouette of a person sitting up in bed in a dark room, opening a laptop.
  > The screen's cold blue light floods their face from below, revealing
  > exhaustion and squinting eyes. Rack focus from the laptop hinge to their
  > face. Static camera, slight low angle, intimate and quiet.

**S03 · 0:08–0:13 · 5s**
- **VO:** "Now the hunt starts. Logs. Metrics. Runbooks. What shipped today."
- **On-screen text:** four words cutting in on the beat — `LOGS` `METRICS` `RUNBOOKS` `DEPLOYS`
- **SFX:** frantic keyboard, layered notification pings
- **Prompt:**
  > Abstract visualization of overwhelming data: dozens of translucent glowing
  > panels of illegible scrolling characters and jagged red graph spikes
  > cascading toward camera through dark space, chaotic, layered and
  > overlapping without order. Fast dolly forward, heavy motion blur,
  > claustrophobic and disorienting.

**S04 · 0:13–0:17 · 4s**
- **VO:** "Forty-five minutes of pattern-matching — at four in the morning."
- **On-screen text:** `45 MINUTES` large, then small beneath: `typical MTTR`
- **SFX:** ticking clock rising in the mix, then everything cuts to silence at 0:17
- **Prompt:**
  > Time-lapse on a dark desk: analog clock hands spinning fast, empty coffee
  > cups accumulating one by one, pale dawn light creeping slowly across the
  > surface. Locked-off static camera, long-exposure light trails, melancholy
  > and still.

### ACT II — THE AGENT

**S05 · 0:17–0:21 · 4s** — *the turn*
- **VO:** "So I built an agent that gets there first."
- **On-screen text:** title reveal — `AGENTIC INCIDENT RESPONSE`
- **SFX:** near-silence, then a single deep resonant tone; a clean pulse begins
- **Prompt:**
  > A single glowing amber orb of light drifts slowly through darkness and is
  > caught by an elegant machined dark-metal aperture, which irises open and
  > swallows it. The surrounding chaos falls away into calm. Slow motion, macro
  > lens, dust motes suspended in volumetric light, cyan glow blooming from
  > deep inside the aperture.

**S06 · 0:21–0:26 · 5s**
- **VO:** "Stage one reads logs and metrics together, and scores severity."
- **On-screen text:** `STAGE 1 — DIAGNOSIS` · then `severity: P1`
- **SFX:** two soft whooshes converging, a chime on the pulse
- **Prompt:**
  > Two ribbons of luminous cyan data flow in from opposite sides of frame and
  > converge into a faceted crystalline node suspended in dark space. The node
  > absorbs them, pulses once, and a concentric ring of light expands outward.
  > Slow precise orbiting camera move, elegant and controlled.

**S07 · 0:26–0:32 · 6s**
- **VO:** "Stage two matches runbooks against the deploy timeline, and commits to a confidence score."
- **On-screen text:** `STAGE 2 — ROOT CAUSE` · then a counter animating `0.00 → 0.92`
- **SFX:** rising tonal sweep as the arc fills; a lock-in click at the end
- **Prompt:**
  > Two vast constellations of glowing points hang facing each other in dark
  > space. Thin threads of light test connections between them one by one, most
  > flickering out, until a single thread ignites bright cyan and holds, linking
  > one point in each constellation. A luminous arc sweeps around that
  > connection and fills like a gauge. Slow dolly in, cinematic, a sense of awe.

**S08 · 0:32–0:39 · 7s** — *the core idea*
- **VO:** "Above eighty-five percent, it fixes it. In between, it asks a human. Below, it escalates."
- **On-screen text:** label each branch as it lights —
  `AUTO-FIX  > 0.85` (green) · `HUMAN REVIEW  0.50–0.85` (amber) · `ESCALATE  < 0.50 or any P0` (red)
- **SFX:** three soft tones, one per branch; a decisive mechanical lock on the green
- **Prompt:**
  > A single beam of cyan light travels along a dark polished channel and
  > reaches a three-way fork. The three diverging paths glow in different
  > colors — green rising to the right, amber running straight ahead, red
  > descending to the left. The beam surges decisively down the green path.
  > Top-down overhead camera slowly rising, geometric and precise.

**S09 · 0:39–0:44 · 5s**
- **VO:** "It applied the fix, verified it, closed the incident. Twenty seconds."
- **On-screen text:** `RESOLVED` · small beneath: `11 steps · 20 seconds`
- **SFX:** mechanical seal, then a warm resolving chord
- **Prompt:**
  > A complex dark machined mechanism with a fractured, angry glowing red seam
  > running through it. Precision components rotate and slide into place,
  > sealing the fracture; the red light drains away and is replaced by steady
  > calm green. Camera pulls back from macro to a wide reveal of the whole
  > mechanism running smoothly. Satisfying mechanical precision.

### ACT III — WHY YOU CAN TRUST IT

**S10 · 0:44–0:49 · 5s**
- **VO:** "When a tool dies mid-investigation, it retries, then continues on partial data."
- **On-screen text:** `tool timeout → classified → 3 retries, exponential backoff → continues on partial data`
- **SFX:** a glitch/static burst on the node death, then steady flow resuming
- **Prompt:**
  > One node in a lattice of glowing cyan nodes flickers, turns red, and goes
  > dark. Three pulsing rings emanate from the dead node and fade. The
  > surrounding light-paths bend and reroute around it, and the network
  > continues flowing without interruption. Medium shot, slow orbit, tension
  > releasing into calm.

**S11 · 0:49–0:53 · 4s**
- **VO:** "When it isn't confident, it escalates — with the entire investigation attached."
- **On-screen text:** `confidence 0.70 → HUMAN REVIEW → escalated with full context`
- **SFX:** warm rising swell
- **Prompt:**
  > A broad beam of amber light rises through darkness toward a human silhouette
  > standing above, carrying with it a glowing translucent stack of layered
  > document planes. The silhouette reaches down toward the light. Low angle
  > looking up, volumetric god-rays, reverent and warm.

**S12 · 0:53–0:56 · 3s**
- **VO:** "Every decision it made, logged for the post-mortem."
- **On-screen text:** `AUDIT TRAIL — every node, every decision, every retry`
- **SFX:** rhythmic soft ticks as entries pass
- **Prompt:**
  > A tall vertical ribbon of glowing horizontal entries scrolls steadily upward
  > through dark space, each entry a small luminous bar receding into depth,
  > endless. Locked-off static camera, cool cyan light, the feeling of a
  > complete permanent archive.

### ACT IV — CLOSE

**S13 · 0:56–1:00 · 4s**
- **VO:** "Not a chatbot. A first responder."
- **On-screen text:** `AGENTIC ON-CALL INCIDENT RESPONSE` · beneath: `LangGraph · Python · FastAPI` · then your GitHub handle
- **SFX:** single held chord, soft impact on the title, tail out
- **Prompt:**
  > Slow drift forward through dark empty space with faint drifting light
  > particles and a soft cyan glow along the horizon line. Clean, minimal,
  > large area of empty negative space in the center of frame. Very slow forward
  > dolly, calm and final.

---

## Post-production checklist

1. **Generate** each shot 3–4 times; AI video is a lottery, pick the best take.
2. **Trim** each clip to its stated duration — most tools output 5–10s.
3. **Add all text in your editor.** Nothing readable comes from the AI clips.
   Use one mono typeface (JetBrains Mono / IBM Plex Mono) for data values and
   one clean sans (Inter / Archivo) for titles. Keep every overlay in the same
   two positions across the film.
4. **Burn in captions.** LinkedIn autoplays muted — assume the first viewing has
   no sound. The video must work silently.
5. **Grade** all clips together for a consistent teal-and-amber look, or the
   cuts will feel like 13 different films.
6. **Sound:** tense sparse drone in Act I → half-beat of silence at 0:17 →
   minimal building electronic pulse through Act II → sustained and confident in
   Act III → single resolving chord on the title.
7. **Export** 1920×1080, H.264, and check it reads on a phone screen.

## Claims you can defend

If someone asks "is that real?", these are measured from actual runs:

| Claim in the film | Where it comes from |
|---|---|
| resolved in ~20 seconds | measured live over HTTP: 19.1s and 21.1s with tool failures injected; 4.1s on a clean local run |
| confidence 0.92, 11 steps | measured on INC-001 through the live server |
| 0.85 auto-fix / 0.50 escalate thresholds | `config.py` — `AUTO_FIX_THRESHOLD`, `HITL_LOWER_THRESHOLD` |
| P0 never auto-resolves | `config.py` — `NO_AUTO_RESOLVE_SEVERITIES` |
| 3 retries, exponential backoff | `config.py` — `MAX_RETRIES_PER_TOOL`, `RETRY_BACKOFF_SECONDS` (1s/3s/10s) |
| confidence 0.70 → human review → escalated | measured live: INC-018 with `{"runbooks":"timeout"}` injected |
| continues on partial data | measured live: INC-016 with `{"metrics":"timeout"}` injected still resolved |

**One caveat:** the *"forty-five minutes"* in Act I is an industry-typical MTTR,
**not** something this project measured. It is fair as a general statement about
manual incident response, but don't present it as your own benchmark. If you
want to be conservative, change the line to "an hour of pattern-matching" or
"however long it takes a human to find it".

## If you want 90 seconds instead

Add three shots after S09 and re-pace the VO:
- **the dead letter queue** — a run that exceeds its step budget being caught and
  preserved rather than lost (the kill switch at 20 steps)
- **crash recovery** — the machine halting mid-run and resuming exactly where it
  stopped, from the SQLite checkpoint
- **the evaluation** — 20 incidents running as a batch, each landing green,
  amber or red, with the scoreboard resolving at the end
