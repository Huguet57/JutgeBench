#!/usr/bin/env python3
"""
Command Line Interface for Jutge Problem Solver
"""

import argparse
import os
from datetime import datetime
from typing import Optional
import json
import csv

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from jutge_solver import JutgeProblemSolver, Config
from jutge_solver.benchmark import AIModelBenchmark
from jutge_solver.benchmark_config import BenchmarkConfig

console = Console()


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Jutge Problem Solver - Automatically solve programming problems using OpenAI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run cli.py solve P68688_en                    # Solve Hello World problem
  uv run cli.py solve P68688_en --compiler G++17   # Use C++ compiler
  uv run cli.py solve --batch problems.txt         # Solve multiple problems
  uv run cli.py config                             # Setup configuration
  uv run cli.py benchmark hello_world              # Benchmark AI models on hello_world problem set
  uv run cli.py benchmark basic_algorithms --models GPT-4o-mini GPT-4o  # Benchmark specific models
  uv run cli.py benchmark --report html            # Generate HTML report
  uv run cli.py benchmark --parallel               # Run models in parallel for faster execution
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Solve command
    solve_parser = subparsers.add_parser('solve', help='Solve a programming problem')
    solve_parser.add_argument('problem_id', nargs='?', help='Problem ID (e.g., P68688_en)')
    solve_parser.add_argument('--compiler', '-c', help='Compiler to use (Python3, G++17, JDK)')
    solve_parser.add_argument('--batch', '-b', help='File containing list of problem IDs')
    solve_parser.add_argument('--config', help='Config file path')
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Setup configuration')
    config_parser.add_argument('--interactive', '-i', action='store_true', help='Interactive setup')
    
    # Test command
    subparsers.add_parser('test', help='Test the system setup')
    
    # Benchmark command
    benchmark_parser = subparsers.add_parser('benchmark', help='Benchmark AI models on problem sets')
    benchmark_parser.add_argument('problem_set', nargs='?', help='Problem set to benchmark (hello_world, basic_algorithms, medium_problems)')
    benchmark_parser.add_argument('--models', '-m', nargs='+', help='Models to benchmark (GPT-4o-mini, GPT-4o, Claude-3.5-Sonnet)')
    benchmark_parser.add_argument('--config', help='Benchmark config file path')
    benchmark_parser.add_argument('--report', '-r', choices=['json', 'csv', 'html'], default='json', help='Report format')
    benchmark_parser.add_argument('--parallel', '-p', action='store_true', help='Run models in parallel')
    
    args = parser.parse_args()
    
    if args.command == 'solve':
        handle_solve_command(args)
    elif args.command == 'config':
        handle_config_command(args)
    elif args.command == 'test':
        handle_test_command(args)
    elif args.command == 'benchmark':
        handle_benchmark_command(args)
    else:
        parser.print_help()


def handle_solve_command(args):
    """Handle the solve command"""
    
    # Load configuration
    config = load_config(args.config)
    if not config.validate():
        console.print("[red]Configuration validation failed. Run 'python cli.py config' to setup.[/red]")
        return
    
    # Initialize solver
    solver = JutgeProblemSolver(config)
    
    if args.batch:
        # Batch processing
        solve_batch(solver, args.batch, args.compiler)
    elif args.problem_id:
        # Single problem
        solve_single(solver, args.problem_id, args.compiler)
    else:
        # Interactive mode
        solve_interactive(solver, args.compiler)


def handle_config_command(args):
    """Handle the config command"""
    if args.interactive:
        setup_interactive_config()
    else:
        setup_default_config()


