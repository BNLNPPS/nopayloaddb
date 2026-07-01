import importlib
from django.conf import settings

def _load_class(path):
    module_name, class_name = path.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)

def load_permission_plugin():
    return _load_class(settings.PERMISSION_PLUGIN_CLASS)()

def load_auth_class():
    if not settings.CDB_AUTH_CLASS:
        return None
    return _load_class(settings.CDB_AUTH_CLASS)
