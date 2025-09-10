#!/usr/bin/env python3

import re
from pathlib import Path
import os
import sys
from google import genai
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
# client = OpenAI()
client = genai.Client()

ERROR_PATTERNS = [
    r'ERROR',
    r'FAILED',
    r'FATAL',
    r'AssertionError',
    r'Exception',
    r'TimeoutError',
    r'Warning'
]

def find_modified_files(log_dir: Path, hours: int =24):
    cutoff_time = datetime.now() - timedelta(hours=hours)
    modified_files = []
    
    for file in log_dir.rglob("*.log"):
        try:
            modified_time = datetime.fromtimestamp(file.stat().st_mtime) 
        except OSError:
            continue # skipping the unreadble files
        
        if modified_time > cutoff_time and file.is_file():
            modified_files.append(file)
    
    return modified_files
        


def filter_error_blocks(file_path : Path, context=0):
    with file_path.open("r", errors="ignore") as f:
        lines = f.readlines()
    
    print(f"\n=========Scanning {file_path}============\n")
    
    result = ""
    
    if context == 0:
        for line in lines:
            if any(re.search(ptr, line, re.IGNORECASE) for ptr in ERROR_PATTERNS):
                result += (line.rstrip() + '\n')
        return result

    
    for (i, line) in enumerate(lines):
        if any(re.search(ptr, line, re.IGNORECASE) for ptr in ERROR_PATTERNS):
            if i > 0:
                print(lines[i-1].strip())
                result += lines[i-1].strip() + ('\n')
            print(">>", line.strip()) 
            result += line.strip() + ('\n')
            if i < len(lines) - 1:
                print(lines[i+1].strip())
                result += lines[i+1].strip() + ('\n')
    return result


def summarise_failed_blocks_OpenAI(failed_blocks):
    response = client.responses.create(
        model="gpt-4.1-mini",
        input="Summarise the following log file in a clean, organised way. Provide the output in text format:\n\n" + failed_blocks
    )
    report = (response.output_text)
    log_summary_writer(report, file="log_report_OpenAI.txt")
    
def summarise_failed_blocks_Gemini(failed_blocks):
    response = client.models.generate_content(
        model="gemini-2.5-flash", contents= "Summarise the following log file in a clean, organised way. Provide the output in text format:\n\n" + failed_blocks
    )
    report = (response.text)
    log_summary_writer(report, file="log_report_Gemini.txt") 

def log_summary_writer(report, file):
    with open(file, "w") as f:
        f.write(report)
    print(f"\n=========Report written to {file}=========")
        
def write_log_summary(failed_blocks):
    with open("log_summary.txt", "w") as f:
            f.write(failed_blocks)

def main():
    DEFAULT_DIR = Path(Path("/Users/thonmay/Documents/Scripting"))
    LOG_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DIR
    
    print("\nLog Files changed in the last 24 hours are: ")
    modified_files = find_modified_files(LOG_DIR, hours=24)
    for file in modified_files:
        print(str(file))
    
    print("=====================================================================")

    for file in modified_files:
        failed_blocks = filter_error_blocks(file)
        write_log_summary(failed_blocks)
        
        print(failed_blocks)
        summarise_failed_blocks_Gemini(failed_blocks)
    

if __name__ == '__main__':
    main()