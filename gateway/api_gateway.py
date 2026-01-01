"""API Gateway with versioning, transformation, and analytics"""

import logging
import time
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx

logger = logging.getLogger(__name__)


class APIVersion(Enum):
    """Supported API versions"""

    V1 = "v1"
    V2 = "v2"
    BETA = "beta"


@dataclass
class APIEndpoint:
    """API endpoint configuration"""

    path: str
    method: str
    version: APIVersion
    target_url: str
    rate_limit: Optional[int] = None
    auth_required: bool = True
    transform_request: Optional[Callable] = None
    transform_response: Optional[Callable] = None
    cache_ttl: Optional[int] = None
    deprecated: bool = False
    deprecation_date: Optional[datetime] = None


@dataclass
class APIRequest:
    """API request information"""

    request_id: str
    method: str
    path: str
    version: str
    headers: Dict[str, str]
    query_params: Dict[str, str]
    body: Optional[Any]
    client_ip: str
    user_agent: str
    timestamp: datetime


@dataclass
class APIResponse:
    """API response information"""

    request_id: str
    status_code: int
    headers: Dict[str, str]
    body: Optional[Any]
    response_time_ms: float
    timestamp: datetime


class RequestTransformer:
    """Request transformation utilities"""

    @staticmethod
    def transform_v1_to_v2_user_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform v1 user request to v2 format"""
        if not request_data:
            return request_data

        # Example transformation: v1 -> v2
        transformed = request_data.copy()

        # Rename fields
        if "phone" in transformed:
            transformed["phone_number"] = transformed.pop("phone")

        # Add new required fields
        transformed["api_version"] = "v2"

        # Convert format
        if "preferences" in transformed and isinstance(transformed["preferences"], str):
            try:
                transformed["preferences"] = json.loads(transformed["preferences"])
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse preferences JSON: {e}")
                transformed["preferences"] = {}

        return transformed

    @staticmethod
    def transform_v2_to_v1_user_response(
        response_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Transform v2 user response to v1 format"""
        if not response_data:
            return response_data

        transformed = response_data.copy()

        # Rename fields back
        if "phone_number" in transformed:
            transformed["phone"] = transformed.pop("phone_number")

        # Remove v2-specific fields
        transformed.pop("api_version", None)
        transformed.pop("enhanced_features", None)

        # Convert format
        if "preferences" in transformed and isinstance(
            transformed["preferences"], dict
        ):
            transformed["preferences"] = json.dumps(transformed["preferences"])

        return transformed


class ResponseTransformer:
    """Response transformation utilities"""

    @staticmethod
    def add_pagination_metadata(
        response_data: Dict[str, Any], page: int, limit: int, total: int
    ) -> Dict[str, Any]:
        """Add pagination metadata to response"""
        if not isinstance(response_data, dict):
            response_data = {"data": response_data}

        response_data["pagination"] = {
            "current_page": page,
            "per_page": limit,
            "total_items": total,
            "total_pages": (total + limit - 1) // limit,
            "has_next": page * limit < total,
            "has_previous": page > 1,
        }

        return response_data

    @staticmethod
    def add_api_metadata(response_data: Dict[str, Any], version: str) -> Dict[str, Any]:
        """Add API metadata to response"""
        if not isinstance(response_data, dict):
            response_data = {"data": response_data}

        response_data["meta"] = {
            "api_version": version,
            "timestamp": datetime.now().isoformat(),
            "request_id": response_data.get("request_id"),
            "server_time": time.time(),
        }

        return response_data


