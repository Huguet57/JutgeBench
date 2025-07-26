#!/usr/bin/env python3
"""
View benchmark results with enhanced debugging information
"""

import json
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax

console = Console()


def view_results(filename: str):
    """View benchmark results from a JSON file"""
    
    with open(filename, 'r') as f:
        data = json.load(f)
    
    console.print(f"\n[bold]Benchmark Results: {data['problem_set']}[/bold]")
    console.print(f"Results file: {filename}\n")
    
    # Group results by model
    results_by_model = {}
    for result in data['results']:
        model = result['model_name']
        if model not in results_by_model:
            results_by_model[model] = []
        results_by_model[model].append(result)
    
    # Display results for each model
    for model_name, results in results_by_model.items():
        console.print(f"\n[bold blue]{model_name} Results:[/bold blue]")
        
        # Create summary table
        table = Table(title=f"{model_name} Summary")
        table.add_column("Problem", style="cyan")
        table.add_column("Verdict", style="green")
        table.add_column("Submission ID")
        table.add_column("Error")
        
        for result in results:
            verdict_style = "green" if result['verdict'] in ["AC", "PE"] else "red" if result['verdict'] else "yellow"
            table.add_row(
                result['problem_id'],
                f"[{verdict_style}]{result['verdict'] or 'N/A'}[/{verdict_style}]",
                result['submission_id'] or "N/A",
                result['error'][:50] + "..." if result['error'] and len(result['error']) > 50 else result['error'] or ""
            )
        
        console.print(table)
        
        # Show failed submissions with details
        failed = [r for r in results if r['verdict'] not in ["AC", "PE"] or r['error']]
        if failed:
            console.print(f"\n[yellow]Failed/Error Details for {model_name}:[/yellow]")
            
            for result in failed:
                console.print(f"\n[bold]Problem: {result['problem_id']}[/bold]")
                console.print(f"Verdict: {result['verdict'] or 'No verdict'}")
                if result['error']:
                    console.print(f"[red]Error: {result['error']}[/red]")
                
                # Show generated code if available
                if 'solution_code' in result and result['solution_code']:
                    console.print("\n[bold]Generated Code:[/bold]")
                    syntax = Syntax(result['solution_code'], "python", theme="monokai", line_numbers=True)
                    console.print(syntax)
                
                # Show submission details if available
                if 'submission_details' in result and result['submission_details']:
                    console.print("\n[bold]Submission Details:[/bold]")
                    console.print(json.dumps(result['submission_details'], indent=2))
                
                console.print("-" * 60)
    
    # Show overall summary
    if 'summary' in data:
        summary = data['summary']
        console.print("\n[bold]Overall Summary:[/bold]")
        console.print(f"Total benchmark time: {summary.get('benchmark_time', 0):.2f} seconds")
        
        if 'model_stats' in summary:
            stats_table = Table(title="Model Performance Comparison")
            stats_table.add_column("Model")
            stats_table.add_column("Problems")
            stats_table.add_column("Solved")
            stats_table.add_column("Failed")
            stats_table.add_column("Success Rate")
            stats_table.add_column("Avg Time")
            
            for model, stats in summary['model_stats'].items():
                stats_table.add_row(
                    model,
                    str(stats['total_problems']),
                    str(stats['solved']),
                    str(stats['failed']),
                    f"{stats['success_rate']:.1f}%",
                    f"{stats['avg_time_per_problem']:.2f}s"
                )
            
            console.print(stats_table)


def main():
    if len(sys.argv) < 2:
        # Find the most recent results file
        results_dir = Path("results")
        json_files = list(results_dir.glob("benchmark_results_*.json"))
        
        if not json_files:
            console.print("[red]No benchmark results found in results/ directory[/red]")
            sys.exit(1)
        
        # Sort by modification time and get the most recent
        latest_file = max(json_files, key=lambda p: p.stat().st_mtime)
        console.print(f"[yellow]No file specified, using most recent: {latest_file}[/yellow]")
        view_results(str(latest_file))
    else:
        view_results(sys.argv[1])


if __name__ == "__main__":
    main() 