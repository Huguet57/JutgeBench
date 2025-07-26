#!/usr/bin/env python3
"""
Test script to validate C++ template enforcement integration with the benchmark system
"""

import sys
import os
from unittest.mock import Mock, MagicMock

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from jutge_solver.solution_generator import SolutionGenerator

def test_solution_generation_with_template_validation():
    """Test that solution generation includes template validation for C++"""
    
    print("Testing C++ Solution Generation with Template Validation...")
    print("=" * 60)
    
    # Mock OpenAI client and config
    mock_client = Mock()
    mock_config = Mock()
    mock_config.model = "gpt-4"
    mock_config.max_tokens = 1000
    mock_config.temperature = 0.3
    mock_config.timeout = 30
    
    # Create mock responses for the two-step process
    # Step 1 response (analysis + initial code)
    step1_response = Mock()
    step1_response.choices = [Mock()]
    step1_response.choices[0].message.content = """
Here's my analysis and solution:

The problem asks to sum two integers.

```cpp
#include <iostream>
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
}
```
"""
    step1_response.usage = Mock()
    step1_response.usage.total_tokens = 150
    step1_response.usage.prompt_tokens = 50
    step1_response.usage.completion_tokens = 100
    
    # Step 2 response (formatted code) - this should be clean code without markdown
    step2_response = Mock()
    step2_response.choices = [Mock()]
    step2_response.choices[0].message.content = """#include <iostream>
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
    step2_response.usage = Mock()
    step2_response.usage.total_tokens = 120
    step2_response.usage.prompt_tokens = 80
    step2_response.usage.completion_tokens = 40
    
    # Configure mock client to return these responses
    mock_client.chat.completions.create.side_effect = [step1_response, step2_response]
    
    # Create solution generator
    generator = SolutionGenerator(mock_client, mock_config)
    
    # Create test problem info
    problem_info = {
        "problem_id": "P12345",
        "title": "Sum Two Numbers",
        "statement": "Read two integers and output their sum",
        "sample_testcases": []
    }
    
    print("Test 1: Valid C++ template should pass")
    print("-" * 40)
    
    # Generate solution
    result = generator.generate_solution(problem_info, "G++17", 1)
    
    print(f"Success: {result.get('success')}")
    print(f"Code generated: {len(result.get('code', '')) > 0}")
    print(f"Token usage: {result.get('token_usage', {}).get('total_tokens', 0)}")
    
    if not result.get('success'):
        print(f"Error: {result.get('error')}")
        print("Extracted code:")
        print(repr(result.get('code', 'No code')))
    
    assert result["success"] == True, "Solution generation should succeed for valid template"
    assert "#include <iostream>" in result["code"], "Generated code should include iostream"
    assert "using namespace std;" in result["code"], "Generated code should include using namespace"
    assert "int main(" in result["code"], "Generated code should include main function"
    assert "return 0;" in result["code"], "Generated code should include return 0"
    
    print("✓ Valid template test passed")
    
    print("\nTest 2: Invalid C++ template should fail")
    print("-" * 40)
    
    # Create invalid response for step 2
    invalid_step2_response = Mock()
    invalid_step2_response.choices = [Mock()]
    invalid_step2_response.choices[0].message.content = """void solve() {
    int a, b;
    scanf("%d %d", &a, &b);
    printf("%d\\n", a + b);
}"""
    invalid_step2_response.usage = Mock()
    invalid_step2_response.usage.total_tokens = 80
    invalid_step2_response.usage.prompt_tokens = 60
    invalid_step2_response.usage.completion_tokens = 20
    
    # Configure mock to return invalid response on second call
    mock_client.chat.completions.create.side_effect = [step1_response, invalid_step2_response]
    
    # Generate solution (should fail due to template validation)
    result = generator.generate_solution(problem_info, "G++17", 2)
    
    print(f"Success: {result.get('success')}")
    print(f"Error: {result.get('error', 'No error')}")
    
    assert result["success"] == False, "Solution generation should fail for invalid template"
    assert "template structure" in result.get("error", "").lower(), "Error should mention template structure"
    
    print("✓ Invalid template test passed")
    
    print("\nTest 3: Python code should not be affected")
    print("-" * 40)
    
    # Test that Python code generation is not affected by C++ template validation
    python_response = Mock()
    python_response.choices = [Mock()]
    python_response.choices[0].message.content = """a, b = map(int, input().split())
print(a + b)"""
    python_response.usage = Mock()
    python_response.usage.total_tokens = 50
    python_response.usage.prompt_tokens = 30
    python_response.usage.completion_tokens = 20
    
    mock_client.chat.completions.create.side_effect = [step1_response, python_response]
    
    result = generator.generate_solution(problem_info, "Python3", 1)
    
    print(f"Success: {result.get('success')}")
    print(f"Code: {result.get('code', 'No code')}")
    
    assert result["success"] == True, "Python solution generation should not be affected"
    
    print("✓ Python test passed")

def test_benchmark_integration():
    """Test that the AIModelAdapter in benchmark.py would work with template validation"""
    
    print("\n" + "=" * 60)
    print("Testing Benchmark Integration...")
    print("=" * 60)
    
    # This test verifies that our changes are compatible with the benchmark system
    from jutge_solver.benchmark import AIModelAdapter
    from jutge_solver.benchmark_config import AIModelConfig
    
    # Create a test model config
    model_config = AIModelConfig(
        name="test-model",
        provider="openai", 
        model_id="gpt-4",
        api_key="test-key",
        max_tokens=1000,
        temperature=0.3,
        timeout=30,
        enabled=True
    )
    
    print("✓ AIModelConfig creation successful")
    
    # Test that AIModelAdapter can be created (this uses SolutionGenerator internally)
    try:
        adapter = AIModelAdapter(model_config)
        print("✓ AIModelAdapter creation successful")
        print("✓ SolutionGenerator integration confirmed")
    except Exception as e:
        print(f"✗ AIModelAdapter creation failed: {e}")
        raise
    
    print("✓ Benchmark integration test passed")

if __name__ == "__main__":
    try:
        test_solution_generation_with_template_validation()
        test_benchmark_integration()
        print("\n🎉 All integration tests completed successfully!")
        print("The C++ template enforcement is properly integrated with the benchmark system.")
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)