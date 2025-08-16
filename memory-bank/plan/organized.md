#	Category	Item / Symptom	Why It Matters	Evidence Hint
C-1	Port-Layout Conflict	Dozens of ${PORT_OFFSET}+NNNN entries but PORT_OFFSET undefined system-wide	All services may bind to port +NNNN literal → startup failure	startup_config.yaml, CI YAML
C-2	Service Duplication	ObservabilityDashboardAPI and UnifiedObservabilityCenter both on MainPC	Metrics fragmentation & extra 8001/9007 ports	plan.md lines 155, 120; main config 611 & 213
C-3	Missing Dockerfiles	ServiceRegistry, SystemDigitalTwin, TieredResponder lack Dockerfiles	CI build breaks → cannot containerise required:true services	services/ tree vs plan.md 112–113, 158
C-4	GPU/CPU Mis-placement	Several CPU-only agents mapped to GPU family images (e.g., Responder, EmpathyAgent)	Wasted GPU VRAM & larger images	plan.md 138, 152 family-torch-cu121
C-5	Legacy Image Drift	10+ agents still on legacy-py310-cpu though Python 3.11 base is default	Security patches & dep divergence	plan.md 133–137
C-6	Security Exposure	SelfHealingSupervisor mounts /var/run/docker.sock RW	Container breakout root-equivalent	supervisor.py line 6, config 144