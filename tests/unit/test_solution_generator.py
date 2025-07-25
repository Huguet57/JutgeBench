"""
Unit tests for solution_generator.py code extraction functionality
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from jutge_solver.solution_generator import SolutionGenerator


class MockConfig:
    """Mock configuration for testing"""
    pass


class TestCodeExtraction:
    """Test suite for code extraction from AI model responses"""
    
    @pytest.fixture
    def generator(self):
        """Create a SolutionGenerator instance for testing"""
        return SolutionGenerator(None, MockConfig())
    
    def test_clean_code_without_markdown(self, generator):
        """Test extraction of clean code without any markdown"""
        test_cases = [
            {
                "input": 'print("Hello world!")',
                "expected": 'print("Hello world!")',
                "description": "Simple print statement"
            },
            {
                "input": 'def solve():\n    x = int(input())\n    print(x * 2)',
                "expected": 'def solve():\n    x = int(input())\n    print(x * 2)',
                "description": "Multi-line function"
            }
        ]
        
        for case in test_cases:
            result = generator._extract_code(case["input"], "Python3")
            assert result == case["expected"], f"Failed for: {case['description']}"
    
    def test_markdown_with_actual_newlines(self, generator):
        """Test extraction from markdown blocks with actual newlines"""
        test_cases = [
            {
                "input": '```python\nprint("Hello world!")\n```',
                "expected": 'print("Hello world!")',
                "description": "Standard markdown with language identifier"
            },
            {
                "input": '```\nprint("Hello world!")\n```',
                "expected": 'print("Hello world!")',
                "description": "Markdown without language identifier"
            },
            {
                "input": '```Python\nprint("Hello world!")\n```',
                "expected": 'print("Hello world!")',
                "description": "Markdown with capitalized Python"
            },
            {
                "input": '```py\nprint("Hello world!")\n```',
                "expected": 'print("Hello world!")',
                "description": "Markdown with py abbreviation"
            }
        ]
        
        for case in test_cases:
            result = generator._extract_code(case["input"], "Python3")
            assert result == case["expected"], f"Failed for: {case['description']}"
    
    def test_markdown_with_escaped_newlines(self, generator):
        """Test extraction from markdown blocks with escaped newlines"""
        test_cases = [
            {
                "input": '```python\\nprint("Hello world!")\\n```',
                "expected": 'print("Hello world!")',
                "description": "Escaped newlines with language"
            },
            {
                "input": '```\\nprint("Hello world!")\\n```',
                "expected": 'print("Hello world!")',
                "description": "Escaped newlines without language"
            }
        ]
        
        for case in test_cases:
            result = generator._extract_code(case["input"], "Python3")
            assert result == case["expected"], f"Failed for: {case['description']}"
    
    def test_inline_markdown_blocks(self, generator):
        """Test extraction from inline markdown blocks (no newlines after backticks)"""
        test_cases = [
            {
                "input": '```python\nprint("Hello world!")```',
                "expected": 'print("Hello world!")',
                "description": "No newline before closing backticks"
            },
            {
                "input": '```print("Hello world!")```',
                "expected": 'print("Hello world!")',
                "description": "Inline code block"
            }
        ]
        
        for case in test_cases:
            result = generator._extract_code(case["input"], "Python3")
            assert result == case["expected"], f"Failed for: {case['description']}"
    
    def test_code_with_explanations(self, generator):
        """Test extraction when code is mixed with explanations"""
        test_cases = [
            {
                "input": 'Here is the solution:\n\n```python\nprint("Hello world!")\n```',
                "expected": 'print("Hello world!")',
                "description": "Code with preceding explanation"
            },
            {
                "input": 'Solution:\n```python\nprint("Hello world!")\n```\n\nThis prints hello world.',
                "expected": 'print("Hello world!")',
                "description": "Code with surrounding text"
            }
        ]
        
        for case in test_cases:
            result = generator._extract_code(case["input"], "Python3")
            assert result == case["expected"], f"Failed for: {case['description']}"
    
    def test_multiline_code_extraction(self, generator):
        """Test extraction of multi-line code"""
        code = '''def solve():
    n = int(input())
    for i in range(n):
        print(i * 2)
        
solve()'''
        
        test_cases = [
            {
                "input": f'```python\n{code}\n```',
                "expected": code,
                "description": "Multi-line code in markdown"
            },
            {
                "input": code,
                "expected": code,
                "description": "Multi-line code without markdown"
            }
        ]
        
        for case in test_cases:
            result = generator._extract_code(case["input"], "Python3")
            assert result == case["expected"], f"Failed for: {case['description']}"
    
    def test_cpp_code_extraction(self, generator):
        """Test C++ code extraction"""
        cpp_code = '''#include <iostream>
using namespace std;

int main() {
    cout << "Hello world!" << endl;
    return 0;
}'''
        
        test_cases = [
            {
                "input": f'```cpp\n{cpp_code}\n```',
                "expected": cpp_code,
                "compiler": "G++17"
            },
            {
                "input": f'```c++\n{cpp_code}\n```',
                "expected": cpp_code,
                "compiler": "G++17"
            }
        ]
        
        for case in test_cases:
            result = generator._extract_code(case["input"], case["compiler"])
            assert result == case["expected"], f"Failed for C++ extraction"
    
    def test_java_code_extraction(self, generator):
        """Test Java code extraction"""
        java_code = '''public class Main {
    public static void main(String[] args) {
        System.out.println("Hello world!");
    }
}'''
        
        test_cases = [
            {
                "input": f'```java\n{java_code}\n```',
                "expected": java_code,
                "compiler": "JDK"
            },
            {
                "input": f'```Java\n{java_code}\n```',
                "expected": java_code,
                "compiler": "JDK"
            }
        ]
        
        for case in test_cases:
            result = generator._extract_code(case["input"], case["compiler"])
            assert result == case["expected"], f"Failed for Java extraction"
    
    def test_edge_cases(self, generator):
        """Test edge cases and potential problem scenarios"""
        test_cases = [
            {
                "input": '```python```',
                "expected": None,
                "description": "Empty code block with language"
            },
            {
                "input": '``````',
                "expected": None,
                "description": "Empty code block"
            },
            {
                "input": 'Just some text without code',
                "expected": 'Just some text without code',  # Falls back to _clean_response
                "description": "No code markers"
            }
        ]
        
        for case in test_cases:
            result = generator._extract_code(case["input"], "Python3")
            if case["expected"] is None:
                assert result is None or result == "", f"Failed for: {case['description']}"
            else:
                assert result == case["expected"], f"Failed for: {case['description']}"
    
    def test_real_world_responses(self, generator):
        """Test with actual responses from different AI models"""
        # Gemini-2.5-Pro style (from the benchmark results)
        gemini_response = '```python\nprint("Hello world!")\n```'
        result = generator._extract_code(gemini_response, "Python3")
        assert result == 'print("Hello world!")', "Failed for Gemini-2.5-Pro style response"
        
        # DeepSeek style
        deepseek_response = '```python\nprint("Hello world!")\n```'
        result = generator._extract_code(deepseek_response, "Python3")
        assert result == 'print("Hello world!")', "Failed for DeepSeek style response"
        
        # Clean response (Gemini-2.5-Flash style)
        clean_response = 'print("Hello world!")'
        result = generator._extract_code(clean_response, "Python3")
        assert result == 'print("Hello world!")', "Failed for clean response"


if __name__ == "__main__":
    # Run tests with pytest if available, otherwise run basic tests
    try:
        import pytest
        pytest.main([__file__, "-v"])
    except ImportError:
        print("pytest not installed, running basic tests...")
        generator = SolutionGenerator(None, MockConfig())
        
        # Test the problematic cases from the benchmark
        test_cases = [
            ('```python\nprint("Hello world!")\n```', 'Gemini-2.5-Pro/DeepSeek style'),
            ('print("Hello world!")', 'Clean code style'),
        ]
        
        for response, style in test_cases:
            result = generator._extract_code(response, "Python3")
            expected = 'print("Hello world!")'
            status = "✓ PASSED" if result == expected else "✗ FAILED"
            print(f"{style}: {status}")
            if result != expected:
                print(f"  Expected: {repr(expected)}")
                print(f"  Got: {repr(result)}") 