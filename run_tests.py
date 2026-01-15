"""
Test runner script - Run all tests and generate report
"""
import subprocess
import sys


def run_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 Running Integration Tests")
    print("="*60 + "\n")
    
    # Run pytest
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "--color=yes"
    ]
    
    result = subprocess.run(cmd, cwd=".", capture_output=False)
    
    print("\n" + "="*60)
    if result.returncode == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")
    print("="*60 + "\n")
    
    return result.returncode


def run_specific_test(test_file=None):
    """Run specific test file"""
    print("\n" + "="*60)
    print(f"🧪 Running tests from {test_file}")
    print("="*60 + "\n")
    
    cmd = [
        sys.executable, "-m", "pytest",
        f"tests/{test_file}",
        "-v",
        "--tb=short"
    ]
    
    result = subprocess.run(cmd, cwd=".", capture_output=False)
    return result.returncode


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run tests for 3D Print Farm")
    parser.add_argument(
        "--file",
        type=str,
        help="Run specific test file (e.g., test_jobs.py)"
    )
    
    args = parser.parse_args()
    
    if args.file:
        exit_code = run_specific_test(args.file)
    else:
        exit_code = run_tests()
    
    sys.exit(exit_code)