def handle_test_command(args):
    """Handle the test command"""
    console.print("[blue]Testing system setup...[/blue]")
    
    config = load_config()
    if not config.validate():
        console.print("[red]✗ Configuration is incomplete[/red]")
        return
    
    try:
        solver = JutgeProblemSolver(config)
        if solver.authenticate():
            console.print("[green]✓ Jutge authentication successful[/green]")
        else:
            console.print("[red]✗ Jutge authentication failed[/red]")
            return
        
        # Test OpenAI API
        test_response = solver.openai_client.chat.completions.create(
            model=config.openai.model,
            messages=[{"role": "user", "content": "Hello, this is a test. Respond with 'API working'."}],
            max_tokens=10
        )
        
        if "API working" in test_response.choices[0].message.content:
            console.print("[green]✓ OpenAI API connection successful[/green]")
        else:
            console.print("[yellow]⚠ OpenAI API responded but with unexpected content[/yellow]")
        
        console.print("[green]✓ All systems operational[/green]")
        
    except Exception as e:
        console.print(f"[red]✗ System test failed: {e}[/red]")


def handle_benchmark_command(args):
    """Handle the benchmark command"""
    console.print("[blue]🔬 Starting AI Model Benchmark[/blue]")
    
    # Load configuration
    config = load_config(args.config)
    if not config.validate():
        console.print("[red]Configuration validation failed. Run 'python cli.py config' to setup.[/red]")
        return
    
    # Load benchmark configuration
    benchmark_config_path = args.config or "benchmark_config.yaml"
    benchmark_config = BenchmarkConfig.load_from_file(benchmark_config_path)
    
    # Override models if specified in command line
    if args.models:
        # Filter to only requested models
        benchmark_config.models = [m for m in benchmark_config.models if m.name in args.models]
        if not benchmark_config.models:
            console.print(f"[red]No valid models found from: {args.models}[/red]")
            return
    
    # Validate benchmark config
    if not benchmark_config.validate():
        console.print("[red]Benchmark configuration validation failed[/red]")
        return
    
    # Select problem set
    if args.problem_set:
        if args.problem_set not in benchmark_config.problem_sets:
            console.print(f"[red]Unknown problem set: {args.problem_set}[/red]")
            console.print(f"Available sets: {list(benchmark_config.problem_sets.keys())}")
            return
    else:
        # Interactive selection
        console.print("\nAvailable problem sets:")
        for name, problems in benchmark_config.problem_sets.items():
            console.print(f"  - {name}: {len(problems)} problems")
        
        args.problem_set = Prompt.ask(
            "Select problem set",
            choices=list(benchmark_config.problem_sets.keys()),
            default="basic_algorithms"
        )
    
    # Initialize benchmark with parallel support
    max_workers = 4 if args.parallel else 1
    use_processes = args.parallel
    benchmark = AIModelBenchmark(
        benchmark_config, 
        config,
        max_workers=max_workers,
        use_processes=use_processes
    )
    
    try:
        # Run benchmark
        console.print(f"\n[blue]Running benchmark on '{args.problem_set}' problem set[/blue]")
        results = benchmark.run_benchmark(args.problem_set)
        
        # Display summary
        display_benchmark_summary(results)
        
        # Generate report
        if args.report == 'csv':
            generate_csv_report(results)
        elif args.report == 'html':
            generate_html_report(results)
        
    except Exception as e:
        console.print(f"[red]✗ Benchmark failed: {e}[/red]")
        import traceback
        traceback.print_exc()


def display_benchmark_summary(results: dict):
    """Display benchmark results summary in a nice table"""
    console.print("\n[bold green]Benchmark Results Summary[/bold green]")
    
    # Create summary table
    table = Table(title="Model Performance")
    table.add_column("Model", style="cyan")
    table.add_column("Problems", justify="right")
    table.add_column("Solved", justify="right", style="green")
    table.add_column("Failed", justify="right", style="red")
    table.add_column("Success Rate", justify="right")
    table.add_column("Avg Time", justify="right")
    table.add_column("Total Tokens", justify="right")
    
    for model_name, stats in results['model_stats'].items():
        success_rate = f"{stats['success_rate']:.1f}%"
        avg_time = f"{stats['avg_time_per_problem']:.2f}s"
        
        table.add_row(
            model_name,
            str(stats['total_problems']),
            str(stats['solved']),
            str(stats['failed'] + stats['errors']),
            success_rate,
            avg_time,
            str(stats['total_tokens'])
        )
    
    console.print(table)
    
    console.print(f"\n[dim]Total benchmark time: {results['benchmark_time']:.2f} seconds[/dim]")


