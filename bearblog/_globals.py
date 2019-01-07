from bearblog.models import ComponentProxy
from bearblog.models import Component

current_component = ComponentProxy()
component_url_for = Component.view_url_for
component_route = Component.view_route
