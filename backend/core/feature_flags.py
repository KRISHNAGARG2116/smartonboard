import os
from typing import Dict


class FeatureFlagsService:
    # Default fallback values for features
    _DEFAULTS: Dict[str, bool] = {
        "ai_recruiter": True,
        "talent_crm": True,
        "executive_analytics": True,
        "sso_integration": False
    }

    @classmethod
    def is_enabled(cls, flag_name: str, company_id: str | None = None) -> bool:
        """
        Check if a feature is enabled.
        Supports environment overrides (e.g. FEATURE_SSO_INTEGRATION=true).
        """
        env_key = f"FEATURE_{flag_name.upper()}"
        env_val = os.getenv(env_key)
        
        if env_val is not None:
            return env_val.lower() in ("true", "1", "yes")
            
        # Optional: add company-specific rollout logic
        # e.g., if company_id in BETA_TENANTS: return True
        
        return cls._DEFAULTS.get(flag_name, False)
