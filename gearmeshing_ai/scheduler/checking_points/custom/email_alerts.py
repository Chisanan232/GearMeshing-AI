"""Email alert checking point for custom monitoring.

This checking point detects email alerts and triggers appropriate
workflows for handling critical email notifications.
"""

import re
from typing import Any

from gearmeshing_ai.scheduler.checking_points.base import CheckingPoint, CheckingPointType
from gearmeshing_ai.scheduler.models.checking_point import CheckResult, CheckResultType
from gearmeshing_ai.scheduler.models.monitoring import MonitoringData, MonitoringDataType
from gearmeshing_ai.scheduler.models.workflow import AIAction


class EmailAlertCheckingPoint(CheckingPoint):
    """Checking point that detects email alerts and triggers response workflows."""

    name = "email_alert_cp"
    type = CheckingPointType.CUSTOM_CP
    description = "Detects email alerts and triggers appropriate response workflows"
    version = "1.0.0"
    priority = 8
    stop_on_match = False
    ai_workflow_enabled = True
    prompt_template_id = "email_alert_response"
    agent_role = "support"
    timeout_seconds = 900
    approval_required = False

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the email alert checking point.

        Args:
            config: Optional configuration dictionary

        """
        super().__init__(config)

        # Configuration options
        self.alert_keywords = config.get("alert_keywords", []) if config else []
        self.urgency_keywords = config.get("urgency_keywords", []) if config else []
        self.sender_domains = config.get("sender_domains", []) if config else []
        self.subject_patterns = config.get("subject_patterns", []) if config else []
        self.auto_triage = config.get("auto_triage", True) if config else True
        self.create_ticket = config.get("create_ticket", True) if config else True
        self.notify_team = config.get("notify_team", True) if config else True
        self.response_channels = config.get("response_channels", []) if config else []

        # Default alert keywords if not provided
        if not self.alert_keywords:
            self.alert_keywords = [
                "alert",
                "critical",
                "error",
                "failure",
                "down",
                "offline",
                "emergency",
                "urgent",
                "immediate",
                "attention",
                "warning",
                "incident",
                "outage",
                "breach",
                "security",
                "threat",
            ]

        # Default urgency keywords if not provided
        if not self.urgency_keywords:
            self.urgency_keywords = [
                "critical",
                "emergency",
                "urgent",
                "immediate",
                "asap",
                "production",
                "down",
                "offline",
                "breach",
                "security",
                "outage",
                "severe",
                "major",
                "high priority",
            ]

    def can_handle(self, data: MonitoringData[dict[str, Any]]) -> bool:
        """Check if this checking point can handle the monitoring data.

        Args:
            data: Monitoring data to check

        Returns:
            True if this checking point can handle the data

        """
        if not self.enabled:
            return False

        # Only handle email messages
        if data.type != MonitoringDataType.EMAIL_MESSAGE:
            return False

        # Check if email contains alert indicators
        email_data = data.data
        subject = email_data.get("subject", "").lower()
        body = email_data.get("body", "").lower()
        sender = email_data.get("sender", "").lower()

        # Check subject and body for alert keywords
        for keyword in self.alert_keywords:
            if keyword in subject or keyword in body:
                return True

        # Check sender domains
        for domain in self.sender_domains:
            if domain in sender:
                return True

        # Check subject patterns
        for pattern in self.subject_patterns:
            if re.search(pattern, subject, re.IGNORECASE):
                return True

        return False

    def evaluate(self, data: MonitoringData[dict[str, Any]]) -> CheckResult:
        """Evaluate the monitoring data for email alerts.

        Args:
            data: Monitoring data to evaluate

        Returns:
            Check result indicating if email alert was detected

        """
        email_data = data.data
        subject = email_data.get("subject", "")
        body = email_data.get("body", "")
        sender = email_data.get("sender", "")

        # Find alert keywords
        found_alert_keywords = []
        subject_lower = subject.lower()
        body_lower = body.lower()

        for keyword in self.alert_keywords:
            if keyword in subject_lower or keyword in body_lower:
                found_alert_keywords.append(keyword)

        # Find urgency indicators
        found_urgency_keywords = []
        urgency_level = "normal"
        for keyword in self.urgency_keywords:
            if keyword in subject_lower or keyword in body_lower:
                found_urgency_keywords.append(keyword)
                urgency_level = self._determine_urgency_level(subject_lower, body_lower, found_urgency_keywords)

        # Check sender domain
        sender_domain = self._extract_domain(sender)
        is_trusted_sender = sender_domain in self.sender_domains

        if not found_alert_keywords and not is_trusted_sender:
            return CheckResult(
                checking_point_name=self.name,
                checking_point_type=self.type.value,
                result_type=CheckResultType.NO_MATCH,
                should_act=False,
                confidence=0.9,
                reason="No alert indicators found in email",
                context={"subject": subject[:100]},  # Truncate for context
            )

        # Calculate confidence
        confidence = self._calculate_alert_confidence(
            email_data, found_alert_keywords, found_urgency_keywords, is_trusted_sender
        )

        # Determine suggested actions
        suggested_actions = ["log_email_alert"]
        if urgency_level == "critical":
            suggested_actions.extend(["immediate_triage", "escalate_team"])
        elif urgency_level == "high":
            suggested_actions.extend(["create_ticket", "notify_team"])
        else:
            suggested_actions.extend(["triage_alert", "track_response"])

        return CheckResult(
            checking_point_name=self.name,
            checking_point_type=self.type.value,
            result_type=CheckResultType.MATCH,
            should_act=True,
            confidence=confidence,
            reason=f"Email alert detected with {len(found_alert_keywords)} keywords, urgency: {urgency_level}",
            context={
                "found_alert_keywords": found_alert_keywords,
                "found_urgency_keywords": found_urgency_keywords,
                "urgency_level": urgency_level,
                "sender": sender,
                "sender_domain": sender_domain,
                "is_trusted_sender": is_trusted_sender,
                "subject": subject,
                "email_length": len(body),
                "requires_triage": self.auto_triage,
            },
            suggested_actions=suggested_actions,
        )

    def get_actions(self, data: MonitoringData[dict[str, Any]], result: CheckResult) -> list[dict[str, Any]]:
        """Get immediate actions for email alert.

        Args:
            data: Monitoring data
            result: Check result

        Returns:
            List of immediate actions to take

        """
        actions = []

        email_data = data.data
        sender = email_data.get("sender", "")
        subject = email_data.get("subject", "")
        urgency_level = result.context.get("urgency_level", "normal")

        # Add acknowledgment action
        actions.append(
            {
                "type": "email_response",
                "name": "acknowledge_alert",
                "params": {
                    "to": sender,
                    "subject": f"Re: {subject}",
                    "message": self._get_acknowledgment_message(urgency_level),
                },
                "priority": 8,
            }
        )

        # Add team notification
        if self.notify_team and self.response_channels:
            actions.append(
                {
                    "type": "notification",
                    "name": "notify_team_alert",
                    "params": {
                        "channels": self.response_channels,
                        "message": f"Email alert received from {sender}: {subject}",
                        "urgency_level": urgency_level,
                        "sender": sender,
                        "subject": subject,
                    },
                    "priority": 7,
                }
            )

        # Add escalation for critical alerts
        if urgency_level == "critical":
            actions.append(
                {
                    "type": "notification",
                    "name": "escalate_critical_alert",
                    "params": {
                        "channels": self.response_channels,
                        "message": f"CRITICAL EMAIL ALERT: {subject} from {sender}",
                        "urgency_level": urgency_level,
                        "original_email": email_data,
                    },
                    "priority": 10,
                }
            )

        return actions

    def get_after_process(self, data: MonitoringData, result: CheckResult) -> list[AIAction]:
        """Get AI workflow actions for email alert.

        Args:
            data: Monitoring data
            result: Check result

        Returns:
            List of AI workflow actions

        """
        if not self.ai_workflow_enabled or not result.should_act:
            return []

        email_data = data.data
        sender = email_data.get("sender", "")
        subject = email_data.get("subject", "")
        body = email_data.get("body", "")
        urgency_level = result.context.get("urgency_level", "normal")

        # Create AI workflow action
        action = AIAction(
            name=f"{self.name}_workflow",
            workflow_name="email_alert_response",
            checking_point_name=self.name,
            prompt_template_id=self.prompt_template_id,
            agent_role=self.agent_role,
            timeout_seconds=self.timeout_seconds,
            approval_required=self.approval_required,
            input_data={
                "monitoring_data": data.dict(),
                "check_result": result.dict(),
                "email_context": {
                    "sender": sender,
                    "subject": subject,
                    "body": body,
                    "urgency_level": urgency_level,
                    "alert_keywords": result.context.get("found_alert_keywords", []),
                    "urgency_keywords": result.context.get("found_urgency_keywords", []),
                    "is_trusted_sender": result.context.get("is_trusted_sender", False),
                },
                "workflow_config": {
                    "auto_triage": self.auto_triage,
                    "create_ticket": self.create_ticket,
                    "notify_team": self.notify_team,
                    "response_channels": self.response_channels,
                },
            },
        )

        return [action]

    def _extract_domain(self, email_address: str) -> str:
        """Extract domain from email address.

        Args:
            email_address: Email address

        Returns:
            Domain part of the email

        """
        try:
            return email_address.split("@")[1].lower()
        except (IndexError, AttributeError):
            return ""

    def _determine_urgency_level(self, subject: str, body: str, urgency_keywords: list[str]) -> str:
        """Determine the urgency level of the email.

        Args:
            subject: Email subject
            body: Email body
            urgency_keywords: List of urgency keywords found

        Returns:
            Urgency level: "normal", "high", or "critical"

        """
        critical_indicators = ["critical", "emergency", "security", "breach", "production", "down"]
        high_indicators = ["urgent", "immediate", "asap", "high priority", "severe", "major"]

        # Check for critical indicators
        for indicator in critical_indicators:
            if indicator in subject or indicator in body:
                return "critical"

        # Check for high urgency indicators
        for indicator in high_indicators:
            if indicator in subject or indicator in body:
                return "high"

        # Check for multiple urgency keywords
        if len(urgency_keywords) >= 2:
            return "high"

        return "normal"

    def _calculate_alert_confidence(
        self,
        email_data: dict[str, Any],
        alert_keywords: list[str],
        urgency_keywords: list[str],
        is_trusted_sender: bool,
    ) -> float:
        """Calculate confidence score for the email alert.

        Args:
            email_data: Email data
            alert_keywords: List of alert keywords found
            urgency_keywords: List of urgency keywords found
            is_trusted_sender: Whether sender is trusted

        Returns:
            Confidence score between 0.0 and 1.0

        """
        base_confidence = 0.6

        # Higher confidence for trusted senders
        if is_trusted_sender:
            base_confidence += 0.2

        # Higher confidence for alert keywords in subject
        subject = email_data.get("subject", "").lower()
        for keyword in alert_keywords:
            if keyword in subject:
                base_confidence += 0.1
                break

        # Higher confidence for urgency keywords
        if urgency_keywords:
            base_confidence += 0.1

        # Higher confidence for multiple alert keywords
        if len(alert_keywords) >= 2:
            base_confidence += 0.1

        # Check email length (longer emails might be more detailed)
        body = email_data.get("body", "")
        if len(body) > 200:
            base_confidence += 0.1
        elif len(body) < 50:
            base_confidence -= 0.1

        # Ensure confidence is within bounds
        return max(0.0, min(1.0, base_confidence))

    def _get_acknowledgment_message(self, urgency_level: str) -> str:
        """Get appropriate acknowledgment message based on urgency.

        Args:
            urgency_level: Urgency level of the alert

        Returns:
            Acknowledgment message

        """
        if urgency_level == "critical":
            return "We have received your critical alert and our team is responding immediately. This is our highest priority."
        if urgency_level == "high":
            return "We have received your alert and our team is prioritizing it for immediate attention."
        return "We have received your alert and our team is reviewing it. We will respond as soon as possible."

    def validate_config(self) -> list[str]:
        """Validate the checking point configuration.

        Returns:
            List of validation errors

        """
        errors = super().validate_config()

        if not self.alert_keywords and not self.sender_domains and not self.subject_patterns:
            errors.append("At least one alert keyword, sender domain, or subject pattern must be configured")

        return errors
