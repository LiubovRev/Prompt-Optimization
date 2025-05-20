import openai
import os
import pandas as pd
import time
import json
from tqdm import tqdm
from datetime import datetime

def simulate_results(reports, prompt_styles):
    """
    Create simulated responses when API quota is exceeded or for testing
    
    Args:
        reports (dict): Dictionary of reports to process
        prompt_styles (dict): Dictionary of prompt styles to test
        
    Returns:
        pandas.DataFrame: Simulated results dataframe
    """
    results = []
    
    # Create a progress bar
    total_requests = len(reports) * len(prompt_styles)
    with tqdm(total=total_requests, desc="Simulating") as pbar:
        for report_title, report_text in reports.items():
            report_type = "personal" if "Budget" in report_title else "company"
            
            for style_name, prompt_text in prompt_styles.items():
                # Generate simulated response based on prompt style and report type
                if style_name == "basic":
                    if report_type == "personal":
                        output = f"[SIMULATED] {report_title} shows a monthly budget with total income of 4850 and remaining balance of 1710."
                    else:
                        output = f"[SIMULATED] {report_title} shows quarterly performance with revenue of 210000 and net profit of 40000."
                elif style_name == "structured":
                    if report_type == "personal":
                        output = f"[SIMULATED] {report_title} Analysis:\n• Total Income: 4850\n• Remaining Balance: 1710\n• Period: April 2024"
                    else:
                        output = f"[SIMULATED] {report_title} Analysis:\n• Total Revenue: 210000\n• Net Profit: 40000\n• Growth: 8% from previous quarter"
                elif style_name == "comparative":
                    if report_type == "company":
                        output = f"[SIMULATED] Aurora Technologies showed 8% revenue growth in Q1 2024 compared to Q4 2023. This performance indicates..."
                    else:
                        output = f"[SIMULATED] The current monthly budget shows standard income and expenses with no major one-time expenses reported."
                else:
                    if report_type == "personal":
                        output = f"[SIMULATED] Detailed analysis of {report_title} showing income and expense patterns for April 2024."
                    else:
                        output = f"[SIMULATED] Detailed analysis of Aurora Technologies' Q1 2024 performance, highlighting 8% revenue growth and 19% profit margin."
                
                # Store results
                results.append({
                    "Report": report_title,
                    "Prompt Style": style_name,
                    "Summary": output
                })
                
                # Update progress bar
                pbar.update(1)
                time.sleep(0.1)  # Small delay for visual effect
    
    return pd.DataFrame(results)


def load_reports_from_json(json_file_path):
    """
    Load financial reports from JSON file
    
    Args:
        json_file_path (str): Path to the JSON file containing reports
        
    Returns:
        dict: Dictionary of reports with titles as keys and formatted report text as values
    """
    try:
        with open(json_file_path, 'r') as file:
            data = json.load(file)
        
        reports = {}
        if 'reports' in data and isinstance(data['reports'], list):
            for index, report in enumerate(data['reports']):
                # Format report as structured text
                report_text = format_report_as_text(report, index)
                title = report.get('title', f"Report {index}")
                reports[title] = report_text
        else:
            print("Warning: JSON file does not contain a 'reports' list.")
        
        return reports
    except FileNotFoundError:
        print(f"Error: File '{json_file_path}' not found.")
        return {}
    except json.JSONDecodeError:
        print(f"Error: '{json_file_path}' is not a valid JSON file.")
        return {}
    except Exception as e:
        print(f"Error loading reports: {e}")
        return {}

def format_report_as_text(report, index):
    """
    Format a report dictionary as readable text
    
    Args:
        report (dict): Report data from JSON
        index (int): Report index
        
    Returns:
        str: Formatted report text
    """
    lines = []
    
    # Add title and period if available
    if 'title' in report:
        lines.append(f"Report: {report['title']}")
    if 'period' in report:
        lines.append(f"Period: {report['period']}")
    if 'company_name' in report:
        lines.append(f"Company: {report['company_name']}")
    
    # Add financial data
    for key, value in report.items():
        # Skip already processed fields and nested objects
        if key in ['title', 'period', 'company_name'] or isinstance(value, (dict, list)):
            continue
        
        # Format key from snake_case to Title Case
        formatted_key = key.replace('_', ' ').title()
        lines.append(f"{formatted_key}: {value}")
    
    # Process nested structures if any
    for key, value in report.items():
        if isinstance(value, dict):
            lines.append(f"\n{key.replace('_', ' ').title()}:")
            for sub_key, sub_value in value.items():
                formatted_sub_key = sub_key.replace('_', ' ').title()
                lines.append(f"  {formatted_sub_key}: {sub_value}")
    
    # Add notes if available
    if 'notes' in report:
        lines.append(f"\nNotes: {report['notes']}")
    
    return "\n".join(lines)

