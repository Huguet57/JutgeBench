"""
Problem analysis module for extracting and parsing problem information
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from rich.console import Console

console = Console()


class ProblemAnalyzer:
    """Analyzes Jutge problems to extract key information for solution generation"""
    
    def __init__(self, jutge_client):
        self.jutge_client = jutge_client
    
    def analyze_problem(self, problem_id: str) -> Dict[str, Any]:
        """
        Analyze a problem and extract all relevant information
        
        Args:
            problem_id: The Jutge problem ID
            
        Returns:
            Dict containing problem analysis results
        """
        try:
            # Get problem details with rich information
            problem_rich = self.jutge_client.problems.get_problem_rich(problem_id)
            statement = problem_rich.html_statement
            
            # Get public test cases
            public_testcases = self.jutge_client.problems.get_public_testcases(problem_id)
            
            # Parse the problem statement
            parsed_info = self._parse_problem_statement(statement)
            
            result = {
                "success": True,
                "problem_id": problem_id,
                "title": problem_rich.title,
                "author": problem_rich.abstract_problem.author,
                "statement": statement,
                "abstract_problem": problem_rich.abstract_problem,
                "sample_testcases": problem_rich.sample_testcases,
                "public_testcases": public_testcases,
                "parsed_info": parsed_info,
                "problem": problem_rich,  # Keep the full problem object
                "timestamp": datetime.now().isoformat()
            }
            
            console.print(f"[green]✓ Problem analyzed: {problem_rich.title}[/green]")
            return result
            
        except Exception as e:
            console.print(f"[red]✗ Problem analysis failed: {e}[/red]")
            return {
                "success": False,
                "problem_id": problem_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _parse_problem_statement(self, statement: str) -> Dict[str, Any]:
        """
        Parse the problem statement to extract key information
        
        Args:
            statement: The raw problem statement text
            
        Returns:
            Dict containing parsed information
        """
        parsed = {
            "description": "",
            "input_format": "",
            "output_format": "",
            "sample_cases": [],
            "constraints": "",
            "notes": ""
        }
        
        # Split the statement into sections
        sections = self._split_into_sections(statement)
        
        # Extract description (everything before "Input" section)
        if "main" in sections:
            parsed["description"] = sections["main"].strip()
        
        # Extract input format
        if "input" in sections:
            parsed["input_format"] = sections["input"].strip()
        
        # Extract output format
        if "output" in sections:
            parsed["output_format"] = sections["output"].strip()
        
        # Extract sample cases
        parsed["sample_cases"] = self._extract_sample_cases(statement)
        
        # Extract constraints and notes
        if "observation" in sections:
            parsed["notes"] = sections["observation"].strip()
        if "constraint" in sections:
            parsed["constraints"] = sections["constraint"].strip()
        
        return parsed
    
    def _split_into_sections(self, statement: str) -> Dict[str, str]:
        """Split the problem statement into labeled sections"""
        sections = {}
        current_section = "main"
        current_content = []
        
        lines = statement.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Check if this line is a section header
            section_name = self._identify_section_header(line)
            if section_name:
                # Save previous section
                sections[current_section] = '\n'.join(current_content)
                # Start new section
                current_section = section_name
                current_content = []
            else:
                current_content.append(line)
        
        # Save the last section
        sections[current_section] = '\n'.join(current_content)
        
        return sections
    
    def _identify_section_header(self, line: str) -> Optional[str]:
        """Identify if a line is a section header"""
        line_lower = line.lower().strip()
        
        # Common section headers in Jutge problems
        if line_lower == "input":
            return "input"
        elif line_lower == "output":
            return "output"
        elif line_lower in ["observation", "observations"]:
            return "observation"
        elif line_lower in ["constraint", "constraints"]:
            return "constraint"
        elif line_lower in ["sample input", "sample", "example"]:
            return "sample"
        elif line_lower in ["note", "notes"]:
            return "notes"
        
        return None
    
    def _extract_sample_cases(self, statement: str) -> List[Dict[str, str]]:
        """
        Extract sample input/output cases from the problem statement
        
        This is tricky because sample cases can be embedded in different ways.
        We'll use heuristics to try to find them.
        """
        sample_cases = []
        
        # Look for common patterns
        # Pattern 1: Explicit "Sample Input" and "Sample Output" sections
        input_pattern = r"(?:Sample\s+Input|Input\s+Example).*?:\s*(.*?)(?=Sample\s+Output|Output\s+Example|$)"
        output_pattern = r"(?:Sample\s+Output|Output\s+Example).*?:\s*(.*?)(?=\n\n|$)"
        
        input_matches = re.findall(input_pattern, statement, re.IGNORECASE | re.DOTALL)
        output_matches = re.findall(output_pattern, statement, re.IGNORECASE | re.DOTALL)
        
        for i, (inp, out) in enumerate(zip(input_matches, output_matches)):
            sample_cases.append({
                "input": inp.strip(),
                "output": out.strip(),
                "case_number": i + 1
            })
        
        # If no explicit samples found, try to infer from context
        if not sample_cases:
            sample_cases = self._infer_sample_cases(statement)
        
        return sample_cases
    
    def _infer_sample_cases(self, statement: str) -> List[Dict[str, str]]:
        """
        Try to infer sample cases from the problem description
        This is best-effort and may not always work
        """
        sample_cases = []
        
        # Look for quoted strings or code blocks that might be examples
        # This is very basic and problem-specific
        
        # For now, return empty list - this can be enhanced later
        return sample_cases
    
    def get_problem_difficulty(self, problem_id: str) -> str:
        """
        Estimate problem difficulty based on various factors
        Returns: "easy", "medium", "hard"
        """
        # This is a placeholder - in practice, this could analyze:
        # - Problem tags/categories
        # - Statement complexity
        # - Historical submission statistics
        # - etc.
        
        return "medium"
    
    def suggest_approach(self, parsed_info: Dict[str, Any]) -> List[str]:
        """
        Suggest potential approaches based on problem analysis
        
        Returns:
            List of suggested approaches/algorithms
        """
        approaches = []
        
        description = parsed_info.get("description", "").lower()
        
        # Basic heuristics for approach suggestion
        if "sort" in description or "order" in description:
            approaches.append("sorting")
        
        if "search" in description or "find" in description:
            approaches.append("search")
        
        if "graph" in description or "tree" in description:
            approaches.append("graph_algorithms")
        
        if "dynamic" in description or "dp" in description:
            approaches.append("dynamic_programming")
        
        if "recursive" in description or "recursion" in description:
            approaches.append("recursion")
        
        # Default to basic algorithms if nothing specific detected
        if not approaches:
            approaches.append("basic_algorithms")
        
        return approaches