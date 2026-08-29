# 60-Second Demo Film — Veo Shooting Script

A shot-by-shot script for an AI-generated demo video of the Agentic On-Call
Incident Response System. Every prompt is written for **Google Veo in the Gemini
app**: paste one, generate, move to the next. Stylized (no screen capture),
separate AI narrator, **16:9** for LinkedIn and the portfolio.

Working copy with copy-to-clipboard buttons:
<https://claude.ai/code/artifact/05eaec9c-d8de-464e-856a-a89f8be3838f>

---

## How to run this in Gemini

1. **Paste one prompt at a time.** Veo has no memory between clips, so every
   prompt is self-contained and repeats the same style sentence verbatim — that
   repetition is what makes 13 separate generations look like one film. Don't
   paraphrase it.
2. **Set the clip length** to each shot's `gen` value. Veo produces 4, 6 or 8
   second clips — nothing in between — so a 5-second shot is generated at 6s and
   trimmed.
3. **Generate 3–4 takes** of each shot and keep the best.
4. **Veo makes the sound too.** Each prompt carries its own `SFX:` and
   `Ambient noise:` lines, so effects come out synchronized to the action. You
   only add a music bed and the narration.
5. **Every prompt ends by refusing dialogue and text.** Leave that line in —
   without it Veo invents mumbled speech and garbled subtitles that fight your
   voiceover.

> **Let Veo handle imagery, not data.** It renders short text better than most
> models but still garbles precise values, and `0.92` rendered as `0.29`
> undermines the film. Generate clean plates with no text, then add every number
> and label as an overlay in CapCut or Premiere.

Total generated: 66s → cut to 60s.

---

## Structure

| Act | Time | Beat |
|-----|------|------|
| I | 0:00–0:17 | The 3 AM reality — alert, exhaustion, manual grind |
| II | 0:17–0:44 | The agent — diagnosis, root cause, confidence gate, auto-fix |
| III | 0:44–0:56 | Why you can trust it — resilience, honest escalation, audit trail |
| IV | 0:56–1:00 | Title card |

The turn at **0:17** is the whole video. Act I is cluttered, noisy and handheld;
everything after is calm, geometric and locked-off. Cut the music to
near-silence for half a beat at that edit — the contrast is what creates
curiosity.

---

## Full voiceover (127 words · ~60s)

Generate separately in ElevenLabs and lay over the cut — do **not** ask Veo to
speak it. Direction: **calm technical documentary narrator**, measured,
unhurried, quietly confident. Not a hype promo read. Pause at each line break.

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

## The 13 prompts

Each follows Veo's formula — cinematography, subject, action, context, then
style and ambiance — with audio specified explicitly.

### ACT I — THE 3 AM REALITY

#### S01 · 0:00–0:04 · 4s · **gen 4s** · cold open
- **VO:** "Three forty-seven AM. Production breaks."
- **Overlay in post:** `03:47`

```
Slow push-in extreme close-up with subtle handheld micro-shake. A smartphone
lying face-up on a wooden nightstand. The screen suddenly ignites with harsh
amber-red alert light that spills across the wood grain and washes up onto the
ceiling. A pitch-dark bedroom at night, the phone the only light source in
frame, faint cold blue moonlight from a window far behind. Cinematic photoreal
render, dark moody tech aesthetic, deep blue-black palette with electric cyan
and amber accents, volumetric light, shallow depth of field, subtle film grain,
anamorphic lens flare, high contrast.
SFX: a phone buzzing hard against wood, twice.
Ambient noise: the dead silence of a bedroom at night, a faint low hum.
No spoken dialogue, no voiceover, no subtitles, no captions, no on-screen text,
no logos, no watermark.
```

#### S02 · 0:04–0:08 · 4s · **gen 4s**
- **VO:** "An alert fires. Somebody's night is over."
- **Overlay in post:** none — let the image breathe

