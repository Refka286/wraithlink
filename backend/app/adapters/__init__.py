from app.adapters.base import AdapterInput, AdapterOutput, ToolAdapter, ToolNotInstalledError
from app.adapters.bloodhound import BloodHoundAdapter
from app.adapters.ffuf import FfufAdapter
from app.adapters.netexec import NetExecAdapter
from app.adapters.nmap import NmapAdapter
from app.adapters.nuclei import NucleiAdapter
from app.adapters.sqlmap import SqlmapAdapter
from app.adapters.zap import ZapAdapter

REGISTRY: dict[str, type[ToolAdapter]] = {
    "nmap": NmapAdapter,
    "ffuf": FfufAdapter,
    "nuclei": NucleiAdapter,
    "netexec": NetExecAdapter,
    "bloodhound": BloodHoundAdapter,
    "sqlmap": SqlmapAdapter,
    "zap": ZapAdapter,
}

__all__ = [
    "AdapterInput",
    "AdapterOutput",
    "ToolAdapter",
    "ToolNotInstalledError",
    "REGISTRY",
]
