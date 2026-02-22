"""
Checking point registry system.

This module provides the auto-registration system for checking points, allowing
checking point implementations to be automatically discovered and registered
without manual configuration.
"""

import inspect
from typing import Any, Dict, List, Optional, Type, Union

from .base import CheckingPoint, CheckingPointType


class CheckingPointRegistry:
    """Registry for managing checking point implementations.
    
    This registry provides automatic discovery and registration of checking point
    implementations, as well as methods for retrieving and managing checking points.
    """
    
    def __init__(self) -> None:
        """Initialize the registry."""
        self._checking_points: Dict[str, Type[CheckingPoint]] = {}
        self._instances: Dict[str, CheckingPoint] = {}
        self._type_mapping: Dict[CheckingPointType, List[str]] = {}
        self._initialized = False
    
    def register(self, checking_point_class: Type[CheckingPoint]) -> None:
        """Register a checking point class.
        
        Args:
            checking_point_class: Checking point class to register
            
        Raises:
            ValueError: If checking point class is invalid or already registered
        """
        # Validate the checking point class
        if not inspect.isclass(checking_point_class):
            raise ValueError("Checking point must be a class")
        
        if not issubclass(checking_point_class, CheckingPoint):
            raise ValueError("Checking point must inherit from CheckingPoint")
        
        # Get checking point metadata
        name = getattr(checking_point_class, "name", None)
        cp_type = getattr(checking_point_class, "type", None)
        
        if not name:
            raise ValueError("Checking point class must have a 'name' attribute")
        
        if not cp_type:
            raise ValueError("Checking point class must have a 'type' attribute")
        
        # Check if already registered
        if name in self._checking_points:
            raise ValueError(f"Checking point '{name}' is already registered")
        
        # Register the checking point
        self._checking_points[name] = checking_point_class
        
        # Update type mapping
        if cp_type not in self._type_mapping:
            self._type_mapping[cp_type] = []
        self._type_mapping[cp_type].append(name)
    
    def unregister(self, name: str) -> None:
        """Unregister a checking point.
        
        Args:
            name: Name of the checking point to unregister
            
        Raises:
            KeyError: If checking point is not registered
        """
        if name not in self._checking_points:
            raise KeyError(f"Checking point '{name}' is not registered")
        
        checking_point_class = self._checking_points[name]
        cp_type = getattr(checking_point_class, "type", None)
        
        # Remove from registry
        del self._checking_points[name]
        
        # Remove from type mapping
        if cp_type and cp_type in self._type_mapping:
            self._type_mapping[cp_type] = [
                name for name in self._type_mapping[cp_type] if name != name
            ]
            
            if not self._type_mapping[cp_type]:
                del self._type_mapping[cp_type]
        
        # Remove instances
        if name in self._instances:
            del self._instances[name]
    
    def get_class(self, name: str) -> Optional[Type[CheckingPoint]]:
        """Get a checking point class by name.
        
        Args:
            name: Name of the checking point
            
        Returns:
            Checking point class or None if not found
        """
        return self._checking_points.get(name)
    
    def get_instance(self, name: str, config: Optional[Dict[str, Any]] = None) -> Optional[CheckingPoint]:
        """Get a checking point instance by name.
        
        Args:
            name: Name of the checking point
            config: Configuration for the checking point instance
            
        Returns:
            Checking point instance or None if not found
        """
        # Return existing instance if available and no config provided
        if name in self._instances and config is None:
            return self._instances[name]
        
        # Get the checking point class
        checking_point_class = self.get_class(name)
        if not checking_point_class:
            return None
        
        # Create new instance
        instance = checking_point_class(config)
        
        # Cache instance if no config provided
        if config is None:
            self._instances[name] = instance
        
        return instance
    
    def get_all_classes(self) -> Dict[str, Type[CheckingPoint]]:
        """Get all registered checking point classes.
        
        Returns:
            Dictionary mapping names to checking point classes
        """
        return self._checking_points.copy()
    
    def get_all_instances(self, configs: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, CheckingPoint]:
        """Get all checking point instances.
        
        Args:
            configs: Optional configuration dictionary for instances
            
        Returns:
            Dictionary mapping names to checking point instances
        """
        instances = {}
        configs = configs or {}
        
        for name in self._checking_points:
            config = configs.get(name)
            instance = self.get_instance(name, config)
            if instance:
                instances[name] = instance
        
        return instances
    
    def get_by_type(self, cp_type: Union[str, CheckingPointType]) -> List[str]:
        """Get checking point names by type.
        
        Args:
            cp_type: Type of checking points to get
            
        Returns:
            List of checking point names of the specified type
        """
        if isinstance(cp_type, str):
            cp_type = CheckingPointType(cp_type)
        
        return self._type_mapping.get(cp_type, []).copy()
    
    def get_enabled_instances(self, configs: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, CheckingPoint]:
        """Get only enabled checking point instances.
        
        Args:
            configs: Optional configuration dictionary for instances
            
        Returns:
            Dictionary mapping names to enabled checking point instances
        """
        all_instances = self.get_all_instances(configs)
        return {
            name: instance for name, instance in all_instances.items()
            if instance.enabled
        }
    
    def validate_all(self, configs: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, List[str]]:
        """Validate all registered checking points.
        
        Args:
            configs: Optional configuration dictionary for instances
            
        Returns:
            Dictionary mapping checking point names to validation error lists
        """
        errors = {}
        instances = self.get_all_instances(configs)
        
        for name, instance in instances.items():
            validation_errors = instance.validate_config()
            if validation_errors:
                errors[name] = validation_errors
        
        return errors
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the registry.
        
        Returns:
            Dictionary containing registry summary information
        """
        return {
            "total_checking_points": len(self._checking_points),
            "total_instances": len(self._instances),
            "type_counts": {
                cp_type.value: len(names) 
                for cp_type, names in self._type_mapping.items()
            },
            "checking_points": {
                name: {
                    "name": name,
                    "type": cp_class.type.value,
                    "description": getattr(cp_class, "description", ""),
                    "version": getattr(cp_class, "version", "1.0.0"),
                }
                for name, cp_class in self._checking_points.items()
            },
        }
    
    def auto_discover(self, package_paths: List[str]) -> None:
        """Automatically discover and register checking points from packages.
        
        Args:
            package_paths: List of package paths to search for checking points
        """
        import importlib
        import pkgutil
        
        for package_path in package_paths:
            try:
                # Import the package
                package = importlib.import_module(package_path)
                
                # Iterate through all modules in the package
                for importer, modname, ispkg in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
                    try:
                        module = importlib.import_module(modname)
                        
                        # Look for checking point classes in the module
                        for name, obj in inspect.getmembers(module, inspect.isclass):
                            if (obj != CheckingPoint and 
                                issubclass(obj, CheckingPoint) and 
                                obj.__module__ == module.__name__):
                                
                                # Register the checking point
                                self.register(obj)
                                
                    except (ImportError, AttributeError) as e:
                        # Skip modules that can't be imported or don't have checking points
                        continue
                        
            except ImportError:
                # Skip packages that can't be imported
                continue
    
    def initialize(self, auto_discover_packages: Optional[List[str]] = None) -> None:
        """Initialize the registry.
        
        Args:
            auto_discover_packages: Optional list of packages to auto-discover
        """
        if self._initialized:
            return
        
        # Auto-discover checking points if requested
        if auto_discover_packages:
            self.auto_discover(auto_discover_packages)
        
        self._initialized = True


# Global registry instance
checking_point_registry = CheckingPointRegistry()


def register_checking_point(checking_point_class: Type[CheckingPoint]) -> Type[CheckingPoint]:
    """Decorator for registering checking point classes.
    
    Args:
        checking_point_class: Checking point class to register
        
    Returns:
        The same checking point class (for decorator usage)
    """
    checking_point_registry.register(checking_point_class)
    return checking_point_class


def get_checking_point(name: str, config: Optional[Dict[str, Any]] = None) -> Optional[CheckingPoint]:
    """Get a checking point instance by name.
    
    Args:
        name: Name of the checking point
        config: Optional configuration for the checking point
        
    Returns:
        Checking point instance or None if not found
    """
    return checking_point_registry.get_instance(name, config)


def get_all_checking_points(configs: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, CheckingPoint]:
    """Get all checking point instances.
    
    Args:
        configs: Optional configuration dictionary for instances
        
    Returns:
        Dictionary mapping names to checking point instances
    """
    return checking_point_registry.get_all_instances(configs)


def get_checking_points_by_type(cp_type: Union[str, CheckingPointType], 
                               configs: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, CheckingPoint]:
    """Get checking point instances by type.
    
    Args:
        cp_type: Type of checking points to get
        configs: Optional configuration dictionary for instances
        
    Returns:
        Dictionary mapping names to checking point instances of the specified type
    """
    names = checking_point_registry.get_by_type(cp_type)
    instances = {}
    
    for name in names:
        config = configs.get(name) if configs else None
        instance = checking_point_registry.get_instance(name, config)
        if instance:
            instances[name] = instance
    
    return instances


def initialize_registry(auto_discover_packages: Optional[List[str]] = None) -> None:
    """Initialize the global checking point registry.
    
    Args:
        auto_discover_packages: Optional list of packages to auto-discover
    """
    checking_point_registry.initialize(auto_discover_packages)
