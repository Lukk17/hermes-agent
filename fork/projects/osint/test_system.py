#!/usr/bin/env python3
"""
OSINT Runner - Full System Test
Tests all services, tools, and integrations.
"""

import sys
import os
import subprocess
import importlib

# Setup paths
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.getcwd(), "src"))


def test_imports():
    """Test all service imports"""
    print("\n=== Testing Service Imports ===")
    services = [
        "base_service",
        "breach_service",
        "company_service",
        "darkweb_service",
        "domain_service",
        "email_service",
        "enrichment_service",
        "github_service",
        "gotools_service",
        "hunter_service",
        "infra_service",
        "people_service",
        "phone_service",
        "polish_gov_service",
        "recon_service",
        "social_extra_service",
        "social_service",
        "spiderfoot_service",
        "local_leak_service",
        "company_parser",
    ]

    results = []
    for svc in services:
        try:
            mod = importlib.import_module(f"services.{svc}")
            print(f"  [OK] services.{svc}")
            results.append(True)
        except Exception as e:
            print(f"  [FAIL] services.{svc}: {e}")
            results.append(False)

    return all(results)


def test_go_tools():
    """Test Go binary tools"""
    print("\n=== Testing Go Tools ===")
    bin_dir = os.path.join(os.getcwd(), "bin")
    tools = {
        "amass": ["amass", "enum", "-help"],
        "subfinder": ["subfinder", "-version"],
        "httpx": ["httpx", "-version"],
        "naabu": ["naabu", "-version"],
        "mosint": ["mosint", "-h"],
    }

    results = []
    for name, args in tools.items():
        bin_path = os.path.join(bin_dir, name)
        try:
            r = subprocess.run(
                [bin_path] + args,
                capture_output=True,
                timeout=15,
                env={**os.environ, "HOME": "/tmp"},
            )
            # Tools return 0 or 1 on help/version
            if r.returncode in (0, 1):
                output = r.stdout.decode() or r.stderr.decode()
                first_line = output.split("\n")[0][:60] if output else "no output"
                print(f"  [OK] {name} - {first_line}")
                results.append(True)
            else:
                print(f"  [FAIL] {name} - exit {r.returncode}")
                results.append(False)
        except subprocess.TimeoutExpired:
            print(f"  [FAIL] {name} - timeout")
            results.append(False)
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            results.append(False)

    return all(results)


def test_python_deps():
    """Test critical Python dependencies"""
    print("\n=== Testing Python Dependencies ===")
    deps = [
        ("requests", "requests"),
        ("httpx", "httpx"),
        ("beautifulsoup4", "bs4"),
        ("lxml", "lxml"),
        ("dnspython", "dns"),
        ("scapy", "scapy"),
        ("pydantic", "pydantic"),
        ("tldextract", "tldextract"),
        ("maigret", "maigret"),
        ("holehe", "holehe"),
        ("socialscan", "socialscan"),
        ("socid_extractor", "socid_extractor"),
        ("wappalyzer", "wappalyzer"),
        ("censys", "censys"),
        ("shodan", "shodan"),
        ("stem", "stem"),
        ("selenium", "selenium"),
        ("flask", "flask"),
        ("click", "click"),
        ("rich", "rich"),
        ("pyyaml", "yaml"),
    ]

    results = []
    for name, import_name in deps:
        try:
            mod = importlib.import_module(import_name)
            print(f"  [OK] {name}")
            results.append(True)
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            results.append(False)

    return all(results)


def test_main_cascade_engine():
    """Test that cascade engine loads"""
    print("\n=== Testing Cascade Engine ===")
    try:
        from src.main import main as main_func
        print("  [OK] main.py main function imported")
        return True
    except Exception as e:
        print(f"  [FAIL] main.py: {e}")
        return False


def test_go_tools_service():
    """Test GoTools service initialization"""
    print("\n=== Testing GoTools Service ===")
    try:
        from services.gotools_service import GoToolsService
        from services.gotools_service import BIN_DIR
        gt = GoToolsService()
        # Check the module-level BIN_DIR
        print(f"  [OK] GoToolsService initialized (BIN_DIR={BIN_DIR})")
        return True
    except Exception as e:
        print(f"  [FAIL] GoToolsService: {e}")
        return False


def test_spiderfoot_service():
    """Test SpiderFoot service import and initialization"""
    print("\n=== Testing SpiderFoot Service ===")
    try:
        from services.spiderfoot_service import SpiderFootService
        sf = SpiderFootService()
        # Check static/class attributes
        print(f"  [OK] SpiderFootService initialized (sf_cli={SpiderFootService._sf_cli})")
        return True
    except Exception as e:
        print(f"  [FAIL] SpiderFootService: {e}")
        return False


