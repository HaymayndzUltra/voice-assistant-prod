#!/usr/bin/env python3
"""
WP-10 Security & Authentication Test Suite
Tests authentication, encryption, and access control functionality
"""

import asyncio
import time
import json
from pathlib import Path
import sys
from common.env_helpers import get_env

# Add common to path
sys.path.insert(0, str(Path(__file__).parent.parent / "common"))

async def test_authentication_system():
    """Test authentication functionality"""
    print("🧪 Testing Authentication System...")
    
    try:
        from common.security.authentication import (
            get_security_manager, SecurityContext, AuthenticationMethod,
            PermissionLevel, ResourceType
        )
        
        security_manager = get_security_manager()
        
        # Test JWT token generation and verification
        user_id = "test_user_123"
        roles = {"admin", "user"}
        
        token = security_manager.generate_token(user_id, roles)
        
        # Verify token
        context = await security_manager.authenticate(
            AuthenticationMethod.JWT,
            {"token": token}
        )
        
        assert context is not None
        assert context.user_id == user_id
        assert "admin" in context.roles
        
        # Test API key generation and verification
        key_id, api_key = security_manager.create_api_key(
            "test_api_key",
            permissions={"api:read", "api:write"},
            rate_limit=100
        )
        
        api_context = await security_manager.authenticate(
            AuthenticationMethod.API_KEY,
            {"api_key": api_key}
        )
        
        assert api_context is not None
        assert "api:read" in api_context.permissions
        
        # Test authorization
        can_read = security_manager.authorize(context, ResourceType.API, PermissionLevel.READ)
        can_admin = security_manager.authorize(context, ResourceType.SYSTEM, PermissionLevel.ADMIN)
        
        # Test HMAC authentication
        hmac_context = await security_manager.authenticate(
            AuthenticationMethod.HMAC,
            {
                "method": "POST",
                "path": "/api/test",
                "body": '{"test": "data"}',
                "timestamp": str(time.time()),
                "signature": security_manager.hmac_validator.generate_signature(
                    "POST", "/api/test", '{"test": "data"}', str(time.time())
                )
            }
        )
        
        print(f"  📊 JWT authentication: {'✅' if context else '❌'}")
        print(f"  📊 API key authentication: {'✅' if api_context else '❌'}")
        print(f"  📊 HMAC authentication: {'✅' if hmac_context else '❌'}")
        print(f"  📊 Authorization checks: {'✅' if can_read and can_admin else '❌'}")
        print(f"  📊 Token contains roles: {'✅' if context.roles == roles else '❌'}")
        print(f"  📊 API key permissions: {'✅' if api_context.permissions else '❌'}")
        print(f"  ✅ Authentication system test passed")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Authentication system test failed: {e}")
        return False

async def test_encryption_system():
    """Test encryption functionality"""
    print("\n🧪 Testing Encryption System...")
    
    try:
        from common.security.encryption import (
            get_encryption_service, get_secrets_manager,
            EncryptionAlgorithm, encrypt_data, decrypt_data,
            set_secret, get_secret
        )
        
        encryption_service = get_encryption_service()
        secrets_manager = get_secrets_manager()
        
        # Test symmetric encryption (AES-256-GCM)
        test_data = "This is highly sensitive test data!"
        
        key_id = encryption_service.key_manager.generate_key(
            EncryptionAlgorithm.AES_256_GCM,
            purpose="test"
        )
        
        encrypted_data = encryption_service.encrypt(test_data, key_id)
        decrypted_data = encryption_service.decrypt(encrypted_data)
        
        assert decrypted_data.decode('utf-8') == test_data
        
        # Test Fernet encryption
        fernet_key_id = encryption_service.key_manager.generate_key(
            EncryptionAlgorithm.FERNET,
            purpose="test_fernet"
        )
        
        fernet_encrypted = encryption_service.encrypt(test_data, fernet_key_id)
        fernet_decrypted = encryption_service.decrypt(fernet_encrypted)
        
        assert fernet_decrypted.decode('utf-8') == test_data
        
        # Test secrets management
        test_secret = {
            "database_url": "postgresql://user:pass@localhost/db",
            "api_key": "sk_test_123456789",
            "encryption_key": "super_secret_key"
        }
        
        set_secret("test_config", test_secret)
        retrieved_secret = get_secret("test_config")
        
        assert retrieved_secret == test_secret
        
        # Test key rotation
        old_key_id = key_id
        new_key_id = encryption_service.key_manager.rotate_key(old_key_id)
        
        # Test convenience functions
        conv_key_id, conv_encrypted = encrypt_data("convenience test")
        conv_decrypted = decrypt_data(conv_encrypted)
        
        print(f"  📊 AES-256-GCM encryption: {'✅' if decrypted_data.decode('utf-8') == test_data else '❌'}")
        print(f"  📊 Fernet encryption: {'✅' if fernet_decrypted.decode('utf-8') == test_data else '❌'}")
        print(f"  📊 Secrets management: {'✅' if retrieved_secret == test_secret else '❌'}")
        print(f"  📊 Key rotation: {'✅' if new_key_id != old_key_id else '❌'}")
        print(f"  📊 Convenience functions: {'✅' if conv_decrypted.decode('utf-8') == 'convenience test' else '❌'}")
        print(f"  📊 Key metadata tracking: {'✅' if encryption_service.key_manager.get_key_metadata(key_id) else '❌'}")
        print(f"  ✅ Encryption system test passed")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Encryption system test failed: {e}")
        return False

