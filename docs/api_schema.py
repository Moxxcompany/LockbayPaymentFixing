"""OpenAPI/Swagger API documentation schema"""

from typing import Dict, Any
import json


class OpenAPISchema:
    """Comprehensive OpenAPI 3.0 schema for the Telegram Escrow Bot API"""

    @staticmethod
    def generate_schema() -> Dict[str, Any]:
        """Generate complete OpenAPI 3.0 schema"""
        return {
            "openapi": "3.0.3",
            "info": {
                "title": "LockBay Telegram Escrow Bot API",
                "description": """
                # LockBay API Documentation
                
                LockBay is a comprehensive cryptocurrency escrow service that provides secure, trust-minimized transactions globally. Our API supports multiple cryptocurrencies, instant fiat conversions, and automated escrow management.
                
                ## Key Features
                - 🔐 **Secure Escrow**: Trust-minimized cryptocurrency transactions
                - 💱 **Multi-Currency**: Support for 9 cryptocurrencies (BTC, ETH, LTC, DOGE, BCH, BSC, TRX, USDT-ERC20, USDT-TRC20)
                - 🌍 **Global Reach**: Available worldwide with specialized NGN integration
                - ⚡ **Instant Processing**: 5-minute average transaction times
                - 🛡️ **Advanced Security**: Multi-layer security with rate limiting and fraud detection
                
                ## Authentication
                All API endpoints require proper authentication. Webhook endpoints use HMAC-SHA256 signature verification.
                
                ## Rate Limiting
                API requests are rate-limited per user/IP to ensure fair usage and system stability.
                """,
                "version": "1.0.0",
                "contact": {
                    "name": "LockBay Support",
                    "email": "support@lockbay.com",
                    "url": "https://lockbay.com/support",
                },
                "license": {
                    "name": "Proprietary",
                    "url": "https://lockbay.com/license",
                },
            },
            "servers": [
                {"url": "https://api.lockbay.com", "description": "Production server"},
                {
                    "url": "https://staging-api.lockbay.com",
                    "description": "Staging server",
                },
            ],
            "paths": OpenAPISchema._generate_paths(),
            "components": {
                "schemas": OpenAPISchema._generate_schemas(),
                "securitySchemes": {
                    "ApiKeyAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-API-Key",
                    },
                    "WebhookSignature": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-Signature",
                    },
                },
                "responses": OpenAPISchema._generate_responses(),
                "parameters": OpenAPISchema._generate_parameters(),
            },
            "security": [{"ApiKeyAuth": []}],
            "tags": [
                {
                    "name": "Webhooks",
                    "description": "Webhook endpoints for external service notifications",
                },
                {"name": "Health", "description": "System health and status endpoints"},
                {"name": "Users", "description": "User management operations"},
                {"name": "Escrow", "description": "Escrow management operations"},
                {"name": "Wallets", "description": "Wallet and balance operations"},
                {
                    "name": "Transactions",
                    "description": "Transaction history and monitoring",
                },
                {"name": "Payments", "description": "Payment processing operations"},
            ],
        }

    @staticmethod
    def _generate_paths() -> Dict[str, Any]:
        """Generate API paths/endpoints"""
        return {
            "/": {
                "get": {
                    "tags": ["Health"],
                    "summary": "Health check endpoint",
                    "description": "Check if the API is running and healthy",
                    "responses": {
                        "200": {
                            "description": "API is healthy",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/HealthResponse"
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/webhook": {
                "post": {
                    "tags": ["Webhooks"],
                    "summary": "Telegram webhook endpoint",
                    "description": "Receives updates from Telegram Bot API",
                    "security": [{"WebhookSignature": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/TelegramUpdate"
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"$ref": "#/components/responses/WebhookSuccess"},
                        "400": {"$ref": "#/components/responses/ValidationError"},
                        "401": {"$ref": "#/components/responses/Unauthorized"},
                        "429": {"$ref": "#/components/responses/RateLimit"},
                    },
                }
            },
            "/webhook/blockbee": {
                "post": {
                    "tags": ["Webhooks"],
                    "summary": "BlockBee payment notification webhook",
                    "description": "Receives cryptocurrency payment confirmations from BlockBee",
                    "security": [{"WebhookSignature": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/BlockBeeWebhook"
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"$ref": "#/components/responses/WebhookSuccess"},
                        "400": {"$ref": "#/components/responses/ValidationError"},
                    },
                }
            },
            "/webhook/fincra": {
                "post": {
                    "tags": ["Webhooks"],
                    "summary": "Fincra payment notification webhook",
                    "description": "Receives NGN payment confirmations from Fincra",
                    "security": [{"WebhookSignature": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/FincraWebhook"}
                            }
                        },
                    },
                    "responses": {
                        "200": {"$ref": "#/components/responses/WebhookSuccess"},
                        "400": {"$ref": "#/components/responses/ValidationError"},
                    },
                }
            },
            "/api/v1/users/{user_id}": {
                "get": {
                    "tags": ["Users"],
                    "summary": "Get user information",
                    "description": "Retrieve user profile and statistics",
                    "parameters": [{"$ref": "#/components/parameters/UserId"}],
                    "responses": {
                        "200": {
                            "description": "User information retrieved",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/UserResponse"
                                    }
                                }
                            },
                        },
                        "404": {"$ref": "#/components/responses/NotFound"},
                    },
                }
            },
            "/api/v1/escrows": {
                "get": {
                    "tags": ["Escrow"],
                    "summary": "List escrows",
                    "description": "Get paginated list of escrows",
                    "parameters": [
                        {"$ref": "#/components/parameters/Page"},
                        {"$ref": "#/components/parameters/Limit"},
                        {"$ref": "#/components/parameters/Status"},
                    ],
                    "responses": {
                        "200": {
                            "description": "Escrows retrieved",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/EscrowListResponse"
                                    }
                                }
                            },
                        }
                    },
                },
                "post": {
                    "tags": ["Escrow"],
                    "summary": "Create new escrow",
                    "description": "Create a new escrow transaction",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/CreateEscrowRequest"
                                }
                            }
                        },
                    },
                    "responses": {
                        "201": {
                            "description": "Escrow created",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/EscrowResponse"
                                    }
                                }
                            },
                        },
                        "400": {"$ref": "#/components/responses/ValidationError"},
                    },
                },
            },
            "/api/v1/wallets/{user_id}/balance": {
                "get": {
                    "tags": ["Wallets"],
                    "summary": "Get wallet balance",
                    "description": "Retrieve user's wallet balances",
                    "parameters": [{"$ref": "#/components/parameters/UserId"}],
                    "responses": {
                        "200": {
                            "description": "Wallet balance retrieved",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/WalletBalanceResponse"
                                    }
                                }
                            },
                        }
                    },
                }
            },
        }

    @staticmethod
    def _generate_schemas() -> Dict[str, Any]:
        """Generate data schemas"""
        return {
            "HealthResponse": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "example": "healthy"},
                    "timestamp": {"type": "string", "format": "date-time"},
                    "version": {"type": "string", "example": "1.0.0"},
                    "uptime": {"type": "number", "example": 3600.5},
                },
            },
            "StandardResponse": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["success", "error", "warning", "partial"],
                    },
                    "message": {"type": "string"},
                    "data": {"type": "object"},
                    "error": {"$ref": "#/components/schemas/ErrorDetails"},
                    "metadata": {"type": "object"},
                    "timestamp": {"type": "string", "format": "date-time"},
                },
            },
            "ErrorDetails": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "example": "VALIDATION_ERROR"},
                    "category": {"type": "string", "example": "validation"},
                    "severity": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                    },
                    "details": {"type": "object"},
                    "retry_after": {"type": "integer"},
                    "recoverable": {"type": "boolean"},
                },
            },
            "TelegramUpdate": {
                "type": "object",
                "properties": {
                    "update_id": {"type": "integer"},
                    "message": {"$ref": "#/components/schemas/TelegramMessage"},
                    "callback_query": {"type": "object"},
                },
            },
            "TelegramMessage": {
                "type": "object",
                "properties": {
                    "message_id": {"type": "integer"},
                    "from": {"$ref": "#/components/schemas/TelegramUser"},
                    "chat": {"$ref": "#/components/schemas/TelegramChat"},
                    "text": {"type": "string"},
                },
            },
            "TelegramUser": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "username": {"type": "string"},
                    "first_name": {"type": "string"},
                    "last_name": {"type": "string"},
                },
            },
            "TelegramChat": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "type": {
                        "type": "string",
                        "enum": ["private", "group", "supergroup"],
                    },
                },
            },
            "BlockBeeWebhook": {
                "type": "object",
                "properties": {
                    "address": {"type": "string", "description": "Payment address"},
                    "value": {
                        "type": "integer",
                        "description": "Amount in smallest unit",
                    },
                    "confirmations": {"type": "integer"},
                    "txid_out": {"type": "string", "description": "Transaction hash"},
                    "coin": {"type": "string", "description": "Cryptocurrency symbol"},
                },
                "required": ["address", "value", "confirmations", "txid_out"],
            },
            "FincraWebhook": {
                "type": "object",
                "properties": {
                    "event": {"type": "string", "example": "charge.success"},
                    "data": {
                        "type": "object",
                        "properties": {
                            "reference": {"type": "string"},
                            "amount": {"type": "number"},
                            "currency": {"type": "string"},
                            "status": {"type": "string"},
                        },
                    },
                },
            },
            "UserResponse": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "telegram_id": {"type": "string"},
                    "username": {"type": "string"},
                    "email": {"type": "string", "format": "email"},
                    "email_verified": {"type": "boolean"},
                    "phone_verified": {"type": "boolean"},
                    "reputation_score": {"type": "number"},
                    "total_trades": {"type": "integer"},
                    "successful_trades": {"type": "integer"},
                    "created_at": {"type": "string", "format": "date-time"},
                },
            },
            "CreateEscrowRequest": {
                "type": "object",
                "properties": {
                    "buyer_identifier": {
                        "type": "string",
                        "description": "Username or email",
                    },
                    "amount": {"type": "number", "minimum": 5.0},
                    "currency": {
                        "type": "string",
                        "enum": ["USD", "BTC", "ETH", "LTC"],
                    },
                    "title": {"type": "string", "maxLength": 100},
                    "description": {"type": "string", "maxLength": 500},
                    "escrow_fee_payer": {
                        "type": "string",
                        "enum": ["seller", "buyer", "split"],
                    },
                },
                "required": ["buyer_identifier", "amount", "currency", "title"],
            },
            "EscrowResponse": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "seller_id": {"type": "integer"},
                    "buyer_id": {"type": "integer"},
                    "amount": {"type": "number"},
                    "currency": {"type": "string"},
                    "status": {"type": "string"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "created_at": {"type": "string", "format": "date-time"},
                    "expires_at": {"type": "string", "format": "date-time"},
                },
            },
            "EscrowListResponse": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/EscrowResponse"},
                    },
                    "total": {"type": "integer"},
                    "page": {"type": "integer"},
                    "per_page": {"type": "integer"},
                    "total_pages": {"type": "integer"},
                },
            },
            "WalletBalanceResponse": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer"},
                    "balances": {
                        "type": "object",
                        "properties": {
                            "USD": {"type": "number"},
                            "BTC": {"type": "number"},
                            "ETH": {"type": "number"},
                            "USDT": {"type": "number"},
                        },
                    },
                    "total_usd_value": {"type": "number"},
                    "last_updated": {"type": "string", "format": "date-time"},
                },
            },
        }

    @staticmethod
    def _generate_responses() -> Dict[str, Any]:
        """Generate reusable response definitions"""
        return {
            "WebhookSuccess": {
                "description": "Webhook processed successfully",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "status": {"type": "string", "example": "success"},
                                "message": {
                                    "type": "string",
                                    "example": "Webhook processed",
                                },
                            },
                        }
                    }
                },
            },
            "ValidationError": {
                "description": "Request validation failed",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/StandardResponse"}
                    }
                },
            },
            "Unauthorized": {
                "description": "Authentication required",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/StandardResponse"}
                    }
                },
            },
            "NotFound": {
                "description": "Resource not found",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/StandardResponse"}
                    }
                },
            },
            "RateLimit": {
                "description": "Rate limit exceeded",
                "headers": {
                    "X-RateLimit-Limit": {
                        "description": "Request limit per window",
                        "schema": {"type": "integer"},
                    },
                    "X-RateLimit-Remaining": {
                        "description": "Remaining requests in window",
                        "schema": {"type": "integer"},
                    },
                    "X-RateLimit-Reset": {
                        "description": "Window reset time",
                        "schema": {"type": "integer"},
                    },
                },
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/StandardResponse"}
                    }
                },
            },
        }

    @staticmethod
    def _generate_parameters() -> Dict[str, Any]:
        """Generate reusable parameter definitions"""
        return {
            "UserId": {
                "name": "user_id",
                "in": "path",
                "required": True,
                "schema": {"type": "integer"},
                "description": "User ID",
            },
            "Page": {
                "name": "page",
                "in": "query",
                "schema": {"type": "integer", "minimum": 1, "default": 1},
                "description": "Page number",
            },
            "Limit": {
                "name": "limit",
                "in": "query",
                "schema": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 20,
                },
                "description": "Items per page",
            },
            "Status": {
                "name": "status",
                "in": "query",
                "schema": {
                    "type": "string",
                    "enum": ["pending", "active", "completed", "cancelled", "disputed"],
                },
                "description": "Filter by status",
            },
        }


def generate_openapi_json() -> str:
    """Generate OpenAPI JSON string"""
    schema = OpenAPISchema.generate_schema()
    return json.dumps(schema, indent=2)


def generate_openapi_yaml() -> str:
    """Generate OpenAPI YAML string"""
    try:
        import yaml

        schema = OpenAPISchema.generate_schema()
        return yaml.dump(schema, default_flow_style=False, sort_keys=False)
    except ImportError:
        return "# YAML generation requires PyYAML package\n# pip install PyYAML"


def save_api_docs():
    """Save API documentation to files"""
    # Save JSON version
    with open("docs/openapi.json", "w") as f:
        f.write(generate_openapi_json())

    # Save YAML version
    with open("docs/openapi.yaml", "w") as f:
        f.write(generate_openapi_yaml())

    print("✅ API documentation saved to docs/openapi.json and docs/openapi.yaml")


if __name__ == "__main__":
    save_api_docs()
