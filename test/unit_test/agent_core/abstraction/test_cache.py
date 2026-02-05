"""
Unit tests for AgentCache singleton implementation.
"""

import pytest
import threading
import time
from unittest.mock import Mock, MagicMock

from gearmeshing_ai.agent_core.abstraction.cache import AgentCache


class TestAgentCache:
    """Test cases for AgentCache singleton implementation."""

    def test_singleton_behavior(self):
        """Test that AgentCache implements singleton pattern correctly."""
        # Create multiple instances
        cache1 = AgentCache()
        cache2 = AgentCache()
        cache3 = AgentCache()
        
        # All should be the same instance
        assert cache1 is cache2
        assert cache2 is cache3
        assert id(cache1) == id(cache2) == id(cache3)

    def test_thread_safety(self):
        """Test that singleton creation is thread-safe."""
        instances = []
        errors = []
        
        def create_cache():
            try:
                cache = AgentCache()
                instances.append(cache)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads that try to create instances
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=create_cache)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check that no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Check that all instances are the same
        assert len(instances) == 10
        first_instance = instances[0]
        for instance in instances[1:]:
            assert instance is first_instance

    def test_get_and_set_operations(self):
        """Test basic get and set operations."""
        cache = AgentCache()
        
        # Clear cache to start fresh
        cache.clear()
        
        # Test getting non-existent agent
        assert cache.get("non_existent") is None
        
        # Test setting and getting an agent
        mock_agent = Mock()
        cache.set("test_agent", mock_agent)
        
        retrieved_agent = cache.get("test_agent")
        assert retrieved_agent is mock_agent
        assert retrieved_agent is not None

    def test_remove_operation(self):
        """Test remove operation."""
        cache = AgentCache()
        cache.clear()
        
        # Add an agent
        mock_agent = Mock()
        cache.set("test_agent", mock_agent)
        assert cache.get("test_agent") is mock_agent
        
        # Remove the agent
        cache.remove("test_agent")
        assert cache.get("test_agent") is None
        
        # Removing non-existent agent should not raise error
        cache.remove("non_existent")  # Should not raise

    def test_clear_operation(self):
        """Test clear operation."""
        cache = AgentCache()
        
        # Add multiple agents
        cache.set("agent1", Mock())
        cache.set("agent2", Mock())
        cache.set("agent3", Mock())
        
        # Verify agents exist
        assert cache.get("agent1") is not None
        assert cache.get("agent2") is not None
        assert cache.get("agent3") is not None
        
        # Clear all agents
        cache.clear()
        
        # Verify all agents are gone
        assert cache.get("agent1") is None
        assert cache.get("agent2") is None
        assert cache.get("agent3") is None

    def test_overwrite_existing_agent(self):
        """Test overwriting an existing cached agent."""
        cache = AgentCache()
        cache.clear()
        
        # Add initial agent
        agent1 = Mock(name="agent1")
        cache.set("test_agent", agent1)
        assert cache.get("test_agent") is agent1
        
        # Overwrite with new agent
        agent2 = Mock(name="agent2")
        cache.set("test_agent", agent2)
        assert cache.get("test_agent") is agent2
        assert cache.get("test_agent") is not agent1

    def test_cache_with_different_agent_types(self):
        """Test cache with various types of agent objects."""
        cache = AgentCache()
        cache.clear()
        
        # Test with different object types
        mock_agent = Mock()
        simple_agent = "simple_agent_string"
        dict_agent = {"type": "dict_agent", "config": {}}
        class_agent = type("CustomAgent", (), {"run": lambda: "test"})
        
        cache.set("mock", mock_agent)
        cache.set("simple", simple_agent)
        cache.set("dict", dict_agent)
        cache.set("class", class_agent)
        
        assert cache.get("mock") is mock_agent
        assert cache.get("simple") is simple_agent
        assert cache.get("dict") is dict_agent
        assert cache.get("class") is class_agent

    def test_cache_key_types(self):
        """Test cache with different key types."""
        cache = AgentCache()
        cache.clear()
        
        mock_agent = Mock()
        
        # Test with string keys (expected usage)
        cache.set("string_key", mock_agent)
        assert cache.get("string_key") is mock_agent
        
        # Test with other hashable types
        cache.set(123, mock_agent)
        assert cache.get(123) is mock_agent
        
        cache.set(("tuple", "key"), mock_agent)
        assert cache.get(("tuple", "key")) is mock_agent

    def test_cache_isolation_between_tests(self):
        """Test that cache state doesn't leak between test instances."""
        # This test verifies that the singleton doesn't cause test pollution
        cache1 = AgentCache()
        cache1.clear()
        cache1.set("test_key", "test_value")
        
        # Create a new reference to the same singleton
        cache2 = AgentCache()
        assert cache2.get("test_key") == "test_value"
        
        # Clear one reference
        cache2.clear()
        
        # Both should see the cleared state
        assert cache1.get("test_key") is None
        assert cache2.get("test_key") is None

    def test_concurrent_operations(self):
        """Test concurrent cache operations."""
        cache = AgentCache()
        cache.clear()
        
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                for i in range(10):
                    agent = Mock(name=f"agent_{worker_id}_{i}")
                    key = f"worker_{worker_id}_agent_{i}"
                    
                    # Set agent
                    cache.set(key, agent)
                    
                    # Small delay to increase chance of race conditions
                    time.sleep(0.001)
                    
                    # Get agent
                    retrieved = cache.get(key)
                    results.append((worker_id, i, retrieved is agent))
                    
                    # Occasionally remove
                    if i % 3 == 0:
                        cache.remove(key)
                        
            except Exception as e:
                errors.append((worker_id, e))
        
        # Create multiple worker threads
        threads = []
        for worker_id in range(5):
            thread = threading.Thread(target=worker, args=(worker_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check that no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Check that operations were successful
        assert len(results) == 50  # 5 workers * 10 operations each
        successful_operations = sum(1 for _, _, success in results if success)
        assert successful_operations >= 45  # Allow for some removals

    def test_cache_memory_behavior(self):
        """Test cache behavior with memory considerations."""
        cache = AgentCache()
        cache.clear()
        
        # Add many agents
        agents = []
        for i in range(100):
            agent = Mock(name=f"agent_{i}")
            agents.append(agent)
            cache.set(f"agent_{i}", agent)
        
        # Verify all agents are cached
        for i in range(100):
            agent = cache.get(f"agent_{i}")
            assert agent is agents[i]
        
        # Clear and verify memory is released
        cache.clear()
        for i in range(100):
            assert cache.get(f"agent_{i}") is None

    def test_cache_edge_cases(self):
        """Test edge cases and boundary conditions."""
        cache = AgentCache()
        cache.clear()
        
        # Test with empty string key
        mock_agent = Mock()
        cache.set("", mock_agent)
        assert cache.get("") is mock_agent
        
        # Test with None value (should be allowed)
        cache.set("none_value", None)
        assert cache.get("none_value") is None
        
        # Test removing None value
        cache.remove("none_value")
        assert cache.get("none_value") is None
        
        # Test clear on empty cache
        cache.clear()  # Should not raise
        assert cache.get("anything") is None

    def test_cache_instance_attributes(self):
        """Test cache instance attributes and their types."""
        cache = AgentCache()
        
        # Check that expected attributes exist
        assert hasattr(cache, '_agents')
        assert hasattr(cache, 'get')
        assert hasattr(cache, 'set')
        assert hasattr(cache, 'remove')
        assert hasattr(cache, 'clear')
        
        # Check that _agents is a dictionary
        assert isinstance(cache._agents, dict)
        
        # Check that methods are callable
        assert callable(cache.get)
        assert callable(cache.set)
        assert callable(cache.remove)
        assert callable(cache.clear)
