#!/usr/bin/env python3
"""
Command Line Interface for Jutge Problem Solver
"""

import argparse
import os
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.prompt import Prompt, Confirm

from jutge_solver import JutgeProblemSolver, Config

console = Console()


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Jutge Problem Solver - Automatically solve programming problems using OpenAI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py solve P68688_en                    # Solve Hello World problem
  python cli.py solve P68688_en --compiler G++17   # Use C++ compiler
  python cli.py solve --batch problems.txt         # Solve multiple problems
  python cli.py config                             # Setup configuration
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
    
    args = parser.parse_args()
    
    if args.command == 'solve':
        handle_solve_command(args)
    elif args.command == 'config':
        handle_config_command(args)
    elif args.command == 'test':
        handle_test_command(args)
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
    
    # Get OpenAI API key
    console.print("\\n[bold]OpenAI Configuration[/bold]")
    console.print("Get your API key from: https://platform.openai.com/api-keys")
    openai_key = Prompt.ask("Enter your OpenAI API key", password=True)
    
    # Get Jutge credentials
    console.print("\\n[bold]Jutge Credentials[/bold]")
    console.print("Register at: https://jutge.org/")
    jutge_email = Prompt.ask("Enter your Jutge email")
    jutge_password = Prompt.ask("Enter your Jutge password", password=True)
    
    # Save to .env file
    env_content = f"""# Jutge Problem Solver Environment Variables
# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# OpenAI API Configuration
OPENAI_API_KEY={openai_key}

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

# OpenAI API Configuration
# Get your API key from: https://platform.openai.com/api-keys
OPENAI_API_KEY=your-openai-api-key-here

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