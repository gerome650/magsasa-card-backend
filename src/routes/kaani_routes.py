"""
KaAni API Routes
Agricultural Diagnosis and Risk Assessment Endpoints
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import json
import sqlite3

# Import KaAni integration modules
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from kaani_integration.diagnosis_engine import DiagnosisEngine
from kaani_integration.openai_provider import OpenAIProvider
from kaani_integration.agscore_calculator import AgScoreCalculator

# Create blueprint
kaani_bp = Blueprint('kaani', __name__)

# Initialize KaAni components
diagnosis_engine = DiagnosisEngine()
openai_provider = OpenAIProvider()
agscore_calculator = AgScoreCalculator()

# Database connection helper
def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect('src/database/dynamic_pricing.db')
    conn.row_factory = sqlite3.Row
    return conn

# =====================================================
# KAANI DIAGNOSIS ENDPOINTS
# =====================================================

@kaani_bp.route('/api/kaani/health', methods=['GET'])
def kaani_health_check():
    """KaAni system health check"""
    try:
        # Test OpenAI connection
        openai_test = openai_provider.test_connection()
        
        # Test database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM farmer_profiles")
        farmer_count = cursor.fetchone()["count"]
        cursor.execute("SELECT COUNT(*) as count FROM diagnosis_sessions")
        diagnosis_count = cursor.fetchone()["count"]
        conn.close()
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "openai_provider": openai_test["status"],
                "database": "connected",
                "diagnosis_engine": "operational"
            },
            "statistics": {
                "total_farmers": farmer_count,
                "total_diagnoses": diagnosis_count
            },
            "features": [
                "agricultural_diagnosis",
                "agscore_risk_assessment", 
                "product_recommendations",
                "seasonal_guidance",
                "ab_testing_framework"
            ]
        })
        
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

@kaani_bp.route('/api/kaani/quick-diagnosis', methods=['POST'])
def quick_diagnosis():
    """Perform quick agricultural diagnosis (short response)"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or 'farmer_id' not in data:
            return jsonify({
                "error": "farmer_id is required"
            }), 400
        
        # Perform quick diagnosis
        diagnosis_result = diagnosis_engine.perform_diagnosis(data, diagnosis_mode="quick")
        
        if diagnosis_result.get("error"):
            return jsonify(diagnosis_result), 500
        
        # Return simplified response for quick mode
        return jsonify({
            "session_id": diagnosis_result["session_id"],
            "diagnosis_mode": "quick",
            "quick_recommendations": {
                "priority_actions": diagnosis_result["ai_analysis"].get("priority_actions", []),
                "confidence": diagnosis_result["metadata"]["confidence_overall"],
                "follow_up_days": diagnosis_result["follow_up"]["recommended_check_days"]
            },
            "top_products": diagnosis_result["product_recommendations"][:2],  # Top 2 products
            "timestamp": diagnosis_result["metadata"]["diagnosis_timestamp"]
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Quick diagnosis failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }), 500

@kaani_bp.route('/api/kaani/regular-diagnosis', methods=['POST'])
def regular_diagnosis():
    """Perform comprehensive agricultural diagnosis"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or 'farmer_id' not in data:
            return jsonify({
                "error": "farmer_id is required"
            }), 400
        
        # Perform comprehensive diagnosis
        diagnosis_result = diagnosis_engine.perform_diagnosis(data, diagnosis_mode="regular")
        
        if diagnosis_result.get("error"):
            return jsonify(diagnosis_result), 500
        
        return jsonify(diagnosis_result)
        
    except Exception as e:
        return jsonify({
            "error": f"Regular diagnosis failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }), 500

@kaani_bp.route('/api/kaani/diagnosis/<session_id>', methods=['GET'])
def get_diagnosis_session(session_id):
    """Retrieve diagnosis session by ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get diagnosis session
        cursor.execute("""
            SELECT * FROM diagnosis_sessions WHERE session_id = ?
        """, (session_id,))
        
        session = cursor.fetchone()
        if not session:
            conn.close()
            return jsonify({"error": "Diagnosis session not found"}), 404
        
        # Get recommendations for this session
        cursor.execute("""
            SELECT * FROM kaani_recommendations WHERE session_id = ?
        """, (session_id,))
        
        recommendations = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # Build response
        response = {
            "session_id": session["session_id"],
            "farmer_id": session["farmer_id"],
            "diagnosis_mode": session["diagnosis_mode"],
            "ai_provider": session["ai_provider"],
            "farmer_input": json.loads(session["farmer_input"]),
            "ai_analysis": {
                "soil_climate": json.loads(session["soil_climate_analysis"]),
                "pests": json.loads(session["pest_assessment"]),
                "disease": json.loads(session["disease_evaluation"]),
                "fertilization": json.loads(session["fertilization_plan"]),
                "overall_confidence": session["confidence_score"]
            },
            "product_recommendations": recommendations,
            "created_at": session["created_at"],
            "status": session["status"]
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to retrieve diagnosis: {str(e)}"
        }), 500