class APIAnalytics:
    """API usage analytics and monitoring"""

    def __init__(self):
        self.request_metrics = {}
        self.endpoint_metrics = {}
        self.user_metrics = {}
        self.error_metrics = {}

    def record_request(self, api_request: APIRequest, api_response: APIResponse):
        """Record API request/response for analytics"""
        endpoint_key = f"{api_request.method}:{api_request.path}"

        # Endpoint metrics
        if endpoint_key not in self.endpoint_metrics:
            self.endpoint_metrics[endpoint_key] = {
                "total_requests": 0,
                "total_response_time": 0,
                "status_codes": {},
                "versions": {},
                "last_24h_requests": [],
            }

        metrics = self.endpoint_metrics[endpoint_key]
        metrics["total_requests"] += 1
        metrics["total_response_time"] += api_response.response_time_ms

        # Status code distribution
        status = str(api_response.status_code)
        metrics["status_codes"][status] = metrics["status_codes"].get(status, 0) + 1

        # Version distribution
        version = api_request.version
        metrics["versions"][version] = metrics["versions"].get(version, 0) + 1

        # Recent requests (for rate calculation)
        metrics["last_24h_requests"].append(api_request.timestamp)
        cutoff = datetime.now() - timedelta(hours=24)
        metrics["last_24h_requests"] = [
            t for t in metrics["last_24h_requests"] if t > cutoff
        ]

        # Error tracking
        if api_response.status_code >= 400:
            error_key = f"{endpoint_key}:{status}"
            if error_key not in self.error_metrics:
                self.error_metrics[error_key] = {
                    "count": 0,
                    "first_occurrence": api_request.timestamp,
                    "last_occurrence": api_request.timestamp,
                    "sample_requests": [],
                }

            self.error_metrics[error_key]["count"] += 1
            self.error_metrics[error_key]["last_occurrence"] = api_request.timestamp

            # Keep sample requests for debugging
            if len(self.error_metrics[error_key]["sample_requests"]) < 10:
                self.error_metrics[error_key]["sample_requests"].append(
                    {
                        "request_id": api_request.request_id,
                        "timestamp": api_request.timestamp.isoformat(),
                        "client_ip": api_request.client_ip,
                        "user_agent": api_request.user_agent,
                    }
                )

    def get_endpoint_analytics(self, endpoint_key: str) -> Dict[str, Any]:
        """Get analytics for specific endpoint"""
        if endpoint_key not in self.endpoint_metrics:
            return {"error": "Endpoint not found"}

        metrics = self.endpoint_metrics[endpoint_key]

        avg_response_time = (
            metrics["total_response_time"] / metrics["total_requests"]
            if metrics["total_requests"] > 0
            else 0
        )

        requests_24h = len(metrics["last_24h_requests"])
        requests_per_hour = requests_24h / 24 if requests_24h > 0 else 0

        return {
            "endpoint": endpoint_key,
            "total_requests": metrics["total_requests"],
            "avg_response_time_ms": round(avg_response_time, 2),
            "requests_last_24h": requests_24h,
            "requests_per_hour": round(requests_per_hour, 2),
            "status_code_distribution": metrics["status_codes"],
            "version_distribution": metrics["versions"],
            "error_rate": (
                sum(int(code) >= 400 for code in metrics["status_codes"].keys())
                / len(metrics["status_codes"])
                * 100
                if metrics["status_codes"]
                else 0
            ),
        }

    def get_overall_analytics(self) -> Dict[str, Any]:
        """Get overall API analytics"""
        total_requests = sum(
            m["total_requests"] for m in self.endpoint_metrics.values()
        )
        total_errors = sum(
            count
            for error_key, error_data in self.error_metrics.items()
            for count in [error_data["count"]]
        )

        return {
            "total_requests": total_requests,
            "total_endpoints": len(self.endpoint_metrics),
            "total_errors": total_errors,
            "overall_error_rate": (
                (total_errors / total_requests * 100) if total_requests > 0 else 0
            ),
            "top_endpoints": sorted(
                [
                    {
                        "endpoint": endpoint,
                        "requests": metrics["total_requests"],
                        "avg_response_time": metrics["total_response_time"]
                        / metrics["total_requests"],
                    }
                    for endpoint, metrics in self.endpoint_metrics.items()
                ],
                key=lambda x: x["requests"],
                reverse=True,
            )[:10],
            "recent_errors": sorted(
                [
                    {
                        "endpoint": error_key.split(":")[0]
                        + ":"
                        + error_key.split(":")[1],
                        "status_code": error_key.split(":")[2],
                        "count": error_data["count"],
                        "last_occurrence": error_data["last_occurrence"].isoformat(),
                    }
                    for error_key, error_data in self.error_metrics.items()
                ],
                key=lambda x: x["last_occurrence"],
                reverse=True,
            )[:20],
        }


