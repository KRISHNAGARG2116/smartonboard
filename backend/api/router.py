from fastapi import APIRouter

from api.applications import router as applications_router
from api.auth import router as auth_router
from api.companies import router as companies_router
from api.jobs import router as jobs_router
from api.audit import router as audit_router
from api.notes import router as notes_router
from api.interviews import router as interviews_router
from api.offers import router as offers_router
from api.candidates import router as candidates_router
from api.analytics import router as analytics_router
from api.intelligence import router as intelligence_router
from api.sso import router as sso_router
from api.calendars import router as calendars_router
from api.scheduling import router as scheduling_router
from api.pipelines import router as pipelines_router
from api.approvals import router as approvals_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth_router)
v1_router.include_router(companies_router)
v1_router.include_router(jobs_router)
v1_router.include_router(applications_router)
v1_router.include_router(audit_router)
v1_router.include_router(notes_router)
v1_router.include_router(interviews_router)
v1_router.include_router(offers_router)
v1_router.include_router(candidates_router)
v1_router.include_router(analytics_router)
v1_router.include_router(intelligence_router)
v1_router.include_router(sso_router)
v1_router.include_router(calendars_router)
v1_router.include_router(scheduling_router)
v1_router.include_router(pipelines_router)
v1_router.include_router(approvals_router)


