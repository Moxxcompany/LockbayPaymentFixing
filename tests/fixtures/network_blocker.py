"""
Network Blocker Fixtures
Prevent real network calls during testing
"""

import pytest
import socket
import ssl
import urllib3
import aiohttp
from typing import Optional, List, Dict, Any, Callable
from unittest.mock import patch, MagicMock
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class NetworkBlocker:
    """
    Comprehensive network call blocker for testing
    
    Features:
    - Block socket connections 
    - Block HTTP/HTTPS requests (requests, aiohttp, urllib3)
    - Allow specific domains/IPs (whitelist)
    - Provide meaningful error messages for blocked calls
    - Support for both sync and async HTTP clients
    """
    
    def __init__(self, 
                 whitelist_domains: Optional[List[str]] = None,
                 whitelist_ips: Optional[List[str]] = None,
                 allow_localhost: bool = True):
        """
        Initialize network blocker
        
        Args:
            whitelist_domains: Domains to allow (e.g., ['test.lockbay.io'])
            whitelist_ips: IPs to allow (e.g., ['127.0.0.1'])  
            allow_localhost: Allow localhost/127.0.0.1 connections
        """
        self.whitelist_domains = whitelist_domains or []
        self.whitelist_ips = whitelist_ips or []
        self.allow_localhost = allow_localhost
        
        # Track blocked calls for debugging
        self.blocked_calls = []
        self.patches = []
        
        # Original functions to restore
        self.original_socket_connect = socket.socket.connect
        self.original_socket_connect_ex = socket.socket.connect_ex
        self.original_ssl_create_default_context = ssl.create_default_context
        
    def __enter__(self):
        """Start network blocking"""
        
        # Patch socket connections
        self.patches.extend([
            patch.object(socket.socket, 'connect', side_effect=self._block_socket_connect),
            patch.object(socket.socket, 'connect_ex', side_effect=self._block_socket_connect_ex),
            patch('socket.create_connection', side_effect=self._block_create_connection),
            patch('socket.getaddrinfo', side_effect=self._block_getaddrinfo),
        ])
        
        # Patch HTTP libraries
        self.patches.extend([
            patch('requests.Session.request', side_effect=self._block_requests),
            patch('requests.get', side_effect=self._block_requests),
            patch('requests.post', side_effect=self._block_requests), 
            patch('requests.put', side_effect=self._block_requests),
            patch('requests.delete', side_effect=self._block_requests),
            patch('requests.patch', side_effect=self._block_requests),
            patch('requests.head', side_effect=self._block_requests),
            patch('requests.options', side_effect=self._block_requests),
        ])
        
        # Patch urllib3
        self.patches.extend([
            patch('urllib3.PoolManager.urlopen', side_effect=self._block_urllib3),
            patch('urllib3.HTTPSConnectionPool._make_request', side_effect=self._block_urllib3),
            patch('urllib3.HTTPConnectionPool._make_request', side_effect=self._block_urllib3),
        ])
        
        # Patch aiohttp
        self.patches.extend([
            patch('aiohttp.ClientSession._request', side_effect=self._block_aiohttp),
            patch('aiohttp.ClientSession.get', side_effect=self._block_aiohttp),
            patch('aiohttp.ClientSession.post', side_effect=self._block_aiohttp),
            patch('aiohttp.ClientSession.put', side_effect=self._block_aiohttp),
            patch('aiohttp.ClientSession.delete', side_effect=self._block_aiohttp),
            patch('aiohttp.ClientSession.patch', side_effect=self._block_aiohttp),
            patch('aiohttp.ClientSession.head', side_effect=self._block_aiohttp),
            patch('aiohttp.ClientSession.options', side_effect=self._block_aiohttp),
        ])
        
        # Start all patches
        active_patches = []
        for patch_obj in self.patches:
            try:
                patch_obj.start()
                active_patches.append(patch_obj)
            except Exception as e:
                logger.debug(f"Could not start network patch: {e}")
        
        self.patches = active_patches
        logger.info(f"🚫 Network calls blocked (whitelisted domains: {self.whitelist_domains})")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop network blocking"""
        for patch_obj in self.patches:
            try:
                patch_obj.stop()
            except Exception as e:
                logger.debug(f"Error stopping network patch: {e}")
        
        self.patches.clear()
        logger.info("🌐 Network calls restored")
        
        if self.blocked_calls:
            logger.info(f"🚫 Blocked {len(self.blocked_calls)} network calls during test")
            for call in self.blocked_calls:
                logger.debug(f"  - {call}")
    
    def _is_allowed_host(self, host: str) -> bool:
        """Check if host is allowed by whitelist rules"""
        if not host:
            return False
            
        # Check localhost rules
        if self.allow_localhost and (
            host in ['localhost', '127.0.0.1', '::1'] or 
            host.startswith('127.') or
            host.startswith('192.168.') or  # Common test networks
            host.startswith('10.') or
            host.endswith('.local')
        ):
            return True
        
        # Check IP whitelist
        if host in self.whitelist_ips:
            return True
            
        # Check domain whitelist
        for domain in self.whitelist_domains:
            if host == domain or host.endswith('.' + domain):
                return True
                
        return False
    
    def _block_socket_connect(self, address):
        """Block socket.connect() calls"""
        host = address[0] if isinstance(address, (tuple, list)) else str(address)
        
        if self._is_allowed_host(host):
            return self.original_socket_connect(address)
        
        blocked_call = f"socket.connect({address})"
        self.blocked_calls.append(blocked_call)
        raise ConnectionError(f"Network call blocked in test: {blocked_call}")
    
    def _block_socket_connect_ex(self, address):
        """Block socket.connect_ex() calls"""
        host = address[0] if isinstance(address, (tuple, list)) else str(address)
        
        if self._is_allowed_host(host):
            return self.original_socket_connect_ex(address)
        
        blocked_call = f"socket.connect_ex({address})"
        self.blocked_calls.append(blocked_call)
        # connect_ex returns error code instead of raising
        return 111  # ECONNREFUSED
    
    def _block_create_connection(self, address, timeout=None, source_address=None):
        """Block socket.create_connection() calls"""
        host = address[0] if isinstance(address, (tuple, list)) else str(address)
        
        if self._is_allowed_host(host):
            import socket
            return socket.create_connection(address, timeout, source_address)
        
        blocked_call = f"socket.create_connection({address})"
        self.blocked_calls.append(blocked_call)
        raise ConnectionError(f"Network call blocked in test: {blocked_call}")
    
    def _block_getaddrinfo(self, host, port, family=0, type=0, proto=0, flags=0):
        """Block socket.getaddrinfo() calls"""
        if self._is_allowed_host(host):
            import socket
            return socket.getaddrinfo(host, port, family, type, proto, flags)
        
        blocked_call = f"socket.getaddrinfo({host}:{port})"
        self.blocked_calls.append(blocked_call)
        raise ConnectionError(f"Network call blocked in test: {blocked_call}")
    
    def _block_requests(self, *args, **kwargs):
        """Block requests library calls"""
        # Extract URL from args/kwargs
        url = None
        if args and len(args) > 0:
            if len(args) > 1:  # method, url, ...
                url = args[1] 
            else:
                url = args[0]  # url only
        elif 'url' in kwargs:
            url = kwargs['url']
        
        if url:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                host = parsed.hostname
                
                if self._is_allowed_host(host):
                    # This would normally call the real requests, but in tests
                    # we want to use provider fakes instead
                    pass  # Fall through to blocking
            except Exception:
                pass  # Fall through to blocking
        
        blocked_call = f"requests call to {url}"
        self.blocked_calls.append(blocked_call)
        raise ConnectionError(f"Network call blocked in test: {blocked_call}. Use provider fakes instead.")
    
    def _block_urllib3(self, *args, **kwargs):
        """Block urllib3 calls"""
        blocked_call = f"urllib3 call"
        self.blocked_calls.append(blocked_call)
        raise ConnectionError(f"Network call blocked in test: {blocked_call}. Use provider fakes instead.")
    
    async def _block_aiohttp(self, *args, **kwargs):
        """Block aiohttp calls"""
        # Extract URL from args/kwargs
        url = None
        if args and len(args) > 0:
            url = args[0] if len(args) == 1 else args[1]  # url or method, url
        elif 'url' in kwargs:
            url = kwargs['url']
        
        blocked_call = f"aiohttp call to {url}"
        self.blocked_calls.append(blocked_call)
        raise ConnectionError(f"Network call blocked in test: {blocked_call}. Use provider fakes instead.")
    
    def get_blocked_calls(self) -> List[str]:
        """Get list of blocked network calls"""
        return self.blocked_calls.copy()
    
    def clear_blocked_calls(self):
        """Clear the list of blocked calls"""
        self.blocked_calls.clear()


@contextmanager
def block_network_calls(
    whitelist_domains: Optional[List[str]] = None,
    whitelist_ips: Optional[List[str]] = None,
    allow_localhost: bool = True
):
    """
    Context manager for blocking network calls
    
    Usage:
        with block_network_calls(whitelist_domains=['api.test.com']) as blocker:
            # All network calls blocked except to api.test.com
            blocked = blocker.get_blocked_calls()  # Check what was blocked
    """
    blocker = NetworkBlocker(whitelist_domains, whitelist_ips, allow_localhost)
    with blocker:
        yield blocker


@pytest.fixture
def network_blocker():
    """
    Pytest fixture for network blocking
    
    Usage:
        def test_something(network_blocker):
            with network_blocker(allow_localhost=False) as blocker:
                # Test with all network calls blocked
                pass
    """
    return block_network_calls


@pytest.fixture
def strict_network_blocker():
    """
    Pytest fixture for strict network blocking (no localhost allowed)
    """
    with block_network_calls(allow_localhost=False) as blocker:
        yield blocker


@pytest.fixture
def production_network_blocker():
    """
    Pytest fixture for production-like network blocking 
    (blocks external APIs, allows test infrastructure)
    """
    whitelist = [
        'test.lockbay.io',
        'localhost',
        'db.test.local'
    ]
    with block_network_calls(whitelist_domains=whitelist) as blocker:
        yield blocker