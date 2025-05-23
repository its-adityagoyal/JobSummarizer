import os
import json
import base64
from pathlib import Path
import requests
from dotenv import load_dotenv
from typing import Union, Optional 
import sys
load_dotenv()

class JobPostingExtractor:
    """
    A class to extract job posting details from a scanned PDF using the OpenRouter API
    """

    def __init__(self,api_key: str = None, model_name="deepseek/deepseek-chat"):
        """
        Initializes the JobPostingExtractor.
        Args: api_key_env_var (str): The name of the environment variable where the OpenRouter API key is stored.
        model_name (str): The name of the OpenRouter model to use for extraction.
        """

        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.model_name = model_name

        if not self.api_key:
            raise ValueError(
                f"Error: OpenRouter API key not found. "
            )

    def _encode_pdf_to_base64(self, pdf_path: str)-> Optional[str]:
        """
        Encodes a PDF file to a base64 string.
        Args: pdf_path (str): The path to the PDF file.
        Returns: str | None: The base64 encoded string of the PDF, or None if the file is not found.
        """

        try:
            with open(pdf_path, "rb") as pdf_file:
                return base64.b64encode(pdf_file.read()).decode('utf-8')
        except FileNotFoundError:
            print(f"Error: PDF file not found at '{pdf_path}'. Please ensure the file exists.")
            return None

    def extract_job_details(self, pdf_path: str) -> Optional[dict]:
        """
        Extracts job details from a PDF using the OpenRouter API.
        Args:  pdf_path (str): The path to the PDF file containing job postings.
        Returns: dict | None: A dictionary containing the extracted job information or None if the extraction fails.
        """

        base64_pdf = self._encode_pdf_to_base64(pdf_path)
        if base64_pdf is None:
            return None
        data_url = f"data:application/pdf;base64,{base64_pdf}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # The detailed prompt for extracting job information
        prompt_text= "This PDF contains details about job openings. Extract the following information in a structured JSON format. If the document lists multiple job openings, treat each one separately. Do NOT combine or mix information across different jobs. Display each job as a separate object in a list, in the order they appear in the PDF.\n\nDo NOT separate job postings based on caste, category, or reservation type (e.g., SC/ST/OBC/EWS/UR). If a job includes reservation breakdowns, include those details under 'Reservation details' within the same job object.\n\nFor each job, extract:\n- Company name\n- Job title\n- Number of openings (if mentioned)\n- Reservation details (if applicable)\n- Location\n- Qualifications required\n- Skills required\n- Age limit (if mentioned)\n- Salary or compensation details\n- Application deadline\n- Mode of application (online/offline, email, etc.)\n- Contact details (if any)\n\nIf any section is missing, use \"not mentioned\".\n\nReturn only a clean JSON array of job objects. Each object must represent a single job posting. Do not include any additional explanation, summary, or text outside of the JSON output."

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt_text
                    },
                    {
                        "type": "file",
                        "file": {
                            "filename": Path(pdf_path).name, # Use actual filename
                            "file_data": data_url
                        }
                    },
                ]
            }
        ]

        payload = {
            "model": self.model_name,
            "messages": messages
        }

        try:
            response = requests.post(self.url, headers=headers, json=payload)
            response.raise_for_status()  
            response_data = response.json()

            # Extract and return the actual text content (which should be JSON)
            if response_data.get("choices") and len(response_data["choices"]) > 0:
                message_content = response_data["choices"][0]["message"].get("content")
                if message_content:
                    try:
                        if message_content.startswith("```json") and message_content.endswith("```"):
                            message_content = message_content.strip("```json").strip("```").strip()

                        return message_content
                    except json.JSONDecodeError:
                        print("Warning: Model did not return clean JSON. Returning raw text content.")
                        return {"raw_output": message_content}
                else:
                    print("No text content found in the response.")
                    return None
            else:
                print("No choices found in the response.")
                return None

        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            if response is not None:
                print(f"Response status code: {response.status_code}")
                print(f"Response text: {response.text}")
            return None
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON response from API: {e}")
            if response is not None:
                print(f"Raw response text: {response.text}")
            return None

if __name__ == "__main__":
    # pdf_file_path = "Input\\PDF5.pdf"

    if len(sys.argv) < 2:
        print("Usage: python summarizer.py <path_to_pdf_file>")
        sys.exit(1) 
    pdf_file_path = sys.argv[1] 

    try:
        extractor = JobPostingExtractor() 
        job_details = extractor.extract_job_details(pdf_file_path)

        if job_details:
            # Get the base name of the input PDF 
            pdf_name = Path(pdf_file_path).stem
            output_dir = "Output"
            os.makedirs(output_dir, exist_ok=True)
            output_file_path = Path(output_dir) / f"{pdf_name}.json"
            
            # Write the raw JSON string to the file
            with open(output_file_path, "w", encoding="utf-8") as f:
                f.write(job_details)
            print(f"Extracted job details saved to: {output_file_path}")
        else:
            print("\nFailed to extract job details.")

    except ValueError as ve:
        print(f"Configuration Error: {ve}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

