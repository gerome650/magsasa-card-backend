"""
KaAni Diagnosis Engine
Main coordinator for agricultural diagnosis and product recommendations
"""

import json
import sqlite3
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from .openai_provider import OpenAIProvider
from .agscore_calculator import AgScoreCalculator

class DiagnosisEngine:
    """Main engine for KaAni agricultural diagnosis and recommendations"""
    
    def __init__(self, db_path: str = "src/database/dynamic_pricing.db"):
        """Initialize diagnosis engine with AI providers and database"""
        self.db_path = db_path
        self.openai_provider = OpenAIProvider()
        self.agscore_calculator = AgScoreCalculator(db_path)
        
        # Supported diagnosis modes
        self.diagnosis_modes = {
            "quick": {
                "description": "Short direct actionable response",
                "max_response_time": 10,  # seconds
                "detail_level": "basic"
            },
            "regular": {
                "description": "Comprehensive analysis with detailed recommendations",
                "max_response_time": 30,  # seconds
                "detail_level": "comprehensive"
            }
        }
        
        # Agricultural topics covered
        self.agricultural_topics = [
            "soil_climate",
            "pests", 
            "disease",
            "fertilization"
        ]
    
    def perform_diagnosis(self, farmer_input: Dict, diagnosis_mode: str = "regular") -> Dict:
        """
        Perform complete agricultural diagnosis
        
        Args:
            farmer_input: Farmer's problem description and context
            diagnosis_mode: "quick" or "regular" diagnosis
            
        Returns:
            Complete diagnosis results with recommendations
        """
        try:
            # Generate unique session ID
            session_id = f"DIAG_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
            
            # Validate input
            if not self._validate_farmer_input(farmer_input):
                return self._create_error_response(session_id, "Invalid farmer input data")
            
            # Get AI diagnosis from OpenAI
            ai_diagnosis = self.openai_provider.diagnose_agricultural_issue(farmer_input, diagnosis_mode)
            
            # Get available products for recommendations
            available_products = self._get_available_products()
            
            # Generate product recommendations
            product_recommendations = self.openai_provider.generate_product_recommendations(
                ai_diagnosis, available_products
            )
            
            # Match recommendations to actual products
            matched_products = self._match_products_to_recommendations(
                product_recommendations, available_products
            )
            
            # Get seasonal guidance
            seasonal_guidance = self._get_seasonal_guidance(farmer_input)
            
            # Create comprehensive diagnosis response
            diagnosis_response = {
                "session_id": session_id,
                "farmer_input": farmer_input,
                "diagnosis_mode": diagnosis_mode,
                "ai_analysis": ai_diagnosis,
                "product_recommendations": matched_products,
                "seasonal_guidance": seasonal_guidance,
                "follow_up": {
                    "recommended_check_days": ai_diagnosis.get("follow_up_days", 7),
                    "monitoring_points": self._get_monitoring_points(ai_diagnosis),
                    "emergency_contacts": self._get_emergency_contacts(farmer_input)
                },
                "metadata": {
                    "diagnosis_timestamp": datetime.utcnow().isoformat(),
                    "ai_provider": "openai",
                    "confidence_overall": ai_diagnosis.get("overall_confidence", 0.0),
                    "processing_time_seconds": None,  # To be calculated
                    "version": "1.0.0"
                }
            }
            
            # Save diagnosis to database
            self._save_diagnosis_session(diagnosis_response)
            
            return diagnosis_response
            
        except Exception as e:
            return self._create_error_response(session_id, f"Diagnosis error: {str(e)}")
    
    def calculate_farmer_agscore(self, farmer_id: str, assessment_data: Dict) -> Dict:
        """
        Calculate AgScore for farmer risk assessment
        
        Args:
            farmer_id: Unique farmer identifier
            assessment_data: Assessment data for scoring
            
        Returns:
            AgScore results and loan recommendations
        """
        try:
            # Calculate AgScore using the calculator
            agscore_result = self.agscore_calculator.calculate_agscore(farmer_id, assessment_data)
            
            # Save assessment to database
            self.agscore_calculator.save_assessment_to_db(agscore_result)
            
            return agscore_result
            
        except Exception as e:
            return {
                "error": True,
                "error_message": f"AgScore calculation error: {str(e)}",
                "farmer_id": farmer_id,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def get_farmer_recommendations(self, farmer_id: str, include_seasonal: bool = True) -> Dict:
        """
        Get personalized product recommendations for a farmer
        
        Args:
            farmer_id: Unique farmer identifier
            include_seasonal: Include seasonal guidance
            
        Returns:
            Personalized recommendations based on farmer profile and history
        """
        try:
            # Get farmer profile
            farmer_profile = self._get_farmer_profile(farmer_id)
            if not farmer_profile:
                return {"error": "Farmer profile not found"}
            
            # Get recent diagnosis sessions
            recent_diagnoses = self._get_recent_diagnoses(farmer_id, limit=3)
            
            # Get available products
            available_products = self._get_available_products()
            
            # Generate recommendations based on profile and history
            recommendations = self._generate_personalized_recommendations(
                farmer_profile, recent_diagnoses, available_products
            )
            
            # Add seasonal guidance if requested
            seasonal_info = None
            if include_seasonal:
                seasonal_info = self._get_seasonal_guidance_for_farmer(farmer_profile)
            
            return {
                "farmer_id": farmer_id,
                "recommendations": recommendations,
                "seasonal_guidance": seasonal_info,
                "based_on": {
                    "profile_data": True,
                    "diagnosis_history": len(recent_diagnoses) > 0,
                    "seasonal_data": include_seasonal
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "error": True,
                "error_message": f"Recommendation error: {str(e)}",
                "farmer_id": farmer_id
            }
    
    def _validate_farmer_input(self, farmer_input: Dict) -> bool:
        """Validate farmer input data"""
        required_fields = ["farmer_id"]
        
        # Check required fields
        for field in required_fields:
            if field not in farmer_input:
                return False
        
        # Validate farmer_id format
        farmer_id = farmer_input.get("farmer_id", "")
        if not farmer_id or len(farmer_id) < 5:
            return False
        
        return True
    
    def _get_available_products(self) -> List[Dict]:
        """Get available products from MAGSASA-CARD catalog"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, name, category, brand, package_size, 
                       wholesale_price, retail_price, description,
                       crop_suitability, application_method, application_rate
                FROM agricultural_inputs 
                WHERE is_active = 1
                ORDER BY category, name
            """)
            
            products = []
            for row in cursor.fetchall():
                products.append({
                    "id": row["id"],
                    "name": row["name"],
                    "category": row["category"],
                    "brand": row["brand"],
                    "package_size": row["package_size"],
                    "wholesale_price": row["wholesale_price"],
                    "retail_price": row["retail_price"],
                    "description": row["description"] or f"{row['brand']} {row['name']}",
                    "crop_suitability": json.loads(row["crop_suitability"] or "[]"),
                    "application_method": row["application_method"],
                    "application_rate": row["application_rate"]
                })
            
            conn.close()
            return products
            
        except Exception as e:
            print(f"Error getting products: {e}")
            return []
    
    def _match_products_to_recommendations(self, ai_recommendations: List[Dict], available_products: List[Dict]) -> List[Dict]:
        """Match AI recommendations to actual MAGSASA-CARD products"""
        matched_products = []
        
        for recommendation in ai_recommendations:
            # Find matching products
            matches = []
            rec_name = recommendation.get("product_name", "").lower()
            rec_category = recommendation.get("category", "").lower()
            
            for product in available_products:
                product_name = product["name"].lower()
                product_category = product["category"].lower()
                
                # Check for name similarity or category match
                if (rec_name in product_name or product_name in rec_name or 
                    rec_category == product_category):
                    matches.append(product)
            
            # Select best match or use first available product in category
            if matches:
                best_match = matches[0]  # Simple selection - could be improved
                
                matched_products.append({
                    "product_id": best_match["id"],
                    "product_name": best_match["name"],
                    "category": best_match["category"],
                    "brand": best_match["brand"],
                    "package_size": best_match["package_size"],
                    "retail_price": best_match["retail_price"],
                    "ai_recommendation": recommendation,
                    "match_confidence": 0.8,  # Could be calculated based on similarity
                    "estimated_quantity": recommendation.get("quantity_estimate", "As needed"),
                    "application_timing": recommendation.get("timing", "As recommended"),
                    "priority": recommendation.get("priority", "medium")
                })
        
        return matched_products
    
    def _get_seasonal_guidance(self, farmer_input: Dict) -> Optional[Dict]:
        """Get seasonal guidance based on farmer location"""
        try:
            location = farmer_input.get("location", {})
            province = location.get("province")
            municipality = location.get("municipality")
            
            if not province:
                return None
            
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get current month guidance
            current_month = datetime.now().month
            
            cursor.execute("""
                SELECT * FROM seasonal_guidance 
                WHERE province = ? AND (municipality = ? OR municipality IS NULL)
                AND month = ?
                ORDER BY municipality DESC
                LIMIT 1
            """, (province, municipality, current_month))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    "province": row["province"],
                    "municipality": row["municipality"],
                    "month": row["month"],
                    "season": row["season"],
                    "temperature": row["avg_temperature_celsius"],
                    "rainfall": row["avg_rainfall_mm"],
                    "recommended_activities": json.loads(row["recommended_activities"] or "[]"),
                    "pest_disease_alerts": json.loads(row["pest_disease_alerts"] or "[]"),
                    "flood_risk": row["flood_risk_level"],
                    "drought_risk": row["drought_risk_level"],
                    "typhoon_risk": row["typhoon_risk_level"]
                }
            
            return None
            
        except Exception as e:
            print(f"Error getting seasonal guidance: {e}")
            return None
    
    def _get_monitoring_points(self, ai_diagnosis: Dict) -> List[str]:
        """Extract monitoring points from AI diagnosis"""
        monitoring_points = []
        
        # Extract from each topic
        for topic in self.agricultural_topics:
            topic_data = ai_diagnosis.get(topic, {})
            if topic == "soil_climate":
                monitoring_points.append("Monitor soil moisture and drainage")
            elif topic == "pests":
                if topic_data.get("risk_level") in ["medium", "high"]:
                    monitoring_points.append("Check for pest presence weekly")
            elif topic == "disease":
                if topic_data.get("likely_diseases"):
                    monitoring_points.append("Monitor for disease symptoms")
            elif topic == "fertilization":
                monitoring_points.append("Track plant response to fertilizer application")
        
        return monitoring_points or ["Monitor general plant health and growth"]
    
    def _get_emergency_contacts(self, farmer_input: Dict) -> List[Dict]:
        """Get emergency agricultural contacts based on location"""
        # This would typically come from a database of agricultural extension offices
        location = farmer_input.get("location", {})
        province = location.get("province", "Philippines")
        
        return [
            {
                "type": "Agricultural Extension Office",
                "name": f"{province} Agricultural Office",
                "phone": "Available through local government",
                "services": ["Emergency consultation", "Pest outbreak response"]
            },
            {
                "type": "CARD MRI Support",
                "name": "CARD MRI Agricultural Support",
                "phone": "Available through CARD centers",
                "services": ["Input supply", "Technical assistance"]
            }
        ]
    
    def _save_diagnosis_session(self, diagnosis_response: Dict) -> bool:
        """Save diagnosis session to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO diagnosis_sessions (
                    session_id, farmer_id, diagnosis_mode, ai_provider, language_preference,
                    farmer_input, soil_climate_analysis, pest_assessment, disease_evaluation,
                    fertilization_plan, diagnosis_summary, confidence_score, processing_time_seconds,
                    status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                diagnosis_response["session_id"],
                diagnosis_response["farmer_input"]["farmer_id"],
                diagnosis_response["diagnosis_mode"],
                diagnosis_response["metadata"]["ai_provider"],
                diagnosis_response["farmer_input"].get("language_preference", "english"),
                json.dumps(diagnosis_response["farmer_input"]),
                json.dumps(diagnosis_response["ai_analysis"].get("soil_climate", {})),
                json.dumps(diagnosis_response["ai_analysis"].get("pests", {})),
                json.dumps(diagnosis_response["ai_analysis"].get("disease", {})),
                json.dumps(diagnosis_response["ai_analysis"].get("fertilization", {})),
                json.dumps(diagnosis_response["ai_analysis"]),
                diagnosis_response["metadata"]["confidence_overall"],
                diagnosis_response["metadata"]["processing_time_seconds"],
                "completed",
                datetime.utcnow().isoformat()
            ))
            
            # Save product recommendations
            for rec in diagnosis_response["product_recommendations"]:
                cursor.execute("""
                    INSERT INTO kaani_recommendations (
                        recommendation_id, session_id, product_category, product_name,
                        recommended_quantity, quantity_unit, priority_level, reasoning,
                        seasonal_timing, estimated_cost, magsasa_product_id, confidence_score,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"REC_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{rec.get('product_id', 0)}",
                    diagnosis_response["session_id"],
                    rec.get("category", "unknown"),
                    rec.get("product_name", "Unknown"),
                    rec.get("estimated_quantity", "As needed"),
                    "units",
                    rec.get("priority", "medium"),
                    rec.get("ai_recommendation", {}).get("reasoning", "AI recommended"),
                    rec.get("application_timing", "As needed"),
                    rec.get("retail_price", 0),
                    rec.get("product_id"),
                    rec.get("match_confidence", 0.5),
                    datetime.utcnow().isoformat()
                ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error saving diagnosis session: {e}")
            return False
    
    def _get_farmer_profile(self, farmer_id: str) -> Optional[Dict]:
        """Get farmer profile from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM farmer_profiles WHERE farmer_id = ?
            """, (farmer_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return dict(row)
            return None
            
        except Exception as e:
            print(f"Error getting farmer profile: {e}")
            return None
    
    def _get_recent_diagnoses(self, farmer_id: str, limit: int = 3) -> List[Dict]:
        """Get recent diagnosis sessions for farmer"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM diagnosis_sessions 
                WHERE farmer_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (farmer_id, limit))
            
            diagnoses = []
            for row in cursor.fetchall():
                diagnoses.append(dict(row))
            
            conn.close()
            return diagnoses
            
        except Exception as e:
            print(f"Error getting recent diagnoses: {e}")
            return []
    
    def _generate_personalized_recommendations(self, farmer_profile: Dict, recent_diagnoses: List[Dict], available_products: List[Dict]) -> List[Dict]:
        """Generate personalized recommendations based on farmer history"""
        # This is a simplified implementation - could be enhanced with ML
        recommendations = []
        
        # Get farmer's primary crops
        primary_crops = json.loads(farmer_profile.get("primary_crops", "[]"))
        
        # Filter products suitable for farmer's crops
        suitable_products = []
        for product in available_products:
            crop_suitability = product.get("crop_suitability", [])
            if any(crop.lower() in [c.lower() for c in crop_suitability] for crop in primary_crops):
                suitable_products.append(product)
        
        # Add top 3 suitable products as recommendations
        for product in suitable_products[:3]:
            recommendations.append({
                "product_id": product["id"],
                "product_name": product["name"],
                "category": product["category"],
                "reasoning": f"Suitable for {', '.join(primary_crops)} cultivation",
                "priority": "medium",
                "estimated_cost": product["retail_price"],
                "recommendation_source": "farmer_profile_match"
            })
        
        return recommendations
    
    def _get_seasonal_guidance_for_farmer(self, farmer_profile: Dict) -> Optional[Dict]:
        """Get seasonal guidance specific to farmer's location"""
        province = farmer_profile.get("province")
        municipality = farmer_profile.get("municipality")
        
        if province:
            return self._get_seasonal_guidance({
                "location": {
                    "province": province,
                    "municipality": municipality
                }
            })
        return None
    
    def _create_error_response(self, session_id: str, error_message: str) -> Dict:
        """Create standardized error response"""
        return {
            "session_id": session_id,
            "error": True,
            "error_message": error_message,
            "ai_analysis": {
                "error": True,
                "overall_confidence": 0.0
            },
            "product_recommendations": [],
            "seasonal_guidance": None,
            "timestamp": datetime.utcnow().isoformat()
        }
