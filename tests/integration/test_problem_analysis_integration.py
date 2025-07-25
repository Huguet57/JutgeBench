"""
Integration tests for the complete problem analysis and statement formatting flow
"""

import pytest
import base64
from unittest.mock import Mock, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from jutge_solver.problem_analyzer import ProblemAnalyzer
from jutge_solver.solution_generator import SolutionGenerator


class TestProblemAnalysisIntegration:
    """Integration tests for problem analysis to solution generation flow"""
    
    @pytest.fixture
    def mock_jutge_client(self):
        """Create a comprehensive mock Jutge API client"""
        client = Mock()
        
        # Mock abstract problem
        mock_abstract_problem = Mock()
        mock_abstract_problem.author = "Programming Contest Committee"
        mock_abstract_problem.problem_nm = "SUM001"
        mock_abstract_problem.created_at = "2024-01-01 12:00:00"
        mock_abstract_problem.type = "basic"
        
        # Mock problem rich data
        mock_problem_rich = Mock()
        mock_problem_rich.title = "Sum of Two Integers"
        mock_problem_rich.html_statement = """
        <div>
            <p>Given two integers A and B, compute their sum.</p>
            <h3>Input</h3>
            <p>Two integers A and B (1 ≤ A, B ≤ 1000)</p>
            <h3>Output</h3>
            <p>Print the sum A + B</p>
        </div>
        """
        mock_problem_rich.abstract_problem = mock_abstract_problem
        mock_problem_rich.sample_testcases = [
            {
                "name": "sample1",
                "input_b64": base64.b64encode("1 2".encode()).decode(),
                "correct_b64": base64.b64encode("3".encode()).decode()
            },
            {
                "name": "sample2",
                "input_b64": base64.b64encode("5 7".encode()).decode(),
                "correct_b64": base64.b64encode("12".encode()).decode()
            }
        ]
        
        # Mock public testcases (includes samples + additional)
        mock_public_testcases = [
            {
                "name": "sample1",
                "input_b64": base64.b64encode("1 2".encode()).decode(),
                "correct_b64": base64.b64encode("3".encode()).decode()
            },
            {
                "name": "sample2", 
                "input_b64": base64.b64encode("5 7".encode()).decode(),
                "correct_b64": base64.b64encode("12".encode()).decode()
            },
            {
                "name": "public1",
                "input_b64": base64.b64encode("10 20".encode()).decode(),
                "correct_b64": base64.b64encode("30".encode()).decode()
            },
            {
                "name": "public2",
                "input_b64": base64.b64encode("100 200".encode()).decode(),
                "correct_b64": base64.b64encode("300".encode()).decode()
            },
            {
                "name": "edge1",
                "input_b64": base64.b64encode("1000 1000".encode()).decode(),
                "correct_b64": base64.b64encode("2000".encode()).decode()
            }
        ]
        
        client.problems.get_problem_rich.return_value = mock_problem_rich
        client.problems.get_public_testcases.return_value = mock_public_testcases
        
        return client
    
    @pytest.fixture 
    def problem_analyzer(self, mock_jutge_client):
        """Create problem analyzer with mocked client"""
        return ProblemAnalyzer(mock_jutge_client)
        
    @pytest.fixture
    def solution_generator(self):
        """Create solution generator for testing"""
        return SolutionGenerator(None, Mock())
    
    def test_complete_problem_analysis_to_statement_flow(self, problem_analyzer, solution_generator):
        """Test the complete flow from problem analysis to formatted statement"""
        # Step 1: Analyze the problem
        problem_info = problem_analyzer.analyze_problem("P12345_en")
        
        # Verify analysis results
        assert problem_info["success"] is True
        assert problem_info["title"] == "Sum of Two Integers"
        assert problem_info["author"] == "Programming Contest Committee"
        assert len(problem_info["sample_testcases"]) == 2
        assert len(problem_info["public_testcases"]) == 5
        
        # Step 2: Generate formatted problem statement
        formatted_statement = solution_generator._get_problem_statement(problem_info)
        
        # Verify comprehensive formatting
        assert "Title: Sum of Two Integers" in formatted_statement
        assert "Author: Programming Contest Committee" in formatted_statement
        assert "Problem Statement:" in formatted_statement
        assert "Given two integers A and B, compute their sum." in formatted_statement
        
        # Verify sample test cases are included
        assert "Sample Test Cases:" in formatted_statement
        assert "Test Case 1:" in formatted_statement
        assert "Input: 1 2" in formatted_statement
        assert "Expected Output: 3" in formatted_statement
        assert "Test Case 2:" in formatted_statement
        assert "Input: 5 7" in formatted_statement
        assert "Expected Output: 12" in formatted_statement
        
        # Verify additional public test cases are included
        assert "Additional Public Test Cases:" in formatted_statement
        assert "Test Case 3:" in formatted_statement
        assert "Input: 10 20" in formatted_statement
        assert "Expected Output: 30" in formatted_statement
        assert "Test Case 4:" in formatted_statement
        assert "Input: 100 200" in formatted_statement
        assert "Expected Output: 300" in formatted_statement
        assert "Test Case 5:" in formatted_statement
        assert "Input: 1000 1000" in formatted_statement
        assert "Expected Output: 2000" in formatted_statement
        
    def test_problem_analysis_preserves_all_data_for_statement(self, problem_analyzer, solution_generator):
        """Test that all necessary data is preserved through the analysis pipeline"""
        # Analyze problem
        problem_info = problem_analyzer.analyze_problem("P12345_en")
        
        # Verify all required fields for statement generation are present
        required_fields = [
            "title", "author", "statement", "abstract_problem", 
            "sample_testcases", "public_testcases"
        ]
        
        for field in required_fields:
            assert field in problem_info, f"Missing required field: {field}"
            
        # Verify abstract problem structure
        assert problem_info["abstract_problem"].author == "Programming Contest Committee"
        assert problem_info["abstract_problem"].problem_nm == "SUM001"
        
        # Verify testcase structure
        sample_testcase = problem_info["sample_testcases"][0]
        assert "name" in sample_testcase
        assert "input_b64" in sample_testcase
        assert "correct_b64" in sample_testcase
        
        public_testcase = problem_info["public_testcases"][0]
        assert "name" in public_testcase
        assert "input_b64" in public_testcase
        assert "correct_b64" in public_testcase
        
    def test_statement_formatting_handles_edge_cases_from_analysis(self, problem_analyzer, solution_generator):
        """Test that statement formatter handles various data scenarios from analysis"""
        problem_info = problem_analyzer.analyze_problem("P12345_en")
        
        # Test with complete data
        full_statement = solution_generator._get_problem_statement(problem_info)
        assert len(full_statement) > 500  # Should be comprehensive
        
        # Test with minimal data (simulate missing optional fields)
        minimal_info = {
            "title": problem_info["title"],
            "author": problem_info["author"],
            "statement": problem_info["statement"]
        }
        minimal_statement = solution_generator._get_problem_statement(minimal_info)
        assert "Title: Sum of Two Integers" in minimal_statement
        assert "Author: Programming Contest Committee" in minimal_statement
        
        # Test with only samples (no additional public testcases)
        samples_only_info = {
            "title": problem_info["title"],
            "author": problem_info["author"], 
            "statement": problem_info["statement"],
            "sample_testcases": problem_info["sample_testcases"],
            "public_testcases": problem_info["sample_testcases"]  # Same as samples
        }
        samples_statement = solution_generator._get_problem_statement(samples_only_info)
        assert "Sample Test Cases:" in samples_statement
        assert "Additional Public Test Cases:" not in samples_statement
        
    def test_api_integration_calls(self, mock_jutge_client, problem_analyzer):
        """Test that the correct API methods are called in the right sequence"""
        problem_analyzer.analyze_problem("P12345_en")
        
        # Verify API calls were made
        mock_jutge_client.problems.get_problem_rich.assert_called_once_with("P12345_en")
        mock_jutge_client.problems.get_public_testcases.assert_called_once_with("P12345_en")
        
        # Verify call order (get_problem_rich should be called first)
        calls = mock_jutge_client.problems.method_calls
        assert len(calls) == 2
        assert calls[0][0] == 'get_problem_rich'
        assert calls[1][0] == 'get_public_testcases'
        
    def test_error_handling_in_integration_flow(self, mock_jutge_client, solution_generator):
        """Test error handling throughout the integration flow"""
        # Simulate API error
        mock_jutge_client.problems.get_problem_rich.side_effect = Exception("Network Error")
        problem_analyzer = ProblemAnalyzer(mock_jutge_client)
        
        # Analysis should handle error gracefully
        problem_info = problem_analyzer.analyze_problem("P12345_en")
        assert problem_info["success"] is False
        assert "error" in problem_info
        
        # Statement generator should handle missing data gracefully
        error_statement = solution_generator._get_problem_statement(problem_info)
        assert "Title: Unknown Problem" in error_statement
        assert "Author: Unknown Author" in error_statement
        # Should not crash and should provide basic fallback