#!/usr/bin/env python3

import sys
import os
import time
from datetime import datetime

# Add current directory to path so we can import jutge_api_client
sys.path.insert(0, os.path.dirname(__file__))

from jutge_api_client import JutgeApiClient
from rich.prompt import Prompt

# Load environment variables from .env file if it exists
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

load_env()

# Create a Jutge API Client
jutge = JutgeApiClient()

# Login getting credentials from the environment or prompting
email = os.environ.get("JUTGE_EMAIL")
password = os.environ.get("JUTGE_PASSWORD")

if not email:
    email = Prompt.ask("Enter your Jutge email")
if not password:
    password = Prompt.ask("Enter your Jutge password", password=True)

print(f"Logging in as {email}...")
jutge.login(email, password)
print("Login successful!")

# Prepare submission
problem_id = "P68688_en"
solution_file = "P68688.py"
compiler_id = "Python3"

# Check if solution file exists
if not os.path.exists(solution_file):
    print(f"Error: Solution file {solution_file} not found!")
    sys.exit(1)

# Read the code from file
with open(solution_file, "r") as file:
    code = file.read()

nowDate = datetime.today().strftime("%d/%m/%Y")
nowTime = datetime.today().strftime("%H:%M:%S")
annotation = f"Hello World solution sent through the API on {nowDate} at {nowTime}"

print(f"Submitting {solution_file} for problem {problem_id} with {compiler_id} compiler...")

# Submit using the simple interface!
submission_id = jutge.student.submissions.submit(
    problem_id,
    compiler_id,
    code,
    annotation
)

print(f"Submission sent! ID: {submission_id}")

# The simple submit method returns just the submission ID as a string
# For getting the verdict, we would need to use the submission management methods
# which might require different API calls. Let's just confirm the submission was sent.

print("Submission completed successfully!")
print("Check your Jutge dashboard to see the verdict.")