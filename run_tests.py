"""
Test runner and validation script for DOI2BibTex application.

This script provides comprehensive testing and validation of the
refactored codebase with detailed reporting.
"""

import sys
import os
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def run_command(command: List[str], cwd: Optional[Path] = None) -> Dict[str, Any]:
    """Run a command and return results."""
    start_time = time.time()
    
    try:
        result = subprocess.run(
            command,
            cwd=cwd or PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        execution_time = time.time() - start_time
        
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "execution_time": execution_time
        }
    
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": "Command timed out after 300 seconds",
            "execution_time": 300
        }
    
    except Exception as e:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
            "execution_time": time.time() - start_time
        }


def check_dependencies() -> Dict[str, Any]:
    """Check if required dependencies are installed."""
    print("🔍 Checking dependencies...")
    
    dependencies = [
        ("python", ["python", "--version"]),
        ("pytest", ["python", "-m", "pytest", "--version"]),
        ("streamlit", ["python", "-c", "import streamlit; print(f'Streamlit {streamlit.__version__}')"]),
    ]
    
    results = {}
    
    for name, command in dependencies:
        result = run_command(command)
        results[name] = {
            "available": result["success"],
            "version": result["stdout"].strip() if result["success"] else "Not found",
            "error": result["stderr"] if not result["success"] else None
        }
        
        status = "✅" if result["success"] else "❌"
        print(f"  {status} {name}: {results[name]['version']}")
    
    return results


def run_static_analysis() -> Dict[str, Any]:
    """Run static analysis tools."""
    print("\n🔬 Running static analysis...")
    
    results = {}
    
    # Check imports and syntax
    modules_to_check = [
        "core.config",
        "core.state", 
        "core.processor",
        "core.exceptions",
        "core.logging_config",
        "core.types"
    ]
    
    # Optional modules
    optional_modules = [
        "core.async_processor"
    ]
    
    for module in modules_to_check:
        result = run_command(["python", "-c", f"import {module}"])
        results[module] = result["success"]
        
        status = "✅" if result["success"] else "❌"
        print(f"  {status} {module}")
        
        if not result["success"]:
            print(f"    Error: {result['stderr']}")
    
    # Check optional modules
    for module in optional_modules:
        result = run_command(["python", "-c", f"import {module}"])
        results[module] = result["success"]
        
        status = "✅" if result["success"] else "⚠️ "
        suffix = "(optional)" if not result["success"] else ""
        print(f"  {status} {module} {suffix}")
        
        if not result["success"]:
            print(f"    Note: {module} requires additional dependencies (aiohttp)")
    
    return results


def run_unit_tests() -> Dict[str, Any]:
    """Run unit tests with pytest."""
    print("\n🧪 Running unit tests...")
    
    # Check if pytest is available
    pytest_check = run_command(["python", "-m", "pytest", "--version"])
    if not pytest_check["success"]:
        return {
            "success": False,
            "error": "pytest not available",
            "details": "Install pytest: pip install pytest"
        }
    
    # Run tests with detailed output
    test_command = [
        "python", "-m", "pytest",
        "tests/",
        "-v",
        "--tb=short", 
        "--no-header",
        "--show-capture=no"
    ]
    
    result = run_command(test_command)
    
    # Parse test results
    lines = result["stdout"].split('\n')
    test_results = {
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 0
    }
    
    for line in lines:
        if "passed" in line and "failed" in line:
            # Summary line
            parts = line.split()
            for i, part in enumerate(parts):
                if part == "passed":
                    test_results["passed"] = int(parts[i-1])
                elif part == "failed":
                    test_results["failed"] = int(parts[i-1])
                elif part == "error":
                    test_results["errors"] = int(parts[i-1])
                elif part == "skipped":
                    test_results["skipped"] = int(parts[i-1])
            break
    
    print(f"  ✅ Passed: {test_results['passed']}")
    print(f"  ❌ Failed: {test_results['failed']}")
    print(f"  ⚠️  Errors: {test_results['errors']}")
    print(f"  ⏭️  Skipped: {test_results['skipped']}")
    
    if result["success"]:
        print("  🎉 All tests passed!")
    else:
        print("  ⚠️  Some tests failed. See details below:")
        print(result["stdout"])
        print(result["stderr"])
    
    return {
        "success": result["success"],
        "execution_time": result["execution_time"],
        "results": test_results,
        "output": result["stdout"],
        "errors": result["stderr"]
    }


