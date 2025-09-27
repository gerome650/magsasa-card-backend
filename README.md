# MAGSASA-CARD Backend - Dynamic Pricing API

## Overview

This is the backend API for the MAGSASA-CARD Enhanced Platform, featuring dynamic pricing for agricultural inputs, logistics integration, and order processing capabilities.

## Features

- **Dynamic Pricing Model**: Wholesale-retail spread with transparent farmer savings
- **CARD Member Benefits**: 3% discount for CARD BDSFI members
- **Multiple Delivery Options**: Supplier delivery, platform logistics, and farmer pickup
- **Bulk Pricing**: Tiered discounts for larger orders
- **Real-time Market Comparison**: Compare prices with market rates
- **Order Processing**: Complete order management system
- **Analytics**: Pricing and sales analytics

## API Endpoints

### Core Endpoints
- `GET /` - API information and status
- `GET /api/health` - Health check
- `GET /api/info` - System information
- `GET /api/demo` - Demo data and examples

### Pricing Endpoints
- `GET /api/pricing/inputs/<id>` - Get pricing for specific input
- `GET /api/pricing/market-comparison` - Market price comparison
- `POST /api/pricing/calculate-order` - Calculate order total

### Logistics Endpoints
- `GET /api/logistics/options` - Available logistics options

### Order Endpoints
- `POST /api/orders/create` - Create new order
- `GET /api/orders/<id>` - Get order details

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Initialize Database
```bash
python create_dynamic_pricing_db.py
```

### 3. Run the Application
```bash
python app.py
```

The API will be available at `http://localhost:5000`

## Deployment

### Render Deployment
This application is configured for deployment on Render:

1. **Procfile**: Configured for gunicorn
2. **Requirements**: All dependencies listed
3. **Database**: SQLite with automatic initialization

### Environment Variables
- `PORT`: Application port (set by Render)
- `DATABASE_URL`: Database path (defaults to SQLite)

## Database Schema

The application uses SQLite with the following main tables:
- `agricultural_inputs`: Product catalog with dynamic pricing
- `logistics_options`: Delivery and logistics providers
- `input_transactions`: Order and transaction records
- `input_pricing_history`: Price change tracking
- `pricing_analytics`: Analytics and reporting data

## Sample Data

The database includes sample data for:
- 3 agricultural inputs (fertilizers and seeds)
- 3 logistics options (supplier delivery, platform logistics, farmer pickup)
- Pricing history and analytics

## API Usage Examples

### Get Product Pricing
```bash
curl https://your-api-url/api/pricing/inputs/1
```

### Calculate Order Total
```bash
curl -X POST https://your-api-url/api/pricing/calculate-order \
  -H "Content-Type: application/json" \
  -d '{
    "items": [{"input_id": 1, "quantity": 10}],
    "delivery_option": "platform_logistics",
    "logistics_provider_id": 1,
    "card_member": true,
    "delivery_location": {"latitude": 14.1694, "longitude": 121.2441}
  }'
```

### Get Market Comparison
```bash
curl https://your-api-url/api/pricing/market-comparison
```

## Technology Stack

- **Framework**: Flask 2.3.3
- **Database**: SQLite
- **CORS**: Flask-CORS for cross-origin requests
- **Deployment**: Gunicorn WSGI server
- **Authentication**: Flask-JWT-Extended (for future use)

## Development

### Project Structure
```
├── app.py                          # Main application file
├── create_dynamic_pricing_db.py    # Database initialization
├── requirements.txt                # Python dependencies
├── Procfile                       # Deployment configuration
└── src/                           # Source code
    ├── routes/                    # API route blueprints
    ├── models/                    # Database models
    └── database/                  # SQLite database files
```

### Adding New Features
1. Create new route blueprints in `src/routes/`
2. Register blueprints in `app.py`
3. Update database schema if needed
4. Add tests and documentation

## Support

For questions or issues, please refer to the main MAGSASA-CARD project documentation.

## License

This project is part of the MAGSASA-CARD Enhanced Platform.
