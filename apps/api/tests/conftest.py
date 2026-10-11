import os

# Tests never read the developer's .env values for the app mode.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("LOG_LEVEL", "WARNING")
