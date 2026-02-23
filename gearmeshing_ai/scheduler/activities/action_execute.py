"""
Action execution activities for the scheduler system.

This module contains activities for executing immediate actions that don't
require AI workflows, such as sending notifications or updating status.
"""

from datetime import datetime
from typing import Any, Dict

from temporalio import activity

from gearmeshing_ai.scheduler.activities.base import BaseActivity


class ActionExecutionActivity(BaseActivity):
    """Activity for executing immediate actions that don't require AI workflows."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.name = "action_execution_activity"
        self.description = "Execute immediate actions without AI workflows"
        self.version = "1.0.0"
        self.timeout_seconds = 300
    
    async def execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an immediate action.
        
        This method executes immediate actions that don't require AI workflows,
        such as sending notifications, updating status, or making simple API calls.
        
        Args:
            action: Action configuration dictionary
            
        Returns:
            Action execution result
        """
        self.log_activity_start(
            "execute_action",
            action_type=action.get("type", "unknown"),
            action_name=action.get("name", "unnamed"),
        )
        
        start_time = datetime.utcnow()
        
        try:
            action_type = action.get("type")
            action_name = action.get("name", "unnamed")
            action_params = action.get("parameters", {})
            
            # Execute different types of actions
            if action_type == "notification":
                result = await self._execute_notification_action(action_params)
            elif action_type == "status_update":
                result = await self._execute_status_update_action(action_params)
            elif action_type == "api_call":
                result = await self._execute_api_call_action(action_params)
            elif action_type == "webhook":
                result = await self._execute_webhook_action(action_params)
            else:
                result = {
                    "success": False,
                    "error": f"Unknown action type: {action_type}",
                    "action_name": action_name,
                }
            
            execution_time = self.measure_execution_time(start_time)
            
            self.log_activity_complete(
                "execute_action",
                action_type=action_type,
                action_name=action_name,
                success=result.get("success", False),
                execution_time_ms=int(execution_time.total_seconds() * 1000),
            )
            
            return result
            
        except Exception as e:
            self.log_activity_error(
                "execute_action",
                e,
                action_type=action.get("type"),
                action_name=action.get("name"),
            )
            
            return {
                "success": False,
                "error": str(e),
                "action_name": action.get("name", "unnamed"),
            }
    
    async def _execute_notification_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute notification action."""
        # Mock implementation
        return {
            "success": True,
            "message": f"Notification sent: {params.get('message', 'No message')}",
            "channel": params.get("channel", "default"),
        }
    
    async def _execute_status_update_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute status update action."""
        # Mock implementation
        return {
            "success": True,
            "message": f"Status updated: {params.get('status', 'unknown')}",
            "item_id": params.get("item_id", "unknown"),
        }
    
    async def _execute_api_call_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute API call action."""
        # Mock implementation
        return {
            "success": True,
            "message": f"API call made to: {params.get('url', 'unknown')}",
            "method": params.get("method", "GET"),
        }
    
    async def _execute_webhook_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute webhook action."""
        # Mock implementation
        return {
            "success": True,
            "message": f"Webhook sent to: {params.get('url', 'unknown')}",
            "event": params.get("event", "unknown"),
        }


# Keep the original activity functions for Temporal workflow compatibility
@activity.defn
async def execute_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """Execute an immediate action."""
    activity_instance = ActionExecutionActivity()
    return await activity_instance.execute_action(action)


