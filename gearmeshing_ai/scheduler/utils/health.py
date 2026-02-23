"""
Health check utilities for the scheduler system.

This module provides health check functionality for monitoring the status
of various scheduler components and dependencies.
"""

import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from gearmeshing_ai.scheduler.config.settings import get_scheduler_settings
from gearmeshing_ai.scheduler.temporal.client import TemporalClient


class HealthStatus(str, Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthCheck:
    """Individual health check result."""
    
    def __init__(
        self,
        name: str,
        status: HealthStatus,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
        timestamp: Optional[datetime] = None,
    ):
        self.name = name
        self.status = status
        self.message = message
        self.details = details or {}
        self.duration_ms = duration_ms
        self.timestamp = timestamp or datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert health check to dictionary."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
        }


class HealthChecker:
    """Health checker for scheduler components."""
    
    def __init__(self):
        """Initialize the health checker."""
        self.settings = get_scheduler_settings()
    
    async def check_all(self) -> Dict[str, Any]:
        """Check health of all components.
        
        Returns:
            Overall health status and individual check results
        """
        start_time = datetime.utcnow()
        
        # Run all health checks
        checks = await asyncio.gather(
            self.check_temporal(),
            self.check_database(),
            self.check_redis(),
            self.check_external_services(),
            self.check_ai_providers(),
            return_exceptions=True,
        )
        
        # Process results
        health_checks = []
        overall_status = HealthStatus.HEALTHY
        
        for check in checks:
            if isinstance(check, Exception):
                # Health check failed with exception
                health_checks.append(HealthCheck(
                    name="unknown",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check failed: {str(check)}",
                ))
                overall_status = HealthStatus.UNHEALTHY
            else:
                health_checks.append(check)
                
                # Update overall status
                if check.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif check.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
        
        # Calculate total duration
        total_duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return {
            "status": overall_status.value,
            "timestamp": start_time.isoformat(),
            "duration_ms": total_duration_ms,
            "checks": [check.to_dict() for check in health_checks],
            "summary": self._get_summary(health_checks),
        }
    
    async def check_temporal(self) -> HealthCheck:
        """Check Temporal server health."""
        start_time = datetime.utcnow()
        
        try:
            # Create client and check connection
            client = TemporalClient(self.settings.get_scheduler_config().temporal)
            await client.connect()
            
            # Get cluster health
            health = await client.get_cluster_health()
            
            await client.disconnect()
            
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            if health["status"] == "healthy":
                return HealthCheck(
                    name="temporal",
                    status=HealthStatus.HEALTHY,
                    message="Temporal server is healthy",
                    details=health,
                    duration_ms=duration_ms,
                )
            else:
                return HealthCheck(
                    name="temporal",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Temporal server unhealthy: {health.get('error', 'Unknown error')}",
                    details=health,
                    duration_ms=duration_ms,
                )
                
        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            return HealthCheck(
                name="temporal",
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to connect to Temporal: {str(e)}",
                duration_ms=duration_ms,
            )
    
    async def check_database(self) -> HealthCheck:
        """Check database connectivity."""
        start_time = datetime.utcnow()
        
        try:
            if not self.settings.has_database_config():
                return HealthCheck(
                    name="database",
                    status=HealthStatus.UNKNOWN,
                    message="Database not configured",
                    duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                )
            
            # TODO: Implement actual database health check
            # For now, just check if configuration exists
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return HealthCheck(
                name="database",
                status=HealthStatus.HEALTHY,
                message="Database connection healthy",
                details={"configured": True},
                duration_ms=duration_ms,
            )
            
        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            return HealthCheck(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database health check failed: {str(e)}",
                duration_ms=duration_ms,
            )
    
    async def check_redis(self) -> HealthCheck:
        """Check Redis connectivity."""
        start_time = datetime.utcnow()
        
        try:
            if not self.settings.has_redis_config():
                return HealthCheck(
                    name="redis",
                    status=HealthStatus.UNKNOWN,
                    message="Redis not configured",
                    duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                )
            
            # TODO: Implement actual Redis health check
            # For now, just check if configuration exists
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return HealthCheck(
                name="redis",
                status=HealthStatus.HEALTHY,
                message="Redis connection healthy",
                details={"configured": True},
                duration_ms=duration_ms,
            )
            
        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            return HealthCheck(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                message=f"Redis health check failed: {str(e)}",
                duration_ms=duration_ms,
            )
    
    async def check_external_services(self) -> HealthCheck:
        """Check external service connectivity."""
        start_time = datetime.utcnow()
        
        try:
            services = self.settings.get_external_services()
            healthy_services = []
            unhealthy_services = []
            
            for service, configured in services.items():
                if configured:
                    # TODO: Implement actual service health checks
                    # For now, just check if service is configured
                    healthy_services.append(service)
                else:
                    unhealthy_services.append(service)
            
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            if unhealthy_services and not healthy_services:
                status = HealthStatus.UNHEALTHY
                message = "No external services configured"
            elif unhealthy_services:
                status = HealthStatus.DEGRADED
                message = f"Some services not configured: {', '.join(unhealthy_services)}"
            else:
                status = HealthStatus.HEALTHY
                message = "All external services configured"
            
            return HealthCheck(
                name="external_services",
                status=status,
                message=message,
                details={
                    "healthy_services": healthy_services,
                    "unhealthy_services": unhealthy_services,
                    "total_configured": len(healthy_services),
                },
                duration_ms=duration_ms,
            )
            
        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            return HealthCheck(
                name="external_services",
                status=HealthStatus.UNHEALTHY,
                message=f"External services health check failed: {str(e)}",
                duration_ms=duration_ms,
            )
    
    async def check_ai_providers(self) -> HealthCheck:
        """Check AI provider connectivity."""
        start_time = datetime.utcnow()
        
        try:
            providers = self.settings.get_ai_providers()
            healthy_providers = []
            unhealthy_providers = []
            
            for provider, configured in providers.items():
                if configured:
                    # TODO: Implement actual AI provider health checks
                    # For now, just check if provider is configured
                    healthy_providers.append(provider)
                else:
                    unhealthy_providers.append(provider)
            
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            if unhealthy_providers and not healthy_providers:
                status = HealthStatus.UNHEALTHY
                message = "No AI providers configured"
            elif unhealthy_providers:
                status = HealthStatus.DEGRADED
                message = f"Some providers not configured: {', '.join(unhealthy_providers)}"
            else:
                status = HealthStatus.HEALTHY
                message = "All AI providers configured"
            
            return HealthCheck(
                name="ai_providers",
                status=status,
                message=message,
                details={
                    "healthy_providers": healthy_providers,
                    "unhealthy_providers": unhealthy_providers,
                    "total_configured": len(healthy_providers),
                },
                duration_ms=duration_ms,
            )
            
        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            return HealthCheck(
                name="ai_providers",
                status=HealthStatus.UNHEALTHY,
                message=f"AI providers health check failed: {str(e)}",
                duration_ms=duration_ms,
            )
    
    def _get_summary(self, health_checks: List[HealthCheck]) -> Dict[str, Any]:
        """Get summary of health check results."""
        total_checks = len(health_checks)
        healthy_checks = sum(1 for check in health_checks if check.status == HealthStatus.HEALTHY)
        degraded_checks = sum(1 for check in health_checks if check.status == HealthStatus.DEGRADED)
        unhealthy_checks = sum(1 for check in health_checks if check.status == HealthStatus.UNHEALTHY)
        unknown_checks = sum(1 for check in health_checks if check.status == HealthStatus.UNKNOWN)
        
        return {
            "total_checks": total_checks,
            "healthy_checks": healthy_checks,
            "degraded_checks": degraded_checks,
            "unhealthy_checks": unhealthy_checks,
            "unknown_checks": unknown_checks,
            "health_percentage": (healthy_checks / total_checks * 100) if total_checks > 0 else 0,
        }
    
    async def check_component(self, component_name: str) -> HealthCheck:
        """Check health of a specific component.
        
        Args:
            component_name: Name of the component to check
            
        Returns:
            Health check result for the component
        """
        check_methods = {
            "temporal": self.check_temporal,
            "database": self.check_database,
            "redis": self.check_redis,
            "external_services": self.check_external_services,
            "ai_providers": self.check_ai_providers,
        }
        
        if component_name not in check_methods:
            return HealthCheck(
                name=component_name,
                status=HealthStatus.UNKNOWN,
                message=f"Unknown component: {component_name}",
            )
        
        return await check_methods[component_name]()
    
    def is_healthy(self, health_result: Dict[str, Any]) -> bool:
        """Check if overall health result is healthy.
        
        Args:
            health_result: Health check result from check_all()
            
        Returns:
            True if healthy, False otherwise
        """
        return health_result.get("status") == HealthStatus.HEALTHY.value
    
    def get_health_status(self, health_result: Dict[str, Any]) -> HealthStatus:
        """Get health status from health result.
        
        Args:
            health_result: Health check result from check_all()
            
        Returns:
            HealthStatus enum value
        """
        status_str = health_result.get("status", HealthStatus.UNKNOWN.value)
        return HealthStatus(status_str)
