#!/usr/bin/env python3
"""Syntax check script for Python backend
This script checks syntax of all Python files before uvicorn starts.
If syntax errors are found, they are sent to the runtime error endpoint.
Run during startup phase to catch syntax errors before import.
"""
import os
import sys
import ast
import traceback
import httpx
import threading

def check_syntax(file_path):
    """Check syntax of a Python file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        # Use compile() instead of ast.parse() to catch all syntax errors including indentation
        compile(source, file_path, 'exec', flags=0, dont_inherit=True)
        return None
    except SyntaxError as e:
        # Extract just the filename from the full path
        file_name = os.path.basename(file_path)
        return {
            'file': file_name,
            'line': e.lineno,
            'message': str(e.msg) if hasattr(e, 'msg') else str(e),
            'text': e.text,
            'offset': e.offset
        }
    except Exception as e:
        file_name = os.path.basename(file_path)
        return {
            'file': file_name,
            'line': None,
            'message': str(e),
            'text': None,
            'offset': None
        }

def send_syntax_error_to_endpoint(errors):
    """Send syntax errors to runtime error endpoint"""
    runtime_error_endpoint_url = os.getenv('RUNTIME_ERROR_ENDPOINT_URL')
    board_id = os.getenv('BOARD_ID')
    
    if not runtime_error_endpoint_url:
        return
    
    # Format error message
    error_messages = []
    for err in errors:
        msg = f"File: {err['file']}, Line: {err['line']}, Error: {err['message']}"
        if err['text']:
            msg += f", Code: {err['text'].strip()}"
        error_messages.append(msg)
    
    error_message = '; '.join(error_messages)
    
    # Build stack trace
    stack_trace = '\n'.join([
        f"  File "{err['file']}", line {err['line'] or '?'}"
        for err in errors
    ])
    
    payload = {
        'boardId': board_id,
        'timestamp': None,  # Will be set by backend
        'file': errors[0]['file'] if errors else None,
        'line': errors[0]['line'] if errors else None,
        'stackTrace': stack_trace,
        'message': error_message,
        'exceptionType': 'SyntaxError',
        'requestPath': 'SYNTAX_CHECK',
        'requestMethod': 'SYNTAX_CHECK',
        'userAgent': 'SYNTAX_CHECKER'
    }
    
    # Send in background (fire and forget)
    def send_error():
        try:
            with httpx.Client(timeout=5.0) as client:
                client.post(runtime_error_endpoint_url, json=payload)
        except:
            pass
    
    thread = threading.Thread(target=send_error, daemon=True)
    thread.start()
    thread.join(timeout=2.0)  # Wait max 2 seconds for send

if __name__ == '__main__':
    # Get backend directory
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Find all Python files
    python_files = []
    for root, dirs, files in os.walk(backend_dir):
        # Skip virtual environment
        if '.venv' in root or 'venv' in root or '__pycache__' in root:
            continue
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    # Check syntax of all files
    errors = []
    print(f'Checking syntax of {len(python_files)} Python files...', file=sys.stderr)
    for file_path in python_files:
        error = check_syntax(file_path)
        if error:
            errors.append(error)
            print(f"✗ Syntax error in {file_path}: {error['message']} at line {error['line']}", file=sys.stderr)
        else:
            print(f'✓ {os.path.basename(file_path)}', file=sys.stderr)
    
    if errors:
        print(f'✗ Found {len(errors)} syntax error(s). Sending to runtime error endpoint...', file=sys.stderr)
        # Send errors to endpoint
        send_syntax_error_to_endpoint(errors)
        print('✗ Syntax check FAILED. Exiting with error code 1.', file=sys.stderr)
        sys.exit(1)
    else:
        print('✓ Syntax check passed. All files are valid.', file=sys.stderr)
        sys.exit(0)
