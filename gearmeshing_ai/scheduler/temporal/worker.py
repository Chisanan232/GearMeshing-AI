"""
Temporal worker setup for the scheduler system.

This module provides the worker configuration and setup for running Temporal
workflows and activities in the scheduler system.
"""

import asyncio
import signal
import sys
from datetime import timedelta
from typing import Any, Dict, List, Optional

from temporalio.worker import Worker
from temporalio.client import Client
from temporalio.worker.workflow_sandbox import (
    SandboxRestrictions,
)

from gearmeshing_ai.scheduler.models.config import SchedulerTemporalConfig
from gearmeshing_ai.scheduler.workflows import SmartMonitoringWorkflow, AIWorkflowExecutor
from gearmeshing_ai.scheduler.activities import (
    fetch_monitoring_data,
    evaluate_checking_point,
    execute_action,
    execute_ai_workflow,
)


class TemporalWorker:
    """Temporal worker with scheduler-specific configuration.
    
    This class provides a Temporal worker with the workflows and activities
    needed for the scheduler system, along with proper sandbox configuration
    and error handling.
    """
    
    def __init__(self, config: SchedulerTemporalConfig) -> None:
        """Initialize the Temporal worker.
        
        Args:
            config: Temporal configuration
        """
        self.config = config
        self._worker: Optional[Worker] = None
        self._client: Optional[Client] = None
        self._running = False
        self._shutdown_event = asyncio.Event()
    
    async def start(self) -> None:
        """Start the Temporal worker."""
        if self._running:
            return
        
        try:
            # Create client
            self._client = Client(
                target_host=f"{self.config.host}:{self.config.port}",
                namespace=self.config.namespace,
            )
            
            # Create sandbox restrictions
            sandbox = self._create_sandbox_restrictions()
            
            # Create worker
            self._worker = Worker(
                client=self._client,
                task_queue=self.config.task_queue,
                workflows=[
                    SmartMonitoringWorkflow,
                    AIWorkflowExecutor,
                ],
                activities=[
                    fetch_monitoring_data,
                    evaluate_checking_point,
                    execute_action,
                    execute_ai_workflow,
                ],
                sandbox=sandbox,
                max_concurrent_activities=self.config.worker_count,
                poll_timeout=self.config.worker_poll_timeout,
            )
            
            # Set up signal handlers for graceful shutdown
            self._setup_signal_handlers()
            
            # Start the worker
            self._running = True
            await self._worker.run()
            
        except Exception as e:
            self._running = False
            raise RuntimeError(f"Failed to start Temporal worker: {str(e)}")
    
    async def stop(self) -> None:
        """Stop the Temporal worker."""
        if not self._running:
            return
        
        self._running = False
        self._shutdown_event.set()
        
        if self._worker:
            await self._worker.shutdown()
            self._worker = None
        
        if self._client:
            await self._client.close()
            self._client = None
    
    def is_running(self) -> bool:
        """Check if the worker is running.
        
        Returns:
            True if running, False otherwise
        """
        return self._running
    
    def _create_sandbox_restrictions(self) -> Optional[SandboxRestrictions]:
        """Create sandbox restrictions for the worker.
        
        Returns:
            Sandbox restrictions or None if disabled
        """
        # For production, you might want stricter restrictions
        # For development, we'll allow more permissive settings
        
        restrictions = SandboxRestrictions(
            # Allow network access for external API calls
            network_addresses=[
                "localhost",
                "127.0.0.1",
                # Add your external service domains here
                "api.clickup.com",
                "slack.com",
                "hooks.slack.com",
            ],
            # Allow specific modules
            modules=[
                "datetime",
                "json",
                "os",
                "sys",
                "time",
                "uuid",
                "re",
                "hashlib",
                "hmac",
                "base64",
                "urllib.parse",
                "httpx",
                "pydantic",
                "gearmeshing_ai",
            ],
            # Allow specific environment variables
            env_vars=[
                "PATH",
                "HOME",
                "PYTHONPATH",
                # Add your API keys and other env vars here
                "OPENAI_API_KEY",
                "ANTHROPIC_API_KEY",
                "GOOGLE_API_KEY",
                "SLACK_BOT_TOKEN",
                "CLICKUP_API_TOKEN",
            ],
        )
        
        return restrictions
    
    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            print(f"\nReceived signal {signum}, shutting down worker...")
            asyncio.create_task(self.stop())
        
        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def run_until_shutdown(self) -> None:
        """Run the worker until shutdown signal is received.
        
        This is a convenience method that starts the worker and waits for
        a shutdown signal before stopping.
        """
        try:
            await self.start()
        except KeyboardInterrupt:
            print("\nReceived keyboard interrupt, shutting down worker...")
        finally:
            await self.stop()
    
    def get_worker_info(self) -> Dict[str, Any]:
        """Get information about the worker.
        
        Returns:
            Worker information dictionary
        """
        return {
            "task_queue": self.config.task_queue,
            "worker_count": self.config.worker_count,
            "poll_timeout": self.config.worker_poll_timeout.total_seconds(),
            "running": self._running,
            "workflows": [
                "SmartMonitoringWorkflow",
                "AIWorkflowExecutor",
            ],
            "activities": [
                "fetch_monitoring_data",
                "evaluate_checking_point", 
                "execute_action",
                "execute_ai_workflow",
            ],
            "config": {
                "host": self.config.host,
                "port": self.config.port,
                "namespace": self.config.namespace,
            }
        }
    
    async def get_worker_metrics(self) -> Dict[str, Any]:
        """Get worker metrics.
        
        Returns:
            Worker metrics dictionary
        """
        if not self._worker:
            return {"status": "not_running"}
        
        try:
            # This would require additional Temporal API calls
            # For now, return basic information
            return {
                "status": "running",
                "task_queue": self.config.task_queue,
                "worker_count": self.config.worker_count,
                "timestamp": asyncio.get_event_loop().time(),
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "task_queue": self.config.task_queue,
            }
    
    async def __aenter__(self) -> "TemporalWorker":
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop()


