# Initialize registry and import concrete providers to trigger registration
from integrations.base.registry import IntegrationRegistry
from integrations.base.factory import ProviderFactory

# Concrete providers imports to trigger @register
import integrations.providers.google
import integrations.providers.microsoft
import integrations.providers.smtp
import integrations.providers.slack
import integrations.providers.teams
import integrations.providers.bamboohr
import integrations.providers.workday
import integrations.providers.hibob
import integrations.providers.greenhouse
import integrations.providers.lever
import integrations.providers.checkr
import integrations.providers.certn