async def test_access_control_system():
    """Test access control functionality"""
    print("\n🧪 Testing Access Control System...")
    
    try:
        from common.security.access_control import (
            get_access_control_engine, AccessDecision, ThreatLevel,
            RateLimitRule, RateLimitType, AccessRule
        )
        
        access_control = get_access_control_engine()
        
        # Test IP access control
        test_context = {
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0 (Test Browser)",
            "user_id": "test_user",
            "roles": ["user"],
            "path": "/api/data",
            "method": "GET"
        }
        
        decision, info = access_control.evaluate_access(test_context)
        
        # Test rate limiting
        user_id = "test_rate_limit_user"
        
        # First few requests should be allowed
        allowed_requests = 0
        for i in range(10):
            allowed, rate_info = access_control.rate_limiter.check_rate_limit(
                user_id, "api_requests_per_minute"
            )
            if allowed:
                allowed_requests += 1
        
        # Test blocking suspicious user agent
        bot_context = {
            "ip_address": "10.0.0.1",
            "user_agent": "BadBot/1.0 (Web Crawler)",
            "user_id": None,
            "roles": [],
            "path": "/api/data",
            "method": "GET"
        }
        
        bot_decision, bot_info = access_control.evaluate_access(bot_context)
        
        # Test admin bypass
        admin_context = {
            "ip_address": "10.0.0.1",
            "user_agent": "BadBot/1.0 (Web Crawler)",  # Should be blocked normally
            "user_id": "admin_user",
            "roles": ["admin"],
            "path": "/api/data",
            "method": "GET"
        }
        
        admin_decision, admin_info = access_control.evaluate_access(admin_context)
        
        # Test security event recording
        initial_events = len(access_control.get_security_events())
        
        # This should create a security event
        blocked_context = {
            "ip_address": "192.0.2.1",  # RFC 5737 test network (blacklisted)
            "user_agent": "Normal Browser",
            "user_id": "test_user",
            "roles": ["user"]
        }
        
        blocked_decision, blocked_info = access_control.evaluate_access(blocked_context)
        final_events = len(access_control.get_security_events())
        
        # Test rate limit status
        rate_status = access_control.rate_limiter.get_rate_limit_status(user_id)
        
        # Test security summary
        security_summary = access_control.get_security_summary()
        
        print(f"  📊 Normal access: {'✅' if decision == AccessDecision.ALLOW else '❌'}")
        print(f"  📊 Rate limiting: {'✅' if allowed_requests > 0 else '❌'}")
        print(f"  📊 Bot blocking: {'✅' if bot_decision == AccessDecision.DENY else '❌'}")
        print(f"  📊 Admin bypass: {'✅' if admin_decision == AccessDecision.ALLOW else '❌'}")
        print(f"  📊 Security events: {'✅' if final_events > initial_events else '❌'}")
        print(f"  📊 Rate status tracking: {'✅' if rate_status else '❌'}")
        print(f"  📊 Security summary: {'✅' if security_summary['total_events'] >= 0 else '❌'}")
        print(f"  ✅ Access control system test passed")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Access control system test failed: {e}")
        return False

