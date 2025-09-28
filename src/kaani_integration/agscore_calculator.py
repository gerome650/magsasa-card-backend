"""
AgScore Calculator for Farmer Risk Assessment
Implements 3-module scoring system for loan officer decision support
"""

import json
import sqlite3
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

class AgScoreCalculator:
    """Calculate AgScore (0-100) for farmer risk assessment"""
    
    def __init__(self, db_path: str = "src/database/dynamic_pricing.db"):
        """Initialize AgScore calculator with database connection"""
        self.db_path = db_path
        
        # Scoring weights (total = 100)
        self.weights = {
            "baseline_farm_profile": 40,    # Farm characteristics and experience
            "financial_history": 35,        # Repayment history and financial stability  
            "climate_sensor_data": 25       # Climate risk and adaptation
        }
        
        # Risk tier thresholds
        self.risk_tiers = {
            "A": {"min_score": 80, "description": "Low Risk", "color": "green"},
            "B": {"min_score": 60, "description": "Medium Risk", "color": "yellow"},
            "C": {"min_score": 0, "description": "High Risk", "color": "red"}
        }
    
    def calculate_agscore(self, farmer_id: str, assessment_data: Dict) -> Dict:
        """
        Calculate comprehensive AgScore for a farmer
        
        Args:
            farmer_id: Unique farmer identifier
            assessment_data: Dictionary containing assessment information
            
        Returns:
            Dictionary containing AgScore results and recommendations
        """
        try:
            # Calculate individual module scores
            baseline_score = self._calculate_baseline_farm_score(assessment_data.get("farm_profile", {}))
            financial_score = self._calculate_financial_score(assessment_data.get("financial_history", {}))
            climate_score = self._calculate_climate_score(assessment_data.get("climate_data", {}))
            
            # Calculate total AgScore
            total_score = baseline_score + financial_score + climate_score
            
            # Determine risk tier
            risk_tier = self._determine_risk_tier(total_score)
            
            # Generate loan recommendations
            loan_recommendations = self._generate_loan_recommendations(total_score, risk_tier)
            
            # Create comprehensive assessment result
            assessment_result = {
                "farmer_id": farmer_id,
                "assessment_id": f"AGS_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "scores": {
                    "baseline_farm_profile": baseline_score,
                    "financial_history": financial_score,
                    "climate_sensor_data": climate_score,
                    "total_agscore": total_score
                },
                "risk_assessment": {
                    "risk_tier": risk_tier,
                    "risk_description": self.risk_tiers[risk_tier]["description"],
                    "risk_color": self.risk_tiers[risk_tier]["color"]
                },
                "loan_recommendations": loan_recommendations,
                "assessment_breakdown": {
                    "farm_profile_details": self._get_farm_profile_breakdown(assessment_data.get("farm_profile", {})),
                    "financial_details": self._get_financial_breakdown(assessment_data.get("financial_history", {})),
                    "climate_details": self._get_climate_breakdown(assessment_data.get("climate_data", {}))
                },
                "bsp_compliance": {
                    "transparent_scoring": True,
                    "explainable_factors": self._get_scoring_explanation(baseline_score, financial_score, climate_score),
                    "audit_trail": {
                        "assessment_date": datetime.utcnow().isoformat(),
                        "scoring_version": "1.0.0",
                        "data_sources": ["farm_profile", "financial_history", "climate_data"]
                    }
                },
                "validity": {
                    "assessment_date": datetime.utcnow().isoformat(),
                    "valid_until": self._calculate_validity_date(),
                    "reassessment_recommended": self._get_reassessment_schedule(risk_tier)
                }
            }
            
            return assessment_result
            
        except Exception as e:
            return self._create_error_assessment(farmer_id, str(e))
    
    def _calculate_baseline_farm_score(self, farm_profile: Dict) -> int:
        """Calculate baseline farm profile score (0-40 points)"""
        score = 0
        
        # Farm size scoring (0-10 points)
        farm_size = farm_profile.get("size_hectares", 0)
        if farm_size >= 5:
            score += 10
        elif farm_size >= 2:
            score += 8
        elif farm_size >= 1:
            score += 6
        elif farm_size >= 0.5:
            score += 4
        else:
            score += 2
        
        # Soil quality scoring (0-8 points)
        soil_quality = farm_profile.get("soil_quality", "unknown").lower()
        soil_scores = {"excellent": 8, "good": 6, "fair": 4, "poor": 2, "unknown": 1}
        score += soil_scores.get(soil_quality, 1)
        
        # Irrigation access (0-6 points)
        irrigation = farm_profile.get("irrigation_access", False)
        score += 6 if irrigation else 2
        
        # Crop diversity (0-6 points)
        crop_diversity = farm_profile.get("crop_diversity", 1)
        if crop_diversity >= 4:
            score += 6
        elif crop_diversity >= 3:
            score += 5
        elif crop_diversity >= 2:
            score += 4
        else:
            score += 2
        
        # Farming experience (0-10 points)
        experience = farm_profile.get("farming_experience", 0)
        if experience >= 15:
            score += 10
        elif experience >= 10:
            score += 8
        elif experience >= 5:
            score += 6
        elif experience >= 2:
            score += 4
        else:
            score += 2
        
        return min(score, 40)  # Cap at maximum 40 points
    
    def _calculate_financial_score(self, financial_history: Dict) -> int:
        """Calculate financial history score (0-35 points)"""
        score = 0
        
        # Repayment rate scoring (0-15 points)
        repayment_rate = financial_history.get("repayment_rate", 0.0)
        if repayment_rate >= 0.95:
            score += 15
        elif repayment_rate >= 0.90:
            score += 12
        elif repayment_rate >= 0.80:
            score += 9
        elif repayment_rate >= 0.70:
            score += 6
        else:
            score += 2
        
        # Income stability (0-8 points)
        income_stability = financial_history.get("income_stability", "unknown").lower()
        stability_scores = {"very_stable": 8, "stable": 6, "moderate": 4, "unstable": 2, "unknown": 1}
        score += stability_scores.get(income_stability, 1)
        
        # Previous loans performance (0-7 points)
        previous_loans = financial_history.get("previous_loans", 0)
        if previous_loans >= 5:
            score += 7
        elif previous_loans >= 3:
            score += 5
        elif previous_loans >= 1:
            score += 3
        else:
            score += 1
        
        # Collateral value (0-5 points)
        collateral_value = financial_history.get("collateral_value", 0)
        if collateral_value >= 200000:
            score += 5
        elif collateral_value >= 100000:
            score += 4
        elif collateral_value >= 50000:
            score += 3
        elif collateral_value >= 25000:
            score += 2
        else:
            score += 1
        
        return min(score, 35)  # Cap at maximum 35 points
    
    def _calculate_climate_score(self, climate_data: Dict) -> int:
        """Calculate climate risk and adaptation score (0-25 points)"""
        score = 0
        
        # Flood risk (0-8 points, inverted - lower risk = higher score)
        flood_risk = climate_data.get("flood_risk", "high").lower()
        flood_scores = {"very_low": 8, "low": 6, "medium": 4, "high": 2, "very_high": 1}
        score += flood_scores.get(flood_risk, 2)
        
        # Drought risk (0-7 points, inverted)
        drought_risk = climate_data.get("drought_risk", "high").lower()
        drought_scores = {"very_low": 7, "low": 5, "medium": 3, "high": 2, "very_high": 1}
        score += drought_scores.get(drought_risk, 2)
        
        # Typhoon exposure (0-5 points, inverted)
        typhoon_risk = climate_data.get("typhoon_exposure", "high").lower()
        typhoon_scores = {"very_low": 5, "low": 4, "medium": 3, "high": 2, "very_high": 1}
        score += typhoon_scores.get(typhoon_risk, 2)
        
        # Climate adaptation measures (0-5 points)
        adaptation = climate_data.get("climate_adaptation", "poor").lower()
        adaptation_scores = {"excellent": 5, "good": 4, "fair": 3, "poor": 2, "none": 1}
        score += adaptation_scores.get(adaptation, 2)
        
        return min(score, 25)  # Cap at maximum 25 points
    
    def _determine_risk_tier(self, total_score: int) -> str:
        """Determine risk tier based on total AgScore"""
        if total_score >= 80:
            return "A"
        elif total_score >= 60:
            return "B"
        else:
            return "C"
    
    def _generate_loan_recommendations(self, total_score: int, risk_tier: str) -> Dict:
        """Generate loan recommendations based on AgScore and risk tier"""
        
        # Base recommendations by risk tier
        tier_recommendations = {
            "A": {
                "max_loan_amount": 100000,
                "interest_rate": 0.12,  # 12% annual
                "repayment_period_months": 12,
                "collateral_requirement": "minimal",
                "approval_probability": "high"
            },
            "B": {
                "max_loan_amount": 50000,
                "interest_rate": 0.15,  # 15% annual
                "repayment_period_months": 9,
                "collateral_requirement": "moderate",
                "approval_probability": "medium"
            },
            "C": {
                "max_loan_amount": 25000,
                "interest_rate": 0.18,  # 18% annual
                "repayment_period_months": 6,
                "collateral_requirement": "high",
                "approval_probability": "low"
            }
        }
        
        base_rec = tier_recommendations[risk_tier]
        
        # Adjust based on specific score within tier
        score_adjustment = (total_score % 20) / 20  # 0.0 to 1.0 within tier
        
        adjusted_recommendations = {
            "max_loan_amount": int(base_rec["max_loan_amount"] * (0.8 + 0.4 * score_adjustment)),
            "interest_rate": base_rec["interest_rate"] * (1.1 - 0.2 * score_adjustment),
            "repayment_period_months": base_rec["repayment_period_months"],
            "collateral_requirement": base_rec["collateral_requirement"],
            "approval_probability": base_rec["approval_probability"],
            "special_conditions": self._get_special_conditions(total_score, risk_tier),
            "input_package_tier": self._recommend_input_package(risk_tier)
        }
        
        return adjusted_recommendations
    
    def _get_special_conditions(self, score: int, tier: str) -> List[str]:
        """Get special loan conditions based on score and tier"""
        conditions = []
        
        if tier == "A":
            conditions.append("Eligible for premium input packages")
            conditions.append("Fast-track approval process")
            if score >= 90:
                conditions.append("Eligible for unsecured loans up to ₱50,000")
        elif tier == "B":
            conditions.append("Standard input packages recommended")
            conditions.append("Regular monitoring required")
            if score >= 70:
                conditions.append("Eligible for seasonal loan extensions")
        else:  # tier == "C"
            conditions.append("Basic input packages only")
            conditions.append("Enhanced monitoring and support required")
            conditions.append("Mandatory agricultural training participation")
            if score < 40:
                conditions.append("Co-signer or group guarantee required")
        
        return conditions
    
    def _recommend_input_package(self, risk_tier: str) -> str:
        """Recommend input package based on risk tier"""
        packages = {
            "A": "Premium Package - Full agricultural inputs with advanced options",
            "B": "Growth Package - Standard inputs with moderate options", 
            "C": "Basic Package - Essential inputs with basic options"
        }
        return packages[risk_tier]
    
    def _get_farm_profile_breakdown(self, farm_profile: Dict) -> Dict:
        """Get detailed breakdown of farm profile scoring"""
        return {
            "farm_size": f"{farm_profile.get('size_hectares', 0)} hectares",
            "soil_quality": farm_profile.get('soil_quality', 'Unknown'),
            "irrigation_access": "Yes" if farm_profile.get('irrigation_access') else "No",
            "crop_diversity": f"{farm_profile.get('crop_diversity', 1)} different crops",
            "farming_experience": f"{farm_profile.get('farming_experience', 0)} years"
        }
    
    def _get_financial_breakdown(self, financial_history: Dict) -> Dict:
        """Get detailed breakdown of financial scoring"""
        return {
            "repayment_rate": f"{financial_history.get('repayment_rate', 0)*100:.1f}%",
            "income_stability": financial_history.get('income_stability', 'Unknown'),
            "previous_loans": f"{financial_history.get('previous_loans', 0)} loans",
            "collateral_value": f"₱{financial_history.get('collateral_value', 0):,}"
        }
    
    def _get_climate_breakdown(self, climate_data: Dict) -> Dict:
        """Get detailed breakdown of climate scoring"""
        return {
            "flood_risk": climate_data.get('flood_risk', 'Unknown'),
            "drought_risk": climate_data.get('drought_risk', 'Unknown'),
            "typhoon_exposure": climate_data.get('typhoon_exposure', 'Unknown'),
            "climate_adaptation": climate_data.get('climate_adaptation', 'Unknown')
        }
    
    def _get_scoring_explanation(self, baseline: int, financial: int, climate: int) -> List[str]:
        """Get explanation of scoring factors for BSP compliance"""
        explanations = []
        
        explanations.append(f"Farm Profile Score: {baseline}/40 - Based on farm size, soil quality, irrigation, crop diversity, and experience")
        explanations.append(f"Financial History Score: {financial}/35 - Based on repayment rate, income stability, loan history, and collateral")
        explanations.append(f"Climate Risk Score: {climate}/25 - Based on flood, drought, typhoon risks and adaptation measures")
        
        total = baseline + financial + climate
        explanations.append(f"Total AgScore: {total}/100 - Weighted combination of all factors")
        
        return explanations
    
    def _calculate_validity_date(self) -> str:
        """Calculate assessment validity expiration date"""
        # AgScore assessments valid for 6 months
        from datetime import timedelta
        validity_date = datetime.utcnow() + timedelta(days=180)
        return validity_date.isoformat()
    
    def _get_reassessment_schedule(self, risk_tier: str) -> str:
        """Get recommended reassessment schedule based on risk tier"""
        schedules = {
            "A": "Annual reassessment recommended",
            "B": "Semi-annual reassessment recommended", 
            "C": "Quarterly reassessment required"
        }
        return schedules[risk_tier]
    
    def _create_error_assessment(self, farmer_id: str, error_message: str) -> Dict:
        """Create error assessment response"""
        return {
            "farmer_id": farmer_id,
            "assessment_id": f"ERROR_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "error": True,
            "error_message": error_message,
            "scores": {
                "baseline_farm_profile": 0,
                "financial_history": 0,
                "climate_sensor_data": 0,
                "total_agscore": 0
            },
            "risk_assessment": {
                "risk_tier": "C",
                "risk_description": "Unable to assess - Error occurred",
                "risk_color": "red"
            },
            "loan_recommendations": {
                "max_loan_amount": 0,
                "interest_rate": 0.20,
                "repayment_period_months": 3,
                "approval_probability": "denied",
                "special_conditions": ["Assessment error - manual review required"]
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def save_assessment_to_db(self, assessment_result: Dict) -> bool:
        """Save AgScore assessment to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insert assessment record
            cursor.execute("""
                INSERT INTO agscore_assessments (
                    assessment_id, farmer_id, baseline_farm_score, financial_history_score,
                    climate_risk_score, total_agscore, risk_tier, risk_description,
                    max_loan_amount, recommended_interest_rate, repayment_period_months,
                    assessment_data, assessment_notes, bsp_compliance_data, audit_trail,
                    status, valid_until, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                assessment_result["assessment_id"],
                assessment_result["farmer_id"],
                assessment_result["scores"]["baseline_farm_profile"],
                assessment_result["scores"]["financial_history"],
                assessment_result["scores"]["climate_sensor_data"],
                assessment_result["scores"]["total_agscore"],
                assessment_result["risk_assessment"]["risk_tier"],
                assessment_result["risk_assessment"]["risk_description"],
                assessment_result["loan_recommendations"]["max_loan_amount"],
                assessment_result["loan_recommendations"]["interest_rate"],
                assessment_result["loan_recommendations"]["repayment_period_months"],
                json.dumps(assessment_result["assessment_breakdown"]),
                json.dumps(assessment_result["loan_recommendations"]["special_conditions"]),
                json.dumps(assessment_result["bsp_compliance"]),
                json.dumps(assessment_result["bsp_compliance"]["audit_trail"]),
                "active",
                assessment_result["validity"]["valid_until"],
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Database save error: {e}")
            return False