async def execute_notification_action(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a notification action.
    
    Args:
        params: Notification parameters
        
    Returns:
        Notification execution result
    """
    base = BaseActivity()
    
    try:
        notification_type = params.get("notification_type", "email")
        recipient = params.get("recipient")
        subject = params.get("subject", "")
        message = params.get("message", "")
        
        if notification_type == "email":
            # Send email notification
            result = await send_email_notification(recipient, subject, message)
        elif notification_type == "slack":
            # Send Slack notification
            result = await send_slack_notification(recipient, message)
        elif notification_type == "teams":
            # Send Teams notification
            result = await send_teams_notification(recipient, message)
        else:
            result = {
                "success": False,
                "error": f"Unknown notification type: {notification_type}",
            }
        
        base.logger.info(
            f"Sent {notification_type} notification",
            extra={
                "notification_type": notification_type,
                "recipient": recipient,
                "success": result.get("success", False),
            }
        )
        
        return result
        
    except Exception as e:
        base.logger.error(f"Error executing notification action: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "notification_type": params.get("notification_type", "unknown"),
        }


async def execute_status_update_action(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a status update action.
    
    Args:
        params: Status update parameters
        
    Returns:
        Status update execution result
    """
    base = BaseActivity()
    
    try:
        system = params.get("system", "unknown")
        entity_id = params.get("entity_id")
        new_status = params.get("new_status")
        update_reason = params.get("reason", "")
        
        if system == "clickup":
            result = await update_clickup_task_status(entity_id, new_status, update_reason)
        elif system == "jira":
            result = await update_jira_issue_status(entity_id, new_status, update_reason)
        elif system == "github":
            result = await update_github_issue_status(entity_id, new_status, update_reason)
        else:
            result = {
                "success": False,
                "error": f"Unknown system: {system}",
            }
        
        base.logger.info(
            f"Updated status in {system}",
            extra={
                "system": system,
                "entity_id": entity_id,
                "new_status": new_status,
                "success": result.get("success", False),
            }
        )
        
        return result
        
    except Exception as e:
        base.logger.error(f"Error executing status update action: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "system": params.get("system", "unknown"),
        }


async def execute_api_call_action(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute an API call action.
    
    Args:
        params: API call parameters
        
    Returns:
        API call execution result
    """
    base = BaseActivity()
    
    try:
        url = params.get("url")
        method = params.get("method", "POST")
        headers = params.get("headers", {})
        data = params.get("data", {})
        
        # Make API call using httpx or requests
        import httpx
        
        async with httpx.AsyncClient() as client:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers)
            elif method.upper() == "POST":
                response = await client.post(url, headers=headers, json=data)
            elif method.upper() == "PUT":
                response = await client.put(url, headers=headers, json=data)
            elif method.upper() == "DELETE":
                response = await client.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
        
        result = {
            "success": response.status_code < 400,
            "status_code": response.status_code,
            "response_data": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
            "url": url,
            "method": method,
        }
        
        base.logger.info(
            f"Made API call to {url}",
            extra={
                "url": url,
                "method": method,
                "status_code": response.status_code,
                "success": result["success"],
            }
        )
        
        return result
        
    except Exception as e:
        base.logger.error(f"Error executing API call action: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "url": params.get("url", "unknown"),
            "method": params.get("method", "unknown"),
        }


async def execute_webhook_action(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a webhook action.
    
    Args:
        params: Webhook parameters
        
    Returns:
        Webhook execution result
    """
    base = BaseActivity()
    
    try:
        webhook_url = params.get("webhook_url")
        payload = params.get("payload", {})
        secret = params.get("secret")
        
        # Make webhook call
        import httpx
        import hashlib
        import hmac
        
        headers = {"Content-Type": "application/json"}
        
        # Add signature if secret is provided
        if secret:
            payload_str = str(payload)
            signature = hmac.new(
                secret.encode(),
                payload_str.encode(),
                hashlib.sha256
            ).hexdigest()
            headers["X-Webhook-Signature"] = f"sha256={signature}"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, headers=headers, json=payload)
        
        result = {
            "success": response.status_code < 400,
            "status_code": response.status_code,
            "response_data": response.text,
            "webhook_url": webhook_url,
        }
        
        base.logger.info(
            f"Triggered webhook {webhook_url}",
            extra={
                "webhook_url": webhook_url,
                "status_code": response.status_code,
                "success": result["success"],
            }
        )
        
        return result
        
    except Exception as e:
        base.logger.error(f"Error executing webhook action: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "webhook_url": params.get("webhook_url", "unknown"),
        }


# Helper functions for specific notification systems
async def send_email_notification(recipient: str, subject: str, message: str) -> Dict[str, Any]:
    """Send email notification.
    
    Args:
        recipient: Email recipient
        subject: Email subject
        message: Email message
        
    Returns:
        Send result
    """
    # This would integrate with email service
    # For now, return mock result
    return {
        "success": True,
        "recipient": recipient,
        "subject": subject,
        "message_id": f"email_{datetime.utcnow().timestamp()}",
    }


async def send_slack_notification(channel: str, message: str) -> Dict[str, Any]:
    """Send Slack notification.
    
    Args:
        channel: Slack channel
        message: Message to send
        
    Returns:
        Send result
    """
    # This would integrate with Slack API via MCP Gateway
    # For now, return mock result
    return {
        "success": True,
        "channel": channel,
        "message_ts": f"{datetime.utcnow().timestamp()}.000001",
        "message_id": f"slack_{datetime.utcnow().timestamp()}",
    }


async def send_teams_notification(channel: str, message: str) -> Dict[str, Any]:
    """Send Teams notification.
    
    Args:
        channel: Teams channel
        message: Message to send
        
    Returns:
        Send result
    """
    # This would integrate with Teams API
    # For now, return mock result
    return {
        "success": True,
        "channel": channel,
        "message_id": f"teams_{datetime.utcnow().timestamp()}",
    }


# Helper functions for status update systems
async def update_clickup_task_status(task_id: str, new_status: str, reason: str) -> Dict[str, Any]:
    """Update ClickUp task status.
    
    Args:
        task_id: ClickUp task ID
        new_status: New status
        reason: Update reason
        
    Returns:
        Update result
    """
    # This would integrate with ClickUp API via MCP Gateway
    # For now, return mock result
    return {
        "success": True,
        "task_id": task_id,
        "old_status": "in_progress",
        "new_status": new_status,
        "updated_at": datetime.utcnow().isoformat(),
    }


async def update_jira_issue_status(issue_id: str, new_status: str, reason: str) -> Dict[str, Any]:
    """Update Jira issue status.
    
    Args:
        issue_id: Jira issue ID
        new_status: New status
        reason: Update reason
        
    Returns:
        Update result
    """
    # This would integrate with Jira API
    # For now, return mock result
    return {
        "success": True,
        "issue_id": issue_id,
        "old_status": "In Progress",
        "new_status": new_status,
        "updated_at": datetime.utcnow().isoformat(),
    }


async def update_github_issue_status(issue_id: str, new_status: str, reason: str) -> Dict[str, Any]:
    """Update GitHub issue status.
    
    Args:
        issue_id: GitHub issue ID
        new_status: New status
        reason: Update reason
        
    Returns:
        Update result
    """
    # This would integrate with GitHub API via MCP Gateway
    # For now, return mock result
    return {
        "success": True,
        "issue_id": issue_id,
        "old_status": "open",
        "new_status": new_status,
        "updated_at": datetime.utcnow().isoformat(),
    }
