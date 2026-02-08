"""Quick start script for local development."""
import os
import sys
import subprocess
import time

def check_env():
    """Check if .env file exists."""
    if not os.path.exists(".env"):
        print("❌ .env file not found")
        print("📝 Copy .env.example to .env and fill in your credentials:")
        print("   cp .env.example .env")
        sys.exit(1)
    print("✅ .env file found")

def check_database():
    """Check if database is accessible."""
    try:
        from config import engine
        with engine.connect() as conn:
            pass
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def run_bootstrap():
    """Run bootstrap script."""
    print("\n🚀 Running bootstrap...")
    try:
        import bootstrap
        bootstrap.bootstrap()
        print("✅ Bootstrap completed")
    except Exception as e:
        print(f"❌ Bootstrap failed: {e}")
        sys.exit(1)

def run_ingestion():
    """Run initial data ingestion."""
    print("\n📥 Running initial data ingestion...")
    print("⏳ This may take a few minutes...")
    try:
        result = subprocess.run(
            [sys.executable, "workers/ingest.py"],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            print("✅ Data ingestion completed")
        else:
            print(f"❌ Data ingestion failed:")
            print(result.stderr)
            sys.exit(1)
    except subprocess.TimeoutExpired:
        print("⚠️  Ingestion timed out, but may still be running")
    except Exception as e:
        print(f"❌ Error running ingestion: {e}")
        sys.exit(1)

def start_streamlit():
    """Start Streamlit app."""
    print("\n🎨 Starting Streamlit app...")
    print("📊 Dashboard will open in your browser")
    print("🔗 Default URL: http://localhost:8501")
    print("\nPress Ctrl+C to stop\n")
    
    try:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", "app/main.py"],
            check=True
        )
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down...")
    except Exception as e:
        print(f"❌ Error starting Streamlit: {e}")
        sys.exit(1)

def main():
    """Main entry point."""
    print("=" * 60)
    print("Kalshi Markets Dashboard - Quick Start")
    print("=" * 60)
    
    # Check environment
    check_env()
    
    # Check database
    if not check_database():
        print("\n💡 Make sure PostgreSQL is running and DATABASE_URL is correct")
        sys.exit(1)
    
    # Bootstrap
    run_bootstrap()
    
    # Ask about ingestion
    print("\n" + "=" * 60)
    response = input("Run initial data ingestion? (y/n) [recommended: y]: ").lower()
    
    if response in ['y', 'yes', '']:
        run_ingestion()
    else:
        print("⏭️  Skipping ingestion (you can run it later with: python workers/ingest.py)")
    
    # Start Streamlit
    print("\n" + "=" * 60)
    response = input("Start Streamlit dashboard? (y/n) [y]: ").lower()
    
    if response in ['y', 'yes', '']:
        start_streamlit()
    else:
        print("\n✅ Setup complete!")
        print("\nTo start the dashboard later, run:")
        print("   streamlit run app/main.py")

if __name__ == "__main__":
    main()
