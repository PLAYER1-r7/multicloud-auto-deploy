import pulumi

config = pulumi.Config()
print(
    f"DEBUG: firebase_api_key from config = {config.get('firebase_api_key')}")
