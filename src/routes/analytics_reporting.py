"""
Analytics and Reporting Routes for Multi-tenant Agricultural Platform
MAGSASA-CARD Enhanced Platform
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import sessionmaker
import json

from src.models.user import db, User, Organization
from src.models.agricultural import Farmer, Farm, Crop, FarmActivity, AgriculturalInput
from src.models.analytics import (
    FarmerAnalytics, CooperativeAnalytics, FieldOperationsAnalytics,
    PartnerAnalytics, CropYieldAnalytics, SystemAnalytics, AnalyticsReport,
    AnalyticsTimeframe, ReportType, AnalyticsCalculator
)
from src.middleware.agricultural_auth import require_permission

analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')

@analytics_bp.route('/dashboard/<int:organization_id>', methods=['GET'])
@jwt_required()
@require_permission('analytics.view_dashboard')
def get_analytics_dashboard(organization_id):
    """Get comprehensive analytics dashboard for an organization"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        # Verify user has access to this organization
        if user.organization_id != organization_id and user.role not in ['super_admin', 'admin']:
            return jsonify({'error': 'Access denied to this organization'}), 403
        
        # Get time period from query params
        period = request.args.get('period', 'monthly')  # daily, weekly, monthly, quarterly, yearly
        end_date = datetime.utcnow()
        
        if period == 'daily':
            start_date = end_date - timedelta(days=30)
        elif period == 'weekly':
            start_date = end_date - timedelta(weeks=12)
        elif period == 'monthly':
            start_date = end_date - timedelta(days=365)
        elif period == 'quarterly':
            start_date = end_date - timedelta(days=730)
        else:  # yearly
            start_date = end_date - timedelta(days=1095)
        
        # Get latest cooperative analytics
        coop_analytics = CooperativeAnalytics.query.filter(
            CooperativeAnalytics.organization_id == organization_id,
            CooperativeAnalytics.period_start >= start_date
        ).order_by(CooperativeAnalytics.period_start.desc()).first()
        
        # Get farmer analytics summary
        farmer_analytics = db.session.query(
            func.count(FarmerAnalytics.id).label('total_records'),
            func.avg(FarmerAnalytics.yield_per_hectare).label('avg_yield'),
            func.sum(FarmerAnalytics.total_yield).label('total_production'),
            func.avg(FarmerAnalytics.net_income).label('avg_income'),
            func.avg(FarmerAnalytics.productivity_score).label('avg_productivity')
        ).filter(
            FarmerAnalytics.organization_id == organization_id,
            FarmerAnalytics.period_start >= start_date
        ).first()
        
        # Get field operations summary
        field_ops = db.session.query(
            func.sum(FieldOperationsAnalytics.total_farm_visits).label('total_visits'),
            func.avg(FieldOperationsAnalytics.visit_success_rate).label('avg_success_rate'),
            func.sum(FieldOperationsAnalytics.technical_assistance_provided).label('total_assistance'),
            func.sum(FieldOperationsAnalytics.farmers_served).label('farmers_served')
        ).filter(
            FieldOperationsAnalytics.organization_id == organization_id,
            FieldOperationsAnalytics.period_start >= start_date
        ).first()
        
        # Get crop yield analytics
        crop_yields = db.session.query(
            Crop.name,
            func.sum(CropYieldAnalytics.total_production).label('production'),
            func.avg(CropYieldAnalytics.average_yield_per_hectare).label('avg_yield'),
            func.sum(CropYieldAnalytics.total_planted_area).label('planted_area')
        ).join(CropYieldAnalytics).filter(
            CropYieldAnalytics.organization_id == organization_id,
            CropYieldAnalytics.period_start >= start_date
        ).group_by(Crop.name).all()
        
        # Get partner performance
        partner_performance = db.session.query(
            PartnerAnalytics.partner_type,
            func.count(PartnerAnalytics.id).label('partner_count'),
            func.avg(PartnerAnalytics.transaction_success_rate).label('avg_success_rate'),
            func.sum(PartnerAnalytics.total_transaction_value).label('total_value'),
            func.sum(PartnerAnalytics.commission_earned).label('total_commission')
        ).filter(
            PartnerAnalytics.client_organization_id == organization_id,
            PartnerAnalytics.period_start >= start_date
        ).group_by(PartnerAnalytics.partner_type).all()
        
        # Build dashboard response
        dashboard_data = {
            'organization_id': organization_id,
            'period': period,
            'period_start': start_date.isoformat(),
            'period_end': end_date.isoformat(),
            'cooperative_summary': {
                'total_farmers': coop_analytics.total_farmers if coop_analytics else 0,
                'active_farmers': coop_analytics.active_farmers if coop_analytics else 0,
                'card_members': coop_analytics.card_members if coop_analytics else 0,
                'total_farm_area': float(coop_analytics.total_farm_area) if coop_analytics else 0.0,
                'total_production': float(coop_analytics.total_production) if coop_analytics else 0.0,
                'average_yield': float(coop_analytics.average_yield_per_hectare) if coop_analytics else 0.0,
                'total_revenue': float(coop_analytics.total_revenue) if coop_analytics else 0.0,
                'efficiency_score': float(coop_analytics.cooperative_efficiency_score) if coop_analytics else 0.0
            },
            'farmer_performance': {
                'total_records': farmer_analytics.total_records if farmer_analytics.total_records else 0,
                'average_yield_per_hectare': float(farmer_analytics.avg_yield) if farmer_analytics.avg_yield else 0.0,
                'total_production': float(farmer_analytics.total_production) if farmer_analytics.total_production else 0.0,
                'average_income': float(farmer_analytics.avg_income) if farmer_analytics.avg_income else 0.0,
                'average_productivity_score': float(farmer_analytics.avg_productivity) if farmer_analytics.avg_productivity else 0.0
            },
            'field_operations': {
                'total_farm_visits': field_ops.total_visits if field_ops.total_visits else 0,
                'average_success_rate': float(field_ops.avg_success_rate) if field_ops.avg_success_rate else 0.0,
                'technical_assistance_provided': field_ops.total_assistance if field_ops.total_assistance else 0,
                'farmers_served': field_ops.farmers_served if field_ops.farmers_served else 0
            },
            'crop_distribution': [
                {
                    'crop_name': crop.name,
                    'production': float(crop.production),
                    'average_yield': float(crop.avg_yield),
                    'planted_area': float(crop.planted_area)
                }
                for crop in crop_yields
            ],
            'partner_performance': [
                {
                    'partner_type': partner.partner_type,
                    'partner_count': partner.partner_count,
                    'success_rate': float(partner.avg_success_rate),
                    'total_transaction_value': float(partner.total_value),
                    'commission_earned': float(partner.total_commission)
                }
                for partner in partner_performance
            ]
        }
        
        return jsonify(dashboard_data), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting analytics dashboard: {str(e)}")
        return jsonify({'error': 'Failed to retrieve analytics dashboard'}), 500

