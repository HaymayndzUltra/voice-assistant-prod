from __future__ import annotations

from typing import Dict, Optional, Literal
from pydantic import BaseModel, Field


class MetricRecord(BaseModel):
    name: str
    value: float
    labels: Dict[str, str] = Field(default_factory=dict)
    timestamp_unix: float


class Alert(BaseModel):
    rule_name: str
    severity: Literal["info", "warning", "critical"] = "warning"
    message: str
    labels: Dict[str, str] = Field(default_factory=dict)
    metric: Optional[MetricRecord] = None


class Action(BaseModel):
    name: str
    params: Dict[str, str] = Field(default_factory=dict)