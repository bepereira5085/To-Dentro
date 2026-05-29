try:
    from flask_debugtoolbar import DebugToolbarExtension
    toolbar = DebugToolbarExtension()
except ImportError:
    toolbar = None

def init_app(app):
    if toolbar is not None:
        toolbar.init_app(app)