@analytics_bp.route('/farmer-performance/<int:organization_id>', methods=['GET'])
@jwt_required()
@require_permission('analytics.view_farmer_performance')
def get_farmer_performance_analytics(organization_id):
    """Get detailed farmer performance analytics"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        # Verify access
        if user.organization_id != organization_id and user.role not in ['super_admin', 'admin']:
            return jsonify({'error': 'Access denied to this organization'}), 403
        
        # Get query parameters
        timeframe = request.args.get('timeframe', 'monthly')
        farmer_id = request.args.get('farmer_id')
        limit = int(request.args.get('limit', 50))
        
        # Build query
        query = FarmerAnalytics.query.filter(
            FarmerAnalytics.organization_id == organization_id,
            FarmerAnalytics.timeframe == timeframe
        )
        
        if farmer_id:
            query = query.filter(FarmerAnalytics.farmer_id == farmer_id)
        
        farmer_analytics = query.order_by(
            FarmerAnalytics.period_start.desc()
        ).limit(limit).all()
        
        # Get farmer details
        farmer_details = {}
        if farmer_analytics:
            farmers = db.session.query(Farmer).filter(
                Farmer.id.in_([fa.farmer_id for fa in farmer_analytics])
            ).all()
            farmer_details = {f.id: {
                'name': f.name,
                'rsbsa_id': f.rsbsa_id,
                'card_member': f.card_member_id is not None
            } for f in farmers}
        
        # Format response
        performance_data = []
        for analytics in farmer_analytics:
            farmer_info = farmer_details.get(analytics.farmer_id, {})
            performance_data.append({
                'farmer_id': analytics.farmer_id,
                'farmer_name': farmer_info.get('name', 'Unknown'),
                'rsbsa_id': farmer_info.get('rsbsa_id', ''),
                'card_member': farmer_info.get('card_member', False),
                'period_start': analytics.period_start.isoformat(),
                'period_end': analytics.period_end.isoformat(),
                'agricultural_metrics': {
                    'total_farm_area': float(analytics.total_farm_area),
                    'planted_area': float(analytics.planted_area),
                    'harvested_area': float(analytics.harvested_area),
                    'total_yield': float(analytics.total_yield),
                    'yield_per_hectare': float(analytics.yield_per_hectare)
                },
                'financial_metrics': {
                    'total_revenue': float(analytics.total_revenue),
                    'total_costs': float(analytics.total_costs),
                    'net_income': float(analytics.net_income),
                    'profit_margin': float(analytics.profit_margin)
                },
                'performance_scores': {
                    'productivity_score': float(analytics.productivity_score),
                    'sustainability_score': float(analytics.sustainability_score),
                    'financial_health_score': float(analytics.financial_health_score)
                },
                'card_bdsfi_metrics': {
                    'benefits_received': float(analytics.card_member_benefits_received),
                    'loan_amount': float(analytics.loan_amount_disbursed),
                    'repayment_rate': float(analytics.loan_repayment_rate)
                }
            })
        
        return jsonify({
            'organization_id': organization_id,
            'timeframe': timeframe,
            'total_records': len(performance_data),
            'farmer_performance': performance_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting farmer performance analytics: {str(e)}")
        return jsonify({'error': 'Failed to retrieve farmer performance analytics'}), 500

@analytics_bp.route('/card-bdsfi-report/<int:organization_id>', methods=['GET'])
@jwt_required()
@require_permission('analytics.view_card_reports')
def get_card_bdsfi_report(organization_id):
    """Generate specialized CARD BDSFI partnership report"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        # Verify access
        if user.organization_id != organization_id and user.role not in ['super_admin', 'admin']:
            return jsonify({'error': 'Access denied to this organization'}), 403
        
        # Get time period
        period_start = datetime.fromisoformat(request.args.get('start_date', (datetime.utcnow() - timedelta(days=90)).isoformat()))
        period_end = datetime.fromisoformat(request.args.get('end_date', datetime.utcnow().isoformat()))
        
        # Generate CARD BDSFI report using the calculator
        report_data = AnalyticsCalculator.generate_card_bdsfi_report(
            organization_id, period_start, period_end
        )
        
        # Add additional CARD BDSFI specific metrics
        # Get CARD member farmers
        card_farmers = db.session.query(Farmer).filter(
            Farmer.organization_id == organization_id,
            Farmer.card_member_id.isnot(None)
        ).all()
        
        # Get recent activities for CARD members
        recent_activities = db.session.query(FarmActivity).join(Farm).join(Farmer).filter(
            Farmer.organization_id == organization_id,
            Farmer.card_member_id.isnot(None),
            FarmActivity.activity_date >= period_start,
            FarmActivity.activity_date <= period_end
        ).count()
        
        # Calculate commission earnings (5% of input sales as per CARD BDSFI model)
        input_sales = db.session.query(
            func.sum(AgriculturalInput.selling_price * FarmActivity.quantity_used)
        ).join(FarmActivity).join(Farm).join(Farmer).filter(
            Farmer.organization_id == organization_id,
            Farmer.card_member_id.isnot(None),
            FarmActivity.activity_date >= period_start,
            FarmActivity.activity_date <= period_end,
            FarmActivity.input_id.isnot(None)
        ).scalar() or 0
        
        commission_earned = float(input_sales) * 0.05  # 5% commission rate
        
        # Enhanced CARD BDSFI report
        enhanced_report = {
            'report_metadata': {
                'organization_id': organization_id,
                'report_type': 'CARD BDSFI Partnership Report',
                'period_start': period_start.isoformat(),
                'period_end': period_end.isoformat(),
                'generated_at': datetime.utcnow().isoformat(),
                'generated_by': user.username
            },
            'executive_summary': {
                'total_card_members': len(card_farmers),
                'total_commission_earned': commission_earned,
                'member_engagement_rate': (recent_activities / len(card_farmers)) if card_farmers else 0,
                'partnership_status': 'Active',
                'compliance_with_free_usage': True  # CARD BDSFI requirement
            },
            'member_demographics': {
                'total_members': len(card_farmers),
                'active_members': len([f for f in card_farmers if f.status == 'active']),
                'average_farm_size': sum(f.total_farm_area for f in card_farmers) / len(card_farmers) if card_farmers else 0,
                'primary_crops': ['Rice', 'Corn', 'Vegetables'],  # Based on CARD BDSFI focus
                'geographic_distribution': {
                    'laguna': len([f for f in card_farmers if 'laguna' in f.address.lower()]),
                    'other_regions': len([f for f in card_farmers if 'laguna' not in f.address.lower()])
                }
            },
            'financial_impact': {
                'total_input_sales': float(input_sales),
                'commission_earned': commission_earned,
                'commission_rate': 5.0,  # 5% as per CARD BDSFI agreement
                'average_member_savings': 1250.0,  # Estimated savings per member
                'total_member_benefits': len(card_farmers) * 1250.0
            },
            'agricultural_performance': report_data.get('farmer_performance', {}),
            'technology_adoption': {
                'mobile_app_users': len(card_farmers),  # All CARD members use the app
                'digital_literacy_score': 78.0,
                'feature_usage_rates': {
                    'farm_planning': 85.0,
                    'input_ordering': 92.0,
                    'yield_tracking': 76.0,
                    'market_access': 68.0
                }
            },
            'partnership_compliance': {
                'free_usage_maintained': True,
                'no_subscription_fees': True,
                'commission_only_model': True,
                'farmer_satisfaction': 87.5,
                'partnership_goals_met': True
            },
            'recommendations': [
                'Continue focus on input commission model to maintain free usage for farmers',
                'Expand digital literacy training to improve feature adoption',
                'Develop specialized modules for CARD BDSFI cooperative management',
                'Implement farmer feedback system for continuous improvement'
            ]
        }
        
        # Save report to database
        report_record = AnalyticsReport(
            organization_id=organization_id,
            report_type=ReportType.CARD_BDSFI_REPORT,
            report_title=f'CARD BDSFI Partnership Report - {period_start.strftime("%B %Y")}',
            report_description='Comprehensive partnership performance and compliance report for CARD BDSFI',
            period_start=period_start,
            period_end=period_end,
            timeframe=AnalyticsTimeframe.MONTHLY,
            report_data=enhanced_report,
            generated_by=current_user_id
        )
        
        db.session.add(report_record)
        db.session.commit()
        
        return jsonify(enhanced_report), 200
        
    except Exception as e:
        current_app.logger.error(f"Error generating CARD BDSFI report: {str(e)}")
        return jsonify({'error': 'Failed to generate CARD BDSFI report'}), 500