# =====================================================
# AGSCORE RISK ASSESSMENT ENDPOINTS
# =====================================================

@kaani_bp.route('/api/agscore/assess-farmer', methods=['POST'])
def assess_farmer_agscore():
    """Calculate AgScore for farmer risk assessment"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or 'farmer_id' not in data or 'assessment_data' not in data:
            return jsonify({
                "error": "farmer_id and assessment_data are required"
            }), 400
        
        farmer_id = data['farmer_id']
        assessment_data = data['assessment_data']
        
        # Calculate AgScore
        agscore_result = diagnosis_engine.calculate_farmer_agscore(farmer_id, assessment_data)
        
        if agscore_result.get("error"):
            return jsonify(agscore_result), 500
        
        return jsonify(agscore_result)
        
    except Exception as e:
        return jsonify({
            "error": f"AgScore assessment failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }), 500

@kaani_bp.route('/api/agscore/farmer/<farmer_id>', methods=['GET'])
def get_farmer_agscore(farmer_id):
    """Get latest AgScore assessment for farmer"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get latest assessment
        cursor.execute("""
            SELECT * FROM agscore_assessments 
            WHERE farmer_id = ? AND status = 'active'
            ORDER BY created_at DESC 
            LIMIT 1
        """, (farmer_id,))
        
        assessment = cursor.fetchone()
        conn.close()
        
        if not assessment:
            return jsonify({
                "error": "No AgScore assessment found for farmer"
            }), 404
        
        # Build response
        response = {
            "assessment_id": assessment["assessment_id"],
            "farmer_id": assessment["farmer_id"],
            "scores": {
                "baseline_farm_profile": assessment["baseline_farm_score"],
                "financial_history": assessment["financial_history_score"],
                "climate_risk": assessment["climate_risk_score"],
                "total_agscore": assessment["total_agscore"]
            },
            "risk_assessment": {
                "risk_tier": assessment["risk_tier"],
                "risk_description": assessment["risk_description"]
            },
            "loan_recommendations": {
                "max_loan_amount": assessment["max_loan_amount"],
                "interest_rate": assessment["recommended_interest_rate"],
                "repayment_period_months": assessment["repayment_period_months"]
            },
            "assessment_date": assessment["created_at"],
            "valid_until": assessment["valid_until"],
            "status": assessment["status"]
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to retrieve AgScore: {str(e)}"
        }), 500

@kaani_bp.route('/api/agscore/risk-tier/<farmer_id>', methods=['GET'])
def get_farmer_risk_tier(farmer_id):
    """Get farmer's current risk tier (A/B/C)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT risk_tier, risk_description, total_agscore, created_at
            FROM agscore_assessments 
            WHERE farmer_id = ? AND status = 'active'
            ORDER BY created_at DESC 
            LIMIT 1
        """, (farmer_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return jsonify({
                "error": "No risk assessment found for farmer"
            }), 404
        
        return jsonify({
            "farmer_id": farmer_id,
            "risk_tier": result["risk_tier"],
            "risk_description": result["risk_description"],
            "agscore": result["total_agscore"],
            "assessment_date": result["created_at"]
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to retrieve risk tier: {str(e)}"
        }), 500

# =====================================================
# PRODUCT RECOMMENDATION ENDPOINTS
# =====================================================

@kaani_bp.route('/api/products/kaani-recommended/<farmer_id>', methods=['GET'])
def get_kaani_recommended_products(farmer_id):
    """Get KaAni AI-recommended products for farmer"""
    try:
        # Get personalized recommendations
        recommendations = diagnosis_engine.get_farmer_recommendations(farmer_id)
        
        if recommendations.get("error"):
            return jsonify(recommendations), 404
        
        return jsonify(recommendations)
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to get recommendations: {str(e)}"
        }), 500

