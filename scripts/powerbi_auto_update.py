#!/usr/bin/env python3
"""
Auto-Update PowerBI Integration for Auê Natural Pipeline
Automatically refreshes dashboards when new data is extracted
"""

import requests
import json
import os
from datetime import datetime
from pathlib import Path

class PowerBIAutoUpdater:
    def __init__(self):
        self.workspace_id = os.getenv('POWERBI_WORKSPACE_ID')
        self.dataset_id = os.getenv('POWERBI_DATASET_ID') 
        self.client_id = os.getenv('POWERBI_CLIENT_ID')
        self.client_secret = os.getenv('POWERBI_CLIENT_SECRET')
        self.tenant_id = os.getenv('POWERBI_TENANT_ID')
        
    def get_access_token(self):
        """Get PowerBI API access token."""
        auth_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        
        auth_data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'https://analysis.windows.net/powerbi/api/.default'
        }
        
        response = requests.post(auth_url, data=auth_data)
        return response.json()['access_token']
    
    def trigger_dataset_refresh(self):
        """Trigger PowerBI dataset refresh after new data extraction."""
        print("🔄 Triggering PowerBI dataset refresh...")
        
        token = self.get_access_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        refresh_url = f"https://api.powerbi.com/v1.0/myorg/groups/{self.workspace_id}/datasets/{self.dataset_id}/refreshes"
        
        refresh_data = {
            "notifyOption": "MailOnCompletion"
        }
        
        response = requests.post(refresh_url, headers=headers, json=refresh_data)
        
        if response.status_code == 202:
            print("✅ PowerBI refresh triggered successfully")
            return True
        else:
            print(f"❌ PowerBI refresh failed: {response.text}")
            return False
    
    def check_refresh_status(self):
        """Check the status of the latest refresh."""
        token = self.get_access_token()
        headers = {'Authorization': f'Bearer {token}'}
        
        status_url = f"https://api.powerbi.com/v1.0/myorg/groups/{self.workspace_id}/datasets/{self.dataset_id}/refreshes?$top=1"
        
        response = requests.get(status_url, headers=headers)
        if response.status_code == 200:
            refresh_data = response.json()
            if refresh_data['value']:
                status = refresh_data['value'][0]['status']
                print(f"📊 Latest refresh status: {status}")
                return status
        
        return "Unknown"
    
    def upload_csv_to_powerbi(self, csv_file_path, table_name):
        """Upload CSV data directly to PowerBI dataset."""
        print(f"📤 Uploading {csv_file_path} to PowerBI...")
        
        token = self.get_access_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Read CSV and convert to JSON for PowerBI REST API
        import pandas as pd
        df = pd.read_csv(csv_file_path)
        
        # Convert to PowerBI-compatible format
        rows = []
        for _, row in df.iterrows():
            rows.append({col: str(val) for col, val in row.items()})
        
        upload_url = f"https://api.powerbi.com/v1.0/myorg/groups/{self.workspace_id}/datasets/{self.dataset_id}/tables/{table_name}/rows"
        
        # Clear existing data first
        requests.delete(upload_url, headers=headers)
        
        # Upload new data in batches (PowerBI has row limits)
        batch_size = 10000
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            response = requests.post(upload_url, headers=headers, json={"rows": batch})
            
            if response.status_code != 200:
                print(f"❌ Upload failed for batch {i//batch_size + 1}: {response.text}")
                return False
        
        print(f"✅ Successfully uploaded {len(rows)} rows to {table_name}")
        return True

def integrate_with_pipeline():
    """Integration function to call from your main pipeline."""
    print("🚀 Starting PowerBI auto-update integration...")
    
    updater = PowerBIAutoUpdater()
    
    # Step 1: Upload latest data files
    data_files = [
        ("powerbi_data/FINAL_MATCHES.csv", "Matches"),
        ("powerbi_data/FINAL_UNMATCHED.csv", "Unmatched")
    ]
    
    upload_success = True
    for csv_file, table_name in data_files:
        if os.path.exists(csv_file):
            success = updater.upload_csv_to_powerbi(csv_file, table_name)
            upload_success = upload_success and success
        else:
            print(f"⚠️  File not found: {csv_file}")
    
    # Step 2: Trigger dashboard refresh
    if upload_success:
        refresh_success = updater.trigger_dataset_refresh()
        
        if refresh_success:
            print("✅ PowerBI dashboards will update automatically")
            print("🔗 Users can view latest competitive intelligence at:")
            print(f"   https://app.powerbi.com/groups/{updater.workspace_id}/dashboards/")
            
            return True
    
    print("❌ PowerBI auto-update failed")
    return False

if __name__ == "__main__":
    # For testing
    integrate_with_pipeline()
