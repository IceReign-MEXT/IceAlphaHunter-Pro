#!/usr/bin/env python3
"""IceAlpha Hunter Pro - Comprehensive Diagnostic Tool"""
import sys
import os
import asyncio
import importlib.util
from pathlib import Path

# Colors for terminal output
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def print_status(check_name, status, details=""):
    icon = f"{GREEN}✅{RESET}" if status else f"{RED}❌{RESET}"
    print(f"{icon} {check_name}")
    if details:
        print(f"   {details}")

def check_python_version():
    """Check Python version"""
    version = sys.version_info
    ok = version >= (3, 8)
    print_status("Python Version", ok, f"{version.major}.{version.minor}.{version.micro} {'(OK)' if ok else '(Need 3.8+)'}")
    return ok

def check_file_structure():
    """Check if all required files exist"""
    required_files = [
        'main.py', 'config.py', 'telegram_bot.py', 'trading_engine.py',
        'mev_scanner.py', 'whale_monitor.py', 'profit_manager.py',
        'database.py', 'requirements.txt', 'Procfile'
    ]
    
    print(f"\n{BLUE}📁 File Structure Check:{RESET}")
    all_ok = True
    for file in required_files:
        exists = Path(file).exists()
        if not exists:
            all_ok = False
        print_status(f"  {file}", exists)
    return all_ok

def check_env_variables():
    """Check environment variables"""
    print(f"\n{BLUE}🔐 Environment Variables:{RESET}")
    
    required_vars = [
        'BOT_TOKEN', 'HELIUS_API_KEY', 'WALLET_PRIVATE_KEY',
        'DATABASE_URL', 'SUPABASE_URL', 'SUPABASE_KEY'
    ]
    
    all_ok = True
    for var in required_vars:
        value = os.getenv(var, '')
        exists = bool(value)
        if not exists:
            all_ok = False
        # Mask sensitive values
        display = value[:10] + "..." + value[-5:] if len(value) > 15 else "NOT SET"
        print_status(f"  {var}", exists, display if exists else "")
    
    return all_ok

def check_dependencies():
    """Check if all dependencies are installed"""
    print(f"\n{BLUE}📦 Dependency Check:{RESET}")
    
    dependencies = [
        ('telegram', 'python-telegram-bot'),
        ('solana.rpc.async_api', 'solana'),
        ('supabase', 'supabase'),
        ('solders.keypair', 'solders'),
        ('aiohttp', 'aiohttp'),
        ('flask', 'Flask'),
        ('requests', 'requests'),
        ('dotenv', 'python-dotenv')
    ]
    
    all_ok = True
    for module, package in dependencies:
        try:
            if '.' in module:
                parts = module.split('.')
                mod = __import__(parts[0])
                for part in parts[1:]:
                    mod = getattr(mod, part)
            else:
                mod = importlib.import_module(module)
            print_status(f"  {package}", True)
        except ImportError as e:
            print_status(f"  {package}", False, f"Missing: pip install {package}")
            all_ok = False
    
    return all_ok

def check_procfile():
    """Check Procfile configuration"""
    print(f"\n{BLUE}🚀 Procfile Check:{RESET}")
    
    try:
        with open('Procfile', 'r') as f:
            content = f.read().strip()
        
        if 'web:' in content:
            print_status("  Type", False, "Using 'web:' - should be 'worker:' for bots!")
            print(f"   {YELLOW}⚠️  WARNING: This bot doesn't bind to HTTP port!{RESET}")
            print(f"   {YELLOW}   Change to: worker: python main.py{RESET}")
            return False
        elif 'worker:' in content:
            print_status("  Type", True, "Correctly using 'worker:'")
            return True
        else:
            print_status("  Type", False, "Unknown Procfile format")
            return False
    except FileNotFoundError:
        print_status("  File", False, "Procfile not found!")
        return False

def main():
    print(f"{BLUE}╔════════════════════════════════════════╗{RESET}")
    print(f"{BLUE}║   IceAlpha Hunter Pro - Diagnostic    ║{RESET}")
    print(f"{BLUE}╚════════════════════════════════════════╝{RESET}")
    
    results = []
    
    results.append(("Python Version", check_python_version()))
    results.append(("File Structure", check_file_structure()))
    results.append(("Environment Variables", check_env_variables()))
    results.append(("Dependencies", check_dependencies()))
    results.append(("Procfile", check_procfile()))
    
    # Summary
    print(f"\n{BLUE}═════════════════════════════════════════{RESET}")
    print(f"{BLUE}📊 Summary:{RESET}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"  {name}: {status}")
    
    print(f"\n{BLUE}Total: {passed}/{total} checks passed{RESET}")
    
    if passed == total:
        print(f"\n{GREEN}🎉 All systems operational! Ready to deploy.{RESET}")
        return 0
    else:
        print(f"\n{RED}⚠️  Some checks failed. Fix issues before deploying.{RESET}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
