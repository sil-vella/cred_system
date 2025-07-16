# Stripe Module Documentation

## Overview

The Stripe Module provides secure payment processing integration for the credit system. It handles payment intents, webhook processing, and credit purchases while maintaining security best practices and using the database queue system.

## Features

### ✅ Secure Payment Processing
- Payment intent creation and confirmation
- Webhook signature verification
- PCI-compliant payment handling
- Automatic credit conversion

### ✅ Database Queue Integration
- All database operations go through the queue system
- Transaction records stored securely
- Failed payment tracking
- Dispute handling

### ✅ Webhook Processing
- Payment success/failure events
- Dispute creation events
- Secure signature validation
- Automatic credit updates

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Mgmt     │    │     Wallet      │    │    Stripe       │
│   Module        │    │    Module       │    │    Module       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │  Transactions   │
                    │    Module       │
                    └─────────────────┘
```

## API Endpoints

### 1. Create Payment Intent
```http
POST /stripe/create-payment-intent
Content-Type: application/json

{
    "user_id": "user123",
    "amount": 10.00,
    "currency": "usd"
}
```

**Response:**
```json
{
    "success": true,
    "client_secret": "pi_xxx_secret_xxx",
    "payment_intent_id": "pi_xxx",
    "amount": 10.00,
    "currency": "usd"
}
```

**Error Responses:**
```json
{
    "success": false,
    "error": "Card declined",
    "error_code": "card_declined",
    "decline_code": "insufficient_funds",
    "message": "Your card was declined."
}
```

```json
{
    "success": false,
    "error": "Invalid request parameters",
    "error_code": "parameter_invalid",
    "param": "amount",
    "message": "Invalid amount"
}
```

### 2. Confirm Payment
```http
POST /stripe/confirm-payment
Content-Type: application/json

{
    "payment_intent_id": "pi_xxx"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Payment confirmed and credits added",
    "data": {
        "transaction_id": "txn_xxx",
        "credits_purchased": 100,
        "amount_paid": 10.00,
        "payment_intent_id": "pi_xxx"
    }
}
```

### 3. Get Credit Packages
```http
GET /stripe/credit-packages
```

**Response:**
```json
{
    "success": true,
    "packages": [
        {
            "id": "basic",
            "name": "Basic Package",
            "credits": 100,
            "price_usd": 10.00,
            "description": "100 credits for $10"
        },
        {
            "id": "standard",
            "name": "Standard Package",
            "credits": 500,
            "price_usd": 45.00,
            "description": "500 credits for $45 (10% discount)"
        }
    ]
}
```

### 4. Get Payment Status
```http
GET /stripe/payment-status/{payment_intent_id}
```

**Response:**
```json
{
    "success": true,
    "status": "succeeded",
    "amount": 10.00,
    "currency": "usd",
    "created": 1640995200
}
```

### 5. Create Customer
```http
POST /stripe/customers
Content-Type: application/json

{
    "user_id": "user123",
    "email": "user@example.com",
    "name": "John Doe",
    "phone": "+1234567890"
}
```

**Response:**
```json
{
    "success": true,
    "customer_id": "cus_xxx",
    "email": "user@example.com",
    "created": 1640995200
}
```

### 6. Get Customer
```http
GET /stripe/customers/{customer_id}
```

**Response:**
```json
{
    "success": true,
    "customer": {
        "id": "cus_xxx",
        "email": "user@example.com",
        "name": "John Doe",
        "phone": "+1234567890",
        "created": 1640995200,
        "metadata": {
            "user_id": "user123",
            "source": "credit_system"
        }
    }
}
```

### 7. List Payment Methods
```http
GET /stripe/payment-methods?customer_id=cus_xxx
```

**Response:**
```json
{
    "success": true,
    "payment_methods": [
        {
            "id": "pm_xxx",
            "type": "card",
            "card": {
                "brand": "visa",
                "last4": "4242",
                "exp_month": 12,
                "exp_year": 2025
            },
            "created": 1640995200
        }
    ]
}
```

### 8. Get Payment Method
```http
GET /stripe/payment-methods/{payment_method_id}
```

**Response:**
```json
{
    "success": true,
    "payment_method": {
        "id": "pm_xxx",
        "type": "card",
        "card": {
            "brand": "visa",
            "last4": "4242",
            "exp_month": 12,
            "exp_year": 2025
        },
        "customer": "cus_xxx",
        "created": 1640995200
    }
}
```

### 9. Webhook Endpoint
```http
POST /stripe/webhook
Content-Type: application/json
Stripe-Signature: t=xxx,v1=xxx

