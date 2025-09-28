#!/usr/bin/env python3
"""
MAGSASA-CARD Platform - Notion Webhook Handler
Handles real-time deployment updates and notifications via webhooks
"""

from flask import Flask, request, jsonify
import json
import os
import sys
from datetime import datetime
import requests
import threading
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from notion_integration import NotionIntegration

app = Flask(__name__)
notion = NotionIntegration()

# Configuration
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', 'magsasa-card-webhook-secret')
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')
EMAIL_NOTIFICATION_URL = os.getenv('EMAIL_NOTIFICATION_URL')

def send_slack_notification(message: str, channel: str = "#deployments"):
    """Send notification to Slack"""
    if not SLACK_WEBHOOK_URL:
        return
    
    try:
        payload = {
            "channel": channel,
            "username": "MAGSASA-CARD Bot",
            "text": message,
            "icon_emoji": ":rocket:"
        }
        
        requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
    except Exception as e:
        print(f"Failed to send Slack notification: {e}")

def send_email_notification(subject: str, message: str, recipients: list):
    """Send email notification"""
    if not EMAIL_NOTIFICATION_URL:
        return
    
    try:
        payload = {
            "subject": subject,
            "message": message,
            "recipients": recipients
        }
        
        requests.post(EMAIL_NOTIFICATION_URL, json=payload, timeout=10)
    except Exception as e:
        print(f"Failed to send email notification: {e}")