class APIGateway:
    """Main API Gateway implementation"""

    def __init__(self):
        self.app = FastAPI(title="LockBay API Gateway", version="1.0.0")
        self.endpoints: Dict[str, APIEndpoint] = {}
        self.analytics = APIAnalytics()
        self.rate_limiter = {}  # Simple in-memory rate limiter
        self.cache = {}  # Simple in-memory cache
        self.setup_middleware()
        self.setup_routes()

    def setup_middleware(self):
        """Setup FastAPI middleware"""
        # CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Custom middleware for request/response logging
        @self.app.middleware("http")
        async def gateway_middleware(request: Request, call_next):
            start_time = time.time()
            request_id = f"req_{int(time.time() * 1000)}"

            # Create API request object
            api_request = APIRequest(
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                version=self.extract_version(request.url.path),
                headers=dict(request.headers),
                query_params=dict(request.query_params),
                body=None,  # Would need to read body carefully
                client_ip=request.client.host,
                user_agent=request.headers.get("user-agent", ""),
                timestamp=datetime.now(),
            )

            try:
                response = await call_next(request)
                response_time = (time.time() - start_time) * 1000

                # Create API response object
                api_response = APIResponse(
                    request_id=request_id,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    body=None,
                    response_time_ms=response_time,
                    timestamp=datetime.now(),
                )

                # Record analytics
                self.analytics.record_request(api_request, api_response)

                # Add response headers
                response.headers["X-Request-ID"] = request_id
                response.headers["X-Response-Time"] = f"{response_time:.2f}ms"

                return response

            except Exception as e:
                response_time = (time.time() - start_time) * 1000

                api_response = APIResponse(
                    request_id=request_id,
                    status_code=500,
                    headers={},
                    body={"error": str(e)},
                    response_time_ms=response_time,
                    timestamp=datetime.now(),
                )

                self.analytics.record_request(api_request, api_response)

                return JSONResponse(
                    status_code=500,
                    content={
                        "error": "Internal server error",
                        "request_id": request_id,
                    },
                )

    def extract_version(self, path: str) -> str:
        """Extract API version from path"""
        if path.startswith("/api/v1/"):
            return "v1"
        elif path.startswith("/api/v2/"):
            return "v2"
        elif path.startswith("/api/beta/"):
            return "beta"
        else:
            return "unknown"

    def register_endpoint(self, endpoint: APIEndpoint):
        """Register API endpoint"""
        key = f"{endpoint.method}:{endpoint.path}"
        self.endpoints[key] = endpoint
        logger.info(f"Registered endpoint: {key} -> {endpoint.target_url}")

    def setup_routes(self):
        """Setup gateway routes"""

        @self.app.get("/gateway/health")
        async def gateway_health():
            """Gateway health check"""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "total_endpoints": len(self.endpoints),
                "total_requests": sum(
                    m["total_requests"]
                    for m in self.analytics.endpoint_metrics.values()
                ),
            }

        @self.app.get("/gateway/analytics")
        async def get_analytics():
            """Get gateway analytics"""
            return self.analytics.get_overall_analytics()

        @self.app.get("/gateway/analytics/{endpoint_path:path}")
        async def get_endpoint_analytics(endpoint_path: str):
            """Get analytics for specific endpoint"""
            return self.analytics.get_endpoint_analytics(endpoint_path)

        @self.app.api_route(
            "/api/{version}/{path:path}",
            methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        )
        async def gateway_proxy(request: Request, version: str, path: str):
            """Main gateway proxy handler"""
            endpoint_key = f"{request.method}:/api/{version}/{path}"

            # Find matching endpoint
            endpoint = self.endpoints.get(endpoint_key)
            if not endpoint:
                raise HTTPException(status_code=404, detail="Endpoint not found")

            # Check if endpoint is deprecated
            if endpoint.deprecated:
                logger.warning(f"Deprecated endpoint accessed: {endpoint_key}")
                # Could add deprecation headers here

            # Rate limiting
            if endpoint.rate_limit:
                if not await self.check_rate_limit(
                    request.client.host, endpoint.rate_limit
                ):
                    raise HTTPException(status_code=429, detail="Rate limit exceeded")

            # Authentication check
            if endpoint.auth_required:
                if not await self.verify_authentication(request):
                    raise HTTPException(
                        status_code=401, detail="Authentication required"
                    )

            # Check cache
            if endpoint.cache_ttl:
                cache_key = f"{endpoint_key}:{hash(str(request.query_params))}"
                cached_response = self.cache.get(cache_key)
                if cached_response and cached_response["expires"] > datetime.now():
                    return cached_response["data"]

            # Transform request if needed
            request_body = None
            if request.method in ["POST", "PUT", "PATCH"]:
                try:
                    request_body = await request.json()
                    if endpoint.transform_request:
                        request_body = endpoint.transform_request(request_body)
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Failed to parse request body as JSON: {e}")
                    request_body = None

            # Proxy request to backend
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.request(
                        method=request.method,
                        url=f"{endpoint.target_url}/{path}",
                        params=request.query_params,
                        headers={
                            k: v
                            for k, v in request.headers.items()
                            if k.lower() not in ["host", "content-length"]
                        },
                        json=request_body if request_body else None,
                        timeout=30.0,
                    )

                    # Get response data
                    try:
                        response_data = response.json()
                    except (json.JSONDecodeError, ValueError) as e:
                        logger.debug(f"Response is not JSON, using text: {e}")
                        response_data = response.text

                    # Transform response if needed
                    if endpoint.transform_response and isinstance(response_data, dict):
                        response_data = endpoint.transform_response(response_data)

                    # Add API metadata
                    if isinstance(response_data, dict):
                        response_data = ResponseTransformer.add_api_metadata(
                            response_data, version
                        )

                    # Cache response if configured
                    if endpoint.cache_ttl and response.status_code == 200:
                        cache_key = f"{endpoint_key}:{hash(str(request.query_params))}"
                        self.cache[cache_key] = {
                            "data": response_data,
                            "expires": datetime.now()
                            + timedelta(seconds=endpoint.cache_ttl),
                        }

                    return JSONResponse(
                        status_code=response.status_code, content=response_data
                    )

            except httpx.TimeoutException:
                raise HTTPException(status_code=504, detail="Backend timeout")
            except httpx.ConnectError:
                raise HTTPException(status_code=503, detail="Backend unavailable")
            except Exception as e:
                logger.error(f"Proxy error: {e}")
                raise HTTPException(status_code=502, detail="Backend error")

    async def check_rate_limit(self, client_ip: str, limit: int) -> bool:
        """Check rate limit for client"""
        now = datetime.now()
        window_start = now - timedelta(minutes=1)

        if client_ip not in self.rate_limiter:
            self.rate_limiter[client_ip] = []

        # Clean old requests
        self.rate_limiter[client_ip] = [
            req_time
            for req_time in self.rate_limiter[client_ip]
            if req_time > window_start
        ]

        # Check limit
        if len(self.rate_limiter[client_ip]) >= limit:
            return False

        # Record request
        self.rate_limiter[client_ip].append(now)
        return True

    async def verify_authentication(self, request: Request) -> bool:
        """Verify request authentication"""
        # Simple token-based auth
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return False

        token = auth_header[7:]  # Remove "Bearer "

        # In production, verify JWT token or API key
        return len(token) > 10  # Mock validation