def generate_csv_report(results: dict):
    """Generate CSV report from benchmark results"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"results/benchmark_report_{timestamp}.csv"
    
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Model', 'Problems', 'Solved', 'Failed', 'Success Rate', 'Avg Time', 'Total Tokens'])
        
        for model_name, stats in results['model_stats'].items():
            writer.writerow([
                model_name,
                stats['total_problems'],
                stats['solved'],
                stats['failed'] + stats['errors'],
                f"{stats['success_rate']:.1f}",
                f"{stats['avg_time_per_problem']:.2f}",
                stats['total_tokens']
            ])
    
    console.print(f"[green]✓ CSV report saved to {filename}[/green]")


def generate_html_report(results: dict):
    """Generate enhanced HTML report from benchmark results with detailed submission information"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"results/benchmark_report_{timestamp}.html"
    
    # Group individual results by model for detailed display
    results_by_model = {}
    individual_results = results.get('results', [])
    
    for result in individual_results:
        model = result.get('model_name', 'Unknown Model')
        if model not in results_by_model:
            results_by_model[model] = []
        results_by_model[model].append(result)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Jutge AI Benchmark Report</title>
        <style>
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                margin: 40px; 
                background: #f8f9fa; 
                line-height: 1.6;
            }}
            .container {{ 
                max-width: 1200px; 
                margin: 0 auto; 
                background: white; 
                padding: 40px; 
                border-radius: 8px; 
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            h1 {{ color: #2c3e50; margin-bottom: 10px; }}
            h2 {{ color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            h3 {{ color: #2c3e50; margin-top: 30px; }}
            .meta {{ color: #7f8c8d; margin-bottom: 30px; }}
            
            /* Summary table */
            .summary-table {{ 
                border-collapse: collapse; 
                width: 100%; 
                margin-bottom: 40px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }}
            .summary-table th {{ 
                background: linear-gradient(135deg, #3498db, #2980b9); 
                color: white; 
                padding: 15px 12px;
                text-align: left;
                font-weight: 600;
            }}
            .summary-table td {{ 
                padding: 12px; 
                border-bottom: 1px solid #ecf0f1;
            }}
            .summary-table tr:hover {{ background-color: #f8f9fa; }}
            
            /* Detailed results */
            .model-section {{ 
                margin: 40px 0; 
                border: 1px solid #ddd; 
                border-radius: 8px; 
                overflow: hidden;
            }}
            .model-header {{ 
                background: linear-gradient(135deg, #2c3e50, #34495e); 
                color: white; 
                padding: 15px 20px; 
                cursor: pointer;
                user-select: none;
            }}
            .model-header:hover {{ background: linear-gradient(135deg, #34495e, #2c3e50); }}
            .model-content {{ 
                display: none; 
                padding: 20px; 
                background: #fafbfc;
            }}
            .model-content.expanded {{ display: block; }}
            
            /* Problem results table */
            .results-table {{ 
                width: 100%; 
                border-collapse: collapse; 
                margin-bottom: 20px;
                background: white;
            }}
            .results-table th {{ 
                background: #34495e; 
                color: white; 
                padding: 12px 8px; 
                text-align: left;
                font-size: 14px;
            }}
            .results-table td {{ 
                padding: 10px 8px; 
                border-bottom: 1px solid #eee; 
                vertical-align: top;
            }}
            .results-table tr:hover {{ background-color: #f1f2f6; }}
            
            /* Code sections */
            .code-section {{ 
                margin: 15px 0; 
                border: 1px solid #ddd; 
                border-radius: 6px; 
                overflow: hidden;
            }}
            .code-header {{ 
                background: #f4f4f4; 
                padding: 8px 12px; 
                font-weight: 600; 
                font-size: 14px;
                color: #2c3e50;
                cursor: pointer;
                user-select: none;
                border-bottom: 1px solid #ddd;
            }}
            .code-header:hover {{ background: #e8e8e8; }}
            .code-content {{ 
                display: none; 
                background: #2f3640; 
                color: #f5f6fa; 
                padding: 15px; 
                font-family: 'Monaco', 'Consolas', monospace; 
                font-size: 13px; 
                line-height: 1.4;
                white-space: pre-wrap; 
                overflow-x: auto;
            }}
            .code-content.expanded {{ display: block; }}
            
            /* Status styling */
            .verdict-AC {{ color: #27ae60; font-weight: bold; }}
            .verdict-WA {{ color: #e74c3c; font-weight: bold; }}
            .verdict-TLE {{ color: #f39c12; font-weight: bold; }}
            .verdict-CE {{ color: #9b59b6; font-weight: bold; }}
            .verdict-RE {{ color: #e67e22; font-weight: bold; }}
            .verdict-NULL {{ color: #95a5a6; font-weight: bold; }}
            
            .success {{ color: #27ae60; font-weight: bold; }}
            .failed {{ color: #e74c3c; font-weight: bold; }}
            .warning {{ color: #f39c12; font-weight: bold; }}
            
            /* Metrics */
            .metrics {{ 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); 
                gap: 10px; 
                margin: 15px 0;
                font-size: 14px;
            }}
            .metric {{ 
                background: white; 
                padding: 8px 12px; 
                border-radius: 4px; 
                border-left: 4px solid #3498db;
            }}
            .metric-label {{ font-weight: 600; color: #2c3e50; }}
            .metric-value {{ color: #7f8c8d; }}
            
            /* Utility classes */
            .toggle-all {{ 
                background: #3498db; 
                color: white; 
                border: none; 
                padding: 10px 20px; 
                border-radius: 5px; 
                cursor: pointer; 
                margin-bottom: 20px;
                font-size: 14px;
            }}
            .toggle-all:hover {{ background: #2980b9; }}
            
            .error-message {{ 
                background: #fee; 
                color: #c62828; 
                padding: 10px; 
                border-radius: 4px; 
                border-left: 4px solid #e53e3e; 
                margin: 10px 0;
                font-size: 14px;
            }}
        </style>
        <script>
            function toggleModel(modelId) {{
                console.log('Toggling model:', modelId);
                const content = document.getElementById(modelId);
                if (!content) {{
                    console.error('Content element not found:', modelId);
                    return;
                }}
                const header = content.previousElementSibling;
                content.classList.toggle('expanded');
                const isExpanded = content.classList.contains('expanded');
                console.log('Model expanded:', isExpanded);
                header.innerHTML = isExpanded ? 
                    header.innerHTML.replace('▶', '▼') : 
                    header.innerHTML.replace('▼', '▶');
            }}
            
            function toggleCode(codeId) {{
                console.log('Toggling code:', codeId);
                const content = document.getElementById(codeId);
                if (!content) {{
                    console.error('Code element not found:', codeId);
                    return;
                }}
                const header = content.previousElementSibling;
                content.classList.toggle('expanded');
                const isExpanded = content.classList.contains('expanded');
                header.innerHTML = isExpanded ? 
                    header.innerHTML.replace('▶', '▼') : 
                    header.innerHTML.replace('▼', '▶');
            }}
            
            function toggleAll() {{
                console.log('Toggle all clicked');
                const contents = document.querySelectorAll('.model-content');
                console.log('Found model contents:', contents.length);
                
                if (contents.length === 0) {{
                    console.warn('No model content sections found!');
                    return;
                }}
                
                const allExpanded = Array.from(contents).every(c => c.classList.contains('expanded'));
                console.log('All expanded:', allExpanded);
                
                contents.forEach((content, index) => {{
                    const header = content.previousElementSibling;
                    console.log(`Processing content ${{index}}, expanded: ${{content.classList.contains('expanded')}}`);
                    if (allExpanded) {{
                        content.classList.remove('expanded');
                        header.innerHTML = header.innerHTML.replace('▼', '▶');
                    }} else {{
                        content.classList.add('expanded');
                        header.innerHTML = header.innerHTML.replace('▶', '▼');
                    }}
                }});
                
                const toggleButton = document.querySelector('.toggle-all');
                if (toggleButton) {{
                    toggleButton.textContent = allExpanded ? 'Expand All Models' : 'Collapse All Models';
                }}
            }}
            
            // Debug function to check DOM state
            window.debugReport = function() {{
                console.log('=== Debug Report ===');
                console.log('Model sections:', document.querySelectorAll('.model-section').length);
                console.log('Model contents:', document.querySelectorAll('.model-content').length);
                console.log('Code sections:', document.querySelectorAll('.code-section').length);
                console.log('Toggle button:', document.querySelector('.toggle-all'));
                document.querySelectorAll('.model-content').forEach((el, i) => {{
                    console.log(`Model content ${{i}}:`, el.id, el.classList.contains('expanded'));
                }});
            }}
        </script>
    </head>
    <body>
        <div class="container">
            <h1>Jutge AI Model Benchmark Report</h1>
            <div class="meta">
                <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>Problem Set:</strong> {results.get('problem_set', 'Unknown')}</p>
                <p><strong>Total Benchmark Time:</strong> {results.get('benchmark_time', 0):.2f} seconds</p>
            </div>
            
            <h2>Summary</h2>
            <table class="summary-table">
                <tr>
                    <th>Model</th>
                    <th>Problems</th>
                    <th>Solved</th>
                    <th>Failed</th>
                    <th>Success Rate</th>
                    <th>Avg Time</th>
                    <th>Total Tokens</th>
                </tr>
    """
    
    # Add summary rows
    for model_name, stats in results.get('model_stats', {}).items():
        success_class = 'success' if stats['success_rate'] >= 80 else 'failed' if stats['success_rate'] < 50 else 'warning'
        html_content += f"""
                <tr>
                    <td><strong>{model_name}</strong></td>
                    <td>{stats['total_problems']}</td>
                    <td class="success">{stats['solved']}</td>
                    <td class="failed">{stats.get('failed', 0) + stats.get('errors', 0)}</td>
                    <td class="{success_class}">{stats['success_rate']:.1f}%</td>
                    <td>{stats.get('avg_time_per_problem', 0):.2f}s</td>
                    <td>{stats.get('total_tokens', 0):,}</td>
                </tr>
        """
    
    html_content += """
            </table>
            
            <h2>Detailed Results</h2>
    """
    
    # Only show toggle button and model sections if we have results
    if results_by_model:
        html_content += """
            <button class="toggle-all" onclick="toggleAll()">Expand All Models</button>
        """
        
        # Add detailed results for each model
        for model_name, model_results in results_by_model.items():
            model_id = model_name.replace(' ', '').replace('-', '').replace('.', '')
            html_content += f"""
            <div class="model-section">
                <div class="model-header" onclick="toggleModel('{model_id}-content')">
                    ▶ {model_name} ({len(model_results)} problems)
                </div>
                <div id="{model_id}-content" class="model-content">
                    <table class="results-table">
                        <tr>
                            <th>Problem</th>
                            <th>Verdict</th>
                            <th>Submission ID</th>
                            <th>Language</th>
                            <th>Time</th>
                            <th>Tokens</th>
                            <th>Attempts</th>
                        </tr>
            """
            
            for result in model_results:
                verdict = result.get('verdict', 'NULL')
                verdict_class = f'verdict-{verdict}' if verdict else 'verdict-NULL'
                error_msg = result.get('error', '')
                
                html_content += f"""
                        <tr>
                            <td><strong>{result.get('problem_id', 'Unknown')}</strong></td>
                            <td class="{verdict_class}">{verdict or 'NULL'}</td>
                            <td>{result.get('submission_id', 'N/A')}</td>
                            <td>{result.get('language', 'Unknown')}</td>
                            <td>{result.get('total_time', 0):.2f}s</td>
                            <td>{result.get('tokens_used', 0):,}</td>
                            <td>{result.get('attempts', 1)}</td>
                        </tr>
                """
                
                # Add detailed metrics and code for this problem
                html_content += f"""
                        <tr>
                            <td colspan="7">
                                <div class="metrics">
                                    <div class="metric">
                                        <div class="metric-label">Generation Time</div>
                                        <div class="metric-value">{result.get('generation_time', 0):.2f}s</div>
                                    </div>
                                    <div class="metric">
                                        <div class="metric-label">Submission Time</div>
                                        <div class="metric-value">{result.get('submission_time', 0):.2f}s</div>
                                    </div>
                                    <div class="metric">
                                        <div class="metric-label">Success</div>
                                        <div class="metric-value">{'✓ Yes' if result.get('success') else '✗ No'}</div>
                                    </div>
                                    <div class="metric">
                                        <div class="metric-label">Timestamp</div>
                                        <div class="metric-value">{result.get('timestamp', 'Unknown')}</div>
                                    </div>
                                </div>
                """
                
                # Add error message if present
                if error_msg:
                    html_content += f"""
                                <div class="error-message">
                                    <strong>Error:</strong> {error_msg}
                                </div>
                    """
                
                # Add code section
                solution_code = result.get('solution_code', '')
                if solution_code:
                    code_id = f"{model_id}{result.get('problem_id', 'unknown')}code".replace('_', '').replace('-', '')
                    html_content += f"""
                                <div class="code-section">
                                    <div class="code-header" onclick="toggleCode('{code_id}')">
                                        ▶ Generated Solution Code
                                    </div>
                                    <div id="{code_id}" class="code-content">{solution_code}</div>
                                </div>
                    """
                
                html_content += "</td></tr>"
            
            html_content += """
                    </table>
                </div>
            </div>
            """
    else:
        html_content += """
            <p><em>No detailed results available. This may happen if the benchmark data doesn't contain individual submission results.</em></p>
        """
    
    html_content += """
        </div>
    </body>
    </html>
    """
    
    with open(filename, 'w') as f:
        f.write(html_content)
    
    console.print(f"[green]✓ Enhanced HTML report saved to {filename}[/green]")


def solve_single(solver: JutgeProblemSolver, problem_id: str, compiler_id: Optional[str]):
    """Solve a single problem"""
    console.print(f"[bold]Solving problem: {problem_id}[/bold]")
    
    result = solver.solve_problem(problem_id, compiler_id)
    
    if result["success"]:
        console.print(f"[green]✓ Problem solved successfully![/green]")
        if "final_verdict" in result:
            console.print(f"Verdict: {result['final_verdict']}")
    else:
        console.print(f"[red]✗ Failed to solve problem: {result.get('error', 'Unknown error')}[/red]")


def solve_batch(solver: JutgeProblemSolver, batch_file: str, compiler_id: Optional[str]):
    """Solve multiple problems from a file"""
    try:
        with open(batch_file, 'r') as f:
            problem_ids = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        console.print(f"[blue]Processing {len(problem_ids)} problems from {batch_file}[/blue]")
        
        results = []
        for i, problem_id in enumerate(problem_ids, 1):
            console.print(f"\\n[bold]Problem {i}/{len(problem_ids)}: {problem_id}[/bold]")
            
            result = solver.solve_problem(problem_id, compiler_id)
            results.append(result)
            
            # Brief pause between problems
            if i < len(problem_ids):
                import time
                time.sleep(2)
        
        # Summary
        console.print("\\n" + "="*60)
        console.print("[bold]BATCH SUMMARY[/bold]")
        console.print("="*60)
        
        successful = sum(1 for r in results if r["success"])
        console.print(f"Successful: {successful}/{len(results)}")
        
        for result in results:
            status = "✓" if result["success"] else "✗"
            verdict = result.get("final_verdict", "FAILED")
            console.print(f"{status} {result['problem_id']}: {verdict}")
        
    except FileNotFoundError:
        console.print(f"[red]✗ Batch file {batch_file} not found[/red]")
    except Exception as e:
        console.print(f"[red]✗ Batch processing failed: {e}[/red]")


def solve_interactive(solver: JutgeProblemSolver, compiler_id: Optional[str]):
    """Interactive problem solving"""
    console.print("[blue]Interactive mode - Enter problem IDs to solve (Ctrl+C to exit)[/blue]")
    
    try:
        while True:
            problem_id = Prompt.ask("\\nEnter problem ID")
            if not problem_id:
                continue
            
            result = solver.solve_problem(problem_id, compiler_id)
            
            if not result["success"]:
                if Confirm.ask("\\nWould you like to try another problem?"):
                    continue
                else:
                    break
            else:
                if not Confirm.ask("\\nWould you like to solve another problem?"):
                    break
                    
    except KeyboardInterrupt:
        console.print("\\n[yellow]Goodbye![/yellow]")


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from various sources"""
    if config_path:
        config = Config.load_from_file(config_path)
    else:
        config = Config.load_from_env()
    
    # Load from .env file
    config.load_env_file()
    
    # Re-apply environment variables after loading .env
    config = Config.load_from_env()
    
    return config


def setup_interactive_config():
    """Setup configuration interactively"""
    console.print("[blue]Setting up Jutge Problem Solver configuration...[/blue]")
    console.print("[dim]This will create/update your .env file with credentials[/dim]")
    
    # Check if .env exists
    env_exists = os.path.exists('.env')
    if env_exists:
        console.print("[yellow]Found existing .env file[/yellow]")
        if not Confirm.ask("Do you want to update it?"):
            return
    
    # Get OpenRouter API key
    console.print("\\n[bold]OpenRouter Configuration[/bold]")
    console.print("Get your API key from: https://openrouter.ai/")
    openai_key = Prompt.ask("Enter your OpenRouter API key", password=True)
    
    # Get Jutge credentials
    console.print("\\n[bold]Jutge Credentials[/bold]")
    console.print("Register at: https://jutge.org/")
    jutge_email = Prompt.ask("Enter your Jutge email")
    jutge_password = Prompt.ask("Enter your Jutge password", password=True)
    
    # Save to .env file
    env_content = f"""# Jutge Problem Solver Environment Variables
# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# OpenRouter API Configuration
OPENROUTER_API_KEY={openai_key}

# Jutge Platform Credentials
JUTGE_EMAIL={jutge_email}
JUTGE_PASSWORD={jutge_password}
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    console.print("[green]✓ Configuration saved to .env[/green]")
    console.print("[dim]Test your setup with: python cli.py test[/dim]")


def setup_default_config():
    """Setup default configuration files"""
    # Create .env.example if it doesn't exist
    if not os.path.exists('.env.example'):
        env_example_content = """# Jutge Problem Solver Environment Variables
# Copy this file to .env and fill in your actual credentials

# OpenRouter API Configuration
# Get your API key from: https://openrouter.ai/
OPENROUTER_API_KEY=your-openrouter-key-here

# Optional: Override default model
# OPENAI_MODEL=gpt-4o-mini

# Jutge Platform Credentials
# Register at: https://jutge.org/
JUTGE_EMAIL=your-email@example.com
JUTGE_PASSWORD=your-password-here
"""
        with open('.env.example', 'w') as f:
            f.write(env_example_content)
        console.print("[green]✓ Created .env.example[/green]")
    
    # Create config.yaml with non-sensitive defaults
    config = Config()
    config.save_to_file('config.yaml')
    console.print("[green]✓ Created config.yaml with default settings[/green]")
    
    console.print("\\n[blue]Next steps:[/blue]")
    console.print("1. Copy .env.example to .env")
    console.print("2. Edit .env with your credentials")
    console.print("3. Run: python cli.py test")
    console.print("\\nOr use interactive setup: python cli.py config --interactive")


if __name__ == '__main__':
    main()