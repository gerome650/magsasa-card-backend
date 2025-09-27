"""
Partner API middleware for authentication, rate limiting, and access control
"""

import json
import time
from functools import wraps
from flask import request, jsonify, current_app, g
from datetime import datetime, timezone

from src.models.partner_api import (
    PartnerAPIKey, APIUsageLog, APIKeyStatus, RateLimiter, RateLimitType
)
from src.models.user import db

class PartnerAPIMiddleware:
    """Middleware for partner API authentication and rate limiting"""
    
    @staticmethod
    def authenticate_api_key():
        """Authenticate API key from request headers"""
        api_key = request.headers.get('X-API-Key') or request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not api_key:
            return None, {'error': 'API key required', 'code': 'MISSING_API_KEY'}
        
        # Find API key by prefix (first 8 characters)
        if len(api_key) < 8:
            return None, {'error': 'Invalid API key format', 'code': 'INVALID_API_KEY'}
        
        key_prefix = api_key[:8]
        api_key_obj = PartnerAPIKey.query.filter_by(key_prefix=key_prefix).first()
        
        if not api_key_obj:
            return None, {'error': 'Invalid API key', 'code': 'INVALID_API_KEY'}
        
        # Verify the full key
        if not api_key_obj.verify_key(api_key):
            return None, {'error': 'Invalid API key', 'code': 'INVALID_API_KEY'}
        
        # Check if key is valid and active
        if not api_key_obj.is_valid():
            return None, {'error': f'API key is {api_key_obj.status.value}', 'code': 'INACTIVE_API_KEY'}
        
        return api_key_obj, None
    
    @staticmethod
    def check_rate_limits(api_key_obj):
        """Check rate limits for API key"""
        # Check per-minute limit
        if not RateLimiter.check_rate_limit(api_key_obj, RateLimitType.PER_MINUTE):
            return False, {'error': 'Rate limit exceeded (per minute)', 'code': 'RATE_LIMIT_EXCEEDED'}
        
        # Check per-hour limit
        if not RateLimiter.check_rate_limit(api_key_obj, RateLimitType.PER_HOUR):
            return False, {'error': 'Rate limit exceeded (per hour)', 'code': 'RATE_LIMIT_EXCEEDED'}
        
        # Check per-day limit
        if not RateLimiter.check_rate_limit(api_key_obj, RateLimitType.PER_DAY):
            return False, {'error': 'Rate limit exceeded (per day)', 'code': 'RATE_LIMIT_EXCEEDED'}
        
        return True, None
    
    @staticmethod
    def check_endpoint_permissions(api_key_obj, endpoint):
        """Check if API key has permission to access endpoint"""
        if not api_key_obj.allowed_endpoints:
            return True  # No restrictions
        
        try:
            allowed_endpoints = json.loads(api_key_obj.allowed_endpoints)
            
            # Check exact match
            if endpoint in allowed_endpoints:
                return True
            
            # Check pattern match (e.g., /api/partners/* allows /api/partners/orders)
            for allowed_pattern in allowed_endpoints:
                if allowed_pattern.endswith('*'):
                    pattern_prefix = allowed_pattern[:-1]
                    if endpoint.startswith(pattern_prefix):
                        return True
            
            return False
            
        except (json.JSONDecodeError, TypeError):
            return True  # If can't parse, allow access
    
    @staticmethod
    def check_ip_whitelist(api_key_obj, client_ip):
        """Check if client IP is in whitelist"""
        if not api_key_obj.ip_whitelist:
            return True  # No IP restrictions
        
        try:
            allowed_ips = json.loads(api_key_obj.ip_whitelist)
            return client_ip in allowed_ips
        except (json.JSONDecodeError, TypeError):
            return True  # If can't parse, allow access
    
    @staticmethod
    def log_api_usage(api_key_obj, endpoint, method, status_code, response_time, 
                     request_size=0, response_size=0, details=None):
        """Log API usage for analytics and monitoring"""
        try:
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            user_agent = request.headers.get('User-Agent', '')
            
            # Update API key usage stats
            api_key_obj.update_usage(endpoint, client_ip)
            
            # Create usage log
            usage_log = APIUsageLog(
                api_key_id=api_key_obj.id,
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                response_time=response_time,
                ip_address=client_ip,
                user_agent=user_agent,
                request_size=request_size,
                response_size=response_size,
                details=json.dumps(details) if details else None
            )
            
            db.session.add(usage_log)
            db.session.commit()
            
        except Exception as e:
            current_app.logger.error(f"Failed to log API usage: {str(e)}")

