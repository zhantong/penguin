from bearblog import current_component
from bearblog.models import Signal

Signal = Signal(None)
Signal.set_default_scope(current_component.slug)


@Signal.connect('sidebar_item', 'admin')
def sidebar_item():
    return Signal.send('admin_sidebar_item')
