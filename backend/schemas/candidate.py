from pydantic import BaseModel, Field

class CandidateDeletionRequest(BaseModel):
    confirm: bool = Field(
        ...,
        description="Explicit confirmation flag required to execute GDPR Right-to-Be-Forgotten candidate erasure."
    )
