"""
Firestore Configuration Diagnostic Script
Run this to diagnose Firestore connection issues
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("Firestore Configuration Diagnostic")
print("=" * 60)

# Check environment variables
project_id = os.getenv("FIRESTORE_PROJECT_ID")
credentials_path = os.getenv("FIRESTORE_CREDENTIALS_PATH")

print(f"\n1. Environment Variables:")
print(f"   FIRESTORE_PROJECT_ID: {project_id or 'NOT SET ❌'}")
print(f"   FIRESTORE_CREDENTIALS_PATH: {credentials_path or 'NOT SET ❌'}")

# Check .env file
env_path = Path(__file__).parent.parent / ".env"
print(f"\n2. .env File:")
print(f"   Path: {env_path}")
print(f"   Exists: {'Yes ✅' if env_path.exists() else 'No ❌'}")

# Check credentials file
if credentials_path:
    print(f"\n3. Credentials File (from environment):")
    print(f"   Path: {credentials_path}")
    exists = os.path.exists(credentials_path)
    print(f"   Exists: {'Yes ✅' if exists else 'No ❌'}")
    if exists:
        readable = os.access(credentials_path, os.R_OK)
        print(f"   Readable: {'Yes ✅' if readable else 'No ❌'}")
        print(f"   Size: {os.path.getsize(credentials_path)} bytes")
        
        # Try to parse JSON
        try:
            import json
            with open(credentials_path, 'r') as f:
                creds = json.load(f)
            print(f"   Valid JSON: Yes ✅")
            print(f"   Project ID in file: {creds.get('project_id', 'NOT FOUND')}")
            print(f"   Service account: {creds.get('client_email', 'NOT FOUND')}")
        except Exception as e:
            print(f"   Valid JSON: No ❌ - {str(e)}")
else:
    # Check default location
    default_path = Path(__file__).parent.parent / "service_key.json"
    print(f"\n3. Default Credentials File:")
    print(f"   Path: {default_path.absolute()}")
    exists = default_path.exists()
    print(f"   Exists: {'Yes ✅' if exists else 'No ❌'}")
    if exists:
        readable = os.access(default_path, os.R_OK)
        print(f"   Readable: {'Yes ✅' if readable else 'No ❌'}")

# Check Google Cloud SDK
print(f"\n4. Google Cloud SDK:")
try:
    import subprocess
    result = subprocess.run(["gcloud", "--version"], capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        version_line = result.stdout.split('\n')[0] if result.stdout else "Unknown"
        print(f"   Installed: Yes ✅")
        print(f"   Version: {version_line}")
        
        # Check current project
        try:
            project_result = subprocess.run(["gcloud", "config", "get-value", "project"], 
                                          capture_output=True, text=True, timeout=5)
            if project_result.returncode == 0:
                gcloud_project = project_result.stdout.strip()
                print(f"   Current project: {gcloud_project}")
                if gcloud_project != project_id:
                    print(f"   ⚠️  WARNING: gcloud project ({gcloud_project}) differs from FIRESTORE_PROJECT_ID ({project_id})")
        except:
            pass
    else:
        print(f"   Installed: No ❌")
except FileNotFoundError:
    print(f"   Installed: No ❌")
except Exception as e:
    print(f"   Check failed: {str(e)}")

# Check Python packages
print(f"\n5. Python Packages:")
try:
    import google.cloud.firestore
    print(f"   google-cloud-firestore: Installed ✅")
    try:
        print(f"   Version: {google.cloud.firestore.__version__}")
    except:
        print(f"   Version: Unknown")
except ImportError:
    print(f"   google-cloud-firestore: NOT INSTALLED ❌")
    print(f"   Install with: pip install google-cloud-firestore")

# Try to initialize client
print(f"\n6. Firestore Client Test:")
try:
    from config.firestore import get_firestore_client
    client = get_firestore_client()
    if client:
        print(f"   Status: ✅ SUCCESS")
        print(f"   Project: {client.project}")
        
        # Try a simple operation
        try:
            # Just check if we can access a collection (doesn't require data)
            collection_ref = client.collection("_test_connection")
            print(f"   Connection test: ✅ Can access Firestore")
        except Exception as e:
            print(f"   Connection test: ⚠️  Warning - {str(e)}")
    else:
        print(f"   Status: ❌ FAILED - Client is None")
        print(f"   Check the error messages above for details")
except Exception as e:
    print(f"   Status: ❌ ERROR")
    print(f"   Error: {str(e)}")
    print(f"   Type: {type(e).__name__}")

print("\n" + "=" * 60)
print("Diagnostic Complete")
print("=" * 60)
print("\nIf Firestore is not working:")
print("1. Check the issues marked with ❌ above")
print("2. See FIRESTORE_TROUBLESHOOTING.md for solutions")
print("3. Most common fix: Create .env file with:")
print("   FIRESTORE_PROJECT_ID=inf1005-452110")
print("   FIRESTORE_CREDENTIALS_PATH=service_key.json")

