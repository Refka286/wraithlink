from fastapi import APIRouter

from app.api import actions, approvals, auth, engagements, findings, reports

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(engagements.router, prefix="/engagements", tags=["engagements"])
router.include_router(actions.router, prefix="/actions", tags=["actions"])
router.include_router(approvals.router, prefix="/approvals", tags=["approvals"])
router.include_router(findings.router, prefix="/findings", tags=["findings"])
router.include_router(reports.router, prefix="/reports", tags=["reports"])
