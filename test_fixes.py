"""
Quick test to verify the fixes work.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))


def test_core_imports():
    """Test that core modules can be imported."""
    print("Testing core module imports...")

    try:
        from core.config import AppConfig

        print("✅ core.config imported successfully")
    except Exception as e:
        print(f"❌ core.config failed: {e}")
        return False

    try:
        from core.state import BibtexEntry, AppState

        print("✅ core.state imported successfully")
    except Exception as e:
        print(f"❌ core.state failed: {e}")
        return False

    try:
        from core.processor import create_processor

        print("✅ core.processor imported successfully")
    except Exception as e:
        print(f"❌ core.processor failed: {e}")
        return False

    try:
        from core.exceptions import DOIError

        print("✅ core.exceptions imported successfully")
    except Exception as e:
        print(f"❌ core.exceptions failed: {e}")
        return False

    try:
        from core.types import DOI

        print("✅ core.types imported successfully")
    except Exception as e:
        print(f"❌ core.types failed: {e}")
        return False

    return True


def test_async_processor_optional():
    """Test that async processor handles missing aiohttp gracefully."""
    print("\nTesting async processor (optional)...")

    try:
        from core.async_processor import AIOHTTP_AVAILABLE, AsyncDOIProcessor

        if AIOHTTP_AVAILABLE:
            print("✅ aiohttp available - async processing enabled")
        else:
            print("⚠️  aiohttp not available - async processing disabled (OK)")

            # Test that it raises proper error
            from core.config import AppConfig

            config = AppConfig()

            try:
                processor = AsyncDOIProcessor(config)
                print("❌ Should have raised ImportError")
                return False
            except ImportError as e:
                if "aiohttp" in str(e):
                    print("✅ Proper ImportError raised for missing aiohttp")
                else:
                    print(f"❌ Wrong error: {e}")
                    return False

        print("✅ Async processor handles dependencies correctly")
        return True

    except Exception as e:
        print(f"❌ Async processor test failed: {e}")
        return False


def test_basic_functionality():
    """Test basic functionality works."""
    print("\nTesting basic functionality...")

    try:
        # Test config
        from core.config import AppConfig

        config = AppConfig()
        assert config.theme == "light"
        print("✅ Configuration works")

        # Test state
        from core.state import BibtexEntry, AppState

        entry = BibtexEntry("test", "content", {"doi": "10.1234/test"})
        state = AppState([entry], {})
        assert state.has_entries
        print("✅ State management works")

        # Test processor creation
        from core.processor import create_processor

        processor = create_processor(config)
        assert processor.config is config
        print("✅ Processor creation works")

        return True

    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🔧 Testing DOI2BibTex fixes...")
    print("=" * 50)

    tests = [
        ("Core Imports", test_core_imports),
        ("Async Processor (Optional)", test_async_processor_optional),
        ("Basic Functionality", test_basic_functionality),
    ]

    passed = 0
    total = len(tests)

    for name, test_func in tests:
        if test_func():
            passed += 1

    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All fixes working correctly!")
        print("💡 You can now run: streamlit run streamlit_app.py")
        if not test_aiohttp_available():
            print("📦 For async processing, install: pip install aiohttp")
    else:
        print("⚠️  Some issues remain - check the errors above")

    return passed == total


def test_aiohttp_available():
    """Check if aiohttp is available."""
    try:
        import aiohttp

        return True
    except ImportError:
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
