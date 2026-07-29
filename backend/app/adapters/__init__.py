from app.adapters.base import AdapterInput, AdapterOutput, ToolAdapter, ToolNotInstalledError
from app.adapters.ffuf import FfufAdapter
from app.adapters.nmap import NmapAdapter
from app.adapters.nuclei import NucleiAdapter

REGISTRY: dict[str, type[ToolAdapter]] = {
    "nmap": NmapAdapter,
    "ffuf": FfufAdapter,
    "nuclei": NucleiAdapter,
}

__all__ = [
    "AdapterInput",
    "AdapterOutput",
    "ToolAdapter",
    "ToolNotInstalledError",
    "REGISTRY",
]