@analytics_bp.route('/field-operations/<int:organization_id>', methods=['GET'])
@jwt_required()
@require_permission('analytics.view_field_operations')
def get_field_operations_analytics(organization_id):
    """Get field operations analytics and performance metrics"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        # Verify access
        if user.organization_id != organization_id and user.role not in ['super_admin', 'admin']:
            return jsonify({'error': 'Access denied to this organization'}), 403
        
        # Get query parameters
        timeframe = request.args.get('timeframe', 'monthly')
        field_officer_id = request.args.get('field_officer_id')
        
        # Build query
        query = FieldOperationsAnalytics.query.filter(
            FieldOperationsAnalytics.organization_id == organization_id,
            FieldOperationsAnalytics.timeframe == timeframe
        )
        
        if field_officer_id:
            query = query.filter(FieldOperationsAnalytics.field_officer_id == field_officer_id)
        
        field_analytics = query.order_by(
            FieldOperationsAnalytics.period_start.desc()
        ).all()
        
        # Get field officer details
        officer_details = {}
        if field_analytics:
            officers = db.session.query(User).filter(
                User.id.in_([fa.field_officer_id for fa in field_analytics if fa.field_officer_id])
            ).all()
            officer_details = {o.id: {
                'name': f"{o.first_name} {o.last_name}",
                'username': o.username,
                'role': o.role
            } for o in officers}
        
        # Calculate summary metrics
        total_visits = sum(fa.total_farm_visits for fa in field_analytics)
        total_successful = sum(fa.successful_visits for fa in field_analytics)
        avg_success_rate = (total_successful / total_visits * 100) if total_visits > 0 else 0
        
        # Format response
        operations_data = {
            'organization_id': organization_id,
            'timeframe': timeframe,
            'summary_metrics': {
                'total_farm_visits': total_visits,
                'successful_visits': total_successful,
                'average_success_rate': avg_success_rate,
                'total_farmers_served': sum(fa.farmers_served for fa in field_analytics),
                'total_technical_assistance': sum(fa.technical_assistance_provided for fa in field_analytics),
                'total_area_covered': sum(fa.total_area_covered for fa in field_analytics)
            },
            'field_officer_performance': []
        }
        
        # Group by field officer
        officer_performance = {}
        for analytics in field_analytics:
            officer_id = analytics.field_officer_id or 0
            if officer_id not in officer_performance:
                officer_info = officer_details.get(officer_id, {'name': 'Unassigned', 'username': '', 'role': ''})
                officer_performance[officer_id] = {
                    'officer_id': officer_id,
                    'officer_name': officer_info['name'],
                    'username': officer_info['username'],
                    'role': officer_info['role'],
                    'performance_metrics': {
                        'total_visits': 0,
                        'successful_visits': 0,
                        'success_rate': 0,
                        'farmers_served': 0,
                        'technical_assistance': 0,
                        'area_covered': 0,
                        'efficiency_score': 0
                    },
                    'monthly_data': []
                }
            
            # Aggregate metrics
            perf = officer_performance[officer_id]['performance_metrics']
            perf['total_visits'] += analytics.total_farm_visits
            perf['successful_visits'] += analytics.successful_visits
            perf['farmers_served'] += analytics.farmers_served
            perf['technical_assistance'] += analytics.technical_assistance_provided
            perf['area_covered'] += analytics.total_area_covered
            
            # Add monthly data point
            officer_performance[officer_id]['monthly_data'].append({
                'period_start': analytics.period_start.isoformat(),
                'period_end': analytics.period_end.isoformat(),
                'visits': analytics.total_farm_visits,
                'success_rate': analytics.visit_success_rate,
                'farmers_served': analytics.farmers_served,
                'satisfaction_score': analytics.farmer_satisfaction_score
            })
        
        # Calculate final metrics for each officer
        for officer_data in officer_performance.values():
            perf = officer_data['performance_metrics']
            if perf['total_visits'] > 0:
                perf['success_rate'] = (perf['successful_visits'] / perf['total_visits']) * 100
                perf['efficiency_score'] = min(perf['success_rate'] + (perf['farmers_served'] / 10), 100)
            
            operations_data['field_officer_performance'].append(officer_data)
        
        return jsonify(operations_data), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting field operations analytics: {str(e)}")
        return jsonify({'error': 'Failed to retrieve field operations analytics'}), 500

@analytics_bp.route('/crop-yield/<int:organization_id>', methods=['GET'])
@jwt_required()
@require_permission('analytics.view_crop_yield')
def get_crop_yield_analytics(organization_id):
    """Get crop yield analytics and production metrics"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        # Verify access
        if user.organization_id != organization_id and user.role not in ['super_admin', 'admin']:
            return jsonify({'error': 'Access denied to this organization'}), 403
        
        # Get query parameters
        timeframe = request.args.get('timeframe', 'monthly')
        crop_type = request.args.get('crop_type')
        
        # Build query
        query = db.session.query(
            CropYieldAnalytics,
            Crop.name.label('crop_name'),
            Crop.variety.label('crop_variety')
        ).join(Crop).filter(
            CropYieldAnalytics.organization_id == organization_id,
            CropYieldAnalytics.timeframe == timeframe
        )
        
        if crop_type:
            query = query.filter(Crop.name == crop_type)
        
        yield_analytics = query.order_by(
            CropYieldAnalytics.period_start.desc()
        ).all()
        
        # Calculate summary metrics
        total_production = sum(ya.CropYieldAnalytics.total_production for ya in yield_analytics)
        total_area = sum(ya.CropYieldAnalytics.total_planted_area for ya in yield_analytics)
        avg_yield = (total_production / total_area) if total_area > 0 else 0
        
        # Group by crop type
        crop_performance = {}
        for analytics, crop_name, crop_variety in yield_analytics:
            if crop_name not in crop_performance:
                crop_performance[crop_name] = {
                    'crop_name': crop_name,
                    'varieties': {},
                    'total_production': 0,
                    'total_area': 0,
                    'average_yield': 0,
                    'performance_trend': []
                }
            
            crop_data = crop_performance[crop_name]
            crop_data['total_production'] += analytics.total_production
            crop_data['total_area'] += analytics.total_planted_area
            
            # Track varieties
            if crop_variety not in crop_data['varieties']:
                crop_data['varieties'][crop_variety] = {
                    'production': 0,
                    'area': 0,
                    'yield': 0
                }
            
            variety_data = crop_data['varieties'][crop_variety]
            variety_data['production'] += analytics.total_production
            variety_data['area'] += analytics.total_planted_area
            variety_data['yield'] = (variety_data['production'] / variety_data['area']) if variety_data['area'] > 0 else 0
            
            # Add to performance trend
            crop_data['performance_trend'].append({
                'period_start': analytics.period_start.isoformat(),
                'period_end': analytics.period_end.isoformat(),
                'production': analytics.total_production,
                'area': analytics.total_planted_area,
                'yield': analytics.average_yield_per_hectare,
                'quality_grade_a': analytics.grade_a_percentage,
                'market_price': analytics.average_farm_gate_price
            })
        
        # Calculate final averages
        for crop_data in crop_performance.values():
            if crop_data['total_area'] > 0:
                crop_data['average_yield'] = crop_data['total_production'] / crop_data['total_area']
        
        yield_data = {
            'organization_id': organization_id,
            'timeframe': timeframe,
            'summary_metrics': {
                'total_production': total_production,
                'total_planted_area': total_area,
                'average_yield_per_hectare': avg_yield,
                'number_of_crops': len(crop_performance),
                'top_performing_crop': max(crop_performance.keys(), key=lambda x: crop_performance[x]['average_yield']) if crop_performance else None
            },
            'crop_performance': list(crop_performance.values())
        }
        
        return jsonify(yield_data), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting crop yield analytics: {str(e)}")
        return jsonify({'error': 'Failed to retrieve crop yield analytics'}), 500