@kaani_bp.route('/api/products/match-diagnosis', methods=['POST'])
def match_products_to_diagnosis():
    """Match products to specific diagnosis results"""
    try:
        data = request.get_json()
        
        if not data or 'session_id' not in data:
            return jsonify({
                "error": "session_id is required"
            }), 400
        
        session_id = data['session_id']
        
        # Get diagnosis session
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM diagnosis_sessions WHERE session_id = ?
        """, (session_id,))
        
        session = cursor.fetchone()
        if not session:
            conn.close()
            return jsonify({"error": "Diagnosis session not found"}), 404
        
        # Get existing recommendations
        cursor.execute("""
            SELECT kr.*, ai.name, ai.retail_price, ai.brand, ai.package_size
            FROM kaani_recommendations kr
            LEFT JOIN agricultural_inputs ai ON kr.magsasa_product_id = ai.id
            WHERE kr.session_id = ?
            ORDER BY 
                CASE kr.priority_level 
                    WHEN 'high' THEN 1 
                    WHEN 'medium' THEN 2 
                    WHEN 'low' THEN 3 
                END
        """, (session_id,))
        
        recommendations = []
        for row in cursor.fetchall():
            recommendations.append({
                "recommendation_id": row["recommendation_id"],
                "product_name": row["name"] or row["product_name"],
                "category": row["product_category"],
                "brand": row["brand"],
                "package_size": row["package_size"],
                "priority": row["priority_level"],
                "reasoning": row["reasoning"],
                "estimated_quantity": row["recommended_quantity"],
                "timing": row["seasonal_timing"],
                "estimated_cost": row["retail_price"] or row["estimated_cost"],
                "confidence": row["confidence_score"]
            })
        
        conn.close()
        
        return jsonify({
            "session_id": session_id,
            "matched_products": recommendations,
            "total_recommendations": len(recommendations)
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to match products: {str(e)}"
        }), 500

# =====================================================
# FARMER PROFILE ENDPOINTS
# =====================================================

@kaani_bp.route('/api/farmers/profile/<farmer_id>', methods=['GET'])
def get_farmer_profile(farmer_id):
    """Get farmer profile information"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM farmer_profiles WHERE farmer_id = ?
        """, (farmer_id,))
        
        profile = cursor.fetchone()
        conn.close()
        
        if not profile:
            return jsonify({
                "error": "Farmer profile not found"
            }), 404
        
        # Build response (excluding sensitive information)
        response = {
            "farmer_id": profile["farmer_id"],
            "first_name": profile["first_name"],
            "last_name": profile["last_name"],
            "location": {
                "province": profile["province"],
                "municipality": profile["municipality"],
                "barangay": profile["barangay"]
            },
            "farm_info": {
                "size_hectares": profile["farm_size_hectares"],
                "primary_crops": json.loads(profile["primary_crops"] or "[]"),
                "soil_type": profile["soil_type"],
                "irrigation_type": profile["irrigation_type"],
                "farming_experience_years": profile["farming_experience_years"]
            },
            "card_membership": {
                "is_member": bool(profile["is_card_member"]),
                "member_since": profile["membership_date"]
            },
            "profile_status": {
                "completeness": profile["profile_completeness"],
                "verification_status": profile["verification_status"]
            },
            "created_at": profile["created_at"],
            "updated_at": profile["updated_at"]
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to retrieve farmer profile: {str(e)}"
        }), 500

@kaani_bp.route('/api/farmers/profile', methods=['POST'])
def create_farmer_profile():
    """Create new farmer profile"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['farmer_id', 'first_name', 'last_name']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "error": f"{field} is required"
                }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if farmer already exists
        cursor.execute("""
            SELECT farmer_id FROM farmer_profiles WHERE farmer_id = ?
        """, (data['farmer_id'],))
        
        if cursor.fetchone():
            conn.close()
            return jsonify({
                "error": "Farmer profile already exists"
            }), 409
        
        # Insert new farmer profile
        cursor.execute("""
            INSERT INTO farmer_profiles (
                farmer_id, first_name, last_name, phone_number, email,
                province, municipality, barangay, latitude, longitude,
                farm_size_hectares, primary_crops, soil_type, irrigation_type,
                farming_experience_years, is_card_member, card_member_id,
                profile_completeness, verification_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['farmer_id'],
            data['first_name'],
            data['last_name'],
            data.get('phone_number'),
            data.get('email'),
            data.get('province'),
            data.get('municipality'),
            data.get('barangay'),
            data.get('latitude'),
            data.get('longitude'),
            data.get('farm_size_hectares', 0),
            json.dumps(data.get('primary_crops', [])),
            data.get('soil_type'),
            data.get('irrigation_type'),
            data.get('farming_experience_years', 0),
            data.get('is_card_member', False),
            data.get('card_member_id'),
            data.get('profile_completeness', 0.5),
            'pending',
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "message": "Farmer profile created successfully",
            "farmer_id": data['farmer_id'],
            "created_at": datetime.utcnow().isoformat()
        }), 201
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to create farmer profile: {str(e)}"
        }), 500

# =====================================================
# A/B TESTING ENDPOINTS
# =====================================================

@kaani_bp.route('/api/testing/assign-farmer', methods=['POST'])
def assign_farmer_to_test():
    """Assign farmer to A/B testing group"""
    try:
        data = request.get_json()
        
        if not data or 'farmer_id' not in data or 'test_name' not in data:
            return jsonify({
                "error": "farmer_id and test_name are required"
            }), 400
        
        farmer_id = data['farmer_id']
        test_name = data['test_name']
        
        # Simple A/B assignment based on farmer_id hash
        import hashlib
        hash_value = int(hashlib.md5(farmer_id.encode()).hexdigest(), 16)
        group_assignment = "A" if hash_value % 2 == 0 else "B"
        ai_provider = "openai" if group_assignment == "A" else "google"
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert or update test assignment
        cursor.execute("""
            INSERT OR REPLACE INTO ab_testing_groups (
                farmer_id, test_name, group_assignment, ai_provider,
                test_parameters, assigned_at, assignment_method, is_active,
                test_start_date, test_end_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            farmer_id,
            test_name,
            group_assignment,
            ai_provider,
            json.dumps({"model": "gpt-4.1-mini" if ai_provider == "openai" else "gemini-pro"}),
            datetime.utcnow().isoformat(),
            "hash_based",
            True,
            datetime.utcnow().date().isoformat(),
            None  # No end date yet
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "farmer_id": farmer_id,
            "test_name": test_name,
            "group_assignment": group_assignment,
            "ai_provider": ai_provider,
            "assigned_at": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to assign farmer to test: {str(e)}"
        }), 500