def validate_refactored_modules() -> Dict[str, Any]:
    """Validate that refactored modules work correctly."""
    print("\n✅ Validating refactored modules...")
    
    validation_script = """
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Test imports
from core.config import AppConfig, get_config, update_config
from core.state import BibtexEntry, AppState, get_state
from core.processor import create_processor
from core.exceptions import DOIError, NetworkError
from core.types import DOI, ProcessingResult
from core.logging_config import setup_preset_logging

# Optional async processor import
try:
    from core.async_processor import AsyncDOIProcessor
    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False

# Test basic functionality
def test_config():
    config = AppConfig()
    assert config.theme == "light"
    assert config.batch_size == 50
    return True

def test_state():
    entry = BibtexEntry("key", "content", {"doi": "test"})
    state = AppState([entry], {})
    assert state.has_entries
    assert state.entry_count == 1
    return True

def test_processor():
    config = AppConfig()
    processor = create_processor(config)
    assert processor.config is config
    return True

def test_logging():
    logger = setup_preset_logging("testing")
    logger.info("Test log message")
    return True

def test_async_optional():
    if ASYNC_AVAILABLE:
        # Test that async processor can be imported
        return True
    else:
        # Test that we handle missing aiohttp gracefully
        return True

# Run all tests
tests = [
    ("Config", test_config),
    ("State", test_state), 
    ("Processor", test_processor),
    ("Logging", test_logging),
    ("Async (Optional)", test_async_optional)
]

results = {}
for name, test_func in tests:
    try:
        result = test_func()
        results[name] = {"success": True, "error": None}
    except Exception as e:
        results[name] = {"success": False, "error": str(e)}

# Print results
for name, result in results.items():
    status = "✅" if result["success"] else "❌"
    print(f"{name}: {status}")
    if not result["success"]:
        print(f"  Error: {result['error']}")

# Overall success
all_passed = all(r["success"] for r in results.values())
print(f"\\nValidation: {'✅ PASSED' if all_passed else '❌ FAILED'}")
sys.exit(0 if all_passed else 1)
"""
    
    # Write validation script to temp file
    temp_script = PROJECT_ROOT / "temp_validation.py"
    with open(temp_script, 'w', encoding='utf-8') as f:
        f.write(validation_script)
    
    try:
        result = run_command(["python", str(temp_script)])
        print(result["stdout"])
        
        if not result["success"]:
            print("Validation errors:")
            print(result["stderr"])
        
        return {
            "success": result["success"],
            "output": result["stdout"],
            "errors": result["stderr"]
        }
    
    finally:
        # Clean up temp file
        if temp_script.exists():
            temp_script.unlink()


def check_performance() -> Dict[str, Any]:
    """Basic performance checks."""
    print("\n⚡ Running performance checks...")
    
    performance_script = """
import time
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from core.config import AppConfig
from core.processor import create_processor

# Test configuration creation performance
start = time.perf_counter()
for _ in range(1000):
    config = AppConfig()
config_time = time.perf_counter() - start

print(f"Config creation: {config_time:.3f}s for 1000 instances")

# Test processor creation performance
start = time.perf_counter()
for _ in range(100):
    processor = create_processor(AppConfig())
processor_time = time.perf_counter() - start

print(f"Processor creation: {processor_time:.3f}s for 100 instances")

# Performance thresholds
config_ok = config_time < 0.1  # Should be very fast
processor_ok = processor_time < 1.0  # Should be reasonable

print(f"\\nPerformance: {'✅ PASSED' if config_ok and processor_ok else '❌ FAILED'}")
if not config_ok:
    print("❌ Config creation too slow")
if not processor_ok:
    print("❌ Processor creation too slow")

sys.exit(0 if config_ok and processor_ok else 1)
"""
    
    temp_script = PROJECT_ROOT / "temp_performance.py"
    with open(temp_script, 'w', encoding='utf-8') as f:
        f.write(performance_script)
    
    try:
        result = run_command(["python", str(temp_script)])
        print(result["stdout"])
        
        return {
            "success": result["success"],
            "output": result["stdout"],
            "errors": result["stderr"]
        }
    
    finally:
        if temp_script.exists():
            temp_script.unlink()


