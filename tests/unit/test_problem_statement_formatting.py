"""
Unit tests for enhanced problem statement formatting in solution_generator.py
"""

import pytest
import base64
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from jutge_solver.solution_generator import SolutionGenerator


class MockConfig:
    """Mock configuration for testing"""
    pass


class TestProblemStatementFormatting:
    """Test suite for enhanced problem statement formatting functionality"""
    
    @pytest.fixture
    def generator(self):
        """Create a SolutionGenerator instance for testing"""
        return SolutionGenerator(None, MockConfig())
    
    def test_basic_problem_statement_formatting(self, generator):
        """Test basic problem statement formatting with title and author"""
        problem_info = {
            "title": "Sum of Two Numbers",
            "author": "Test Author",
            "statement": "<p>Calculate the sum of two integers</p>"
        }
        
        result = generator._get_problem_statement(problem_info)
        
        assert "Title: Sum of Two Numbers" in result
        assert "Author: Test Author" in result
        assert "Problem Statement:" in result
        assert "<p>Calculate the sum of two integers</p>" in result
        
    def test_problem_statement_with_sample_testcases(self, generator):
        """Test formatting with sample test cases"""
        problem_info = {
            "title": "Sum Problem",
            "author": "Test Author", 
            "statement": "<p>Add two numbers</p>",
            "sample_testcases": [
                {
                    "name": "sample1",
                    "input_b64": base64.b64encode("1 2\n".encode()).decode(),
                    "correct_b64": base64.b64encode("3\n".encode()).decode()
                },
                {
                    "name": "sample2",
                    "input_b64": base64.b64encode("5 7\n".encode()).decode(), 
                    "correct_b64": base64.b64encode("12\n".encode()).decode()
                }
            ]
        }
        
        result = generator._get_problem_statement(problem_info)
        
        # Check that sample test cases are included
        assert "Sample Test Cases:" in result
        assert "Test Case 1:" in result
        assert "Input: 1 2" in result
        assert "Expected Output: 3" in result
        assert "Test Case 2:" in result
        assert "Input: 5 7" in result
        assert "Expected Output: 12" in result
        
    def test_problem_statement_with_public_testcases(self, generator):
        """Test formatting with both sample and public test cases"""
        problem_info = {
            "title": "Sum Problem",
            "author": "Test Author",
            "statement": "<p>Add two numbers</p>",
            "sample_testcases": [
                {
                    "name": "sample1",
                    "input_b64": base64.b64encode("1 2\n".encode()).decode(),
                    "correct_b64": base64.b64encode("3\n".encode()).decode()
                }
            ],
            "public_testcases": [
                {
                    "name": "sample1", 
                    "input_b64": base64.b64encode("1 2\n".encode()).decode(),
                    "correct_b64": base64.b64encode("3\n".encode()).decode()
                },
                {
                    "name": "public1",
                    "input_b64": base64.b64encode("10 20\n".encode()).decode(),
                    "correct_b64": base64.b64encode("30\n".encode()).decode()
                },
                {
                    "name": "public2",
                    "input_b64": base64.b64encode("100 200\n".encode()).decode(),
                    "correct_b64": base64.b64encode("300\n".encode()).decode()
                }
            ]
        }
        
        result = generator._get_problem_statement(problem_info)
        
        # Check sample test cases
        assert "Sample Test Cases:" in result
        assert "Test Case 1:" in result
        assert "Input: 1 2" in result
        assert "Expected Output: 3" in result
        
        # Check additional public test cases
        assert "Additional Public Test Cases:" in result
        assert "Test Case 2:" in result
        assert "Input: 10 20" in result
        assert "Expected Output: 30" in result
        assert "Test Case 3:" in result
        assert "Input: 100 200" in result
        assert "Expected Output: 300" in result
        
    def test_problem_statement_handles_malformed_testcases(self, generator):
        """Test that malformed test cases are skipped gracefully"""
        problem_info = {
            "title": "Sum Problem",
            "author": "Test Author",
            "statement": "<p>Add two numbers</p>", 
            "sample_testcases": [
                {
                    # Valid test case
                    "name": "sample1",
                    "input_b64": base64.b64encode("1 2\n".encode()).decode(),
                    "correct_b64": base64.b64encode("3\n".encode()).decode()
                },
                {
                    # Malformed test case - invalid base64
                    "name": "sample2",
                    "input_b64": "invalid_base64!!!",
                    "correct_b64": "also_invalid!!!"
                },
                {
                    # Valid test case
                    "name": "sample3",
                    "input_b64": base64.b64encode("5 7\n".encode()).decode(),
                    "correct_b64": base64.b64encode("12\n".encode()).decode()
                }
            ]
        }
        
        result = generator._get_problem_statement(problem_info)
        
        # Should include valid test cases
        assert "Test Case 1:" in result
        assert "Input: 1 2" in result
        assert "Expected Output: 3" in result
        assert "Test Case 3:" in result
        assert "Input: 5 7" in result
        assert "Expected Output: 12" in result
        
        # Should not crash on malformed test case
        assert "Sample Test Cases:" in result
        
    def test_problem_statement_without_testcases(self, generator):
        """Test formatting when no test cases are available"""
        problem_info = {
            "title": "Sum Problem",
            "author": "Test Author",
            "statement": "<p>Add two numbers</p>"
        }
        
        result = generator._get_problem_statement(problem_info)
        
        assert "Title: Sum Problem" in result
        assert "Author: Test Author" in result
        assert "Problem Statement:" in result
        assert "<p>Add two numbers</p>" in result
        assert "Sample Test Cases:" not in result
        assert "Additional Public Test Cases:" not in result
        
    def test_problem_statement_without_statement(self, generator):
        """Test formatting when statement is missing"""
        problem_info = {
            "title": "Sum Problem", 
            "author": "Test Author"
        }
        
        result = generator._get_problem_statement(problem_info)
        
        assert "Title: Sum Problem" in result
        assert "Author: Test Author" in result
        assert "Problem Statement:" not in result
        
    def test_problem_statement_fallback_on_error(self, generator):
        """Test fallback behavior when formatting fails"""
        # Simulate error by passing None
        problem_info = None
        
        result = generator._get_problem_statement(problem_info)
        
        assert "Title: Unknown Problem" in result
        assert "Problem: Please solve this programming problem." in result
        
    def test_problem_statement_handles_multiline_input_output(self, generator):
        """Test formatting with multi-line input and output"""
        problem_info = {
            "title": "Matrix Problem",
            "author": "Test Author",
            "statement": "<p>Process a matrix</p>",
            "sample_testcases": [
                {
                    "name": "matrix1",
                    "input_b64": base64.b64encode("2 2\n1 2\n3 4\n".encode()).decode(),
                    "correct_b64": base64.b64encode("1 2\n3 4\n".encode()).decode()
                }
            ]
        }
        
        result = generator._get_problem_statement(problem_info)
        
        assert "Input: 2 2\n1 2\n3 4" in result
        assert "Expected Output: 1 2\n3 4" in result
        
    def test_problem_statement_with_empty_testcase_lists(self, generator):
        """Test behavior with empty test case lists"""
        problem_info = {
            "title": "Sum Problem",
            "author": "Test Author", 
            "statement": "<p>Add two numbers</p>",
            "sample_testcases": [],
            "public_testcases": []
        }
        
        result = generator._get_problem_statement(problem_info)
        
        assert "Title: Sum Problem" in result
        assert "Author: Test Author" in result
        assert "Sample Test Cases:" not in result
        assert "Additional Public Test Cases:" not in result