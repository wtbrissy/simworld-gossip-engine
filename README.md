# SimWorld Gossip Engine

> **A tiny AI fishbowl: open your phone and see who is falling apart today.**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-local%20web%20app-green)
![SQLite](https://img.shields.io/badge/SQLite-local%20database-lightgrey)
![Ollama](https://img.shields.io/badge/Ollama-optional-purple)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Status](https://img.shields.io/badge/status-experimental-orange)

SimWorld Gossip Engine is a lightweight local AI town simulator.

It creates a fictional town of 100 virtual residents who live, form relationships, hide secrets, trigger conflicts, fall into crisis, attempt to leave town, and generate daily gossip reports.

Most AI writing starts with a prompt.

**This starts with a town.**

---

## Demo

![SimWorld Gossip Engine Demo](docs/screenshots/demo.gif)

## Overview

![SimWorld Gossip Engine Overview](docs/screenshots/demo-graphic.png)

---

## What Makes It Different

SimWorld does **not** run 100 large language model agents in real time.

Instead, it uses a lighter hybrid approach:

```txt
Structured residents
        ↓
Rule-based daily simulation
        ↓
Relationship and memory updates
        ↓
Story score ranking
        ↓
Gossip and event generation
        ↓
Optional local AI rewriting with Ollama
```

The simulation creates the pressure.

Memory creates consequences.

The gossip engine surfaces the drama.

Optional local AI makes the output more readable.

---

## Core Idea

This project is not trying to perfectly simulate human society.

It is designed around a much less serious question:

> What if you could check a local AI town every day and see who is emotionally collapsing?

It is part life simulation, part emergent storytelling toy, part AI gossip dashboard.

You do not directly write the plot.

You let a town accumulate pressure, secrets, relationships, and consequences.

Then you watch the story surface.

---

## Features

- 100 simulated residents
- Daily world advancement
- Local web app
- Mobile-friendly interface
- Resident profiles
- Goals and hidden secrets
- Health, happiness, stress, wealth, and energy
- Long-term memories
- Dynamic relationships:
  - trust
  - resentment
  - attraction
  - dependency
  - jealousy
- Story score ranking
- Daily town gossip dashboard
- Secret radar: `hidden → suspected → revealed`
- Health crisis events
- Runaway signals
- Public conflict events
- Serial story archive
- Share card page for screenshots
- Optional local AI writing with Ollama
- Runs on a normal Windows machine

---

## Pages

After starting the app, open:

```txt
http://127.0.0.1:8000
```

Main pages:

```txt
/          Home dashboard
/residents Residents
/today     Daily story
/serial    Serial archive
/story     Story candidates
/director  Director view
/writer    Writing material
/gossip    Gossip dashboard
/share     Share card
```

On your phone, use your computer’s local IP address, for example:

```txt
http://192.168.1.23:8000/gossip
```

Your phone and computer must be on the same Wi-Fi network.

---

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/wtbrissy/simworld-gossip-engine.git
cd simworld-gossip-engine
```

### 2. Install dependencies

On Windows:

```bat
install_windows.bat
```

Or manually:

```bash
pip install -r requirements.txt
```

### 3. Start the app

```bat
run_windows.bat
```

Then open:

```txt
http://127.0.0.1:8000
```

---

## Optional: Use Ollama

The app works without Ollama.

Without Ollama, the simulation still runs and generates rule-based gossip.

With Ollama, daily stories, dialogue, and inner monologues become more natural.

Install Ollama, then pull a small local model:

```bash
ollama pull qwen2.5:3b
```

Then run:

```bat
run_with_ai_ollama.bat
```

Recommended local models:

```txt
qwen2.5:3b
llama3.2:3b
```

A 7B model may work, but it will be slower on machines with limited RAM.

---

## Example Gossip

```txt
Today’s Town Gossip

#1 Mia Lee is under pressure
Her health is collapsing, her family repair goal is active, and her secret debt is now suspected.

#2 Luna Zhang still has unfinished business
Her old secret remains unresolved, but her long-term memory score keeps rising.

#3 Nora Zhang may be preparing to leave
Her runaway signal is increasing, but her debt is keeping her tied to town.

#4 A public argument damaged trust
Two residents argued in public after resentment passed the conflict threshold.

#5 The town is not okay
Multiple residents are showing high stress, low health, and unstable relationships.
```

---

## Why Not 100 AI Agents?

Running 100 full LLM agents in real time is expensive, slow, and unnecessary for this kind of project.

SimWorld uses structured simulation first and AI writing second.

This makes it possible to run locally on a modest machine while still producing emergent drama.

In short:

```txt
Rules simulate life.
Memory preserves consequences.
AI turns signals into language.
```

---

## Suggested Workflow

```txt
Advance 7 days
        ↓
Open /gossip
        ↓
Check who is collapsing
        ↓
Open /share
        ↓
Screenshot the town drama
        ↓
Advance again
```

For longer experiments:

```txt
Day 30  → early patterns
Day 75  → main characters emerge
Day 150 → secrets spread
Day 250 → generational damage appears
```

---

## Tech Stack

- Python
- FastAPI
- SQLite
- Jinja2
- HTML/CSS
- Optional Ollama local model integration

---

## Project Philosophy

This is not an AI novel generator.

It is closer to a narrative terrarium.

Or, more simply:

> A tiny AI fishbowl where simulated people slowly ruin their lives.

The point is not to produce a perfect story in one prompt.

The point is to create a small world where drama can accumulate over time.

---

## Roadmap

Possible future upgrades:

- better secret reveal logic
- stronger continuity between daily chapters
- relationship graph visualization
- richer shareable image cards
- configurable town size
- seeded demo towns
- Docker support
- richer event types
- recurring weekly town summaries
- export to Markdown / JSON
- better GitHub demo screenshots
- automated demo GIF generation

---

## Disclaimer

This is an experimental side project.

It is not a scientific social simulation, not a psychological model, and not a serious agent benchmark.

It is a local simulation toy for emergent storytelling, town drama, and AI-assisted gossip generation.

---

## License

MIT License.