# Define prompt styles to test
prompt_styles = {
    "basic": "Summarize the following financial report:",
    "structured": "You are a financial analyst. Provide a concise, bullet-point summary of the key financial data in this report:",
    "instructional": "Analyze the following financial report and summarize the most important income, expenses, profit, and trends in under 100 words:",
    "comparative": "As a business advisor, compare the financial performance in this report with benchmarks or previous periods and highlight the most significant changes:",
    "actionable": "Based on this financial report, identify 3-5 key insights and suggest specific actionable recommendations:"
}

# Backoff decorator to handle rate limiting
def query_gpt(prompt, text, api_key, model="gpt-3.5-turbo"):
    """
    Query the OpenAI API with quota checking
    
    Args:
        prompt (str): The instruction prompt
        text (str): The text to analyze
        api_key (str): OpenAI API key
        model (str): Model to use
        
    Returns:
        str: The generated summary or error message
    """
    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"{prompt}\n\n{text}"}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
    except openai.RateLimitError as e:
        error_message = str(e)
        if "insufficient_quota" in error_message:
            print("\n⚠️ ERROR: You have exceeded your OpenAI API quota.")
            print("Please check your billing details at https://platform.openai.com/account/billing")
            print("Switching to simulation mode...\n")
            return f"[SIMULATED RESPONSE] Summary for prompt: '{prompt}'"
        else:
            print(f"Rate limit exceeded. Waiting 20 seconds before retrying: {e}")
            time.sleep(20)
            # Try one more time
            try:
                client = openai.OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": f"{prompt}\n\n{text}"}
                    ],
                    temperature=0.7
                )
                return response.choices[0].message.content
            except:
                return f"[SIMULATED RESPONSE] Summary for prompt: '{prompt}'"
    except Exception as e:
        print(f"Error querying OpenAI API: {e}")
        return f"Error: {str(e)}"

def batch_process(reports, prompt_styles, api_key, batch_size=2, delay=2):
    """
    Process reports in batches to avoid rate limits
    
    Args:
        reports (dict): Dictionary of reports to process
        prompt_styles (dict): Dictionary of prompt styles to test
        api_key (str): OpenAI API key
        batch_size (int): Number of requests to process before pausing
        delay (int): Seconds to wait between batches
        
    Returns:
        pandas.DataFrame: Results dataframe
    """
    results = []
    count = 0
    
    # Create a progress bar
    total_requests = len(reports) * len(prompt_styles)
    with tqdm(total=total_requests, desc="Processing") as pbar:
        for report_title, report_text in reports.items():
            for style_name, prompt_text in prompt_styles.items():
                # Call API with backoff retry logic
                output = query_gpt(prompt_text, report_text, api_key)
                
                # Store results
                results.append({
                    "Report": report_title,
                    "Prompt Style": style_name,
                    "Summary": output,
                    "Original Report": report_text[:200] + "..." if len(report_text) > 200 else report_text  # Include snippet of original report
                })
                
                # Update progress bar
                pbar.update(1)
                
                # Rate limiting logic
                count += 1
                if count % batch_size == 0:
                    print(f"Processed {count}/{total_requests} requests. Pausing for {delay} seconds...")
                    time.sleep(delay)
    
    return pd.DataFrame(results)

def evaluate_results(df):
    """
    Create a simple evaluation framework for the summaries
    
    Args:
        df (pandas.DataFrame): DataFrame with summaries
        
    Returns:
        pandas.DataFrame: Evaluation results
    """
    # Initialize evaluation columns
    df["Accuracy"] = None
    df["Conciseness"] = None 
    df["Clarity"] = None
    df["Actionability"] = None
    df["Total Score"] = None
    
    print("\nEvaluation Instructions:")
    print("For each summary, rate on a scale of 0-5 for:")
    print("- Accuracy: How well does it capture the key financial information?")
    print("- Conciseness: How brief yet comprehensive is the summary?")
    print("- Clarity: How easy is it to understand?")
    print("- Actionability: How useful is it for making decisions?")
    
    # For each summary, ask for ratings
    for idx, row in df.iterrows():
        print(f"\n\n--- Report: {row['Report']} ---")
        print(f"Prompt Style: {row['Prompt Style']}")
        
        # Show snippet of original report for reference
        if "Original Report" in row:
            print(f"\nOriginal Report (snippet):\n{row['Original Report']}")
        
        print(f"\nSummary:\n{row['Summary']}")
        
        try:
            accuracy = float(input("Accuracy (0-5): "))
            conciseness = float(input("Conciseness (0-5): "))
            clarity = float(input("Clarity (0-5): "))
            actionability = float(input("Actionability (0-5): "))
            
            df.at[idx, "Accuracy"] = accuracy
            df.at[idx, "Conciseness"] = conciseness
            df.at[idx, "Clarity"] = clarity
            df.at[idx, "Actionability"] = actionability
            df.at[idx, "Total Score"] = accuracy + conciseness + clarity + actionability
        except ValueError:
            print("Invalid input. Skipping evaluation for this entry.")
    
    return df