```
Static medium shot at a slight low angle, rack focus from the laptop hinge to
the face. The silhouette of a tired person sitting up in bed, opening a laptop.
The screen's cold blue light floods their face from below, revealing exhaustion
and squinting eyes. A dark bedroom in the hours before dawn. Cinematic photoreal
render, dark moody tech aesthetic, deep blue-black palette with electric cyan
and amber accents, volumetric light, shallow depth of field, subtle film grain,
anamorphic lens flare, high contrast.
SFX: bedsheets shifting, a laptop lid opening, a single keystroke.
Ambient noise: quiet room tone, a distant refrigerator hum.
No spoken dialogue, no voiceover, no subtitles, no captions, no on-screen text,
no logos, no watermark.
```

#### S03 · 0:08–0:13 · 5s · **gen 6s → trim** · the manual grind
- **VO:** "Now the hunt starts. Logs. Metrics. Runbooks. What shipped today."
- **Overlay in post:** `LOGS` `METRICS` `RUNBOOKS` `DEPLOYS` — cut each in on the beat

```
Fast dolly forward with heavy motion blur, claustrophobic framing. Dozens of
translucent glowing panels covered in illegible scrolling characters, alongside
jagged red graph spikes, cascading toward camera through dark space, chaotic and
layered, overlapping without order. An infinite dark digital void. Cinematic
photoreal render, dark moody tech aesthetic, deep blue-black palette with
electric cyan and amber accents, volumetric light, shallow depth of field,
subtle film grain, anamorphic lens flare, high contrast.
SFX: a frantic mechanical keyboard, layered notification pings piling up until
they overwhelm.
Ambient noise: a rising electrical hum building in pressure.
No spoken dialogue, no voiceover, no subtitles, no captions, no on-screen text,
no logos, no watermark.
```

#### S04 · 0:13–0:17 · 4s · **gen 4s**
- **VO:** "Forty-five minutes of pattern-matching — at four in the morning."
- **Overlay in post:** `45 MINUTES` / `typical MTTR`

```
Locked-off static wide shot, time-lapse with long-exposure light trails. An
analog desk clock and a growing collection of empty coffee cups on a dark desk.
The clock hands spin fast while cups accumulate one by one and pale dawn light
creeps slowly across the surface. A home office at the end of a long night.
Cinematic photoreal render, dark moody tech aesthetic, deep blue-black palette
with electric cyan and amber accents, volumetric light, shallow depth of field,
subtle film grain, anamorphic lens flare, high contrast.
SFX: a clock ticking, gradually accelerating.
Ambient noise: very faint early morning birdsong outside a closed window.
No spoken dialogue, no voiceover, no subtitles, no captions, no on-screen text,
no logos, no watermark.
```

### ACT II — THE AGENT

#### S05 · 0:17–0:21 · 4s · **gen 4s** · the turn
- **VO:** "So I built an agent that gets there first."
- **Overlay in post:** `AGENTIC INCIDENT RESPONSE` (title reveal)

```
Slow-motion macro shot with a slow push-in. A single glowing amber orb of light
drifting through darkness toward an elegant machined dark-metal aperture. The
aperture irises open and swallows the orb, and cyan light blooms from deep inside
it as the surrounding chaos falls away into calm. A void of darkness with dust
motes suspended in shafts of light. Cinematic photoreal render, dark moody tech
aesthetic, deep blue-black palette with electric cyan and amber accents,
volumetric light, shallow depth of field, subtle film grain, anamorphic lens
flare, high contrast.
SFX: one deep resonant tone, then a precise mechanical iris click.
Ambient noise: near silence, then a clean rhythmic electronic pulse beginning.
No spoken dialogue, no voiceover, no subtitles, no captions, no on-screen text,
no logos, no watermark.
```

#### S06 · 0:21–0:26 · 5s · **gen 6s → trim** · diagnosis
- **VO:** "Stage one reads logs and metrics together, and scores severity."
- **Overlay in post:** `STAGE 1 — DIAGNOSIS` / `severity: P1`