{
    "type": "payment_intent.succeeded",
    "data": {
        "object": {
            "id": "pi_xxx",
            "status": "succeeded",
            "metadata": {
                "user_id": "user123",
                "amount_usd": "10.00"
            }
        }
    }
}
```

## Configuration

### Configuration

The Stripe module uses the same secure configuration pattern as the rest of the system:

#### Vault Configuration (Production)
```bash
# Vault path: flask-app/stripe
{
  "secret_key": "sk_test_xxx",
  "publishable_key": "pk_test_xxx", 
  "webhook_secret": "whsec_xxx"
}
```

#### Secret Files (Development/Testing)
```bash
# /secrets/stripe_secret_key
sk_test_xxx

# /secrets/stripe_publishable_key  
pk_test_xxx

# /secrets/stripe_webhook_secret
whsec_xxx

# /secrets/stripe_api_version
2023-10-16
```

#### Environment Variables (Fallback)
```bash
# Only used if Vault and secret files are unavailable
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_API_VERSION=2023-10-16
```

### Security Features

1. **Webhook Signature Verification**
   - Validates Stripe webhook signatures
   - Prevents replay attacks
   - Ensures webhook authenticity

2. **PCI Compliance**
   - No sensitive data stored locally
   - All payment data handled by Stripe
   - Secure API key management

3. **Database Security**
   - Encrypted sensitive fields
   - Queue-based operations
   - Audit trail for all transactions

## Database Collections

### credit_purchases
```json
{
    "_id": "ObjectId",
    "user_id": "user123",
    "payment_intent_id": "pi_xxx",
    "amount_usd": 10.00,
    "credits_purchased": 100,
    "status": "completed",
    "payment_method": "stripe",
    "created_at": "2024-01-01T00:00:00Z",
    "stripe_payment_intent": "pi_xxx"
}
```

### failed_payments
```json
{
    "_id": "ObjectId",
    "user_id": "user123",
    "payment_intent_id": "pi_xxx",
    "status": "failed",
    "created_at": "2024-01-01T00:00:00Z",
    "failure_reason": "Insufficient funds"
}
```

### disputes
```json
{
    "_id": "ObjectId",
    "payment_intent_id": "pi_xxx",
    "dispute_id": "dp_xxx",
    "amount": 1000,
    "reason": "fraudulent",
    "status": "needs_response",
    "created_at": "2024-01-01T00:00:00Z"
}
```

### stripe_customers
```json
{
    "_id": "ObjectId",
    "user_id": "user123",
    "stripe_customer_id": "cus_xxx",
    "email": "user@example.com",
    "name": "John Doe",
    "created_at": "2024-01-01T00:00:00Z"
}
```

## Credit Conversion

The module uses a simple credit conversion formula:
- **$1 USD = 10 credits**
- Configurable in `_calculate_credits_from_usd()` method
- Can be extended for tiered pricing

## Error Handling

### Common Error Responses

```json
{
    "success": false,
    "error": "Stripe is not configured"
}
```

```json
{
    "success": false,
    "error": "Payment not successful. Status: requires_payment_method"
}
```

```json
{
    "success": false,
    "error": "Invalid Stripe signature"
}
```

## Testing

Run the test suite:
```bash
cd python_base_04_k8s/core/modules/stripe_module
python test_stripe.py
```

## Integration with Other Modules

### Transactions Module
- Creates transaction records
- Handles refund processing
- Provides transaction history

### User Management Module
- Validates user existence
- Updates user wallet balances
- Tracks user payment history

### Wallet Module
- Updates credit balances
- Provides balance information
- Handles credit calculations

## Security Checklist

- [x] Webhook signature verification
- [x] PCI-compliant payment processing
- [x] Encrypted database storage
- [x] Queue-based database operations
- [x] Audit trail for all transactions
- [x] Secure API key management
- [x] Error handling and logging
- [x] Dispute handling
- [x] Failed payment tracking

## Deployment Notes

1. **Environment Setup**
   - Set Stripe API keys in environment
   - Configure webhook endpoint in Stripe dashboard
   - Test webhook signature verification

2. **Database Setup**
   - Ensure collections exist
   - Set up proper indexes
   - Configure encryption for sensitive fields

3. **Monitoring**
   - Monitor webhook delivery
   - Track failed payments
   - Monitor credit conversion accuracy

## Troubleshooting

### Common Issues

1. **Webhook Not Receiving Events**
   - Check webhook endpoint URL
   - Verify signature secret
   - Check firewall settings

2. **Payment Intent Creation Fails**
   - Verify Stripe API key
   - Check amount format (cents)
   - Validate currency code

3. **Credits Not Added After Payment**
   - Check webhook processing
   - Verify user wallet exists
   - Check database queue status

### Debug Commands

```bash
# Check module health
curl http://localhost:8080/modules/stripe/health

# Test credit packages
curl http://localhost:8080/stripe/credit-packages

# Check database queue status
curl http://localhost:8080/modules/transactions/health
``` 