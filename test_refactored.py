"""
Simple test script to validate the refactored modules.
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

def test_imports():
    """Test that all modules can be imported without errors."""
    try:
        from core.config import AppConfig, ConfigManager, get_config
        from core.state import BibtexEntry, AppState, StateManager
        from core.exceptions import DOIError, NetworkError, handle_exception
        from core.processor import DOIProcessor, create_processor
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_config():
    """Test configuration management."""
    try:
        # Test default config
        config = AppConfig()
        print(f"✅ Default config created: theme={config.theme}, batch_size={config.batch_size}")
        
        # Test validation
        try:
            bad_config = AppConfig(batch_size=1000)  # Should fail validation
            print("❌ Validation should have failed")
            return False
        except ValueError:
            print("✅ Config validation working correctly")
        
        return True
    except Exception as e:
        print(f"❌ Config test error: {e}")
        return False

def test_state():
    """Test state management."""
    try:
        # Test BibtexEntry
        entry = BibtexEntry(
            key="test2023",
            content="@article{test2023, title={Test}, year={2023}}",
            metadata={"doi": "10.1234/test", "status": "ok", "metadata": {"year": "2023"}}
        )
        
        print(f"✅ BibtexEntry created: key={entry.key}, year={entry.year}")
        
        # Test AppState  
        state = AppState(entries=[entry], analytics={})
        print(f"✅ AppState created: {state.entry_count} entries, success_rate={state.success_rate}%")
        
        return True
    except Exception as e:
        print(f"❌ State test error: {e}")
        return False

def test_processor():
    """Test DOI processor creation."""
    try:
        config = AppConfig()
        processor = create_processor(config)
        print(f"✅ DOI processor created with timeout={processor.config.timeout}")
        
        # Test input parsing
        dois = processor.parse_input("10.1234/test, 10.5678/example", None)
        print(f"✅ Parsed {len(dois)} DOIs: {dois}")
        
        return True
    except Exception as e:
        print(f"❌ Processor test error: {e}")
        return False

def main():
    """Run all tests."""
    print("🔬 Testing refactored DOI2BibTex modules...")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config), 
        ("State Management", test_state),
        ("DOI Processor", test_processor),
    ]
    
    passed = 0
    total = len(tests)
    
    for name, test_func in tests:
        print(f"\n📋 Testing {name}...")
        if test_func():
            passed += 1
        else:
            print(f"❌ {name} test failed")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! The refactored modules are working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