```
Slow precise orbiting camera move. Two ribbons of luminous cyan data and a
faceted crystalline node suspended in dark space. The ribbons flow in from
opposite sides of frame and converge into the node, which absorbs them, pulses
once, and emits an expanding concentric ring of light. An empty dark void with
depth and drifting particles. Cinematic photoreal render, dark moody tech
aesthetic, deep blue-black palette with electric cyan and amber accents,
volumetric light, shallow depth of field, subtle film grain, anamorphic lens
flare, high contrast.
SFX: two soft whooshes converging, then a clean bell chime on the pulse.
Ambient noise: a low steady electronic pulse.
No spoken dialogue, no voiceover, no subtitles, no captions, no on-screen text,
no logos, no watermark.
```

#### S07 · 0:26–0:32 · 6s · **gen 6s** · root cause
- **VO:** "Stage two matches runbooks against the deploy timeline, and commits to a confidence score."
- **Overlay in post:** `STAGE 2 — ROOT CAUSE` / counter `0.00 → 0.92`

```
Slow cinematic dolly in on a wide composition. Two vast constellations of glowing
points hanging facing each other in dark space. Thin threads of light test
connections between the two constellations one by one, most flickering out and
dying, until a single thread ignites bright cyan and holds, linking one point in
each constellation; a luminous arc then sweeps around that connection and fills
like a gauge. Deep dark space with a sense of scale and awe. Cinematic photoreal
render, dark moody tech aesthetic, deep blue-black palette with electric cyan and
amber accents, volumetric light, shallow depth of field, subtle film grain,
anamorphic lens flare, high contrast.
SFX: rapid soft ticks as threads test and fail, a rising tonal sweep as the arc
fills, then a single decisive lock-in click.
Ambient noise: a deep resonant space hum.
No spoken dialogue, no voiceover, no subtitles, no captions, no on-screen text,
no logos, no watermark.
```

#### S08 · 0:32–0:39 · 7s · **gen 8s → trim** · the core idea
- **VO:** "Above eighty-five percent, it fixes it. In between, it asks a human. Below, it escalates."
- **Overlay in post:** `AUTO-FIX > 0.85` (green) / `HUMAN REVIEW 0.50–0.85` (amber) / `ESCALATE < 0.50 or any P0` (red)

```
Top-down overhead shot, camera slowly rising. A single beam of cyan light
travelling along a dark polished channel toward a three-way fork. The beam
reaches the fork, where the three diverging paths light up in different colors,
green rising to the right, amber running straight ahead, red descending to the
left, and then the beam surges decisively down the green path. A precise
geometric dark environment of machined channels. Cinematic photoreal render,
dark moody tech aesthetic, deep blue-black palette with electric cyan and amber
accents, volumetric light, shallow depth of field, subtle film grain, anamorphic
lens flare, high contrast.
SFX: three soft distinct tones, one as each path lights, then a decisive
mechanical lock as the beam commits.
Ambient noise: a low pulsing electronic bed.
No spoken dialogue, no voiceover, no subtitles, no captions, no on-screen text,
no logos, no watermark.
```

#### S09 · 0:39–0:44 · 5s · **gen 6s → trim** · the payoff
- **VO:** "It applied the fix, verified it, closed the incident. Twenty seconds."
- **Overlay in post:** `RESOLVED` / `11 steps · 20 seconds`

```
Camera pulls back from a macro detail to a wide reveal. A complex dark machined
mechanism with a fractured, angry glowing red seam running through it. Precision
components rotate and slide into place, sealing the fracture; the red light
drains away and is replaced by steady calm green as the whole mechanism settles
into smooth motion. A dark workshop void lit only by the mechanism itself.
Cinematic photoreal render, dark moody tech aesthetic, deep blue-black palette
with electric cyan and amber accents, volumetric light, shallow depth of field,
subtle film grain, anamorphic lens flare, high contrast.
SFX: metal sliding and seating, a solid mechanical seal, then a warm resolving
chord.
Ambient noise: a smooth confident machine hum.
No spoken dialogue, no voiceover, no subtitles, no captions, no on-screen text,
no logos, no watermark.
```

