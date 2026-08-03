from fastapi import APIRouter

from app.api import (
    actions,
    analytics,
    approvals,
    auth,
    credentials,
    engagements,
    findings,
    reports,
    suggestions,
    tools,
    users,
)

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
router.include_router(engagements.router, prefix="/engagements", tags=["engagements"])
router.include_router(actions.router, prefix="/actions", tags=["actions"])
router.include_router(approvals.router, prefix="/approvals", tags=["approvals"])
router.include_router(findings.router, prefix="/findings", tags=["findings"])
router.include_router(reports.router, prefix="/reports", tags=["reports"])
router.include_router(suggestions.router, prefix="/suggestions", tags=["suggestions"])
router.include_router(tools.router, prefix="/tools", tags=["tools"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(credentials.router, prefix="/credentials", tags=["credentials"])
