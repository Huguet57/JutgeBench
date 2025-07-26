#!/usr/bin/env python3
"""
Test script to debug code extraction issues
"""

import sys
import os

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from jutge_solver.solution_generator import SolutionGenerator

def test_code_extraction():
    """Test the code extraction directly"""
    
    generator = SolutionGenerator(None, None)
    
    # Test raw C++ code (no markdown)
    raw_cpp = """#include <iostream>
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
    
    print("Testing raw C++ code extraction:")
    print("-" * 40)
    print("Input:")
    print(repr(raw_cpp))
    
    extracted = generator._extract_code(raw_cpp, "G++17")
    print("\nExtracted:")
    print(repr(extracted))
    
    if extracted:
        print("\nValidation result:")
        is_valid = generator._validate_cpp_template(extracted)
        print(f"Valid: {is_valid}")
    else:
        print("\nNo code extracted!")
    
    # Test C++ code in markdown
    markdown_cpp = """Here's the solution:

```cpp
#include <iostream>
using namespace std;

int main() {
    int a, b;
    cin >> a >> b;
    cout << a + b << endl;
    return 0;
}
```

This should work correctly."""
    
    print("\n" + "=" * 50)
    print("Testing markdown C++ code extraction:")
    print("-" * 40)
    print("Input:")
    print(repr(markdown_cpp))
    
    extracted2 = generator._extract_code(markdown_cpp, "G++17")
    print("\nExtracted:")
    print(repr(extracted2))
    
    if extracted2:
        print("\nValidation result:")
        is_valid2 = generator._validate_cpp_template(extracted2)
        print(f"Valid: {is_valid2}")
    else:
        print("\nNo code extracted!")

if __name__ == "__main__":
    test_code_extraction()