### ACT III — WHY YOU CAN TRUST IT

#### S10 · 0:44–0:49 · 5s · **gen 6s → trim** · resilience
- **VO:** "When a tool dies mid-investigation, it retries, then continues on partial data."
- **Overlay in post:** `tool timeout` → `classified` → `3 retries, exponential backoff` → `continues on partial data`

```
Medium shot with a slow orbiting camera move. A lattice of glowing cyan nodes
connected by flowing light paths. One node flickers, turns red and goes dark;
three pulsing rings emanate outward from the dead node and fade; the surrounding
light paths then bend and reroute around it, and the network continues flowing
without interruption. An endless dark digital space. Cinematic photoreal render,
dark moody tech aesthetic, deep blue-black palette with electric cyan and amber
accents, volumetric light, shallow depth of field, subtle film grain, anamorphic
lens flare, high contrast.
SFX: an electrical glitch and static burst as the node dies, three soft retry
pings, then steady flow resuming.
Ambient noise: a steady electronic pulse that never stops.
No spoken dialogue, no voiceover, no subtitles, no captions, no on-screen text,
no logos, no watermark.
```

#### S11 · 0:49–0:53 · 4s · **gen 4s** · honest escalation
- **VO:** "When it isn't confident, it escalates — with the entire investigation attached."
- **Overlay in post:** `confidence 0.70` / `HUMAN REVIEW` / `escalated with full context`

```
Low angle looking steeply upward, volumetric god-rays. A broad beam of amber
light and the silhouette of a person standing high above. The beam rises through
darkness toward the silhouette carrying a glowing translucent stack of layered
document planes, and the silhouette reaches down toward the light. A
cathedral-like dark space with depth above. Cinematic photoreal render, dark
moody tech aesthetic, deep blue-black palette with electric cyan and amber
accents, volumetric light, shallow depth of field, subtle film grain, anamorphic
lens flare, high contrast.
SFX: a warm rising swell.
Ambient noise: a soft reverent low hum with gentle reverb.
No spoken dialogue, no voiceover, no subtitles, no captions, no on-screen text,
no logos, no watermark.
```

#### S12 · 0:53–0:56 · 3s · **gen 4s → trim** · the receipts
- **VO:** "Every decision it made, logged for the post-mortem."
- **Overlay in post:** `AUDIT TRAIL — every node, every decision, every retry`

```
Locked-off static camera. A tall vertical ribbon of glowing horizontal entries,
each a small luminous bar, receding into depth. The ribbon scrolls steadily
upward through dark space, endless and orderly. A cool archival void. Cinematic
photoreal render, dark moody tech aesthetic, deep blue-black palette with
electric cyan and amber accents, volumetric light, shallow depth of field,
subtle film grain, anamorphic lens flare, high contrast.
SFX: rhythmic soft mechanical ticks as each entry passes.
Ambient noise: a cool steady archival hum.
No spoken dialogue, no voiceover, no subtitles, no captions, no on-screen text,
no logos, no watermark.
```

### ACT IV — CLOSE

#### S13 · 0:56–1:00 · 4s · **gen 4s** · end card
- **VO:** "Not a chatbot. A first responder."
- **Overlay in post:** `AGENTIC ON-CALL INCIDENT RESPONSE` / `LangGraph · Python · FastAPI` / your GitHub handle

