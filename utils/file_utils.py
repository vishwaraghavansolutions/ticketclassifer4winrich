import json
import streamlit as st
import os
import yaml
from utils.S3Client import S3Client
import boto3

# 📌 Constants
USER_FILE = st.secrets["USERS_JSON"] 
USER_MAPPING_FILE = st.secrets["USER_COURSE_MAPPING"]
ASSESS_MAPPING_FILE = st.secrets["USER_ASSESSMENT_MAPPING"]
COURSE_MAPPING_FILE = st.secrets["USER_COURSE_MAPPING"]
COURSE_MASTER_FILE = st.secrets["COURSE_MASTER"]
ASSESS_MASTER_FILE = st.secrets["ASSESS_MASTER"]
ASSESS_PROMPT_FILE = st.secrets["ASSESS_PROMPT_FILE"]
COURSE_PROMPT_FILE = st.secrets["COURSE_PROMPT_FILE"]
FEEDBACK_PROMPT_FILE = st.secrets["FEEDBACK_PROMPT_FILE"]
storage_bucket = st.secrets["aws_bucket"]
assessments_key=st.secrets["aws_assessments_key"]
assessments_key = st.secrets["aws_assessments_key"]
courses_key = st.secrets["aws_courses_key"]
assessment_feedback_key = st.secrets["aws_assessments_feedback_key"]

def load_credentials():
    key = USER_FILE
    s3client = S3Client()
    userdata = s3client.get_json(storage_bucket,key)
    return userdata
    
# 📥 Load users from users.json
def load_users():
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as f:
            return json.load(f)
    return []

# 📂 Discover all course JSON files in the folder
def discover_courses():
    course_files = []
    for file in os.listdir():
        if file.endswith(".json") and file not in [USER_FILE, USER_MAPPING_FILE]:
            course_files.append(file)
    return course_files

# 🧠 Load existing mapping if available
def load_existing_mapping(type):
    if type == "course":
        MAPPING_FILE = COURSE_MAPPING_FILE
    
    if type == "assessment":
        MAPPING_FILE = ASSESS_MAPPING_FILE

    if os.path.exists(MAPPING_FILE):
        with open(MAPPING_FILE, "r") as f:
            return json.load(f)
    return {}

def load_user_courses():
    file_path=COURSE_MAPPING_FILE
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    return {}

def save_user_courses(users_courses):
    file_path=COURSE_MAPPING_FILE
    if os.path.exists(file_path):
        with open(file_path, "w") as f:
            json.dump(users_courses, f, indent=4)
    return

def save_courses_master(course_meta):
    file_path=COURSE_MASTER_FILE
    
    try:
        if os.path.exists(file_path):
            with open(file_path, "w") as f:
                json.dump(course_meta, f, indent=4)
        else:
            raise ValueError("Course master file does not exist.")
    except json.JSONDecodeError:
        raise ValueError("Failed to parse courses_master.json — check for corruption or formatting issues.")
    
def get_skill_list(path):
    """
    Extracts a list of skill names from a JSON list of skill dictionaries.

    Args:
        skills_json (list): List of dictionaries, each representing a skill.

    Returns:
        List[str]: List of skill names.
    """
    with open(path, "r") as f:
        skills_json = json.load(f)

    if not isinstance(skills_json, list):
        raise ValueError("Input must be a list of skill dictionaries")

    return [skill["skill"] for skill in skills_json if "skill" in skill]

def save_formatted_txt(audit_log, general_notes, timeatwrite, filename="report.txt"):
    with open(filename, "w", encoding="utf-8") as f:
        # Title
        f.write("📋 Quiz Audit Report\n")
        f.write("=" * 40 + "\n\n")

        # General Notes
        f.write("🧠 Summary Notes:\n")
        f.write(general_notes.strip() + "\n\n")

        # Audit Log
        f.write("📝 Detailed Responses:\n")
        for entry in audit_log:
            f.write(f"Q{entry['question_index'] + 1}: {entry['question']}\n")
            f.write(f"Your Answer     : {entry['selected_answer']}\n")
            f.write(f"Correct Answer  : {entry['correct_answer']}\n")
            f.write(f"Correct?        : {'✅' if entry['is_correct'] else '❌'}\n")
            f.write(f"Timestamp       : {entry['timestamp']}\n")
            f.write("-" * 40 + "\n")
        # Footer
        f.write("\nGenerated on: " + str(timeatwrite))
    return

def append_response_to_txt(response_text, filename="llm_response.txt"):
    with open(filename, "a", encoding="utf-8") as f:
        f.write(response_text.strip())

def isValidJSON(file_path):
    """
    Checks if the file at file_path contains valid JSON.

    Args:
        file_path (str): Path to the JSON file. 
    Returns:
        bool: True if valid JSON, False otherwise.
    """  
    s3client = S3Client()
    filename = file_path
    return s3client.bucket_and_key_exist(storage_bucket, filename)
    

def load_yaml(path):
    s3client = S3Client()

    userdata = s3client.get_yaml(storage_bucket,path)
    return userdata

        
def save_yaml(path, config):
    s3client = S3Client()
    s3client.upload_json(storage_bucket,path, config)


def save_file(path, config):
    s3client = S3Client()
    s3client.upload_json(storage_bucket,path, config)

def load_json(jsonfile):

    s3client = S3Client()
    userdata = s3client.get_json(storage_bucket,jsonfile)
    return userdata


def save_json(filename, data):
    s3client = S3Client()   
    s3client.upload_json(storage_bucket,filename, data)    
    return filename

def delete_json(filename):
    s3client = S3Client()   
    key = courses_key
    s3client.remove_file(storage_bucket, key, filename)    
    return filename