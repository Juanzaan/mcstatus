#!/usr/bin/env python3
"""
Pre-deploy Configuration Validator
----------------------------------
Checks:
1. Environment Variables (via core.config)
2. YAML Configuration (via core.config_loader)
3. Security Best Practices (Debug mode, Secrets)

Usage:
    python scripts/validate_config.py
"""
import sys
import os
import logging

# Ensure we can import core modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_security_best_practices():
    """Check for common security misconfigurations"""
    issues = []
    
    # Check Debug Mode
    from core.config import DEBUG
    if os.getenv('FLASK_ENV') == 'production' and DEBUG:
        issues.append("⚠️  CRITICAL: DEBUG is True in production environment!")
        
    # Check Secret Keys (Placeholder check)
    secret_key = os.getenv('SECRET_KEY')
    if secret_key and len(secret_key) < 32:
        issues.append("⚠️  WARNING: SECRET_KEY is too short (< 32 chars).")
        
    # Check for default credentials in YAML
    from core.config_loader import ConfigLoader
    config = ConfigLoader.load()
    proxies = config.get('proxies', {}).get('sources', [])
    for proxy in proxies:
        if "user:pass" in proxy:
            issues.append("⚠️  WARNING: Placeholder credentials found in proxy list!")
            
    return issues

def main():
    print("🔍 Starting Pre-deploy Configuration Check...\n")
    
    has_errors = False
    
    # 1. Validate Environment Variables
    print("1️⃣  Checking Environment Variables...")
    try:
        import core.config
        print("   ✅ Environment variables valid.")
    except Exception as e:
        print(f"   ❌ Environment validation failed: {e}")
        has_errors = True

    # 2. Validate YAML Configuration
    print("\n2️⃣  Checking YAML Configuration...")
    try:
        from core.config_loader import ConfigLoader
        ConfigLoader.load()
        print("   ✅ YAML schema valid.")
    except Exception as e:
        print(f"   ❌ YAML validation failed: {e}")
        has_errors = True
        
    # 3. Security Checks
    print("\n3️⃣  Checking Security Best Practices...")
    security_issues = check_security_best_practices()
    if security_issues:
        for issue in security_issues:
            print(f"   {issue}")
        if any("CRITICAL" in i for i in security_issues):
            has_errors = True
    else:
        print("   ✅ No obvious security issues found.")
        
    print("\n" + "="*40)
    if has_errors:
        print("❌ VALIDATION FAILED. Fix errors before deploying.")
        sys.exit(1)
    else:
        print("✅ VALIDATION PASSED. Ready for deployment.")
        sys.exit(0)

if __name__ == "__main__":
    main()
