# Format Proposal: @tasks_active.json

## Analysis

Ang `@tasks_active.json` ay isang JSON file na naglalaman ng listahan ng mga aktibong tasks o jobs sa isang system. Karaniwan itong ginagamit para sa monitoring, orchestration, o status tracking ng mga running na proseso. Ang bawat entry ay nagrerepresenta ng isang task na may mga detalye tulad ng pangalan, estado, resource usage, at iba pa.

### Typical Fields (based on common patterns and orchestration needs):

- `task_id` (string): Unique identifier ng task
- `name` (string): Pangalan ng task o job
- `status` (string): Estado ng task (e.g., "running", "pending", "failed", "completed")
- `host` (string): Saan tumatakbo ang task (e.g., "MainPC", "PC2")
- `start_time` (ISO8601 string): Kailan nagsimula ang task
- `end_time` (ISO8601 string, optional): Kailan natapos (kung applicable)
- `resources` (object): Resource usage (e.g., CPU, RAM, GPU, VRAM)
    - `cpu_pct` (number)
    - `ram_mb` (number)
    - `gpu` (string, optional)
    - `vram_mb` (number, optional)
- `priority` (integer): Priority level (1=highest)
- `owner` (string): User o agent na nag-launch ng task
- `meta` (object): Iba pang metadata (labels, tags, etc.)

## Example Format