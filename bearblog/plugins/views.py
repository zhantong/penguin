from bearblog import current_component
from bearblog.models import Signal


@Signal.connect('admin', 'sidebar_item')
def sidebar_item():
    return current_component.signal.send_this('admin_sidebar_item')
