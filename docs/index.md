---
title: Home
description: Local AI D&D campaign co-pilot — world state tracking, entity extraction, and RAG over campaign lore.
---

# Shared World — Campaign Engine

A local, containerized AI campaign management co-pilot for D&D (West Marches
style). It tracks long-term world state, extracts entities (NPCs, locations,
factions, items, quests) from session narration, persists that state, and
answers questions over campaign lore using retrieval-augmented generation
(RAG).

## Why

West Marches campaigns span many independent sessions and player groups
exploring a shared, persistent world. Keeping that world consistent — who's
alive, what's been discovered, what changed last session — is a manual
bookkeeping burden. This project offloads that bookkeeping to a local agent
that both DMs and players can query.

## Core capabilities

- **Long-term world state tracking** — structured entities persisted in
  Postgres, not just chat history.
- **Entity extraction** — the agent pulls NPCs/locations/factions/items/quests
  out of freeform narration as it happens.
- **RAG over campaign lore** — `pgvector`-backed semantic search over past
  sessions and world documents.
- **Fully local** — inference via Ollama, no data leaves the machine.

See [Architecture](architecture.md) for the technical design and
[Setup](setup.md) to run it locally.

## Planned features

The four features below are the next things to build. See
[Architecture](architecture.md) for how each one fits into the existing
design, and [Roadmap](roadmap.md) for the phased build plan (not started
yet).

### 1. Graph RAG (Entity & Faction Relation Mapping)
Standard vector search (RAG) is great for finding a specific sentence about a past event, but it's terrible at tracking interconnected relationships over time. In a West Marches game, everything is connected.

Instead of just storing chunks of text, your ingestion pipeline can use an LLM purely for Named Entity Recognition (NER) and Relationship Extraction.

 - The Implementation: When you upload a session log, the AI extracts nodes (e.g., Player: Thia, NPC: Captain Vael, Faction: The Iron Ring, Location: Shadowbrook) and defines the directional edges between them (e.g., Thia -> KILLED -> Captain Vael and Captain Vael -> LEADER OF -> The Iron Ring).
 - The Tech: You can store these vectors in a hybrid graph-vector database.
 - The DM Value: You can query: "What are the current political relationships in Shadowbrook after Group A's raid?" The system doesn't generate a story—it queries the graph and returns a structured list of geopolitical shifts.
 
### 2. Automated Rumor Mill & Town Notice Board (Player-Facing)
The biggest bottleneck in a 25+ player West Marches campaign is cross-table communication. If Group A discovers a ruined tower on Tuesday, Group B playing on Friday needs a way to find out about it in-character.
 - The Implementation: You build an asynchronous pipeline. When a DM approves a session log, a background worker runs a structured prompt: "Based on these events, generate 3 short, out-of-character 'Rumors' or 'Notice Board Bullets' that would filter back to the home base city."
 - The Tech: A Python background worker (Celery or Redis Queue) that intercepts the approved log, processes it via an LLM API using strict JSON schemas (using Pydantic), and writes to a database.
 - The DM Value: Complete automated campaign engagement. The system can automatically push these rumors to a dedicated #town-notice-board Discord channel via a webhook, prompting the next group of players to schedule a session to investigate.

### 3. The "Schrödinger’s Hex" Content Auditor (Conflict Detector)
In a West Marches game, multiple DMs often share the same map. If DM Greg runs a game in Hex 0412 on Monday and populates it with an abandoned monastery, and DM Sarah runs a game nearby on Wednesday, they might accidentally contradict each other's lore.

 - The Implementation: A conflict-detection system. When a DM enters notes for an upcoming session ("I'm planning an encounter with a red dragon in the Whispering Caves"), the backend triggers a semantic vector search restricted to a spatial metadata tag (e.g., checking only logs tagged within a 2-hex radius of the Whispering Caves).
 - The Tech: Utilizing metadata filtering in your vector database (like Supabase pgvector or Pinecone). The LLM acts as a strict classification agent: Is there a conflict between [Proposed Session] and [Historical Logs]? (Yes/No) + Explanation.
 - The DM Value: It acts as a silent co-DM auditor. It flags a warning: "Hey, Group C collapsed the entrance to the Whispering Caves three weeks ago. The red dragon wouldn't be accessible unless it dug its way out."

### 4. Multi-DM Session Log Intake Pipeline
To show off true enterprise-level software engineering skills, the project needs an ingestion pipeline that handles messy data. DMs write notes differently: one might paste bullet points, another might write a narrative story, and a third might upload a transcript of their voice notes.

 - The Implementation: Build an ingestion framework that standardizes data using a multimodal pipeline.
 - The Tech:If a DM uploads an audio file of their post-game thoughts, trigger an asynchronous job using an audio transcription API (like Whisper).Run the text through a formatting LLM layer that doesn't add content, but formats the text into a strict, unified JSON schema: Date, Players, Location, Key Achievements, Casualties, Open Plot Hooks.
 - The DM Value: Zero tedious formatting work for the GMs. They braindump their notes, and the pipeline perfectly structures it for the campaign database.