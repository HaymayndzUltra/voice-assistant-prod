#!/usr/bin/env python3
"""
VramOptimizationModule
- Event-driven VRAM optimization module for ModelOps Coordinator
- Subscribes to:
  * models.model.loaded (CSV: model_id,model_type,vram_mb,device,ts)
  * memory.pressure.warning (CSV: device,usage_mb,total_mb,severity,ts)
- Maintains in-memory map of loaded models
- In dry-run mode, computes an OptimizationPlan and logs actions
"""
import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Callable

from ..adapters.event_bus_adapter import EventBusAdapter


@dataclass
class OptimizationAction:
    action: str
    model_id: str
    device: str
    expected_freed_mb: int


@dataclass
class OptimizationPlan:
    actions: List[OptimizationAction]
    expected_freed_mb: int
    strategy: str
    confidence: float


class VramOptimizationModule:
    def __init__(self, bus: EventBusAdapter, logger, dry_run: bool = True, budget_pct: float = 0.85,
                 apply_unload: Optional[Callable[[str], bool]] = None) -> None:
        self.bus = bus
        self.logger = logger
        self.dry_run = dry_run
        self.budget_pct = budget_pct
        self.loaded_models: Dict[str, Dict[str, Any]] = {}
        self._started = False
        self._apply_unload = apply_unload

    async def start(self) -> None:
        if self._started:
            return
        await self.bus.start()
        await self.bus.subscribe("models.model.loaded", self._on_model_loaded)
        await self.bus.subscribe("memory.pressure.warning", self._on_memory_pressure)
        self._started = True
        self.logger.info("VramOptimizationModule started (dry_run=%s, budget_pct=%.2f)", self.dry_run, self.budget_pct)

    async def _on_model_loaded(self, data: bytes) -> None:
        try:
            model_id, model_type, vram_mb, device, ts = data.decode().split(",")
            self.loaded_models[model_id] = {
                "model_type": model_type,
                "vram_mb": int(vram_mb),
                "device": device,
                "ts": float(ts),
            }
            self.logger.info("[VRAM] Loaded model tracked: %s (%sMB) on %s", model_id, vram_mb, device)
        except Exception as e:
            self.logger.error("Failed to parse model.loaded event: %s", e)

    async def _on_memory_pressure(self, data: bytes) -> None:
        try:
            device, usage_mb, total_mb, severity, ts = data.decode().split(",")
            usage_mb, total_mb = int(usage_mb), int(total_mb)
            budget_mb = int(total_mb * self.budget_pct)
        except Exception as e:
            self.logger.error("Failed to parse memory.pressure.warning event: %s", e)
            return

        if usage_mb < budget_mb:
            self.logger.debug("[VRAM] Pressure OK on %s: %d/%dMB", device, usage_mb, total_mb)
            return

        plan = self._build_plan(device=device, usage_mb=usage_mb, budget_mb=budget_mb)
        if not plan.actions:
            self.logger.warning("[VRAM] No candidates to unload on %s under pressure", device)
            return

        if self.dry_run or self._apply_unload is None:
            self.logger.info(
                "[VRAM] Dry-run plan on %s: free %dMB via %s",
                device,
                plan.expected_freed_mb,
                [a.model_id for a in plan.actions],
            )
            return

        # Enforcement path
        freed = 0
        for a in plan.actions:
            try:
                ok = self._apply_unload(a.model_id)
                self.logger.info("[VRAM] Unload %s result=%s", a.model_id, ok)
                if ok:
                    freed += a.expected_freed_mb
                    self.loaded_models.pop(a.model_id, None)
                if usage_mb - freed <= budget_mb:
                    break
            except Exception as e:
                self.logger.error("[VRAM] Failed to unload %s: %s", a.model_id, e)

    def _build_plan(self, device: str, usage_mb: int, budget_mb: int) -> OptimizationPlan:
        # oldest-first (ts ascending), skip critical models by naming heuristic
        candidates = sorted(self.loaded_models.items(), key=lambda kv: kv[1]["ts"])
        plan = OptimizationPlan(actions=[], expected_freed_mb=0, strategy="EMERGENCY", confidence=0.6)
        for mid, meta in candidates:
            if meta.get("device") != device:
                continue
            if "critical" in str(meta.get("model_type", "")).lower():
                continue
            plan.actions.append(OptimizationAction("UNLOAD", mid, device, int(meta.get("vram_mb", 0))))
            plan.expected_freed_mb += int(meta.get("vram_mb", 0))
            if usage_mb - plan.expected_freed_mb <= budget_mb:
                break
        return plan

    async def emit_model_loaded(self, model_id: str, model_type: str, vram_mb: int, device: str) -> None:
        # Helper for local tests: emit an event into the bus
        payload = f"{model_id},{model_type},{vram_mb},{device},{time.time()}".encode()
        await self.bus.publish("models.model.loaded", payload)

    async def emit_memory_pressure(self, device: str, usage_mb: int, total_mb: int, severity: str = "critical") -> None:
        payload = f"{device},{usage_mb},{total_mb},{severity},{time.time()}".encode()
        await self.bus.publish("memory.pressure.warning", payload)