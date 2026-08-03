from app.models.enums import EngagementStatus, RiskTier

# mirrors the state diagram in Plan_de_Travail_Wraithlink.md section 6.3
TRANSITIONS: dict[EngagementStatus, set[EngagementStatus]] = {
    EngagementStatus.scope_validation: {EngagementStatus.reconnaissance},
    # approval_pending is reachable straight from reconnaissance too: a
    # pentester can submit an approval-tier action (e.g. sqlmap aggressive)
    # before any automatic action has moved the engagement into 'scan'.
    EngagementStatus.reconnaissance: {EngagementStatus.scan, EngagementStatus.approval_pending},
    EngagementStatus.scan: {EngagementStatus.approval_pending, EngagementStatus.reporting},
    EngagementStatus.approval_pending: {EngagementStatus.exploitation, EngagementStatus.scan},
    EngagementStatus.exploitation: {EngagementStatus.approval_pending, EngagementStatus.reporting},
    EngagementStatus.reporting: {EngagementStatus.closed},
    EngagementStatus.closed: set(),
}


class InvalidTransitionError(ValueError):
    def __init__(self, current: EngagementStatus, target: EngagementStatus):
        super().__init__(f"cannot move engagement from '{current.value}' to '{target.value}'")
        self.current = current
        self.target = target


def can_transition(current: EngagementStatus, target: EngagementStatus) -> bool:
    return target in TRANSITIONS.get(current, set())


def next_status_after_action(current: EngagementStatus, tier: RiskTier) -> EngagementStatus:
    """
    Given the engagement's current status and the tier of the action that was
    just submitted, returns the status the engagement should move to. A
    forbidden action never changes engagement status - it is rejected before
    reaching this point. Actions that do not warrant moving forward (for
    example a second automatic scan while already in 'scan') leave the
    engagement exactly where it was, which is why this function can return
    the current status unchanged instead of always requiring a real edge.
    """
    if tier == RiskTier.forbidden:
        raise ValueError("a forbidden action cannot drive an engagement transition")

    if current == EngagementStatus.scope_validation:
        target = EngagementStatus.reconnaissance
    elif tier == RiskTier.approval:
        target = EngagementStatus.approval_pending
    elif current == EngagementStatus.reconnaissance:
        target = EngagementStatus.scan
    else:
        target = current

    if target == current:
        return current

    if not can_transition(current, target):
        raise InvalidTransitionError(current, target)

    return target
