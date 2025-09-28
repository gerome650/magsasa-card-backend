"""
OpenAI Provider for KaAni Agricultural Diagnosis
Handles AI-powered agricultural analysis and recommendations
"""

import os
import json
import openai
from datetime import datetime
from typing import Dict, List, Optional, Tuple

class OpenAIProvider:
    """OpenAI integration for agricultural diagnosis and recommendations"""
    
    def __init__(self):
        """Initialize OpenAI provider with API key and configuration"""
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            # For development, we can work without API key
            self.client = None
            self.model = "gpt-4o-mini"
            return
        
        try:
            self.client = openai.OpenAI(api_key=self.api_key)
        except Exception as e:
            # Fallback for development environment
            print(f"Warning: OpenAI client initialization failed: {e}")
            self.client = None
        self.model = "gpt-4.1-mini"  # Supported model for agricultural analysis
        
        # Agricultural diagnosis system prompt
        self.system_prompt = """You are KaAni, an expert agricultural diagnosis AI assistant for Filipino farmers. 

Your expertise covers:
1. SOIL & CLIMATE: Soil conditions, climate suitability, seasonal factors
2. PESTS: Pest identification, prevention, control methods  
3. DISEASE: Disease diagnosis, treatment, prevention
4. FERTILIZATION: Nutrient management, fertilizer recommendations, timing

Provide practical, actionable advice in simple terms. Always structure your response as JSON with the following format:

{
    "soil_climate": {
        "assessment": "Brief soil and climate analysis",
        "recommendations": ["specific action 1", "specific action 2"],
        "confidence": 0.85
    },
    "pests": {
        "likely_pests": ["pest name 1", "pest name 2"],
        "risk_level": "low|medium|high",
        "prevention": ["prevention method 1", "prevention method 2"],
        "confidence": 0.80
    },
    "disease": {
        "likely_diseases": ["disease 1", "disease 2"],
        "primary_cause": "main cause description",
        "treatment": ["treatment 1", "treatment 2"],
        "confidence": 0.75
    },
    "fertilization": {
        "diagnosis": "nutrient status assessment",
        "recommendations": ["fertilizer type and amount", "application timing"],
        "timing": "when to apply",
        "confidence": 0.90
    },
    "overall_confidence": 0.82,
    "priority_actions": ["most important action", "second priority"],
    "follow_up_days": 7
}

Be specific about Philippine agricultural conditions, crops, and available inputs."""

    def diagnose_agricultural_issue(self, farmer_input: Dict, diagnosis_mode: str = "regular") -> Dict:
        """
        Perform AI-powered agricultural diagnosis
        
        Args:
            farmer_input: Dictionary containing farmer's problem description and context
            diagnosis_mode: "quick" or "regular" diagnosis mode
            
        Returns:
            Dictionary containing structured diagnosis results
        """
        try:
            # Prepare diagnosis prompt based on farmer input
            user_prompt = self._build_diagnosis_prompt(farmer_input, diagnosis_mode)
            
            # Set token limits based on diagnosis mode
            max_tokens = 200 if diagnosis_mode == "quick" else 600
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            # Parse AI response
            ai_response = response.choices[0].message.content
            diagnosis_result = json.loads(ai_response)
            
            # Add metadata
            diagnosis_result.update({
                "ai_provider": "openai",
                "model_used": self.model,
                "diagnosis_mode": diagnosis_mode,
                "processing_time": response.usage.total_tokens if hasattr(response, 'usage') else None,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return diagnosis_result
            
        except json.JSONDecodeError as e:
            # Handle JSON parsing errors
            return self._create_error_response(f"AI response parsing error: {str(e)}")
        except Exception as e:
            # Handle other errors
            return self._create_error_response(f"Diagnosis error: {str(e)}")
    
    def _build_diagnosis_prompt(self, farmer_input: Dict, diagnosis_mode: str) -> str:
        """Build structured prompt from farmer input"""
        
        # Extract key information
        location = farmer_input.get('location', {})
        farm_profile = farmer_input.get('farm_profile', {})
        current_issue = farmer_input.get('current_issue', {})
        season_info = farmer_input.get('season_info', {})
        
        prompt_parts = []
        
        # Location context
        if location:
            prompt_parts.append(f"Location: {location.get('province', 'Unknown')}, {location.get('municipality', 'Unknown')}")
        
        # Farm details
        if farm_profile:
            prompt_parts.append(f"Farm: {farm_profile.get('size_hectares', 'Unknown')} hectares")
            prompt_parts.append(f"Soil: {farm_profile.get('soil_type', 'Unknown')}")
            prompt_parts.append(f"Crop: {farm_profile.get('primary_crop', 'Unknown')}")
            prompt_parts.append(f"Irrigation: {farm_profile.get('irrigation', 'Unknown')}")
        
        # Current problem
        if current_issue:
            prompt_parts.append(f"Problem: {current_issue.get('problem', 'General consultation')}")
            prompt_parts.append(f"Severity: {current_issue.get('severity', 'Unknown')}")
            prompt_parts.append(f"Affected area: {current_issue.get('affected_area', 'Unknown')}")
            prompt_parts.append(f"Duration: {current_issue.get('duration', 'Unknown')}")
        
        # Seasonal context
        if season_info:
            prompt_parts.append(f"Season: {season_info.get('planting_season', 'Unknown')}")
            prompt_parts.append(f"Growth stage: {season_info.get('growth_stage', 'Unknown')}")
            prompt_parts.append(f"Days after planting: {season_info.get('days_after_planting', 'Unknown')}")
        
        # Mode-specific instructions
        if diagnosis_mode == "quick":
            prompt_parts.append("\nProvide a QUICK diagnosis with direct, actionable recommendations.")
        else:
            prompt_parts.append("\nProvide a COMPREHENSIVE diagnosis with detailed analysis and multiple options.")
        
        return "\n".join(prompt_parts)
    
    def _create_error_response(self, error_message: str) -> Dict:
        """Create standardized error response"""
        return {
            "error": True,
            "error_message": error_message,
            "soil_climate": {
                "assessment": "Unable to analyze due to error",
                "recommendations": ["Please try again or contact support"],
                "confidence": 0.0
            },
            "pests": {
                "likely_pests": [],
                "risk_level": "unknown",
                "prevention": ["Unable to assess"],
                "confidence": 0.0
            },
            "disease": {
                "likely_diseases": [],
                "primary_cause": "Unable to determine",
                "treatment": ["Please consult local agricultural expert"],
                "confidence": 0.0
            },
            "fertilization": {
                "diagnosis": "Unable to assess",
                "recommendations": ["Please try again"],
                "timing": "Unknown",
                "confidence": 0.0
            },
            "overall_confidence": 0.0,
            "priority_actions": ["Contact local agricultural extension office"],
            "follow_up_days": 1,
            "ai_provider": "openai",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def generate_product_recommendations(self, diagnosis_result: Dict, available_products: List[Dict]) -> List[Dict]:
        """
        Generate product recommendations based on diagnosis results
        
        Args:
            diagnosis_result: AI diagnosis output
            available_products: List of available MAGSASA-CARD products
            
        Returns:
            List of recommended products with reasoning
        """
        try:
            # Build product recommendation prompt
            products_info = "\n".join([
                f"- {p.get('name', 'Unknown')}: {p.get('category', 'Unknown')} - {p.get('description', 'No description')}"
                for p in available_products[:10]  # Limit to top 10 products
            ])
            
            recommendation_prompt = f"""
Based on this agricultural diagnosis:
{json.dumps(diagnosis_result, indent=2)}

Available products:
{products_info}

Recommend the most suitable products for this farmer's situation. Return JSON format:
{{
    "recommendations": [
        {{
            "product_name": "exact product name",
            "category": "fertilizer|pesticide|seed|tool",
            "priority": "high|medium|low",
            "reasoning": "why this product is recommended",
            "quantity_estimate": "estimated amount needed",
            "timing": "when to use this product",
            "confidence": 0.85
        }}
    ]
}}
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an agricultural product recommendation expert."},
                    {"role": "user", "content": recommendation_prompt}
                ],
                max_tokens=400,
                temperature=0.5,
                response_format={"type": "json_object"}
            )
            
            recommendations = json.loads(response.choices[0].message.content)
            return recommendations.get("recommendations", [])
            
        except Exception as e:
            return [{
                "product_name": "Unable to recommend",
                "category": "error",
                "priority": "low",
                "reasoning": f"Recommendation error: {str(e)}",
                "quantity_estimate": "Unknown",
                "timing": "Unknown",
                "confidence": 0.0
            }]
    
    def test_connection(self) -> Dict:
        """Test OpenAI API connection and model availability"""
        if not self.client:
            return {
                "status": "disabled",
                "message": "OpenAI client not initialized (API key not provided)",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a test assistant."},
                    {"role": "user", "content": "Test connection. Respond with: Connection successful"}
                ],
                max_tokens=10
            )
            
            return {
                "status": "success",
                "model": self.model,
                "response": response.choices[0].message.content,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