def test_email_service():
    """Test Email service"""
    print("\n=== Testing Email Service ===")
    try:
        from services.email_service import EmailService
        es = EmailService()
        print(f"  [OK] EmailService initialized")
        return True
    except Exception as e:
        print(f"  [FAIL] EmailService: {e}")
        return False


def test_domain_service():
    """Test Domain service"""
    print("\n=== Testing Domain Service ===")
    try:
        from services.domain_service import DomainService
        ds = DomainService()
        print(f"  [OK] DomainService initialized")
        return True
    except Exception as e:
        print(f"  [FAIL] DomainService: {e}")
        return False


def test_people_service():
    """Test People service"""
    print("\n=== Testing People Service ===")
    try:
        from services.people_service import PeopleService
        ps = PeopleService()
        print(f"  [OK] PeopleService initialized")
        return True
    except Exception as e:
        print(f"  [FAIL] PeopleService: {e}")
        return False


def test_social_service():
    """Test Social service"""
    print("\n=== Testing Social Service ===")
    try:
        from services.social_service import SocialService
        ss = SocialService()
        print(f"  [OK] SocialService initialized")
        return True
    except Exception as e:
        print(f"  [FAIL] SocialService: {e}")
        return False


def test_report_renderer():
    """Test report renderer"""
    print("\n=== Testing Report Renderer ===")
    try:
        from report_renderer import ReportRenderer
        rr = ReportRenderer()
        print("  [OK] ReportRenderer initialized")
        return True
    except Exception as e:
        print(f"  [FAIL] ReportRenderer: {e}")
        return False


def test_cascade_engine_class():
    """Test cascade engine class definition"""
    print("\n=== Testing CascadeEngine Class ===")
    try:
        from cascade_engine import CascadeEngine
        # Check signature - it requires query: OsintQuery
        import inspect
        sig = inspect.signature(CascadeEngine.__init__)
        params = list(sig.parameters.keys())
        print(f"  [OK] CascadeEngine.__init__ params: {params}")
        # It should have 'query' and 'max_depth'
        if "query" in params and "max_depth" in params:
            return True
        else:
            print(f"  [FAIL] Expected 'query' and 'max_depth', got {params}")
            return False
    except Exception as e:
        print(f"  [FAIL] CascadeEngine: {e}")
        return False


def test_models():
    """Test data models"""
    print("\n=== Testing Models ===")
    try:
        from src.models import ServiceResult, OsintQuery
        sr = ServiceResult(source="test", success=True, data={})
        print(f"  [OK] ServiceResult: source={sr.source}, success={sr.success}")
        return True
    except Exception as e:
        print(f"  [FAIL] models: {e}")
        return False


def test_venv_python():
    """Test venv Python is correct"""
    print("\n=== Testing Python Environment ===")
    py = os.path.join(os.getcwd(), ".venv", "bin", "python")
    try:
        result = subprocess.run([py, "--version"], capture_output=True, text=True)
        version = result.stdout.strip()
        print(f"  [OK] venv Python: {version}")
        return "3.12" in version
    except Exception as e:
        print(f"  [FAIL] venv Python: {e}")
        return False


def test_config_and_env():
    """Test that .env is not in workspace (security check)"""
    print("\n=== Testing Credential Security ===")
    workspace_env = os.path.join(os.getcwd(), ".env")
    if os.path.exists(workspace_env):
        print(f"  [FAIL] .env found in workspace (should be in host repo)")
        return False
    else:
        print(f"  [OK] No .env in workspace (secrets stay in host)")
        return True


def run_all_tests():
    print("=" * 60)
    print("OSINT RUNNER - FULL SYSTEM TEST")
    print("=" * 60)

    tests = [
        ("Python Environment", test_venv_python),
        ("Python Dependencies", test_python_deps),
        ("Go Tools Binaries", test_go_tools),
        ("Service Imports", test_imports),
        ("Main Function", test_main_cascade_engine),
        ("GoToolsService", test_go_tools_service),
        ("SpiderFootService", test_spiderfoot_service),
        ("EmailService", test_email_service),
        ("DomainService", test_domain_service),
        ("PeopleService", test_people_service),
        ("SocialService", test_social_service),
        ("ReportRenderer", test_report_renderer),
        ("CascadeEngine Class", test_cascade_engine_class),
        ("Data Models", test_models),
        ("Credential Security", test_config_and_env),
    ]

    results = []
    for name, fn in tests:
        try:
            r = fn()
            results.append((name, r))
        except Exception as e:
            print(f"  [ERROR] {name} crashed: {e}")
            results.append((name, False))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    passed = sum(1 for _, r in results if r)
    total = len(results)
    for name, r in results:
        status = "PASS" if r else "FAIL"
        print(f"  [{status}] {name}")
    print(f"\nTotal: {passed}/{total} passed")

    if passed == total:
        print("\n[SUCCESS] All tests passed!")
        return 0
    else:
        print(f"\n[FAILURE] {total - passed} tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())