def require_partner_api_key(allowed_partner_types=None):
    """
    Decorator to require valid partner API key for endpoint access
    
    Args:
        allowed_partner_types: List of allowed partner types (None = all types allowed)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            
            try:
                # Authenticate API key
                api_key_obj, auth_error = PartnerAPIMiddleware.authenticate_api_key()
                if auth_error:
                    return jsonify(auth_error), 401
                
                # Check partner type restrictions
                if allowed_partner_types and api_key_obj.partner_type not in allowed_partner_types:
                    error_response = {
                        'error': f'Partner type {api_key_obj.partner_type.value} not allowed for this endpoint',
                        'code': 'PARTNER_TYPE_NOT_ALLOWED'
                    }
                    return jsonify(error_response), 403
                
                # Check rate limits
                rate_limit_ok, rate_limit_error = PartnerAPIMiddleware.check_rate_limits(api_key_obj)
                if not rate_limit_ok:
                    # Add rate limit headers
                    rate_status = RateLimiter.get_rate_limit_status(api_key_obj)
                    response = jsonify(rate_limit_error)
                    response.headers['X-RateLimit-Limit-Minute'] = str(api_key_obj.rate_limit_per_minute)
                    response.headers['X-RateLimit-Remaining-Minute'] = str(rate_status['per_minute']['remaining'])
                    response.headers['X-RateLimit-Limit-Hour'] = str(api_key_obj.rate_limit_per_hour)
                    response.headers['X-RateLimit-Remaining-Hour'] = str(rate_status['per_hour']['remaining'])
                    return response, 429
                
                # Check endpoint permissions
                endpoint = request.endpoint or request.path
                if not PartnerAPIMiddleware.check_endpoint_permissions(api_key_obj, endpoint):
                    error_response = {
                        'error': 'Access denied to this endpoint',
                        'code': 'ENDPOINT_ACCESS_DENIED'
                    }
                    return jsonify(error_response), 403
                
                # Check IP whitelist
                client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
                if not PartnerAPIMiddleware.check_ip_whitelist(api_key_obj, client_ip):
                    error_response = {
                        'error': 'IP address not allowed',
                        'code': 'IP_NOT_ALLOWED'
                    }
                    return jsonify(error_response), 403
                
                # Store API key in Flask's g object for use in the endpoint
                g.partner_api_key = api_key_obj
                g.partner_organization = api_key_obj.organization
                
                # Call the actual endpoint
                response = f(*args, **kwargs)
                
                # Calculate response time
                response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                
                # Log successful API usage
                status_code = response[1] if isinstance(response, tuple) else 200
                request_size = len(request.get_data()) if request.get_data() else 0
                response_size = len(str(response)) if response else 0
                
                PartnerAPIMiddleware.log_api_usage(
                    api_key_obj=api_key_obj,
                    endpoint=endpoint,
                    method=request.method,
                    status_code=status_code,
                    response_time=response_time,
                    request_size=request_size,
                    response_size=response_size,
                    details={'success': True}
                )
                
                # Add rate limit headers to successful responses
                rate_status = RateLimiter.get_rate_limit_status(api_key_obj)
                if isinstance(response, tuple):
                    response_obj, status_code = response
                    if hasattr(response_obj, 'headers'):
                        response_obj.headers['X-RateLimit-Limit-Minute'] = str(api_key_obj.rate_limit_per_minute)
                        response_obj.headers['X-RateLimit-Remaining-Minute'] = str(rate_status['per_minute']['remaining'])
                        response_obj.headers['X-RateLimit-Limit-Hour'] = str(api_key_obj.rate_limit_per_hour)
                        response_obj.headers['X-RateLimit-Remaining-Hour'] = str(rate_status['per_hour']['remaining'])
                
                return response
                
            except Exception as e:
                # Log failed API usage
                response_time = (time.time() - start_time) * 1000
                
                if 'api_key_obj' in locals():
                    PartnerAPIMiddleware.log_api_usage(
                        api_key_obj=api_key_obj,
                        endpoint=request.endpoint or request.path,
                        method=request.method,
                        status_code=500,
                        response_time=response_time,
                        details={'error': str(e), 'success': False}
                    )
                
                current_app.logger.error(f"Partner API error: {str(e)}")
                return jsonify({'error': 'Internal server error', 'code': 'INTERNAL_ERROR'}), 500
        
        return decorated_function
    return decorator

def add_cors_headers(response):
    """Add CORS headers for partner API responses"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-API-Key'
    return response

def validate_partner_request_data(required_fields=None, optional_fields=None):
    """
    Decorator to validate partner API request data
    
    Args:
        required_fields: List of required fields in request JSON
        optional_fields: List of optional fields (for documentation)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.method in ['POST', 'PUT', 'PATCH']:
                if not request.is_json:
                    return jsonify({
                        'error': 'Content-Type must be application/json',
                        'code': 'INVALID_CONTENT_TYPE'
                    }), 400
                
                data = request.get_json()
                if not data:
                    return jsonify({
                        'error': 'Request body must contain valid JSON',
                        'code': 'INVALID_JSON'
                    }), 400
                
                # Check required fields
                if required_fields:
                    missing_fields = [field for field in required_fields if field not in data]
                    if missing_fields:
                        return jsonify({
                            'error': f'Missing required fields: {", ".join(missing_fields)}',
                            'code': 'MISSING_REQUIRED_FIELDS',
                            'missing_fields': missing_fields
                        }), 400
                
                # Store validated data in g object
                g.validated_data = data
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

class PartnerAPIResponse:
    """Helper class for standardized partner API responses"""
    
    @staticmethod
    def success(data=None, message=None, meta=None):
        """Create a successful API response"""
        response = {
            'success': True,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        if message:
            response['message'] = message
        
        if data is not None:
            response['data'] = data
        
        if meta:
            response['meta'] = meta
        
        return jsonify(response)
    
    @staticmethod
    def error(message, code=None, details=None, status_code=400):
        """Create an error API response"""
        response = {
            'success': False,
            'error': message,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        if code:
            response['code'] = code
        
        if details:
            response['details'] = details
        
        return jsonify(response), status_code
    
    @staticmethod
    def paginated(data, page, per_page, total, endpoint=None):
        """Create a paginated API response"""
        total_pages = (total + per_page - 1) // per_page
        
        meta = {
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
        }
        
        if endpoint:
            base_url = request.url_root.rstrip('/') + endpoint
            meta['pagination']['links'] = {
                'self': f"{base_url}?page={page}&per_page={per_page}",
                'first': f"{base_url}?page=1&per_page={per_page}",
                'last': f"{base_url}?page={total_pages}&per_page={per_page}"
            }
            
            if page > 1:
                meta['pagination']['links']['prev'] = f"{base_url}?page={page-1}&per_page={per_page}"
            
            if page < total_pages:
                meta['pagination']['links']['next'] = f"{base_url}?page={page+1}&per_page={per_page}"
        
        return PartnerAPIResponse.success(data=data, meta=meta)