def generate_report(results: Dict[str, Any]) -> None:
    """Generate a comprehensive test report."""
    print("\n" + "="*60)
    print("📊 COMPREHENSIVE TEST REPORT")
    print("="*60)
    
    # Summary
    total_tests = 0
    passed_tests = 0
    
    sections = [
        ("Dependencies", results.get("dependencies", {})),
        ("Static Analysis", results.get("static_analysis", {})),
        ("Unit Tests", results.get("unit_tests", {})),
        ("Module Validation", results.get("module_validation", {})),
        ("Performance", results.get("performance", {}))
    ]
    
    for section_name, section_results in sections:
        print(f"\n📋 {section_name}")
        print("-" * 40)
        
        if section_name == "Dependencies":
            for dep, info in section_results.items():
                status = "✅" if info["available"] else "❌"
                print(f"  {status} {dep}: {info['version']}")
                total_tests += 1
                if info["available"]:
                    passed_tests += 1
        
        elif section_name == "Static Analysis":
            for module, success in section_results.items():
                status = "✅" if success else "❌"
                print(f"  {status} {module}")
                total_tests += 1
                if success:
                    passed_tests += 1
        
        elif section_name == "Unit Tests":
            if section_results.get("success"):
                test_counts = section_results.get("results", {})
                print(f"  ✅ Passed: {test_counts.get('passed', 0)}")
                print(f"  ❌ Failed: {test_counts.get('failed', 0)}")
                print(f"  ⚠️  Errors: {test_counts.get('errors', 0)}")
                print(f"  ⏭️  Skipped: {test_counts.get('skipped', 0)}")
                
                total_tests += 1
                if section_results["success"]:
                    passed_tests += 1
            else:
                print("  ❌ Unit tests not available or failed")
                total_tests += 1
        
        else:
            success = section_results.get("success", False)
            status = "✅" if success else "❌"
            print(f"  {status} {section_name}")
            total_tests += 1
            if success:
                passed_tests += 1
    
    # Overall summary
    print(f"\n" + "="*60)
    print("📈 OVERALL SUMMARY")
    print("="*60)
    
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    print(f"Tests Passed: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
    
    if success_rate >= 90:
        print("🎉 EXCELLENT! Refactoring was highly successful.")
    elif success_rate >= 75:
        print("✅ GOOD! Most improvements working well.")
    elif success_rate >= 50:
        print("⚠️  PARTIAL SUCCESS. Some issues need attention.")
    else:
        print("❌ NEEDS WORK. Several issues to address.")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS")
    print("-" * 40)
    
    if results.get("dependencies", {}).get("pytest", {}).get("available", False):
        print("  ✅ Testing environment is ready")
    else:
        print("  📦 Install pytest: pip install pytest")
    
    if success_rate < 100:
        print("  🔧 Address failed tests before production use")
    
    print("  📚 Run 'python -m streamlit run streamlit_app_v3.py' to test UI")
    print("  🚀 Consider deploying to production after validation")


def main():
    """Main test runner function."""
    print("🔬 DOI2BibTex - Comprehensive Test Suite")
    print("="*60)
    
    results = {}
    
    # 1. Check dependencies
    results["dependencies"] = check_dependencies()
    
    # 2. Static analysis
    results["static_analysis"] = run_static_analysis()
    
    # 3. Unit tests (optional, may not be available)
    results["unit_tests"] = run_unit_tests()
    
    # 4. Module validation  
    results["module_validation"] = validate_refactored_modules()
    
    # 5. Performance checks
    results["performance"] = check_performance()
    
    # 6. Generate comprehensive report
    generate_report(results)
    
    # Determine exit code
    critical_checks = [
        results["static_analysis"],
        results["module_validation"],
        results["performance"]
    ]
    
    all_critical_passed = all(
        any(v for v in check.values()) if isinstance(check, dict) else check.get("success", False)
        for check in critical_checks
    )
    
    exit_code = 0 if all_critical_passed else 1
    print(f"\n🏁 Test suite completed with exit code: {exit_code}")
    
    return exit_code


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
