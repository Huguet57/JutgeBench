"""
Verdict management module for polling and handling submission results
"""

import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)


class VerdictManager:
    """Manages submission verdict polling and interpretation"""
    
    def __init__(self, jutge_client, jutge_config):
        self.client = jutge_client
        self.config = jutge_config
        
        # Verdict interpretations
        self.verdict_meanings = {
            "AC": "Accepted ✓",
            "WA": "Wrong Answer ✗",
            "TLE": "Time Limit Exceeded ⏰",
            "CE": "Compilation Error 🔨",
            "RE": "Runtime Error 💥",
            "PE": "Presentation Error 📝",
            "OLE": "Output Limit Exceeded 📄",
            "MLE": "Memory Limit Exceeded 💾",
            "IE": "Internal Error ⚠️",
            "QE": "Queue Error 🚨"
        }
    
    def get_verdict(self, problem_id: str, submission_id: str) -> Dict[str, Any]:
        """
        Poll for verdict until submission is complete
        
        Args:
            problem_id: The problem identifier
            submission_id: The submission identifier
            
        Returns:
            Dict containing verdict information
        """
        start_time = datetime.now()
        poll_count = 0
        
        try:
            console.print(f"  Polling for verdict of submission {submission_id}...")
            
            while True:
                poll_count += 1
                elapsed = (datetime.now() - start_time).total_seconds()
                
                # Check timeout
                if elapsed > self.config.submission_timeout:
                    return {
                        "success": False,
                        "error": "Verdict polling timeout",
                        "timeout": True,
                        "elapsed_seconds": elapsed,
                        "polls": poll_count
                    }
                
                try:
                    # Get submission status
                    # Note: The API structure might need adjustment based on actual Jutge API
                    state = self.client.student.submissions.get(problem_id, submission_id)
                    
                    if state.state == "done":
                        verdict = state.veredict
                        meaning = self.verdict_meanings.get(verdict, f"Unknown verdict: {verdict}")
                        
                        console.print(f"  [{'green' if verdict == 'AC' else 'red'}]Verdict: {meaning}[/{'green' if verdict == 'AC' else 'red'}]")
                        
                        return {
                            "success": True,
                            "verdict": verdict,
                            "meaning": meaning,
                            "state": state.state,
                            "elapsed_seconds": elapsed,
                            "polls": poll_count,
                            "timestamp": datetime.now().isoformat(),
                            "submission_details": self._extract_submission_details(state)
                        }
                    
                    else:
                        # Still processing
                        console.print(f"  Status: {state.state} (poll #{poll_count}, {elapsed:.1f}s)")
                        time.sleep(2)  # Wait 2 seconds before next poll
                
                except AttributeError as e:
                    logger.warning(f"API structure issue: {e}")
                    # Fallback: try alternative API structure
                    return self._try_alternative_verdict_check(problem_id, submission_id, elapsed, poll_count)
                
                except Exception as e:
                    logger.error(f"Error polling verdict: {e}")
                    time.sleep(1)  # Brief wait before retry
                    continue
                    
        except Exception as e:
            console.print(f"  [red]✗ Verdict polling failed: {e}[/red]")
            logger.error(f"Verdict polling failed: {e}")
            
            return {
                "success": False,
                "error": str(e),
                "elapsed_seconds": (datetime.now() - start_time).total_seconds(),
                "polls": poll_count
            }
    
    def _try_alternative_verdict_check(self, problem_id: str, submission_id: str, 
                                     elapsed: float, poll_count: int) -> Dict[str, Any]:
        """
        Try alternative methods to get verdict if primary method fails
        """
        try:
            # Since the simple submit API returns just an ID, we might need to use
            # different approaches to get the verdict
            
            # Method 1: Check if we can get recent submissions
            try:
                submissions = self.client.student.submissions.get_all()
                for submission in submissions:
                    if hasattr(submission, 'submission_id') and submission.submission_id == submission_id:
                        if hasattr(submission, 'veredict') and submission.veredict:
                            verdict = submission.veredict
                            meaning = self.verdict_meanings.get(verdict, f"Unknown verdict: {verdict}")
                            
                            return {
                                "success": True,
                                "verdict": verdict,
                                "meaning": meaning,
                                "method": "alternative_check",
                                "elapsed_seconds": elapsed,
                                "polls": poll_count,
                                "timestamp": datetime.now().isoformat()
                            }
            except Exception as e:
                logger.debug(f"Alternative method 1 failed: {e}")
            
            # Method 2: For now, return a pending status if we can't determine the verdict
            console.print(f"  [yellow]⏳ Verdict check inconclusive after {elapsed:.1f}s[/yellow]")
            
            return {
                "success": True,
                "verdict": "PENDING",
                "meaning": "Verdict check completed but result inconclusive",
                "method": "fallback",
                "elapsed_seconds": elapsed,
                "polls": poll_count,
                "timestamp": datetime.now().isoformat(),
                "note": "Check Jutge dashboard manually for final verdict"
            }
            
        except Exception as e:
            logger.error(f"Alternative verdict check failed: {e}")
            return {
                "success": False,
                "error": f"All verdict checking methods failed: {e}",
                "elapsed_seconds": elapsed,
                "polls": poll_count
            }
    
    def _extract_submission_details(self, state) -> Dict[str, Any]:
        """
        Extract additional details from the submission state
        """
        details = {}
        
        try:
            # Extract any available details from the state object
            if hasattr(state, 'execution_time'):
                details['execution_time'] = state.execution_time
            if hasattr(state, 'memory_usage'):
                details['memory_usage'] = state.memory_usage
            if hasattr(state, 'score'):
                details['score'] = state.score
            if hasattr(state, 'compiler_output'):
                details['compiler_output'] = state.compiler_output
                
        except Exception as e:
            logger.debug(f"Could not extract submission details: {e}")
        
        return details
    
    def interpret_verdict(self, verdict: str) -> Dict[str, Any]:
        """
        Provide detailed interpretation of a verdict
        
        Args:
            verdict: The verdict code (AC, WA, etc.)
            
        Returns:
            Dict with interpretation details
        """
        interpretation = {
            "verdict": verdict,
            "meaning": self.verdict_meanings.get(verdict, "Unknown"),
            "success": verdict == "AC",
            "should_retry": verdict in ["CE", "RE", "IE"],  # Errors that might be fixable
            "is_timeout": verdict in ["TLE"],
            "is_memory_issue": verdict in ["MLE", "OLE"],
            "is_logic_error": verdict in ["WA", "PE"]
        }
        
        # Add suggestions based on verdict type
        suggestions = []
        
        if verdict == "WA":
            suggestions.extend([
                "Check edge cases and boundary conditions",
                "Verify input/output format matches exactly",
                "Review algorithm logic"
            ])
        elif verdict == "TLE":
            suggestions.extend([
                "Optimize algorithm complexity",
                "Use more efficient data structures",
                "Check for infinite loops"
            ])
        elif verdict == "CE":
            suggestions.extend([
                "Check syntax errors",
                "Verify all imports and includes",
                "Ensure proper language syntax"
            ])
        elif verdict == "RE":
            suggestions.extend([
                "Check for array bounds errors",
                "Handle division by zero",
                "Verify input parsing"
            ])
        elif verdict == "MLE":
            suggestions.extend([
                "Reduce memory usage",
                "Use more efficient data structures",
                "Check for memory leaks"
            ])
        
        interpretation["suggestions"] = suggestions
        
        return interpretation