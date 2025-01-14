import sys
import platform
import importlib

def diagnose():
    print("System Diagnostics")
    print("-" * 20)
    
    # Python Information
    print(f"Python Version: {sys.version}")
    print(f"Platform: {platform.platform()}")
    
    # Check key libraries
    libraries = [
        'flask', 'chromadb', 'anthropic', 
        'pydantic', 'dotenv', 'gunicorn'
    ]
    
    print("\nLibrary Versions:")
    for lib in libraries:
        try:
            module = importlib.import_module(lib)
            print(f"{lib}: {getattr(module, '__version__', 'Unknown')}")
        except ImportError:
            print(f"{lib}: Not installed")

if __name__ == "__main__":
    diagnose()
