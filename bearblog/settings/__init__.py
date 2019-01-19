from bearblog import Signal

from . import component, models
from .component import get_setting_value, set_setting

get_setting = models.Settings.get_setting


@Signal.connect('context_processor', 'bearblog')
def context_processor():
    return {
        'get_setting': get_setting
    }
