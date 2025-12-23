from dataclasses import dataclass
from typing import List, Any

@dataclass
class PluginPricing:
    type: str
    sku: str | None = None

@dataclass
class PluginCompatibility:
    min_app_version: str
    os: list
    requires_ssh: bool
    requires_slurm: bool

@dataclass
class PluginUIField:
    id: str
    label: str
    type: str
    required: bool = False
    default: Any | None = None

@dataclass
class PluginUIView:
    id: str
    type: str
    title: str

@dataclass
class PluginExecution:
    mode: str
    entry_script: str | None = None
    entry_function: str | None = None
    sbatch_template: str | None = None
    config_template: str | None = None

@dataclass
class PluginInfo:
    id: str
    name: str
    version: str
    author: str
    description: str
    category: str
    engine: str
    visibility: str
    license: str
    pricing: PluginPricing
    compatibility: PluginCompatibility
    ui_fields: List[PluginUIField]
    ui_views: List[PluginUIView]
    execution: PluginExecution
