#!/usr/bin/env python3
"""
MAGSASA-CARD Platform - Notion Integration for Deployment Tracking
Automates deployment status updates and monitoring in Notion databases
"""

import os
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional
import sys

class NotionIntegration:
    """Notion integration for deployment tracking and monitoring"""
    
    def __init__(self):
        """Initialize Notion integration with API credentials"""
        self.api_key = os.getenv('NOTION_API_KEY')
        self.deployment_db_id = os.getenv('NOTION_DEPLOYMENT_DB_ID')
        self.features_db_id = os.getenv('NOTION_FEATURES_DB_ID')
        self.infrastructure_db_id = os.getenv('NOTION_INFRASTRUCTURE_DB_ID')
        
        if not self.api_key:
            print("Warning: NOTION_API_KEY not set. Notion integration disabled.")
            self.enabled = False
            return
            
        self.enabled = True
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
    
    def test_connection(self) -> Dict:
        """Test Notion API connection"""
        if not self.enabled:
            return {
                "status": "disabled",
                "message": "Notion integration not configured"
            }
        
        try:
            response = requests.get(
                f"{self.base_url}/users/me",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return {
                    "status": "success",
                    "message": "Notion API connection successful",
                    "user": response.json().get("name", "Unknown")
                }
            else:
                return {
                    "status": "failed",
                    "message": f"API request failed: {response.status_code}",
                    "error": response.text
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Connection failed: {str(e)}"
            }
    
    def update_deployment_status(self, environment: str, status: str, **kwargs) -> Dict:
        """Update deployment status in Notion database"""
        if not self.enabled or not self.deployment_db_id:
            return {"status": "disabled", "message": "Deployment tracking not configured"}
        
        try:
            # Prepare properties for Notion
            properties = {
                "Environment": {
                    "select": {"name": environment}
                },
                "Status": {
                    "select": {"name": status}
                },
                "Last Updated": {
                    "date": {"start": datetime.utcnow().isoformat()}
                }
            }
            
            # Add optional properties
            if "platform" in kwargs:
                properties["Platform"] = {"select": {"name": kwargs["platform"]}}
            if "version" in kwargs:
                properties["Version"] = {"rich_text": [{"text": {"content": kwargs["version"]}}]}
            if "url" in kwargs:
                properties["URL"] = {"url": kwargs["url"]}
            if "health_status" in kwargs:
                properties["Health Status"] = {"select": {"name": kwargs["health_status"]}}
            if "database_type" in kwargs:
                properties["Database Type"] = {"select": {"name": kwargs["database_type"]}}
            if "notes" in kwargs:
                properties["Notes"] = {"rich_text": [{"text": {"content": kwargs["notes"]}}]}
            if "features" in kwargs:
                properties["Features"] = {
                    "multi_select": [{"name": feature} for feature in kwargs["features"]]
                }
            
            # Check if record exists, update or create
            existing_record = self._find_deployment_record(environment)
            
            if existing_record:
                # Update existing record
                response = requests.patch(
                    f"{self.base_url}/pages/{existing_record['id']}",
                    headers=self.headers,
                    json={"properties": properties},
                    timeout=10
                )
            else:
                # Create new record
                response = requests.post(
                    f"{self.base_url}/pages",
                    headers=self.headers,
                    json={
                        "parent": {"database_id": self.deployment_db_id},
                        "properties": properties
                    },
                    timeout=10
                )
            
            if response.status_code in [200, 201]:
                return {
                    "status": "success",
                    "message": f"Deployment status updated for {environment}",
                    "record_id": response.json()["id"]
                }
            else:
                return {
                    "status": "failed",
                    "message": f"Failed to update Notion: {response.status_code}",
                    "error": response.text
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Update failed: {str(e)}"
            }
    
    def update_feature_flag(self, feature_name: str, development: bool = None, 
                           staging: bool = None, production: bool = None, **kwargs) -> Dict:
        """Update feature flag status in Notion database"""
        if not self.enabled or not self.features_db_id:
            return {"status": "disabled", "message": "Feature flags tracking not configured"}
        
        try:
            properties = {
                "Feature Name": {
                    "title": [{"text": {"content": feature_name}}]
                },
                "Last Updated": {
                    "date": {"start": datetime.utcnow().isoformat()}
                }
            }
            
            # Add environment flags
            if development is not None:
                properties["Development"] = {"checkbox": development}
            if staging is not None:
                properties["Staging"] = {"checkbox": staging}
            if production is not None:
                properties["Production"] = {"checkbox": production}
            
            # Add optional properties
            if "description" in kwargs:
                properties["Description"] = {"rich_text": [{"text": {"content": kwargs["description"]}}]}
            if "dependencies" in kwargs:
                properties["Dependencies"] = {"rich_text": [{"text": {"content": kwargs["dependencies"]}}]}
            if "risk_level" in kwargs:
                properties["Risk Level"] = {"select": {"name": kwargs["risk_level"]}}
            
            # Check if record exists
            existing_record = self._find_feature_record(feature_name)
            
            if existing_record:
                response = requests.patch(
                    f"{self.base_url}/pages/{existing_record['id']}",
                    headers=self.headers,
                    json={"properties": properties},
                    timeout=10
                )
            else:
                response = requests.post(
                    f"{self.base_url}/pages",
                    headers=self.headers,
                    json={
                        "parent": {"database_id": self.features_db_id},
                        "properties": properties
                    },
                    timeout=10
                )
            
            if response.status_code in [200, 201]:
                return {
                    "status": "success",
                    "message": f"Feature flag updated: {feature_name}",
                    "record_id": response.json()["id"]
                }
            else:
                return {
                    "status": "failed",
                    "message": f"Failed to update feature flag: {response.status_code}",
                    "error": response.text
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Feature flag update failed: {str(e)}"
            }
    
    def update_infrastructure_status(self, component: str, component_type: str, 
                                   environment: str, status: str, **kwargs) -> Dict:
        """Update infrastructure component status in Notion database"""
        if not self.enabled or not self.infrastructure_db_id:
            return {"status": "disabled", "message": "Infrastructure monitoring not configured"}
        
        try:
            properties = {
                "Component": {
                    "title": [{"text": {"content": component}}]
                },
                "Type": {
                    "select": {"name": component_type}
                },
                "Environment": {
                    "select": {"name": environment}
                },
                "Status": {
                    "select": {"name": status}
                },
                "Last Check": {
                    "date": {"start": datetime.utcnow().isoformat()}
                }
            }
            
            # Add optional properties
            if "provider" in kwargs:
                properties["Provider"] = {"select": {"name": kwargs["provider"]}}
            if "url" in kwargs:
                properties["URL/Endpoint"] = {"url": kwargs["url"]}
            if "uptime" in kwargs:
                properties["Uptime"] = {"rich_text": [{"text": {"content": kwargs["uptime"]}}]}
            if "notes" in kwargs:
                properties["Notes"] = {"rich_text": [{"text": {"content": kwargs["notes"]}}]}
            
            # Check if record exists
            existing_record = self._find_infrastructure_record(component, environment)
            
            if existing_record:
                response = requests.patch(
                    f"{self.base_url}/pages/{existing_record['id']}",
                    headers=self.headers,
                    json={"properties": properties},
                    timeout=10
                )
            else:
                response = requests.post(
                    f"{self.base_url}/pages",
                    headers=self.headers,
                    json={
                        "parent": {"database_id": self.infrastructure_db_id},
                        "properties": properties
                    },
                    timeout=10
                )
            
            if response.status_code in [200, 201]:
                return {
                    "status": "success",
                    "message": f"Infrastructure status updated: {component}",
                    "record_id": response.json()["id"]
                }
            else:
                return {
                    "status": "failed",
                    "message": f"Failed to update infrastructure: {response.status_code}",
                    "error": response.text
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Infrastructure update failed: {str(e)}"
            }
    
    def _find_deployment_record(self, environment: str) -> Optional[Dict]:
        """Find existing deployment record by environment"""
        if not self.deployment_db_id:
            return None
            
        try:
            response = requests.post(
                f"{self.base_url}/databases/{self.deployment_db_id}/query",
                headers=self.headers,
                json={
                    "filter": {
                        "property": "Environment",
                        "select": {"equals": environment}
                    }
                },
                timeout=10
            )
            
            if response.status_code == 200:
                results = response.json().get("results", [])
                return results[0] if results else None
                
        except Exception:
            pass
        
        return None
    
    def _find_feature_record(self, feature_name: str) -> Optional[Dict]:
        """Find existing feature flag record by name"""
        if not self.features_db_id:
            return None
            
        try:
            response = requests.post(
                f"{self.base_url}/databases/{self.features_db_id}/query",
                headers=self.headers,
                json={
                    "filter": {
                        "property": "Feature Name",
                        "title": {"equals": feature_name}
                    }
                },
                timeout=10
            )
            
            if response.status_code == 200:
                results = response.json().get("results", [])
                return results[0] if results else None
                
        except Exception:
            pass
        
        return None
    
    def _find_infrastructure_record(self, component: str, environment: str) -> Optional[Dict]:
        """Find existing infrastructure record by component and environment"""
        if not self.infrastructure_db_id:
            return None
            
        try:
            response = requests.post(
                f"{self.base_url}/databases/{self.infrastructure_db_id}/query",
                headers=self.headers,
                json={
                    "filter": {
                        "and": [
                            {
                                "property": "Component",
                                "title": {"equals": component}
                            },
                            {
                                "property": "Environment",
                                "select": {"equals": environment}
                            }
                        ]
                    }
                },
                timeout=10
            )
            
            if response.status_code == 200:
                results = response.json().get("results", [])
                return results[0] if results else None
                
        except Exception:
            pass
        
        return None

def main():
    """Main function for testing Notion integration"""
    print("🔗 MAGSASA-CARD Notion Integration Test")
    print("=" * 50)
    
    # Initialize integration
    notion = NotionIntegration()
    
    # Test connection
    print("Testing Notion API connection...")
    connection_result = notion.test_connection()
    print(f"Status: {connection_result['status']}")
    print(f"Message: {connection_result['message']}")
    
    if connection_result['status'] != 'success':
        print("❌ Notion integration test failed")
        return
    
    print("✅ Notion API connection successful")
    print()
    
    # Test deployment status update
    print("Testing deployment status update...")
    deployment_result = notion.update_deployment_status(
        environment="Development",
        status="Deployed",
        platform="Local",
        version="2.1.0",
        url="http://localhost:5000",
        health_status="Healthy",
        database_type="SQLite",
        features=["Dynamic Pricing", "KaAni Integration", "AI Diagnosis"],
        notes="Test deployment from Notion integration script"
    )
    print(f"Deployment update: {deployment_result['status']} - {deployment_result['message']}")
    
    # Test feature flag update
    print("Testing feature flag update...")
    feature_result = notion.update_feature_flag(
        feature_name="KaAni Integration",
        development=True,
        staging=True,
        production=True,
        description="AI-powered agricultural diagnosis and recommendations",
        dependencies="OpenAI API, Google AI API",
        risk_level="Medium"
    )
    print(f"Feature flag update: {feature_result['status']} - {feature_result['message']}")
    
    # Test infrastructure status update
    print("Testing infrastructure status update...")
    infrastructure_result = notion.update_infrastructure_status(
        component="MAGSASA-CARD API",
        component_type="Application",
        environment="Development",
        status="Online",
        provider="Local",
        url="http://localhost:5000",
        uptime="99.9%",
        notes="Local development environment"
    )
    print(f"Infrastructure update: {infrastructure_result['status']} - {infrastructure_result['message']}")
    
    print()
    print("✅ Notion integration test completed")

if __name__ == "__main__":
    main()