@app.route('/api/notion/deployment-update', methods=['POST'])
def handle_deployment_update():
    """Handle deployment status updates"""
    try:
        # Verify webhook secret
        provided_secret = request.headers.get('X-Webhook-Secret')
        if provided_secret != WEBHOOK_SECRET:
            return jsonify({"error": "Invalid webhook secret"}), 401
        
        data = request.get_json()
        
        # Extract deployment information
        environment = data.get('environment')
        status = data.get('status')
        platform = data.get('platform')
        version = data.get('version')
        url = data.get('url')
        notes = data.get('notes', '')
        
        # Update Notion database
        result = notion.update_deployment_status(
            environment=environment,
            status=status,
            platform=platform,
            version=version,
            url=url,
            notes=f"{notes} (Updated via webhook at {datetime.utcnow().isoformat()})"
        )
        
        # Send notifications based on status
        if status.lower() == 'deployed':
            message = f"🚀 Deployment successful!\n" \
                     f"Environment: {environment}\n" \
                     f"Platform: {platform}\n" \
                     f"Version: {version}\n" \
                     f"URL: {url}"
            send_slack_notification(message)
            
        elif status.lower() == 'failed':
            message = f"❌ Deployment failed!\n" \
                     f"Environment: {environment}\n" \
                     f"Platform: {platform}\n" \
                     f"Version: {version}\n" \
                     f"Notes: {notes}"
            send_slack_notification(message, "#alerts")
            send_email_notification(
                f"MAGSASA-CARD Deployment Failed - {environment}",
                message,
                ["admin@magsasa-card.com"]
            )
        
        return jsonify({
            "status": "success",
            "message": "Deployment status updated",
            "notion_result": result
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/notion/health-update', methods=['POST'])
def handle_health_update():
    """Handle health check updates"""
    try:
        # Verify webhook secret
        provided_secret = request.headers.get('X-Webhook-Secret')
        if provided_secret != WEBHOOK_SECRET:
            return jsonify({"error": "Invalid webhook secret"}), 401
        
        data = request.get_json()
        
        # Extract health information
        component = data.get('component')
        environment = data.get('environment')
        status = data.get('status')
        uptime = data.get('uptime')
        response_time = data.get('response_time')
        
        # Update infrastructure status
        result = notion.update_infrastructure_status(
            component=component,
            component_type="Application",
            environment=environment,
            status=status,
            uptime=uptime,
            notes=f"Response time: {response_time}ms (Updated at {datetime.utcnow().isoformat()})"
        )
        
        # Send alert if unhealthy
        if status.lower() in ['unhealthy', 'degraded', 'offline']:
            message = f"🚨 Health Alert!\n" \
                     f"Component: {component}\n" \
                     f"Environment: {environment}\n" \
                     f"Status: {status}\n" \
                     f"Uptime: {uptime}"
            send_slack_notification(message, "#alerts")
        
        return jsonify({
            "status": "success",
            "message": "Health status updated",
            "notion_result": result
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/notion/feature-update', methods=['POST'])
def handle_feature_update():
    """Handle feature flag updates"""
    try:
        # Verify webhook secret
        provided_secret = request.headers.get('X-Webhook-Secret')
        if provided_secret != WEBHOOK_SECRET:
        
        data = request.get_json()
        
        # Extract feature information
        feature_name = data.get('feature_name')
        development = data.get('development')
        staging = data.get('staging')
        production = data.get('production')
        description = data.get('description')
        risk_level = data.get('risk_level')
        
        # Update feature flag
        result = notion.update_feature_flag(
            feature_name=feature_name,
            development=development,
            staging=staging,
            production=production,
            description=description,
            risk_level=risk_level
        )
        
        # Send notification for production changes
        if production is not None:
            status_text = "enabled" if production else "disabled"
            message = f"🎛️ Feature flag updated!\n" \
                     f"Feature: {feature_name}\n" \
                     f"Production: {status_text}\n" \
                     f"Risk Level: {risk_level}"
            send_slack_notification(message)
        
        return jsonify({
            "status": "success",
            "message": "Feature flag updated",
            "notion_result": result
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/notion/test', methods=['GET', 'POST'])
def test_notion_integration():
    """Test endpoint for Notion integration"""
    try:
        # Test connection
        connection_result = notion.test_connection()
        
        if request.method == 'POST':
            # Test with sample data
            deployment_result = notion.update_deployment_status(
                environment="Development",
                status="Deployed",
                platform="Local",
                version="2.1.0-test",
                url="http://localhost:5000",
                health_status="Healthy",
                notes="Test update from webhook handler"
            )
            
            return jsonify({
                "status": "success",
                "connection": connection_result,
                "deployment_test": deployment_result
            })
        
        return jsonify({
            "status": "success",
            "connection": connection_result
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for the webhook handler"""
    return jsonify({
        "status": "healthy",
        "service": "MAGSASA-CARD Notion Webhook Handler",
        "timestamp": datetime.utcnow().isoformat(),
        "notion_enabled": notion.enabled
    })

def periodic_health_check():
    """Periodic health check for all environments"""
    while True:
        try:
            # Check development environment
            try:
                response = requests.get("http://localhost:5000/health", timeout=10)
                if response.status_code == 200:
                    health_data = response.json()
                    notion.update_infrastructure_status(
                        component="MAGSASA-CARD API",
                        component_type="Application",
                        environment="Development",
                        status="Online",
                        provider="Local",
                        url="http://localhost:5000",
                        uptime="Available",
                        notes=f"Health check passed at {datetime.utcnow().isoformat()}"
                    )
                else:
                    notion.update_infrastructure_status(
                        component="MAGSASA-CARD API",
                        component_type="Application",
                        environment="Development",
                        status="Degraded",
                        provider="Local",
                        notes=f"Health check returned {response.status_code}"
                    )
            except Exception:
                notion.update_infrastructure_status(
                    component="MAGSASA-CARD API",
                    component_type="Application",
                    environment="Development",
                    status="Offline",
                    provider="Local",
                    notes=f"Health check failed at {datetime.utcnow().isoformat()}"
                )
            
            # Check staging environment (if URL is available)
            staging_url = os.getenv('STAGING_URL', 'https://magsasa-card-api-staging.onrender.com')
            try:
                response = requests.get(f"{staging_url}/health", timeout=30)
                if response.status_code == 200:
                    notion.update_infrastructure_status(
                        component="MAGSASA-CARD API",
                        component_type="Application",
                        environment="Staging",
                        status="Online",
                        provider="Render",
                        url=staging_url,
                        uptime="Available",
                        notes=f"Health check passed at {datetime.utcnow().isoformat()}"
                    )
                else:
                    notion.update_infrastructure_status(
                        component="MAGSASA-CARD API",
                        component_type="Application",
                        environment="Staging",
                        status="Degraded",
                        provider="Render",
                        notes=f"Health check returned {response.status_code}"
                    )
            except Exception:
                # Staging might not be deployed yet
                pass
            
        except Exception as e:
            print(f"Periodic health check error: {e}")
        
        # Wait 5 minutes before next check
        time.sleep(300)

if __name__ == '__main__':
    print("🔗 Starting MAGSASA-CARD Notion Webhook Handler")
    print(f"Notion Integration: {'Enabled' if notion.enabled else 'Disabled'}")
    
    # Start periodic health check in background
    health_thread = threading.Thread(target=periodic_health_check, daemon=True)
    health_thread.start()
    
    # Start Flask app
    port = int(os.getenv('WEBHOOK_PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)