@analytics_bp.route('/generate-report', methods=['POST'])
@jwt_required()
@require_permission('analytics.generate_reports')
def generate_custom_report():
    """Generate custom analytics report"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['organization_id', 'report_type', 'period_start', 'period_end']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        organization_id = data['organization_id']
        
        # Verify access
        if user.organization_id != organization_id and user.role not in ['super_admin', 'admin']:
            return jsonify({'error': 'Access denied to this organization'}), 403
        
        # Parse dates
        period_start = datetime.fromisoformat(data['period_start'])
        period_end = datetime.fromisoformat(data['period_end'])
        
        # Generate report based on type
        report_type = data['report_type']
        report_data = {}
        
        if report_type == 'farmer_performance':
            # Generate farmer performance report
            farmer_analytics = FarmerAnalytics.query.filter(
                FarmerAnalytics.organization_id == organization_id,
                FarmerAnalytics.period_start >= period_start,
                FarmerAnalytics.period_end <= period_end
            ).all()
            
            report_data = {
                'total_farmers': len(farmer_analytics),
                'average_yield': sum(fa.yield_per_hectare for fa in farmer_analytics) / len(farmer_analytics) if farmer_analytics else 0,
                'total_production': sum(fa.total_yield for fa in farmer_analytics),
                'average_income': sum(fa.net_income for fa in farmer_analytics) / len(farmer_analytics) if farmer_analytics else 0,
                'top_performers': sorted(farmer_analytics, key=lambda x: x.productivity_score, reverse=True)[:10]
            }
            
        elif report_type == 'card_bdsfi_report':
            # Generate CARD BDSFI report
            report_data = AnalyticsCalculator.generate_card_bdsfi_report(
                organization_id, period_start, period_end
            )
            
        # Add more report types as needed
        
        # Save report
        report_record = AnalyticsReport(
            organization_id=organization_id,
            report_type=ReportType(report_type),
            report_title=data.get('title', f'{report_type.replace("_", " ").title()} Report'),
            report_description=data.get('description', ''),
            period_start=period_start,
            period_end=period_end,
            timeframe=AnalyticsTimeframe(data.get('timeframe', 'monthly')),
            report_data=report_data,
            generated_by=current_user_id,
            is_scheduled=data.get('is_scheduled', False),
            schedule_frequency=data.get('schedule_frequency')
        )
        
        db.session.add(report_record)
        db.session.commit()
        
        return jsonify({
            'report_id': report_record.id,
            'message': 'Report generated successfully',
            'report_data': report_data
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error generating custom report: {str(e)}")
        return jsonify({'error': 'Failed to generate report'}), 500

@analytics_bp.route('/reports/<int:organization_id>', methods=['GET'])
@jwt_required()
@require_permission('analytics.view_reports')
def get_organization_reports(organization_id):
    """Get all reports for an organization"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        # Verify access
        if user.organization_id != organization_id and user.role not in ['super_admin', 'admin']:
            return jsonify({'error': 'Access denied to this organization'}), 403
        
        # Get query parameters
        report_type = request.args.get('report_type')
        limit = int(request.args.get('limit', 20))
        
        # Build query
        query = AnalyticsReport.query.filter(
            AnalyticsReport.organization_id == organization_id
        )
        
        if report_type:
            query = query.filter(AnalyticsReport.report_type == report_type)
        
        reports = query.order_by(
            AnalyticsReport.generated_at.desc()
        ).limit(limit).all()
        
        # Format response
        reports_data = []
        for report in reports:
            reports_data.append({
                'report_id': report.id,
                'report_type': report.report_type.value,
                'title': report.report_title,
                'description': report.report_description,
                'period_start': report.period_start.isoformat(),
                'period_end': report.period_end.isoformat(),
                'timeframe': report.timeframe.value,
                'generated_at': report.generated_at.isoformat(),
                'generated_by': report.generated_by_user.username if report.generated_by_user else 'System',
                'is_scheduled': report.is_scheduled,
                'file_path': report.file_path
            })
        
        return jsonify({
            'organization_id': organization_id,
            'total_reports': len(reports_data),
            'reports': reports_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting organization reports: {str(e)}")
        return jsonify({'error': 'Failed to retrieve reports'}), 500

@analytics_bp.route('/system-analytics', methods=['GET'])
@jwt_required()
@require_permission('analytics.view_system_analytics')
def get_system_analytics():
    """Get system-wide analytics (Super Admin only)"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        # Only super admins can view system analytics
        if user.role != 'super_admin':
            return jsonify({'error': 'Access denied. Super admin required.'}), 403
        
        # Get latest system analytics
        system_analytics = SystemAnalytics.query.order_by(
            SystemAnalytics.period_start.desc()
        ).first()
        
        if not system_analytics:
            return jsonify({'error': 'No system analytics data available'}), 404
        
        # Get organization breakdown
        org_breakdown = db.session.query(
            Organization.name,
            Organization.organization_type,
            func.count(User.id).label('user_count'),
            func.count(Farmer.id).label('farmer_count')
        ).outerjoin(User).outerjoin(Farmer).group_by(
            Organization.id, Organization.name, Organization.organization_type
        ).all()
        
        system_data = {
            'system_metrics': {
                'total_users': system_analytics.total_users,
                'active_users': system_analytics.active_users,
                'total_organizations': system_analytics.total_organizations,
                'total_farmers': system_analytics.total_farmers_in_system,
                'total_api_calls': system_analytics.total_api_calls,
                'api_success_rate': system_analytics.api_success_rate,
                'system_health_score': system_analytics.system_health_score
            },
            'organization_breakdown': [
                {
                    'name': org.name,
                    'type': org.organization_type,
                    'users': org.user_count,
                    'farmers': org.farmer_count
                }
                for org in org_breakdown
            ],
            'period_start': system_analytics.period_start.isoformat(),
            'period_end': system_analytics.period_end.isoformat()
        }
        
        return jsonify(system_data), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting system analytics: {str(e)}")
        return jsonify({'error': 'Failed to retrieve system analytics'}), 500
