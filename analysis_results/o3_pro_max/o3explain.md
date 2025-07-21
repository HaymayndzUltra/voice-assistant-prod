# Pinaka-Detalyadong Paliwanag: Cursor Features gamit ang o3-pro (Max Mode)

## 1. Max Mode at o3-pro Support
- Ang Max Mode ay nagbibigay ng pinakamalaking context window (up to ~1 million tokens), pinapalakas nito ang kakayahan ni o3-pro para sa large codebases at deep reasoning.
- Kapag naka-enable ang Max Mode, ang Cursor ay gumagamit ng o3-pro para sa mga tasks na nangangailangan ng malawak na context at malalim na analysis.
- Mas mahal at mas mabagal kaysa Lite/Standard Mode, pero essential para sa advanced use cases at complex system changes.


## 2. Background Agents (Cloud AI Agents)
- Background Agents ay asynchronous AI agents na naispawn sa Ubuntu-based remote VM.
- Pwedeng mag-edit, mag-run ng code, mag-test, at mag-push ng changes sa GitHub kahit hindi mo na kailangan hintayin sa IDE.
- Activated sa Cursor via cloud icon o `Ctrl+E`, may panel para mag-launch, mag-follow up, mag-take over anytime.
- Lahat ng agent work ay hiwalay sa local machine, isolated for privacy and security.


## 3. Remote VM at Custom Environment Setup
- Lahat ng agents ay tumatakbo sa Ubuntu VM na may internet access at kakayahang mag-install ng dependencies.
- Environment setup ay configurable via `.cursor/environment.json` para sa basic setup, o Dockerfile para sa custom/multi-container workflows.
- Pwede kang magpa-install ng `npm`, `pip`, `apt` packages, at mag-launch ng dev servers/daemons sa `tmux` session.


## 4. GitOps Integration
- Agents ay awtomatikong nag-clone ng GitHub repo, gumagawa ng sariling branch, at magpu-push ng code changes bilang pull request.
- Requires read-write access sa GitHub repo; seamless handoff sa code review and CI/CD.

## 5. Billing & Usage
- Kahit naka-Pro plan ($20/mo), kailangan naka-enable ang usage-based billing para makagamit ng o3-pro at Background Agents (Max Mode).
- Bawat agent/model call ay may corresponding token usage fee (API pricing), mabilis tumaas kung hindi maingat.
- May option na mag-set ng spending cap para di lumagpas sa budget.
- Feedback mula sa users: runaway agents can incur big charges, kaya monitoring is a must.


## 6. User Control & Transparency
- Merong live status at logs sa dashboard: pwede mag-send ng follow-up prompt, mag-takeover ng agent, at makita ang usage/cost breakdown.
- Pwedeng i-kill/stop ang runaway agent para di lumaki ang cost.
- May logs at audit trail bawat action ng agents.

## 7. Best Use Cases at Performance
- Pinakamabisa si o3-pro para sa:
  - Bug diagnosis & advanced debugging (deep trace)
  - Codebase refactoring & architecture planning
  - Large-scale code search, migration, at automation
  - End-to-end agent flows na nangangailangan ng matinding reasoning
- Mas magastos at mabagal para sa maliit na edits, kaya optional na gamitin ang cheaper models for routine tasks.


## 8. Best Practices at Babala
- Gumamit ng o3-pro lang sa complex/critical tasks (e.g. system analysis, multi-file refactoring).
- Maging SPECIFIC at malinaw sa prompt para iwas recursive/model spam.
- Monitor lagi ang dashboard para sa usage spikes; maglagay ng spend cap.
- Take over agad kapag may kahina-hinalang activity.



# SUMMARY TABLE

| Feature                 | Detalye                                                |
|-------------------------|--------------------------------------------------------|
| Model                   | o3-pro sa Max Mode (~1M tokens, deep context)          |
| Background Agent        | Async cloud agent, runs in Ubuntu VM, auto GitOps      |
| Env Setup               | .cursor/environment.json, Dockerfile                   |
| Billing                 | Usage-based, may spend cap, monitoring recommended     |
| User Control            | Follow-up, takeover, kill agent, logs, audit trail     |
| Best Use Cases          | Debugging, system refactor, automation, deep search    |
| Caution                 | Costly kapag runaway, dapat specific prompts & monitor |



