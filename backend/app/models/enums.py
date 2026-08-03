import enum


class EngagementStatus(str, enum.Enum):
    scope_validation = "scope_validation"
    reconnaissance = "reconnaissance"
    scan = "scan"
    approval_pending = "approval_pending"
    exploitation = "exploitation"
    reporting = "reporting"
    closed = "closed"


class TargetType(str, enum.Enum):
    web = "web"
    active_directory = "active_directory"


class RiskTier(str, enum.Enum):
    automatic = "automatic"
    approval = "approval"
    forbidden = "forbidden"


class ActionStatus(str, enum.Enum):
    pending = "pending"
    blocked = "blocked"
    awaiting_approval = "awaiting_approval"
    running = "running"
    completed = "completed"
    failed = "failed"


class ApprovalOption(str, enum.Enum):
    conservative = "A"
    aggressive = "B"


class FindingSeverity(str, enum.Enum):
    info = "info"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class UserRole(str, enum.Enum):
    admin = "admin"
    pentester = "pentester"
    reader = "reader"
