"""
Test suite for UnifiedConfigLoader.

Tests configuration loading, environment variable substitution,
validation, and multi-environment support.
"""

import os

# Import the configuration loader
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.loader import ConfigurationError, UnifiedConfigLoader


class TestUnifiedConfigLoader:
    """Test suite for configuration loading functionality."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary directory with test configurations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            # Create default config
            default_config = {
                'title': 'TestConfig',
                'version': '1.0',
                'audio': {
                    'sample_rate': 16000,
                    'frame_ms': 20,
                    'channels': 1,
                    'device': '${AUDIO_DEVICE:default}'
                },
                'output': {
                    'zmq_pub_port_events': 6552,
                    'zmq_pub_port_transcripts': 6553,
                    'websocket_port': 5802
                }
            }

            with open(config_dir / 'default.yaml', 'w') as f:
                yaml.dump(default_config, f)

            # Create environment-specific config
            env_config = {
                'title': 'TestConfig - Environment',
                'audio': {
                    'sample_rate': 48000,  # Override default
                    'device': '${ENV_DEVICE:env_default}'
                }
            }

            with open(config_dir / 'test_env.yaml', 'w') as f:
                yaml.dump(env_config, f)

            yield config_dir

    def test_basic_config_loading(self, temp_config_dir):
        """Test basic configuration loading."""
        loader = UnifiedConfigLoader(temp_config_dir)
        config = loader.load_config(config_file='default.yaml')

        assert config['title'] == 'TestConfig'
        assert config['version'] == '1.0'
        assert config['audio']['sample_rate'] == 16000
        assert config['audio']['frame_ms'] == 20

    def test_environment_variable_substitution(self, temp_config_dir):
        """Test environment variable substitution."""
        # Set test environment variables
        os.environ['AUDIO_DEVICE'] = 'test_audio_device'
        os.environ['ENV_DEVICE'] = 'test_env_device'

        try:
            loader = UnifiedConfigLoader(temp_config_dir)
            config = loader.load_config(config_file='default.yaml')

            # Should substitute environment variable
            assert config['audio']['device'] == 'test_audio_device'

        finally:
            # Clean up environment variables
            os.environ.pop('AUDIO_DEVICE', None)
            os.environ.pop('ENV_DEVICE', None)

    def test_environment_variable_defaults(self, temp_config_dir):
        """Test environment variable default values."""
        # Ensure environment variable is not set
        os.environ.pop('AUDIO_DEVICE', None)

        loader = UnifiedConfigLoader(temp_config_dir)
        config = loader.load_config(config_file='default.yaml')

        # Should use default value
        assert config['audio']['device'] == 'default'

    def test_configuration_inheritance(self, temp_config_dir):
        """Test configuration inheritance from default."""
        os.environ['ENV_DEVICE'] = 'inherited_device'

        try:
            loader = UnifiedConfigLoader(temp_config_dir)
            config = loader.load_config(environment='test_env')

            # Should inherit from default and override specific values
            assert config['title'] == 'TestConfig - Environment'  # Overridden
            assert config['version'] == '1.0'  # Inherited from default
            assert config['audio']['sample_rate'] == 48000  # Overridden
            assert config['audio']['frame_ms'] == 20  # Inherited
            assert config['audio']['device'] == 'inherited_device'  # Environment substitution

        finally:
            os.environ.pop('ENV_DEVICE', None)

    def test_configuration_validation(self, temp_config_dir):
        """Test configuration validation."""
        loader = UnifiedConfigLoader(temp_config_dir)

        # Valid configuration should pass
        config = loader.load_config(config_file='default.yaml', validate=True)
        assert config is not None

        # Test validation with invalid config
        invalid_config = {
            'title': 'Invalid',
            'audio': {
                'sample_rate': 'invalid',  # Should be integer
                'frame_ms': 20,
                'channels': 1
            }
            # Missing required 'output' section
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(invalid_config, f)
            invalid_path = f.name

        try:
            with pytest.raises(ConfigurationError):
                loader.load_config(config_file=Path(invalid_path).name, validate=True)
        finally:
            os.unlink(invalid_path)

    def test_type_conversion(self, temp_config_dir):
        """Test automatic type conversion for environment variables."""
        # Test various type conversions
        os.environ['TEST_INT'] = '42'
        os.environ['TEST_FLOAT'] = '3.14'
        os.environ['TEST_BOOL_TRUE'] = 'true'
        os.environ['TEST_BOOL_FALSE'] = 'false'
        os.environ['TEST_STRING'] = 'hello'

        try:
            loader = UnifiedConfigLoader(temp_config_dir)

            # Test integer conversion
            result = loader._convert_type('42')
            assert result == 42
            assert isinstance(result, int)

            # Test float conversion
            result = loader._convert_type('3.14')
            assert result == 3.14
            assert isinstance(result, float)

            # Test boolean conversion
            assert loader._convert_type('true') is True
            assert loader._convert_type('false') is False
            assert loader._convert_type('yes') is True
            assert loader._convert_type('no') is False

            # Test string (no conversion)
            result = loader._convert_type('hello')
            assert result == 'hello'
            assert isinstance(result, str)

        finally:
            # Clean up
            for var in ['TEST_INT', 'TEST_FLOAT', 'TEST_BOOL_TRUE', 'TEST_BOOL_FALSE', 'TEST_STRING']:
                os.environ.pop(var, None)

    def test_missing_config_file(self, temp_config_dir):
        """Test handling of missing configuration files."""
        loader = UnifiedConfigLoader(temp_config_dir)

        with pytest.raises(ConfigurationError):
            loader.load_config(config_file='nonexistent.yaml')

    def test_environment_detection(self, temp_config_dir):
        """Test automatic environment detection."""
        loader = UnifiedConfigLoader(temp_config_dir)

        # Should detect default environment when specific ones don't exist
        env = loader._detect_environment()
        assert env == 'default'  # Should fall back to default

    def test_config_caching(self, temp_config_dir):
        """Test configuration caching functionality."""
        loader = UnifiedConfigLoader(temp_config_dir)

        # Load config first time
        config1 = loader.load_config(config_file='default.yaml')

        # Load same config again
        config2 = loader.load_config(config_file='default.yaml')

        # Should be the same content (but caching is internal)
        assert config1['title'] == config2['title']
        assert config1['audio']['sample_rate'] == config2['audio']['sample_rate']

    def test_list_available_configs(self, temp_config_dir):
        """Test listing available configuration files."""
        loader = UnifiedConfigLoader(temp_config_dir)
        available = loader.list_available_configs()

        assert 'default' in available
        assert 'test_env' in available
        assert len(available) == 2

    def test_validate_environment_variables(self, temp_config_dir):
        """Test environment variable validation."""
        os.environ['TEST_VAR'] = 'test_value'

        try:
            loader = UnifiedConfigLoader(temp_config_dir)
            config = loader.load_config(config_file='default.yaml')

            env_vars = loader.validate_environment_variables(config)

            # Should find AUDIO_DEVICE variable
            assert 'AUDIO_DEVICE' in env_vars

        finally:
            os.environ.pop('TEST_VAR', None)


class TestConfigurationEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_config_file(self):
        """Test handling of empty configuration files."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml') as f:
            f.write('')  # Empty file
            f.flush()

            loader = UnifiedConfigLoader(Path(f.name).parent)

            with pytest.raises(ConfigurationError):
                loader.load_config(config_file=Path(f.name).name)

    def test_invalid_yaml_syntax(self):
        """Test handling of invalid YAML syntax."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml') as f:
            f.write('invalid: yaml: syntax: [unclosed')
            f.flush()

            loader = UnifiedConfigLoader(Path(f.name).parent)

            with pytest.raises(ConfigurationError):
                loader.load_config(config_file=Path(f.name).name)

    def test_circular_environment_variables(self):
        """Test handling of circular environment variable references."""
        # This would test ${VAR1} -> ${VAR2} -> ${VAR1} scenarios
        # For now, we test that it doesn't crash

        os.environ['CIRCULAR1'] = '${CIRCULAR2:default1}'
        os.environ['CIRCULAR2'] = '${CIRCULAR1:default2}'

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                config_dir = Path(temp_dir)

                test_config = {
                    'test': '${CIRCULAR1:fallback}'
                }

                with open(config_dir / 'test.yaml', 'w') as f:
                    yaml.dump(test_config, f)

                loader = UnifiedConfigLoader(config_dir)
                config = loader.load_config(config_file='test.yaml')

                # Should handle gracefully (may use fallback or default)
                assert config['test'] is not None

        finally:
            os.environ.pop('CIRCULAR1', None)
            os.environ.pop('CIRCULAR2', None)


class TestConfigurationValidation:
    """Test comprehensive configuration validation."""

    def test_audio_section_validation(self):
        """Test audio section validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            # Test invalid sample rate
            invalid_config = {
                'audio': {
                    'sample_rate': 1000,  # Too low
                    'frame_ms': 20,
                    'channels': 1
                },
                'output': {
                    'zmq_pub_port_events': 6552,
                    'zmq_pub_port_transcripts': 6553,
                    'websocket_port': 5802
                }
            }

            with open(config_dir / 'invalid.yaml', 'w') as f:
                yaml.dump(invalid_config, f)

            loader = UnifiedConfigLoader(config_dir)

            with pytest.raises(ConfigurationError):
                loader.load_config(config_file='invalid.yaml', validate=True)

    def test_port_validation(self):
        """Test port number validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            # Test invalid port numbers
            invalid_config = {
                'audio': {
                    'sample_rate': 16000,
                    'frame_ms': 20,
                    'channels': 1
                },
                'output': {
                    'zmq_pub_port_events': 99999,  # Too high
                    'zmq_pub_port_transcripts': 6553,
                    'websocket_port': 5802
                }
            }

            with open(config_dir / 'invalid_port.yaml', 'w') as f:
                yaml.dump(invalid_config, f)

            loader = UnifiedConfigLoader(config_dir)

            with pytest.raises(ConfigurationError):
                loader.load_config(config_file='invalid_port.yaml', validate=True)


# Integration test
def test_config_loader_integration():
    """Integration test with actual configuration files."""
    print("\n=== Configuration Loader Integration Test ===")

    # Test with actual RTAP configuration
    try:
        # Use the actual config directory
        loader = UnifiedConfigLoader()

        # Test loading default configuration
        config = loader.load_config()

        print(f"Loaded configuration: {config['title']}")
        print(f"Audio settings: {config['audio']['sample_rate']}Hz, {config['audio']['frame_ms']}ms")
        print(f"Output ports: {config['output']['zmq_pub_port_events']}, {config['output']['zmq_pub_port_transcripts']}")

        # Validate required sections exist
        assert 'audio' in config
        assert 'output' in config
        assert 'wakeword' in config
        assert 'stt' in config

        # Test environment variable validation
        env_vars = loader.validate_environment_variables(config)
        if env_vars:
            print(f"Environment variables used: {list(env_vars.keys())}")

        print("✅ Configuration loader integration test passed!")

    except Exception as e:
        print(f"❌ Configuration loader integration test failed: {e}")
        raise


if __name__ == "__main__":
    # Run integration test when executed directly
    test_config_loader_integration()
