import boto3
import streamlit as st
import json
from botocore.exceptions import ClientError
import yaml

class S3Client:
    def __init__(self):
        self.s3 = boto3.client(
            's3',
            aws_access_key_id=st.secrets["aws_access_key_id"].strip(),
            aws_secret_access_key=st.secrets["aws_secret_access_key"].strip(),
            region_name=st.secrets["aws_region"].strip()
        )

    def get_file(self, bucket: str, key: str) -> str:
        """Download file content from S3 as string"""
        if self.bucket_and_key_exist(bucket, key):
            try:
                obj = self.s3.get_object(Bucket=bucket, Key=key)
                return obj['Body'].read().decode('utf-8')
            except Exception as e:
                st.error(f"Error fetching file: {e}")
                return ""
        else: 
            return ""

    def get_json(self, bucket: str, key: str) -> dict:
        """Download and parse JSON file from S3"""
        if self.bucket_and_key_exist(bucket, key):
            content = self.get_file(bucket, key)
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                st.error("Failed to parse JSON.")
                return {}
        else:
            return {}
        
    def get_yaml(self, bucket: str, key: str) -> dict:
        """Download and parse YAML file from S3"""
        try:
            obj = self.s3.get_object(Bucket=bucket, Key=key)
            content = obj['Body'].read().decode('utf-8')
            return yaml.safe_load(content)
        except ClientError as e:
            st.error(f"S3 error: {e}")
            return {}
        except yaml.YAMLError as e:
            st.error(f"YAML parse error: {e}")
            return {}

    def upload_json(self, bucket: str, key: str, content: str) -> bool:
        """Upload string content to S3"""
        jsoncontent = json.dumps(content)
        try:
            self.s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=jsoncontent,
                ContentType='application/json'
            )
            return True
        except Exception as e:
            st.error(f"Upload failed: {e}")
            return False
        
    def upload_yaml(self, bucket: str, key: str, data: dict) -> bool:
        """Upload dictionary as YAML to S3"""
        try:
            yaml_content = yaml.dump(data, sort_keys=False)
            self.s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=yaml_content,
                ContentType='application/x-yaml'
            )
            return True
        except Exception as e:
            st.error(f"Upload failed: {e}")
            return False

    def upload_file(self, bucket: str, key: str, filename) -> bool:
        """Upload file to S3"""
        try:
            self.s3.upload(filename, bucket, key)
            return True
        except Exception as e:
            st.error(f"Upload failed: {e}")
            return False

    def remove_file(self, bucket: str, key: str, filename) -> bool:
        """Upload file to S3"""
        print("Removing file:", filename)
        filetoremove = key+"/"+filename
        print("From bucket:", bucket)
        try:
            self.s3.delete_object(Bucket=bucket, Key=filetoremove)
            return True
        except Exception as e:
            st.error(f"Remove failed: {e}")
            return False
        
    def bucket_and_key_exist(self, bucket_name, key_name):
        
        # Check if bucket exists
        try:
            self.s3.head_bucket(Bucket=bucket_name)
        except ClientError as e:
            print(f"Bucket check failed: {e}")
            return False

        # Check if key exists
        try:
            self.s3.head_object(Bucket=bucket_name, Key=key_name)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                print(f"Key '{key_name}' not found in bucket '{bucket_name}'")
                return False
            else:
                print(f"Key check failed: {e}")
                return False
