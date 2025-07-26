#!/usr/bin/env python3
"""
Test script to validate C++ template enforcement in the benchmark system
"""

import sys
import os

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from jutge_solver.solution_generator import SolutionGenerator

def test_cpp_template_validation():
    """Test the C++ template validation functionality"""
    
    # Create a dummy solution generator (we only need the validation method)
    generator = SolutionGenerator(None, None)
    
    print("Testing C++ Template Validation...")
    print("=" * 50)
    
    # Test 1: Valid template
    valid_template = """#include <iostream>
using namespace std;

int main() {
    // Read input
    int a, b;
    cin >> a >> b;
    
    // Process/Algorithm
    int sum = a + b;
    
    // Print output
    cout << sum << endl;
    
    return 0;
}"""
    
    print("\nTest 1: Valid template")
    print("-" * 30)
    result1 = generator._validate_cpp_template(valid_template)
    print(f"Result: {result1}")
    assert result1 == True, "Valid template should pass validation"
    
    # Test 2: Missing include
    missing_include = """using namespace std;

int main() {
    int a, b;
    cin >> a >> b;
    int sum = a + b;
    cout << sum << endl;
    return 0;
}"""
    
    print("\nTest 2: Missing #include <iostream>")
    print("-" * 30)
    result2 = generator._validate_cpp_template(missing_include)
    print(f"Result: {result2}")
    assert result2 == False, "Missing include should fail validation"
    
    # Test 3: Missing using namespace
    missing_namespace = """#include <iostream>

int main() {
    int a, b;
    std::cin >> a >> b;
    int sum = a + b;
    std::cout << sum << std::endl;
    return 0;
}"""
    
    print("\nTest 3: Missing using namespace std")
    print("-" * 30)
    result3 = generator._validate_cpp_template(missing_namespace)
    print(f"Result: {result3}")
    assert result3 == False, "Missing using namespace should fail validation"
    
    # Test 4: Missing main function
    missing_main = """#include <iostream>
using namespace std;

void solve() {
    int a, b;
    cin >> a >> b;
    cout << a + b << endl;
}"""
    
    print("\nTest 4: Missing main function")
    print("-" * 30)
    result4 = generator._validate_cpp_template(missing_main)
    print(f"Result: {result4}")
    assert result4 == False, "Missing main function should fail validation"
    
    # Test 5: Missing return 0
    missing_return = """#include <iostream>
using namespace std;

int main() {
    int a, b;
    cin >> a >> b;
    cout << a + b << endl;
}"""
    
    print("\nTest 5: Missing return 0")
    print("-" * 30)
    result5 = generator._validate_cpp_template(missing_return)
    print(f"Result: {result5}")
    assert result5 == False, "Missing return 0 should fail validation"
    
    # Test 6: Missing input/output
    missing_io = """#include <iostream>
using namespace std;

int main() {
    int result = 42;
    return 0;
}"""
    
    print("\nTest 6: Missing input/output operations")
    print("-" * 30)
    result6 = generator._validate_cpp_template(missing_io)
    print(f"Result: {result6}")
    assert result6 == False, "Missing I/O should fail validation"
    
    # Test 7: Valid template with extra headers
    valid_with_extras = """#include <iostream>
#include <string>
#include <vector>
using namespace std;

int main() {
    string text;
    cin >> text;
    vector<char> chars;
    for (char c : text) {
        chars.push_back(c);
    }
    for (char c : chars) {
        cout << c;
    }
    cout << endl;
    return 0;
}"""
    
    print("\nTest 7: Valid template with extra headers")
    print("-" * 30)
    result7 = generator._validate_cpp_template(valid_with_extras)
    print(f"Result: {result7}")
    assert result7 == True, "Valid template with extras should pass validation"
    
    print("\n" + "=" * 50)
    print("All tests passed! C++ template validation is working correctly.")

def test_example_templates():
    """Test that the example templates from the prompts are valid"""
    
    generator = SolutionGenerator(None, None)
    
    print("\nTesting Example Templates from Prompts...")
    print("=" * 50)
    
    # Example 1 from prompt
    example1 = """#include <iostream>
using namespace std;

int main() {
    // Read input
    int a, b;
    cin >> a >> b;
    
    // Process/Algorithm
    int sum = a + b;
    
    // Print output
    cout << sum << endl;
    
    return 0;
}"""
    
    print("\nExample 1: Sum of two integers")
    result1 = generator._validate_cpp_template(example1)
    assert result1 == True, "Example 1 should be valid"
    
    # Example 2 from prompt
    example2 = """#include <iostream>
using namespace std;

int main() {
    // Read input
    string text;
    cin >> text;
    
    // Process/Algorithm
    string result = "";
    for (char c : text) {
        result += (char)tolower(c);
    }
    
    // Print output
    cout << result << endl;
    
    return 0;
}"""
    
    print("Example 2: String processing")
    result2 = generator._validate_cpp_template(example2)
    assert result2 == True, "Example 2 should be valid"
    
    # Example 3 from prompt
    example3 = """#include <iostream>
using namespace std;

int main() {
    // Read input
    int n;
    cin >> n;
    
    // Process/Algorithm
    for (int i = 0; i < n; i++) {
        int x;
        cin >> x;
        cout << x * 2 << endl;
    }
    
    return 0;
}"""
    
    print("Example 3: Multiple test cases")
    result3 = generator._validate_cpp_template(example3)
    assert result3 == True, "Example 3 should be valid"
    
    print("\nAll example templates are valid!")

if __name__ == "__main__":
    try:
        test_cpp_template_validation()
        test_example_templates()
        print("\n🎉 All tests completed successfully!")
        print("The C++ template enforcement system is ready for benchmarking.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)