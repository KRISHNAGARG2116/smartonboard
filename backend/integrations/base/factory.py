from integrations.base.registry import IntegrationRegistry
from typing import Any

class ProviderFactory:
    @classmethod
    def get_provider(cls, category: str, provider_name: str, **kwargs: Any) -> Any:
        impl_class = IntegrationRegistry.get(category, provider_name)
        if not impl_class:
            raise ValueError(f"No integration adapter registered for category '{category}', provider '{provider_name}'")
        return impl_class(**kwargs)
