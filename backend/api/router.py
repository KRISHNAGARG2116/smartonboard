from fastapi import APIRouter

from api.applications import router as applications_router
from api.auth import router as auth_router
from api.companies import router as companies_router
from api.jobs import router as jobs_router
from api.audit import router as audit_router
from api.notes import router as notes_router
from api.interviews import router as interviews_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth_router)
v1_router.include_router(companies_router)
v1_router.include_router(jobs_router)
v1_router.include_router(applications_router)
v1_router.include_router(audit_router)
v1_router.include_router(notes_router)
v1_router.include_router(interviews_router)
