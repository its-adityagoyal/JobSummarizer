import unittest
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Union
import importlib.util
from fuzzywuzzy import fuzz 

#List of fields to consolidate from each job object for regex testing
FIELDS_TO_CONSOLIDATE = [
    "Company name",
    "Job title",
    "Number of openings",
    "Reservation details",
    "Location",
    "Qualifications required",
    "Skills required",
    "Age limit",
    "Salary or compensation details",
    "Application deadline",
    "Mode of application",
    "Contact details"
]

def load_json_output(file_path: Path) -> Union[List[Dict[str, Any]], None]:
    """
    Loads and parses a JSON file into a Python list of dictionaries
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not isinstance(data, list):
                print(f"Error: JSON in {file_path} is not a list of objects")
                return None
            return data
    except FileNotFoundError:
        print(f"Error: JSON file not found at {file_path}. Please ensure the path is correct")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Could not decode JSON from {file_path}. Check file format. Error: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading {file_path}: {e}")
        return None


        
def normalize_value(value: Any) -> str:
    """
    Normalizes a single value (string, list, dict) for consistent comparison
    """
    if value is None:
        return ""
    
    if isinstance(value, list):
        #Flatten list items into a single string, normalizing each item
        normalized_items = [normalize_value(item) for item in value if item is not None and str(item).strip() != ""]
        return " ".join(normalized_items)
    
    if isinstance(value, dict):
        #Convert dict to a sorted JSON string, then normalize and clean
        value = json.dumps(value, sort_keys=True)
        

    text = str(value).lower().strip()
    
    # if text == "not mentioned":
    #    return ""
    # if text == "notmentioned":
    #    return ""
    
    text = re.sub(r'[,]', '', text)
    text = re.sub(r'[-|.:]', ' ', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'[₹]', 'rs', text)
    text = re.sub(r'[$]', 'usd', text)
    text = text.replace("senior", "sr")
    text = text.replace("junior", "jr")
    
    #Normalize spacing
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def job_data(job_list: List[Dict[str, Any]], fields: List[str]) -> Dict[str, str]:
    """
    Consolidates specified fields from all job objects in the list, into a dictionary
    where keys are normalized field names and values are single strings containing all occurrences for that field
    """
    aggregated_field_values: Dict[str, List[str]] = {field: [] for field in fields}

    for job in job_list:
        for field in fields:
            value = job.get(field)
            
            normalized_val = normalize_value(value)
            if normalized_val: 
                aggregated_field_values[str(field)].append(normalized_val)
        
    # Convert lists of values into single strings for each field
    consolidated_output_fields: Dict[str, str] = {}
    for field_name, values in aggregated_field_values.items():
        if values: 
            consolidated_output_fields[field_name] = ' '.join(values)
    return consolidated_output_fields


def load_expected_test_data(file_path: Path, variable_name: str = "EXPECTED_PATTERNS") -> Dict[str, Dict[str, str]]:
    """
    Loads expected test data 
    """
    if not file_path.exists():
        print(f"Error: Expected test data file not found at {file_path}.")
        return {}

    try:
        spec = importlib.util.spec_from_file_location("expected_data_module", file_path)
        if spec is None:
            print(f"Error: Could not load module spec for {file_path}")
            return {}
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module) # Execute the module to load its contents

        # Retrieve the dictionary variable from the loaded module
        expected_data = getattr(module, variable_name, None)

        if expected_data is None:
            print(f"Error: Variable '{variable_name}' not found in {file_path}.")
            return {}
        if not isinstance(expected_data, dict):
            print(f"Error: Variable '{variable_name}' in {file_path} is not a dictionary.")
            return {}
        
        return expected_data
    except Exception as e:
        print(f"An unexpected error occurred while loading expected test data from {file_path}: {e}")
        return {}

class TestJsonConsolidation(unittest.TestCase):
    """
    A unit test class to test the consolidation of job data from a specific JSON file.
    """
    # Class variables to hold data loaded once for the entire test class
    _all_expected_test_data: Dict[str, Dict[str, str]] = {} 
    json_file_path: Path = None 
    _consolidated_data: Dict[str, str] = {} 
    _expected_patterns_for_file: Dict[str, str] = {} 

    @classmethod
    def setUpClass(cls):

        if not cls.json_file_path:
            raise unittest.SkipTest("JSON file path not set for testing. Skipping all tests.")
        job_data_list = load_json_output(cls.json_file_path)
        cls._consolidated_data = job_data(job_data_list, FIELDS_TO_CONSOLIDATE)
        
        # Get the expected patterns specifically for this file (assumes original keys in .py)
        cls._expected_patterns_for_file = cls._all_expected_test_data.get(cls.json_file_path.name, {})
        if not cls._expected_patterns_for_file:
            print(f"  WARNING: No expected patterns found for '{cls.json_file_path.name}'. Field tests might not have assertions.")

        # Print the loaded data
        # for field, content in cls._consolidated_data.items():
        #     print(f"[{field}]:\n{content}\n")
        # print(json.dumps(cls._expected_patterns_for_file, indent=4))    


    def _evaluate_field(self, field_name: str):
        """
        Helper to evaluate a specific field against its expected regex pattern using fuzzy matching.
        Uses the ORIGINAL field_name directly.
        """
        consolidated_value = self._consolidated_data.get(field_name, "")
        expected_pattern = self._expected_patterns_for_file.get(field_name, None) 

        if expected_pattern:
            # normalized_consolidated = normalize_value(consolidated_value)
            # normalized_expected = normalize_value(expected_pattern) 

            normalized_consolidated = consolidated_value
            normalized_expected = expected_pattern

            similarity_score = fuzz.token_set_ratio(normalized_consolidated, normalized_expected)
            FUZZY_MATCH_THRESHOLD=50
            # print(f"Similarity for '{field_name}': {similarity_score} (Threshold: {FUZZY_MATCH_THRESHOLD})")
            self.assertGreaterEqual(similarity_score, FUZZY_MATCH_THRESHOLD,
                                    f"Failed '{field_name}' for {self.json_file_path.name}.\n"
                                    f"  Expected content (normalized): '{normalized_expected}'\n"
                                    f"  Actual content (normalized): '{normalized_consolidated[:200]}'\n"
                                    f"  Similarity Score: {similarity_score} (Threshold: {FUZZY_MATCH_THRESHOLD})\n")
        else:
            print(f"  Warning: No expected pattern defined for '{field_name}' in '{self.json_file_path.name}'. Skipping assertion for this field.")
    
 
    def test_company_name(self):
        self._evaluate_field("Company name")

    def test_job_title(self):
        self._evaluate_field("Job title")

    def test_number_of_openings(self):
        self._evaluate_field("Number of openings")
    
    def test_reservation_details(self):
        self._evaluate_field("Reservation details")

    def test_location(self):
        self._evaluate_field("Location")

    def test_qualifications_required(self):
        self._evaluate_field("Qualifications required")

    def test_skills_required(self):
        self._evaluate_field("Skills required")

    def test_age_limit(self):
        self._evaluate_field("Age limit")

    def test_salary_or_compensation_details(self):
        self._evaluate_field("Salary or compensation details")

    def test_application_deadline(self):
        self._evaluate_field("Application deadline")

    def test_mode_of_application(self):
        self._evaluate_field("Mode of application")

    def test_contact_details(self):
        self._evaluate_field("Contact details")

    # # --- General Test for Required Fields (example) ---
    # def test_required_fields_not_empty(self):
    #     # Define your truly required fields using their ORIGINAL names
    #     required_fields = ["Job title", "Company name", "Location"] 
    #     if self._consolidated_data: 
    #         for field in required_fields:
    #             self.assertNotEqual(self._consolidated_data.get(field, "").strip(), "",
    #                                 f"Required field '{field}' is empty for {self._json_file_to_test.name}")


# --- Main Execution Block ---
if __name__ == "__main__":
    # Hardcode the paths as requested
    # IMPORTANT: Adjust these paths to match your actual file locations
    TestJsonConsolidation.json_file_path = Path("Output (openai_gpt-4o)") / "PDF1.json"
    expected_data_file_path = Path("Test_Data") / "PDF1.py" 

    # --- Step 1: Load Expected Test Data ---
    TestJsonConsolidation._all_expected_test_data = load_expected_test_data(
        expected_data_file_path, variable_name="EXPECTED_PATTERNS"
    )
    if not TestJsonConsolidation._all_expected_test_data:
        print(f"WARNING: No expected test data loaded from {expected_data_file_path}. Field evaluation tests might be skipped.")
    
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestJsonConsolidation)) 

    if suite.countTestCases() > 0:
        runner = unittest.TextTestRunner(verbosity=2) 
        runner.run(suite)
    else:
        print("No tests found in TestJsonConsolidation. Please check the class structure.")

# if __name__ == "__main__":
#     # Step 1: Load the JSON data
#     JSON_FILE_PATH = Path("Output (deepseek_deepseek-chat)\\PDF11.json")
#     job_data_list = load_json_output(JSON_FILE_PATH)

#     if job_data_list is None:
#         print("Exiting as JSON data could not be loaded or parsed")
#     else:
#         consolidated_field_data = consolidate_job_data(job_data_list, FIELDS_TO_CONSOLIDATE)
#         # Print the consolidated data for each field
#         print("\nConsolidated Data for Each Field")
#         for field_name, text in consolidated_field_data.items():
#             print(f"[{field_name}]:\n{text}\n")