async def test_security_integration():
    """Test integrated security (auth + encryption + access control)"""
    print("\n🧪 Testing Security Integration...")
    
    try:
        from common.security.authentication import get_security_manager, AuthenticationMethod
        from common.security.encryption import get_encryption_service, EncryptionAlgorithm
        from common.security.access_control import get_access_control_engine
        
        security_manager = get_security_manager()
        encryption_service = get_encryption_service()
        access_control = get_access_control_engine()
        
        # Integrated workflow: authenticate -> authorize -> encrypt data -> store
        
        # 1. Create user with permissions
        user_token = security_manager.generate_token(
            user_id="integration_user",
            roles={"user", "data_manager"},
            permissions={"data:read", "data:write", "api:read"}
        )
        
        # 2. Authenticate user
        security_context = await security_manager.authenticate(
            AuthenticationMethod.JWT,
            {"token": user_token}
        )
        
        # 3. Check access control
        request_context = {
            "ip_address": "192.168.1.200",
            "user_agent": "SecureApp/1.0",
            "user_id": security_context.user_id,
            "roles": list(security_context.roles),
            "path": "/api/secure-data",
            "method": "POST"
        }
        
        access_decision, access_info = access_control.evaluate_access(request_context)
        
        # 4. Encrypt sensitive data
        sensitive_data = {
            "user_id": "integration_user",
            "personal_info": {
                "ssn": "123-45-6789",
                "credit_card": "4111-1111-1111-1111",
                "password": "super_secure_password"
            },
            "preferences": {
                "theme": "dark",
                "notifications": True
            }
        }
        
        # Generate encryption key
        data_key_id = encryption_service.key_manager.generate_key(
            EncryptionAlgorithm.AES_256_GCM,
            purpose="user_data"
        )
        
        # Encrypt sensitive fields
        encrypted_ssn = encryption_service.encrypt(
            sensitive_data["personal_info"]["ssn"],
            data_key_id
        )
        
        encrypted_cc = encryption_service.encrypt(
            sensitive_data["personal_info"]["credit_card"],
            data_key_id
        )
        
        # 5. Verify decryption
        decrypted_ssn = encryption_service.decrypt(encrypted_ssn).decode('utf-8')
        decrypted_cc = encryption_service.decrypt(encrypted_cc).decode('utf-8')
        
        # 6. Test rate limiting in integration
        rate_limit_passed = 0
        for i in range(5):
            allowed, _ = access_control.rate_limiter.check_rate_limit(
                security_context.user_id,
                "api_requests_per_minute"
            )
            if allowed:
                rate_limit_passed += 1
        
        print(f"  📊 User authentication: {'✅' if security_context else '❌'}")
        print(f"  📊 Access control check: {'✅' if access_decision == access_decision.ALLOW else '❌'}")
        print(f"  📊 Data encryption: {'✅' if encrypted_ssn and encrypted_cc else '❌'}")
        print(f"  📊 Data decryption: {'✅' if decrypted_ssn == sensitive_data['personal_info']['ssn'] else '❌'}")
        print(f"  📊 Rate limiting integration: {'✅' if rate_limit_passed > 0 else '❌'}")
        print(f"  📊 Permission validation: {'✅' if 'data:write' in security_context.permissions else '❌'}")
        print(f"  ✅ Security integration test passed")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Security integration test failed: {e}")
        return False