```
Very slow forward dolly through empty space. Faint drifting light particles
catching the light, with a soft cyan glow along a distant horizon line. Dark,
clean and minimal, with a large area of empty negative space in the center of
frame. Calm and final. Cinematic photoreal render, dark moody tech aesthetic,
deep blue-black palette with electric cyan and amber accents, volumetric light,
shallow depth of field, subtle film grain, anamorphic lens flare, high contrast.
SFX: a single held chord with a soft low impact, then tailing out into silence.
Ambient noise: deep quiet with a faint sub-bass presence.
No spoken dialogue, no voiceover, no subtitles, no captions, no on-screen text,
no logos, no watermark.
```

---

## Saving generations with timestamp prompting

Veo can direct several shots inside one clip if you give it timestamps. Pairing
adjacent shots into one 8-second generation halves your credit spend on Act I.
Keep the hero shots (S07, S08, S09) separate so you can re-roll them
independently.

```
[00:00-00:04] Slow push-in extreme close-up. A smartphone lying face-up on a
wooden nightstand in a pitch-dark bedroom. The screen ignites with harsh
amber-red alert light spilling across the wood grain and washing onto the
ceiling, the only light source in frame.
[00:04-00:08] Cut to a static medium shot at a slight low angle. The silhouette
of a tired person sitting up in bed, opening a laptop; the screen's cold blue
light floods their face from below, revealing exhaustion.
Cinematic photoreal render, dark moody tech aesthetic, deep blue-black palette
with electric cyan and amber accents, volumetric light, shallow depth of field,
subtle film grain, anamorphic lens flare, high contrast.
SFX: a phone buzzing hard against wood, then bedsheets shifting and a laptop lid
opening.
Ambient noise: the dead silence of a bedroom at night.
No spoken dialogue, no voiceover, no subtitles, no captions, no on-screen text,
no logos, no watermark.
```

---

## Assembling the cut

1. **Trim each clip** to the duration on its slate and lay them in order. You
   generated 66 seconds; the cut is 60.
2. **Add every text overlay.** One mono face for data values, one clean sans for
   titles; keep each overlay in the same two screen positions throughout.
3. **Lay the narration** over the top and nudge clip lengths so each line lands
   inside its shot. The VO is the master timing reference, not the visuals.
4. **Keep Veo's audio** underneath at low level — it is already synchronized —
   and add one music bed across the whole film.
5. **Cut the music to near-silence at 0:17** for half a beat. Most important
   edit in the video.
6. **Burn in captions.** LinkedIn autoplays muted; the film must work silently.
7. **Grade all clips together** toward one teal-and-amber look, export
   1920×1080 H.264, and watch it once on a phone.

## Claims you can defend

| Claim in the film | Where it comes from |
|---|---|
| resolved in ~20 seconds | measured live over HTTP: 19.1s and 21.1s with tool failures injected; 4.1s clean local run |
| confidence 0.92, 11 steps | measured on INC-001 through the live server |
| 0.85 / 0.50 thresholds | `config.py` — `AUTO_FIX_THRESHOLD`, `HITL_LOWER_THRESHOLD` |
| P0 never auto-resolves | `config.py` — `NO_AUTO_RESOLVE_SEVERITIES` |
| 3 retries, exponential backoff | `config.py` — `RETRY_BACKOFF_SECONDS` (1s/3s/10s) |
| confidence 0.70 → human review → escalated | measured live: INC-018 with `{"runbooks":"timeout"}` injected |
| continues on partial data | measured live: INC-016 with `{"metrics":"timeout"}` injected still resolved |

**One caveat:** the *"forty-five minutes"* in Act I is an industry-typical MTTR,
**not** something this project measured. Fair as a general statement about manual
incident response, but don't present it as your own benchmark. To stay
conservative, change the line to "however long it takes a human to find it".

## If you want 90 seconds

Add three shots after S09 and re-pace the VO:
- **the dead letter queue** — a run that blows its 20-step budget being caught
  and preserved rather than silently lost
- **crash recovery** — the machine halting mid-run and resuming exactly where it
  stopped, from the SQLite checkpoint
- **the evaluation** — 20 incidents running as a batch, each landing green,
  amber or red, with the scoreboard resolving at the end
