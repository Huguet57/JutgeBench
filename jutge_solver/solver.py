"""
Main Jutge Problem Solver class
"""

import sys
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime

# Add parent directory to path for jutge_api_client import
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import openai
from rich.console import Console

from jutge_api_client import JutgeApiClient
from .config import Config
from .problem_analyzer import ProblemAnalyzer
from .solution_generator import SolutionGenerator
from .verdict_manager import VerdictManager

console = Console()


class JutgeProblemSolver:
    """Main class for solving Jutge problems using OpenAI API"""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the solver with configuration"""
        self.config = config or Config.load_from_env()
        
        # Setup logging
        logging.basicConfig(
            level=getattr(logging, self.config.solver.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.jutge_client = JutgeApiClient()
        self.openai_client = openai.OpenAI(
            api_key=self.config.openai.api_key,
            base_url=self.config.openai.base_url,
        )
        self.problem_analyzer = ProblemAnalyzer(self.jutge_client)
        self.solution_generator = SolutionGenerator(self.openai_client, self.config.openai)
        self.verdict_manager = VerdictManager(self.jutge_client, self.config.jutge)
        
        self._authenticated = False
    
    def authenticate(self) -> bool:
        """Authenticate with Jutge platform"""
        if self._authenticated:
            return True
            
        try:
            console.print(f"[blue]Authenticating with Jutge as {self.config.jutge.email}...[/blue]")
            self.jutge_client.login(self.config.jutge.email, self.config.jutge.password)
            self._authenticated = True
            console.print("[green]✓ Authentication successful[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Authentication failed: {e}[/red]")
            self.logger.error(f"Authentication failed: {e}")
            return False
    
    def solve_problem(self, problem_id: str, compiler_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Complete workflow: Read problem -> Generate solution -> Submit -> Get verdict
        
        Args:
            problem_id: The Jutge problem ID (e.g., "P68688_en")
            compiler_id: Optional compiler override
            
        Returns:
            Dict containing the full workflow results
        """
        if not self.authenticate():
            return {"success": False, "error": "Authentication failed"}
        
        workflow_start = datetime.now()
        results = {
            "problem_id": problem_id,
            "timestamp": workflow_start.isoformat(),
            "success": False,
            "steps": {}
        }
        
        try:
            # Step 1: Read and analyze problem
            console.print(f"[blue]📖 Reading problem {problem_id}...[/blue]")
            problem_info = self.problem_analyzer.analyze_problem(problem_id)
            results["steps"]["problem_analysis"] = problem_info
            
            if not problem_info["success"]:
                results["error"] = "Failed to read problem"
                return results
            
            # Step 2: Generate solution
            console.print("[blue]🤖 Generating solution with OpenAI...[/blue]")
            target_compiler = compiler_id or self._select_compiler(problem_info)
            
            solution_result = self.solution_generator.generate_solution(
                problem_info,
                target_compiler
            )
            results["steps"]["solution_generation"] = solution_result
            
            if not solution_result["success"]:
                results["error"] = "Failed to generate solution"
                return results
            
            # Step 3: Submit solution
            console.print("[blue]📤 Submitting solution...[/blue]")
            submission_result = self._submit_solution(
                problem_id,
                target_compiler,
                solution_result["code"]
            )
            results["steps"]["submission"] = submission_result
            
            if not submission_result["success"]:
                results["error"] = "Failed to submit solution"
                return results
            
            # Step 4: Get verdict
            console.print("[blue]⏳ Waiting for verdict...[/blue]")
            verdict_result = self.verdict_manager.get_verdict(
                problem_id,
                submission_result["submission_id"]
            )
            results["steps"]["verdict"] = verdict_result
            
            results["success"] = True
            results["final_verdict"] = verdict_result.get("verdict", "UNKNOWN")
            
            # Summary
            duration = (datetime.now() - workflow_start).total_seconds()
            results["duration_seconds"] = duration
            
            self._print_summary(results)
            
        except Exception as e:
            console.print(f"[red]✗ Workflow failed: {e}[/red]")
            self.logger.error(f"Workflow failed: {e}")
            results["error"] = str(e)
        
        return results
    
    def _select_compiler(self, problem_info: Dict[str, Any]) -> str:
        """Select appropriate compiler based on problem analysis"""
        # For now, use the default compiler
        # TODO: Implement intelligent compiler selection based on problem type
        return self.config.jutge.default_compiler
    
    def _submit_solution(self, problem_id: str, compiler_id: str, code: str) -> Dict[str, Any]:
        """Submit solution to Jutge"""
        try:
            annotation = f"Generated by Jutge Problem Solver at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            submission_id = self.jutge_client.student.submissions.submit(
                problem_id,
                compiler_id,
                code,
                annotation
            )
            
            console.print(f"[green]✓ Solution submitted with ID: {submission_id}[/green]")
            
            return {
                "success": True,
                "submission_id": submission_id,
                "compiler_id": compiler_id,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            console.print(f"[red]✗ Submission failed: {e}[/red]")
            self.logger.error(f"Submission failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _print_summary(self, results: Dict[str, Any]) -> None:
        """Print a formatted summary of the workflow results"""
        console.print("\n" + "="*60)
        console.print(f"[bold]WORKFLOW SUMMARY - {results['problem_id']}[/bold]")
        console.print("="*60)
        
        if results["success"]:
            verdict = results["final_verdict"]
            color = "green" if verdict == "AC" else "red" if verdict in ["WA", "TLE", "CE"] else "yellow"
            console.print(f"[{color}]Final Verdict: {verdict}[/{color}]")
        else:
            console.print(f"[red]Status: FAILED - {results.get('error', 'Unknown error')}[/red]")
        
        console.print(f"Duration: {results.get('duration_seconds', 0):.2f} seconds")
        
        # Step details
        steps = results.get("steps", {})
        for step_name, step_data in steps.items():
            status = "✓" if step_data.get("success", False) else "✗"
            console.print(f"{status} {step_name.replace('_', ' ').title()}")
        
        console.print("="*60)