
import os
from app.config import Settings

# Simulate env vars
os.environ["AUTH_PROVIDER"] = "firebase"
# Add other likely vars
os.environ["API_BASE_URL"] = "https://example.com"
os.environ["FIREBASE_API_KEY"] = "somekey"
os.environ["FIREBASE_AUTH_DOMAIN"] = "ashnova.firebaseapp.com"
os.environ["FIREBASE_PROJECT_ID"] = "ashnova"
os.environ["FIREBASE_APP_ID"] = "someappid"

try:
    settings = Settings()
    print("Settings created successfully")
    print(settings.model_dump())
except Exception as e:
    print(e)