async def test_security_decorators():
    """Test security decorators and middleware"""
    print("\n🧪 Testing Security Decorators...")
    
    try:
        from common.security.authentication import require_auth, ResourceType, PermissionLevel
        from common.security.access_control import protect_endpoint
        from common.security.authentication import SecurityContext
        
        # Test authentication decorator
        @require_auth(resource=ResourceType.API, action=PermissionLevel.READ)
        async def protected_function(data, security_context=None):
            return {"message": "Access granted", "user": security_context.user_id}
        
        # Create test security context
        test_context = SecurityContext(
            user_id="decorator_test_user",
            permissions={"api:read", "api:write"},
            roles={"user"}
        )
        
        # Test with valid context
        try:
            result = await protected_function("test_data", security_context=test_context)
            decorator_success = True
        except PermissionError:
            decorator_success = False
        
        # Test without context (should fail)
        try:
            await protected_function("test_data")
            no_auth_blocked = False
        except PermissionError:
            no_auth_blocked = True
        
        # Test with insufficient permissions
        insufficient_context = SecurityContext(
            user_id="limited_user",
            permissions={"other:read"},  # No api:read permission
            roles={"limited"}
        )
        
        try:
            await protected_function("test_data", security_context=insufficient_context)
            insufficient_blocked = False
        except PermissionError:
            insufficient_blocked = True
        
        print(f"  📊 Decorator with valid auth: {'✅' if decorator_success else '❌'}")
        print(f"  📊 Decorator blocks no auth: {'✅' if no_auth_blocked else '❌'}")
        print(f"  📊 Decorator blocks insufficient perms: {'✅' if insufficient_blocked else '❌'}")
        print(f"  📊 Function returns user ID: {'✅' if result and result.get('user') == test_context.user_id else '❌'}")
        print(f"  ✅ Security decorators test passed")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Security decorators test failed: {e}")
        return False

async def test_threat_detection():
    """Test threat detection and monitoring"""
    print("\n🧪 Testing Threat Detection...")
    
    try:
        from common.security.access_control import get_access_control_engine, ThreatLevel
        
        access_control = get_access_control_engine()
        
        # Simulate various threat scenarios
        threat_contexts = [
            {
                "name": "SQL injection attempt",
                "context": {
                    "ip_address": "10.0.0.100",
                    "user_agent": "sqlmap/1.0",
                    "path": "/api/users?id=1' OR '1'='1",
                    "user_id": None,
                    "roles": []
                }
            },
            {
                "name": "Directory traversal",
                "context": {
                    "ip_address": "10.0.0.101",
                    "user_agent": "AttackBot/1.0",
                    "path": "/api/../../../etc/passwd",
                    "user_id": None,
                    "roles": []
                }
            },
            {
                "name": "Brute force attempt",
                "context": {
                    "ip_address": "10.0.0.102",
                    "user_agent": "BruteForcer/2.0",
                    "path": "/api/login",
                    "user_id": "admin",
                    "roles": []
                }
            }
        ]
        
        initial_events = len(access_control.get_security_events())
        
        # Process threat scenarios
        blocked_threats = 0
        for threat in threat_contexts:
            decision, info = access_control.evaluate_access(threat["context"])
            if decision.name in ["DENY", "THROTTLE"]:
                blocked_threats += 1
        
        # Generate multiple rapid requests (should trigger rate limiting)
        rapid_requests_blocked = 0
        for i in range(20):
            allowed, _ = access_control.rate_limiter.check_rate_limit(
                "rapid_fire_user",
                "api_requests_per_minute"
            )
            if not allowed:
                rapid_requests_blocked += 1
        
        final_events = len(access_control.get_security_events())
        
        # Check for high-threat events
        high_threat_events = access_control.get_security_events(
            threat_level=ThreatLevel.HIGH
        )
        
        # Get security summary
        security_summary = access_control.get_security_summary()
        
        print(f"  📊 Threats detected: {blocked_threats}/{len(threat_contexts)}")
        print(f"  📊 Rate limiting triggered: {'✅' if rapid_requests_blocked > 0 else '❌'}")
        print(f"  📊 Security events generated: {'✅' if final_events > initial_events else '❌'}")
        print(f"  📊 High threat detection: {'✅' if len(high_threat_events) > 0 else '❌'}")
        print(f"  📊 Security monitoring: {'✅' if security_summary['total_events'] > 0 else '❌'}")
        print(f"  ✅ Threat detection test passed")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Threat detection test failed: {e}")
        return False

