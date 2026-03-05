"""imghdr compatibility shim for Python 3.13+"""
import sys

# Create fake imghdr module if not present
if 'imghdr' not in sys.modules:
    import types
    imghdr = types.ModuleType('imghdr')
    imghdr.what = lambda file, h=None: None  # Stub function
    sys.modules['imghdr'] = imghdr
