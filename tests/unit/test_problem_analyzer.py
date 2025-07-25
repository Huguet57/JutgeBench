"""
Unit tests for problem_analyzer.py enhanced functionality
"""

import pytest
import base64
from unittest.mock import Mock, MagicMock
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from jutge_solver.problem_analyzer import ProblemAnalyzer


class TestProblemAnalyzer:
    """Test suite for enhanced problem analyzer functionality"""
    
    @pytest.fixture
    def mock_jutge_client(self):
        """Create a mock Jutge API client"""
        client = Mock()
        
        # Mock problem rich data
        mock_abstract_problem = Mock()
        mock_abstract_problem.author = "Test Author"
        mock_abstract_problem.problem_nm = "TEST001"
        
        mock_problem_rich = Mock()
        mock_problem_rich.title = "Test Problem"
        mock_problem_rich.html_statement = "<p>This is a test problem statement</p>"
        mock_problem_rich.abstract_problem = mock_abstract_problem
        mock_problem_rich.sample_testcases = [
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
        
        # Mock public testcases
        mock_public_testcases = [
            {
                "name": "sample1",
                "input_b64": base64.b64encode("1 2\n".encode()).decode(),
                "correct_b64": base64.b64encode("3\n".encode()).decode()
            },
            {
                "name": "sample2",
                "input_b64": base64.b64encode("5 7\n".encode()).decode(), 
                "correct_b64": base64.b64encode("12\n".encode()).decode()
            },
            {
                "name": "public1",
                "input_b64": base64.b64encode("10 20\n".encode()).decode(),
                "correct_b64": base64.b64encode("30\n".encode()).decode()
            }
        ]
        
        client.problems.get_problem_rich.return_value = mock_problem_rich
        client.problems.get_public_testcases.return_value = mock_public_testcases
        
        return client
    
    @pytest.fixture
    def analyzer(self, mock_jutge_client):
        """Create a ProblemAnalyzer instance with mocked client"""
        return ProblemAnalyzer(mock_jutge_client)
    
    def test_analyze_problem_with_rich_data(self, analyzer):
        """Test that analyze_problem returns comprehensive problem information"""
        result = analyzer.analyze_problem("P12345_en")
        
        assert result["success"] is True
        assert result["problem_id"] == "P12345_en"
        assert result["title"] == "Test Problem"
        assert result["author"] == "Test Author"
        assert result["statement"] == "<p>This is a test problem statement</p>"
        assert "timestamp" in result
        
    def test_analyze_problem_includes_abstract_problem(self, analyzer):
        """Test that abstract problem details are included in result"""
        result = analyzer.analyze_problem("P12345_en")
        
        assert "abstract_problem" in result
        assert result["abstract_problem"].author == "Test Author"
        assert result["abstract_problem"].problem_nm == "TEST001"
        
    def test_analyze_problem_includes_sample_testcases(self, analyzer):
        """Test that sample testcases are included in result"""
        result = analyzer.analyze_problem("P12345_en")
        
        assert "sample_testcases" in result
        assert len(result["sample_testcases"]) == 2
        
        # Check first sample testcase
        testcase1 = result["sample_testcases"][0]
        assert testcase1["name"] == "sample1"
        assert base64.b64decode(testcase1["input_b64"]).decode() == "1 2\n"
        assert base64.b64decode(testcase1["correct_b64"]).decode() == "3\n"
        
    def test_analyze_problem_includes_public_testcases(self, analyzer):
        """Test that public testcases are included in result"""
        result = analyzer.analyze_problem("P12345_en")
        
        assert "public_testcases" in result
        assert len(result["public_testcases"]) == 3
        
        # Check that we have the additional public testcase
        public_testcase = result["public_testcases"][2]
        assert public_testcase["name"] == "public1"
        assert base64.b64decode(public_testcase["input_b64"]).decode() == "10 20\n"
        assert base64.b64decode(public_testcase["correct_b64"]).decode() == "30\n"
        
    def test_analyze_problem_calls_correct_api_methods(self, analyzer, mock_jutge_client):
        """Test that the correct API methods are called"""
        analyzer.analyze_problem("P12345_en")
        
        mock_jutge_client.problems.get_problem_rich.assert_called_once_with("P12345_en")
        mock_jutge_client.problems.get_public_testcases.assert_called_once_with("P12345_en")
        
    def test_analyze_problem_handles_api_error(self, mock_jutge_client):
        """Test that API errors are handled gracefully"""
        mock_jutge_client.problems.get_problem_rich.side_effect = Exception("API Error")
        analyzer = ProblemAnalyzer(mock_jutge_client)
        
        result = analyzer.analyze_problem("P12345_en")
        
        assert result["success"] is False
        assert "error" in result
        assert result["problem_id"] == "P12345_en"
        
    def test_analyze_problem_preserves_full_problem_object(self, analyzer):
        """Test that the full problem rich object is preserved in result"""
        result = analyzer.analyze_problem("P12345_en")
        
        assert "problem" in result
        assert result["problem"].title == "Test Problem"
        assert result["problem"].html_statement == "<p>This is a test problem statement</p>"