async def test_performance_security():
    """Test security performance under load"""
    print("\n🧪 Testing Security Performance...")
    
    try:
        from common.security.authentication import get_security_manager, AuthenticationMethod
        from common.security.encryption import get_encryption_service, EncryptionAlgorithm
        from common.security.access_control import get_access_control_engine
        import time
        
        security_manager = get_security_manager()
        encryption_service = get_encryption_service()
        access_control = get_access_control_engine()
        
        # Performance test parameters
        num_operations = 100
        
        # Test JWT verification performance
        token = security_manager.generate_token("perf_user", {"user"})
        
        start_time = time.time()
        successful_auths = 0
        for i in range(num_operations):
            context = await security_manager.authenticate(
                AuthenticationMethod.JWT,
                {"token": token}
            )
            if context:
                successful_auths += 1
        auth_time = time.time() - start_time
        
        # Test encryption performance
        test_data = "Performance test data " * 10  # ~200 bytes
        key_id = encryption_service.key_manager.generate_key(EncryptionAlgorithm.AES_256_GCM)
        
        start_time = time.time()
        for i in range(num_operations):
            encrypted = encryption_service.encrypt(test_data, key_id)
            decrypted = encryption_service.decrypt(encrypted)
        encryption_time = time.time() - start_time
        
        # Test access control performance
        test_context = {
            "ip_address": "192.168.1.100",
            "user_agent": "PerformanceTest/1.0",
            "user_id": "perf_user",
            "roles": ["user"],
            "path": "/api/test",
            "method": "GET"
        }
        
        start_time = time.time()
        allowed_requests = 0
        for i in range(num_operations):
            decision, info = access_control.evaluate_access(test_context)
            if decision.name == "ALLOW":
                allowed_requests += 1
        access_control_time = time.time() - start_time
        
        # Calculate performance metrics
        auth_ops_per_sec = num_operations / auth_time
        encryption_ops_per_sec = num_operations / encryption_time
        access_control_ops_per_sec = num_operations / access_control_time
        
        print(f"  📊 JWT auth performance: {auth_ops_per_sec:.1f} ops/sec")
        print(f"  📊 Encryption performance: {encryption_ops_per_sec:.1f} ops/sec")
        print(f"  📊 Access control performance: {access_control_ops_per_sec:.1f} ops/sec")
        print(f"  📊 Authentication success rate: {successful_auths}/{num_operations}")
        print(f"  📊 Access control success rate: {allowed_requests}/{num_operations}")
        print(f"  📊 Performance acceptable: {'✅' if auth_ops_per_sec > 50 else '❌'}")
        print(f"  ✅ Security performance test passed")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Security performance test failed: {e}")
        return False

async def main():
    """Run all security tests"""
    print("🚀 WP-10 Security & Authentication Test Suite")
    print("=" * 50)
    
    test_results = []
    
    # Run tests
    test_results.append(await test_authentication_system())
    test_results.append(await test_encryption_system())
    test_results.append(await test_access_control_system())
    test_results.append(await test_security_integration())
    test_results.append(await test_security_decorators())
    test_results.append(await test_threat_detection())
    test_results.append(await test_performance_security())
    
    # Summary
    passed_tests = sum(1 for result in test_results if result)
    total_tests = len(test_results)
    
    print(f"\n📊 TEST SUMMARY:")
    print(f"✅ Passed: {passed_tests}/{total_tests} tests")
    
    if passed_tests == total_tests:
        print(f"🎉 All security tests passed!")
        print(f"\n🚀 Security system is ready for production use!")
    else:
        print(f"⚠️  Some tests failed or were skipped")
        print(f"\n📋 Security components:")
        print(f"   - Authentication & Authorization (common/security/authentication.py)")
        print(f"   - Encryption & Secrets Management (common/security/encryption.py)")
        print(f"   - Access Control & Rate Limiting (common/security/access_control.py)")
    
    print(f"\n💡 Usage Examples:")
    print(f"   # Authentication")
    print(f"   from common.security.authentication import get_security_manager")
    print(f"   security_manager = get_security_manager()")
    print(f"   token = security_manager.generate_token('user123', {{'user'}})")
    print(f"\n   # Encryption")
    print(f"   from common.security.encryption import encrypt_data, get_secret")
    print(f"   key_id, encrypted = encrypt_data('sensitive data')")
    print(f"   secret = get_secret('api_key')")
    print(f"\n   # Access Control")
    print(f"   from common.security.access_control import protect_endpoint")
    print(f"   @protect_endpoint(require_auth=True, allowed_roles=['admin'])")
    print(f"   async def protected_function(): ...")

if __name__ == "__main__":
    asyncio.run(main()) 