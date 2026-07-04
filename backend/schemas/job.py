import uuid
from datetime import date, datetime
from pydantic import BaseModel, Field, field_validator


class JobSettingsSchema(BaseModel):
    # Workplace Details
    workplace_type: str = "On-site"  # "Remote", "Hybrid", "On-site"
    timezone: str | None = None
    office_address: str | None = None
    relocation_offered: bool = False

    # Job Specs
    employment_type: str = "Full Time"  # "Full Time", "Part Time", "Contract", "Internship", "Temporary"
    travel_required: bool = False
    visa_sponsorship: bool = False
    security_clearance_required: bool = False
    openings: int = 1

    # Compensation
    salary_min: float | None = None
    salary_max: float | None = None
    currency: str = "USD"  # "USD", "EUR", "GBP", "INR"
    hide_salary: bool = False
    bonus: bool = False
    equity: bool = False
    pay_frequency: str = "Annual"  # "Hourly", "Monthly", "Annual"

    # Experience & Education
    min_experience_years: int | None = None
    max_experience_years: int | None = None
    education: str | None = None  # "High School", "Bachelor", "Master", "PhD", etc.
    certifications: list[str] = Field(default_factory=list)

    # Skills & Details
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)

    # Hiring Team & Templates
    hiring_manager_id: str | None = None
    recruiter_ids: list[str] = Field(default_factory=list)
    interviewer_ids: list[str] = Field(default_factory=list)
    stages: list[str] | None = None

    # AI Weighting
    skills_weight: float = 0.4
    experience_weight: float = 0.2
    education_weight: float = 0.1
    certification_weight: float = 0.1
    language_weight: float = 0.05
    location_weight: float = 0.05
    work_authorization_weight: float = 0.05
    availability_weight: float = 0.05

    @field_validator("stages")
    @classmethod
    def validate_stages(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        if len(v) < 1:
            raise ValueError("Hiring pipeline must have at least one stage")
        if len(v) > 10:
            raise ValueError("Hiring pipeline cannot exceed 10 stages")
        # Check duplicates
        normalized_stages = [stage.strip().lower() for stage in v]
        if len(normalized_stages) != len(set(normalized_stages)):
            raise ValueError("Stage names must be unique")
        return v


class JobCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    department: str = Field(default="General", max_length=100)
    description: str = Field(default="", max_length=20000)
    status: str = Field(default="draft")
    start_date: date | None = None
    settings: JobSettingsSchema = Field(default_factory=JobSettingsSchema)


class JobUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    department: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=20000)
    status: str | None = None
    start_date: date | None = None
    settings: JobSettingsSchema | None = None
    client_updated_at: datetime | None = None
    change_reason: str | None = None


class JobResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    title: str
    department: str
    description: str
    status: str
    start_date: date | None
    settings: JobSettingsSchema = Field(default_factory=JobSettingsSchema)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