@kaani_bp.route('/api/testing/results/<test_name>', methods=['GET'])
def get_test_results(test_name):
    """Get A/B testing results summary"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get test group statistics
        cursor.execute("""
            SELECT 
                group_assignment,
                ai_provider,
                COUNT(*) as farmer_count
            FROM ab_testing_groups 
            WHERE test_name = ? AND is_active = 1
            GROUP BY group_assignment, ai_provider
        """, (test_name,))
        
        group_stats = [dict(row) for row in cursor.fetchall()]
        
        # Get performance metrics (if any results exist)
        cursor.execute("""
            SELECT 
                atr.test_name,
                atg.group_assignment,
                atg.ai_provider,
                AVG(atr.user_satisfaction_score) as avg_satisfaction,
                AVG(atr.ai_confidence_score) as avg_confidence,
                AVG(atr.response_time_seconds) as avg_response_time,
                COUNT(*) as total_interactions
            FROM ab_testing_results atr
            JOIN ab_testing_groups atg ON atr.farmer_id = atg.farmer_id AND atr.test_name = atg.test_name
            WHERE atr.test_name = ?
            GROUP BY atg.group_assignment, atg.ai_provider
        """, (test_name,))
        
        performance_stats = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({
            "test_name": test_name,
            "group_statistics": group_stats,
            "performance_metrics": performance_stats,
            "summary": {
                "total_farmers_assigned": sum(stat["farmer_count"] for stat in group_stats),
                "total_interactions": sum(stat["total_interactions"] for stat in performance_stats) if performance_stats else 0
            },
            "generated_at": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to get test results: {str(e)}"
        }), 500
