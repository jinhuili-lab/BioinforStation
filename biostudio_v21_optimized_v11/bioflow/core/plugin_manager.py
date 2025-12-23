import os
import json
from typing import List
from bioflow.core.models import PluginInfo, PluginPricing, PluginCompatibility, PluginUIField, PluginUIView, PluginExecution

class PluginManager:
    def __init__(self, plugins_root: str):
        self.plugins_root = plugins_root
        self.plugins: List[PluginInfo] = []

    def scan(self):
        self.plugins.clear()
        if not os.path.isdir(self.plugins_root):
            return
        for entry in os.listdir(self.plugins_root):
            plugin_dir = os.path.join(self.plugins_root, entry)
            if not os.path.isdir(plugin_dir):
                continue
            config_path = os.path.join(plugin_dir, "plugin.json")
            if not os.path.exists(config_path):
                continue
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            pricing = data.get("pricing", {})
            compatibility = data.get("compatibility", {})
            ui = data.get("ui", {})
            execution = data.get("execution", {})
            fields = []
            for field in ui.get("form_schema", []):
                fields.append(
                    PluginUIField(
                        id=field.get("id"),
                        label=field.get("label"),
                        type=field.get("type"),
                        required=field.get("required", False),
                        default=field.get("default"),
                    )
                )
            views = []
            for view in ui.get("output_views", []):
                views.append(
                    PluginUIView(
                        id=view.get("id"),
                        type=view.get("type"),
                        title=view.get("title"),
                    )
                )
            exec_obj = PluginExecution(
                mode=execution.get("mode"),
                entry_script=execution.get("entry_script"),
                entry_function=execution.get("entry_function"),
                sbatch_template=execution.get("sbatch_template"),
                config_template=execution.get("config_template"),
            )
            info = PluginInfo(
                id=data.get("id"),
                name=data.get("name"),
                version=data.get("version"),
                author=data.get("author"),
                description=data.get("description", ""),
                category=data.get("category", ""),
                engine=data.get("engine", "local"),
                visibility=data.get("visibility", "public"),
                license=data.get("license", ""),
                pricing=PluginPricing(type=pricing.get("type", "free"), sku=pricing.get("sku")),
                compatibility=PluginCompatibility(
                    min_app_version=compatibility.get("min_app_version", "0.1.0"),
                    os=compatibility.get("os", []),
                    requires_ssh=compatibility.get("requires_ssh", False),
                    requires_slurm=compatibility.get("requires_slurm", False),
                ),
                ui_fields=fields,
                ui_views=views,
                execution=exec_obj,
            )
            self.plugins.append(info)
