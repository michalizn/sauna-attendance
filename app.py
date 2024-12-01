import dash
import dash_bootstrap_components as dbc
from dash import Dash, DiskcacheManager, CeleryManager, Input, Output, State, html, callback, dcc
import os

if 'REDIS_URL' in os.environ:
    # Use Redis & Celery if REDIS_URL set as an env variable
    from celery import Celery
    celery_app = Celery(__name__, broker=os.environ['REDIS_URL'], backend=os.environ['REDIS_URL'])
    background_callback_manager = CeleryManager(celery_app)

else:
    # Diskcache for non-production apps when developing locally
    import diskcache
    cache = diskcache.Cache("./cache")
    background_callback_manager = DiskcacheManager(cache)

app = dash.Dash(__name__, 
                external_stylesheets=[dbc.themes.BOOTSTRAP, '/assets/css/styles.css'], 
                external_scripts=['/assets/js/screen_size.js'],
                meta_tags=[{"name": "viewport", "content": "width=device-width"}],
                suppress_callback_exceptions=True,
                background_callback_manager=background_callback_manager)