# Example endpoint registration
def setup_api_endpoints(gateway: APIGateway):
    """Setup API endpoint configurations"""

    # User endpoints
    gateway.register_endpoint(
        APIEndpoint(
            path="/api/v1/users",
            method="GET",
            version=APIVersion.V1,
            target_url="http://localhost:5000",
            rate_limit=100,
            cache_ttl=300,
        )
    )

    gateway.register_endpoint(
        APIEndpoint(
            path="/api/v2/users",
            method="GET",
            version=APIVersion.V2,
            target_url="http://localhost:5000",
            rate_limit=100,
            transform_response=ResponseTransformer.add_api_metadata,
        )
    )

    # Escrow endpoints
    gateway.register_endpoint(
        APIEndpoint(
            path="/api/v1/escrows",
            method="POST",
            version=APIVersion.V1,
            target_url="http://localhost:5000",
            rate_limit=50,
            transform_request=RequestTransformer.transform_v1_to_v2_user_request,
        )
    )


# Global gateway instance
api_gateway = None


def initialize_api_gateway():
    """Initialize API Gateway"""
    global api_gateway
    api_gateway = APIGateway()
    setup_api_endpoints(api_gateway)
    return api_gateway.app


def get_gateway_app():
    """Get FastAPI app for gateway"""
    if not api_gateway:
        return initialize_api_gateway()
    return api_gateway.app
