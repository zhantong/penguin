from bearblog import Signal

from . import component, models, api

get_setting = models.Settings.get_setting
add_default_cateogry = models.Settings.add_default_category
set_setting = models.Settings.set_setting


@Signal.connect('context_processor', 'bearblog')
def context_processor():
    return {
        'get_setting': get_setting
    }
