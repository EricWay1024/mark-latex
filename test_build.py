#!/usr/bin/env python3
"""
Test script to verify MarkLatex dependencies and basic functionality.
Run this before building the executable to ensure everything works.
"""

import sys
import importlib

def test_import(module_name, description):
    """Test if a module can be imported."""
    try:
        importlib.import_module(module_name)
        print(f"✓ {description}: OK")
        return True
    except ImportError as e:
        print(f"✗ {description}: FAILED - {e}")
        return False

def test_pyqt6():
    """Test PyQt6 functionality."""
    try:
        from PyQt6.QtWidgets import QApplication, QWidget
        from PyQt6.QtCore import Qt
        print("✓ PyQt6 GUI components: OK")
        return True
    except Exception as e:
        print(f"✗ PyQt6 GUI components: FAILED - {e}")
        return False

def test_pymupdf():
    """Test PyMuPDF functionality."""
    try:
        import fitz
        # Test basic PDF functionality
        doc = fitz.open()
        doc.close()
        print("✓ PyMuPDF (fitz): OK")
        return True
    except Exception as e:
        print(f"✗ PyMuPDF (fitz): FAILED - {e}")
        return False

def test_matplotlib():
    """Test matplotlib functionality."""
    try:
        import matplotlib
        matplotlib.use('Agg')  # Use non-interactive backend
        import matplotlib.pyplot as plt
        import matplotlib.text
        
        # Test basic plotting
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "Test", fontsize=12)
        plt.close(fig)
        
        print("✓ Matplotlib (Agg backend): OK")
        return True
    except Exception as e:
        print(f"✗ Matplotlib (Agg backend): FAILED - {e}")
        return False

def test_main_import():
    """Test if main.py can be imported."""
    try:
        # Add current directory to path
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        import main
        print("✓ main.py import: OK")
        return True
    except Exception as e:
        print(f"✗ main.py import: FAILED - {e}")
        return False

def main():
    """Run all tests."""
    print("MarkLatex Dependency Test")
    print("=" * 40)
    
    tests = [
        ("PyQt6", "PyQt6 core library"),
        ("PyQt6.QtWidgets", "PyQt6 widgets"),
        ("PyQt6.QtGui", "PyQt6 GUI"),
        ("PyQt6.QtSvg", "PyQt6 SVG support"),
        ("PyQt6.QtSvgWidgets", "PyQt6 SVG widgets"),
        ("fitz", "PyMuPDF (fitz)"),
        ("matplotlib", "Matplotlib core"),
        ("matplotlib.pyplot", "Matplotlib pyplot"),
        ("matplotlib.text", "Matplotlib text"),
        ("matplotlib.font_manager", "Matplotlib font manager"),
        ("matplotlib.backends.backend_agg", "Matplotlib Agg backend"),
    ]
    
    results = []
    
    # Test basic imports
    for module, description in tests:
        results.append(test_import(module, description))
    
    # Test specific functionality
    results.append(test_pyqt6())
    results.append(test_pymupdf())
    results.append(test_matplotlib())
    results.append(test_main_import())
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("\n" + "=" * 40)
    print(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("✓ All tests passed! Ready to build.")
        print("\nTo build the executable, run:")
        print("  python build_simple.py")
        return 0
    else:
        print("✗ Some tests failed. Please fix issues before building.")
        print("\nCommon fixes:")
        print("  pip install -r requirements.txt")
        print("  pip install --upgrade pyqt6 pymupdf matplotlib")
        return 1

if __name__ == "__main__":
    sys.exit(main())