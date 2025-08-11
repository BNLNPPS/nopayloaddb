import importlib
from django.conf import settings

def load_permission_plugin():
    path = settings.PERMISSION_PLUGIN_CLASS
    module_name, class_name = path.rsplit(".", 1)
    module = importlib.import_module(module_name)
    cls = getattr(module, class_name)
    return cls()