class WorkerManager:
    """Manager for multiple Temporal workers.
    
    This class manages multiple Temporal workers, allowing for different
    configurations and task queues to be run simultaneously.
    """
    
    def __init__(self) -> None:
        """Initialize the worker manager."""
        self._workers: Dict[str, TemporalWorker] = {}
        self._running = False
    
    def add_worker(self, name: str, worker: TemporalWorker) -> None:
        """Add a worker to the manager.
        
        Args:
            name: Worker name
            worker: Temporal worker instance
        """
        self._workers[name] = worker
    
    def remove_worker(self, name: str) -> None:
        """Remove a worker from the manager.
        
        Args:
            name: Worker name
        """
        if name in self._workers:
            del self._workers[name]
    
    async def start_all(self) -> None:
        """Start all workers."""
        if self._running:
            return
        
        self._running = True
        
        # Start all workers concurrently
        tasks = []
        for name, worker in self._workers.items():
            task = asyncio.create_task(
                self._run_worker_with_error_handling(name, worker),
                name=f"worker-{name}"
            )
            tasks.append(task)
        
        # Wait for all workers to complete (they should run indefinitely)
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def stop_all(self) -> None:
        """Stop all workers."""
        if not self._running:
            return
        
        self._running = False
        
        # Stop all workers concurrently
        tasks = []
        for name, worker in self._workers.items():
            task = asyncio.create_task(
                self._stop_worker_with_error_handling(name, worker),
                name=f"stop-worker-{name}"
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _run_worker_with_error_handling(self, name: str, worker: TemporalWorker) -> None:
        """Run a worker with error handling.
        
        Args:
            name: Worker name
            worker: Temporal worker instance
        """
        try:
            await worker.run_until_shutdown()
        except Exception as e:
            print(f"Worker {name} failed: {str(e)}")
    
    async def _stop_worker_with_error_handling(self, name: str, worker: TemporalWorker) -> None:
        """Stop a worker with error handling.
        
        Args:
            name: Worker name
            worker: Temporal worker instance
        """
        try:
            await worker.stop()
        except Exception as e:
            print(f"Failed to stop worker {name}: {str(e)}")
    
    def get_worker_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all workers.
        
        Returns:
            Dictionary mapping worker names to their status
        """
        status = {}
        for name, worker in self._workers.items():
            status[name] = worker.get_worker_info()
        
        return status
    
    def is_running(self) -> bool:
        """Check if any workers are running.
        
        Returns:
            True if any workers are running
        """
        return self._running or any(worker.is_running() for worker in self._workers.values())
