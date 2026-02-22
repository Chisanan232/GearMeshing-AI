"""
Bot mention checking point for Slack.

This checking point detects when the bot is mentioned in Slack messages
and triggers appropriate responses or workflows.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from gearmeshing_ai.scheduler.checking_points.base import CheckingPoint, CheckingPointType
from gearmeshing_ai.scheduler.models.monitoring import MonitoringData, MonitoringDataType
from gearmeshing_ai.scheduler.models.checking_point import CheckResult, CheckResultType
from gearmeshing_ai.scheduler.models.workflow import AIAction


class BotMentionCheckingPoint(CheckingPoint):
    """Checking point that detects bot mentions in Slack messages."""
    
    name = "slack_bot_mention_cp"
    type = CheckingPointType.SLACK_BOT_MENTION_CP
    description = "Detects when the bot is mentioned in Slack messages and triggers responses"
    version = "1.0.0"
    priority = 7
    stop_on_match = False
    ai_workflow_enabled = True
    prompt_template_id = "slack_bot_mention_response"
    agent_role = "support"
    timeout_seconds = 600
    approval_required = False
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the bot mention checking point.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        
        # Configuration options
        self.bot_user_id = config.get("bot_user_id", "") if config else ""
        self.bot_name = config.get("bot_name", "bot") if config else "bot"
        self.mention_patterns = config.get("mention_patterns", []) if config else []
        self.response_channels = config.get("response_channels", []) if config else []
        self.auto_reply = config.get("auto_reply", True) if config else True
        self.ignore_bots = config.get("ignore_bots", True) if config else True
        self.required_permissions = config.get("required_permissions", []) if config else []
        
        # Default mention patterns if not provided
        if not self.mention_patterns:
            self.mention_patterns = [
                f"<@{self.bot_user_id}>",
                f"@{self.bot_name}",
                f"{self.bot_name}",
            ]
    
    def can_handle(self, data: MonitoringData) -> bool:
        """Check if this checking point can handle the monitoring data.
        
        Args:
            data: Monitoring data to check
            
        Returns:
            True if this checking point can handle the data
        """
        if not self.enabled:
            return False
        
        # Only handle Slack messages
        if data.type != MonitoringDataType.SLACK_MESSAGE:
            return False
        
        # Check if message contains bot mention
        message_text = data.data.get("text", "").lower()
        
        for pattern in self.mention_patterns:
            if pattern.lower() in message_text:
                return True
        
        return False
    
    def evaluate(self, data: MonitoringData) -> CheckResult:
        """Evaluate the monitoring data for bot mentions.
        
        Args:
            data: Monitoring data to evaluate
            
        Returns:
            Check result indicating if bot was mentioned
        """
        message_data = data.data
        message_text = message_data.get("text", "")
        channel = message_data.get("channel", "")
        user = message_data.get("user", "")
        is_bot = message_data.get("bot_id", "") != ""
        
        # Check if we should ignore bot messages
        if self.ignore_bots and is_bot:
            return CheckResult(
                checking_point_name=self.name,
                checking_point_type=self.type.value,
                result_type=CheckResultType.NO_MATCH,
                should_act=False,
                confidence=1.0,
                reason="Ignoring bot message",
                context={"is_bot": True},
            )
        
        # Find mention patterns in message
        found_patterns = []
        for pattern in self.mention_patterns:
            if pattern.lower() in message_text.lower():
                found_patterns.append(pattern)
        
        if not found_patterns:
            return CheckResult(
                checking_point_name=self.name,
                checking_point_type=self.type.value,
                result_type=CheckResultType.NO_MATCH,
                should_act=False,
                confidence=0.9,
                reason="No bot mention found in message",
                context={"message_text": message_text[:100]},  # Truncate for context
            )
        
        # Extract the actual command/question after the mention
        cleaned_text = self._extract_command_text(message_text, found_patterns)
        
        # Determine confidence based on context
        confidence = self._calculate_mention_confidence(message_data, found_patterns)
        
        return CheckResult(
            checking_point_name=self.name,
            checking_point_type=self.type.value,
            result_type=CheckResultType.MATCH,
            should_act=True,
            confidence=confidence,
            reason=f"Bot mentioned with patterns: {', '.join(found_patterns)}",
            context={
                "found_patterns": found_patterns,
                "command_text": cleaned_text,
                "channel": channel,
                "user": user,
                "is_bot": is_bot,
                "message_length": len(message_text),
            },
            suggested_actions=["respond_to_mention", "log_interaction"],
        )
    
    def get_actions(self, data: MonitoringData, result: CheckResult) -> List[Dict[str, Any]]:
        """Get immediate actions for bot mention.
        
        Args:
            data: Monitoring data
            result: Check result
            
        Returns:
            List of immediate actions to take
        """
        actions = []
        
        if not self.auto_reply:
            return actions
        
        message_data = data.data
        channel = message_data.get("channel", "")
        user = message_data.get("user", "")
        thread_ts = message_data.get("thread_ts", message_data.get("ts", ""))
        
        # Add typing indicator action
        actions.append({
            "type": "slack_typing",
            "name": "show_typing",
            "params": {
                "channel": channel,
                "user": user,
            },
            "priority": 8,
        })
        
        # Add acknowledgment message
        actions.append({
            "type": "slack_message",
            "name": "acknowledge_mention",
            "params": {
                "channel": channel,
                "thread_ts": thread_ts,
                "message": f"Hi <@{user}>! I've received your message and I'm processing it...",
            },
            "priority": 7,
        })
        
        return actions
    
    def get_after_process(self, data: MonitoringData, result: CheckResult) -> List[AIAction]:
        """Get AI workflow actions for bot mention.
        
        Args:
            data: Monitoring data
            result: Check result
            
        Returns:
            List of AI workflow actions
        """
        if not self.ai_workflow_enabled or not result.should_act:
            return []
        
        message_data = data.data
        channel = message_data.get("channel", "")
        user = message_data.get("user", "")
        thread_ts = message_data.get("thread_ts", message_data.get("ts", ""))
        
        # Create AI workflow action
        action = AIAction(
            name=f"{self.name}_workflow",
            workflow_name="slack_bot_mention_response",
            checking_point_name=self.name,
            prompt_template_id=self.prompt_template_id,
            agent_role=self.agent_role,
            timeout_seconds=self.timeout_seconds,
            approval_required=self.approval_required,
            input_data={
                "monitoring_data": data.dict(),
                "check_result": result.dict(),
                "slack_context": {
                    "channel": channel,
                    "user": user,
                    "thread_ts": thread_ts,
                    "command_text": result.context.get("command_text", ""),
                    "found_patterns": result.context.get("found_patterns", []),
                },
            },
        )
        
        return [action]
    
    def _extract_command_text(self, message_text: str, found_patterns: List[str]) -> str:
        """Extract the actual command/question after removing mention patterns.
        
        Args:
            message_text: Original message text
            found_patterns: List of mention patterns found
            
        Returns:
            Cleaned command text
        """
        cleaned_text = message_text
        
        # Remove mention patterns
        for pattern in found_patterns:
            cleaned_text = cleaned_text.replace(pattern, "").strip()
        
        # Remove extra whitespace
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
        
        return cleaned_text
    
    def _calculate_mention_confidence(self, message_data: Dict[str, Any], found_patterns: List[str]) -> float:
        """Calculate confidence score for the bot mention.
        
        Args:
            message_data: Message data
            found_patterns: List of mention patterns found
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        base_confidence = 0.7
        
        # Higher confidence for direct mentions (@bot)
        if any(pattern.startswith("@") for pattern in found_patterns):
            base_confidence += 0.2
        
        # Higher confidence for user ID mentions (<@U123>)
        if any(pattern.startswith("<@") for pattern in found_patterns):
            base_confidence += 0.1
        
        # Lower confidence for name-only mentions (can be false positives)
        if any(not pattern.startswith("@") and not pattern.startswith("<@") for pattern in found_patterns):
            base_confidence -= 0.1
        
        # Check message length (very short messages might be accidental)
        message_text = message_data.get("text", "")
        if len(message_text.strip()) < 10:
            base_confidence -= 0.1
        
        # Check if message is in a DM channel (more likely intentional)
        channel = message_data.get("channel", "")
        if channel.startswith("D"):  # DM channel
            base_confidence += 0.1
        
        # Ensure confidence is within bounds
        return max(0.0, min(1.0, base_confidence))
    
    def validate_config(self) -> List[str]:
        """Validate the checking point configuration.
        
        Returns:
            List of validation errors
        """
        errors = super().validate_config()
        
        if not self.bot_name and not self.bot_user_id:
            errors.append("Either bot_name or bot_user_id must be configured")
        
        if not self.mention_patterns:
            errors.append("At least one mention pattern must be configured")
        
        return errors
