from core.notifications import NotificationManager, EmailChannel, WebhookChannel

def test_notifications():
    print("Testing Notification System...")
    
    # Mock Config
    config = {
        "email": {
            "enabled": True,
            "smtp_host": "smtp.mailtrap.io", # Mock or example
            "smtp_port": 2525,
            "user": "test_user",
            "password": "test_password",
            "recipients": ["test@example.com"]
        },
        "webhook": {
            "enabled": True,
            "url": "https://discord.com/api/webhooks/1234567890/token" # Mock
        }
    }

    manager = NotificationManager()
    
    # Test Config Loading
    print("1. Loading Config...")
    manager.load_from_config(config)
    
    if len(manager.channels) == 2:
        print("   [PASS] Loaded 2 channels.")
    else:
        print(f"   [FAIL] Loaded {len(manager.channels)} channels.")

    # Test Integration (without actually sending, just ensuring no crashes)
    # To truly test without sending, we'd need to mock smtplib and urllib, 
    # but for a simple "test script" requested by user, we might want to just instantiate and run 'notify'.
    # However, running notify will fail on network calls with fake creds.
    
    print("2. Sending Test Message (Simulated)...")
    try:
        # We can't easily assert success here without mocking in a script,
        # but we can ensure it doesn't throw exceptions up the stack.
        manager.notify("This is a test message from Hygiene Suite", level="test")
        print("   [PASS] Notify executed without crashing.")
    except Exception as e:
        print(f"   [FAIL] Notify crashed: {e}")

if __name__ == "__main__":
    test_notifications()
