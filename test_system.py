"""Test script to verify system functionality."""
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    try:
        from config import settings, SessionLocal
        from db.models import Event, Market, EmailSettings
        from kalshi import KalshiClient
        from workers.ingest import DataIngester
        from workers.emailer import EmailDigester
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_config():
    """Test configuration."""
    print("\nTesting configuration...")
    try:
        from config import settings
        
        required_vars = [
            "DATABASE_URL",
            "SENDGRID_API_KEY"
        ]
        
        missing = []
        for var in required_vars:
            if not hasattr(settings, var) or not getattr(settings, var):
                missing.append(var)
        
        if missing:
            print(f"❌ Missing environment variables: {', '.join(missing)}")
            return False
        
        print("✅ Configuration valid")
        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_database():
    """Test database connection."""
    print("\nTesting database connection...")
    try:
        from config import SessionLocal, engine
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            assert result.scalar() == 1
        
        # Test session
        db = SessionLocal()
        try:
            from db.models import EmailSettings
            settings = db.query(EmailSettings).first()
            print(f"✅ Database connected (email settings exist: {settings is not None})")
            return True
        finally:
            db.close()
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_kalshi_client():
    """Test Kalshi API client."""
    print("\nTesting Kalshi API client...")
    try:
        from kalshi import KalshiClient
        
        client = KalshiClient()
        
        # Test public endpoint (no auth needed)
        markets = client.get_markets(limit=5)
        
        if markets and markets.markets:
            print(f"✅ Kalshi API connected (fetched {len(markets.markets)} markets)")
            return True
        else:
            print("⚠️  Kalshi API connected but no markets returned")
            return True
    except Exception as e:
        print(f"❌ Kalshi API test failed: {e}")
        return False

def test_data_models():
    """Test data models."""
    print("\nTesting data models...")
    try:
        from config import SessionLocal
        from db.models import Event, Market, MarketSnapshot, EmailSettings, Category
        
        db = SessionLocal()
        try:
            # Test queries
            event_count = db.query(Event).count()
            market_count = db.query(Market).count()
            settings = db.query(EmailSettings).first()
            
            print(f"✅ Data models working")
            print(f"   - Events: {event_count}")
            print(f"   - Markets: {market_count}")
            print(f"   - Email settings: {'configured' if settings else 'not configured'}")
            return True
        finally:
            db.close()
    except Exception as e:
        print(f"❌ Data models test failed: {e}")
        return False

def test_email_config():
    """Test email configuration."""
    print("\nTesting email configuration...")
    try:
        from config import settings
        
        if not settings.SENDGRID_API_KEY:
            print("⚠️  SendGrid API key not configured")
            return False
        
        if not settings.EMAIL_FROM:
            print("⚠️  Email FROM address not configured")
            return False
        
        print("✅ Email configuration valid")
        return True
    except Exception as e:
        print(f"❌ Email config test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Kalshi Markets Dashboard - System Tests")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config),
        ("Database", test_database),
        ("Data Models", test_data_models),
        ("Kalshi API", test_kalshi_client),
        ("Email Config", test_email_config),
    ]
    
    results = []
    for name, test_func in tests:
        result = test_func()
        results.append((name, result))
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
