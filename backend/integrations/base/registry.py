import logging
from typing import Dict, Type, Any

logger = logging.getLogger(__name__)

class IntegrationRegistry:
    _registry: Dict[str, Dict[str, Type[Any]]] = {
        "calendar": {},
        "email": {},
        "chat": {},
        "hris": {},
        "background_check": {},
    }

    @classmethod
    def register(cls, category: str, provider_name: str, implementation_class: Type[Any]):
        category = category.lower()
        provider_name = provider_name.lower()
        if category not in cls._registry:
            cls._registry[category] = {}
        cls._registry[category][provider_name] = implementation_class
        logger.info(f"Registered integration implementation: {category} -> {provider_name} ({implementation_class.__name__})")

    @classmethod
    def get(cls, category: str, provider_name: str) -> Type[Any] | None:
        category = category.lower()
        provider_name = provider_name.lower()
        return cls._registry.get(category, {}).get(provider_name)
