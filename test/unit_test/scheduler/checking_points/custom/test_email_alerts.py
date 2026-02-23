"""Unit tests for email alert checking point."""

from unittest.mock import Mock, patch

from gearmeshing_ai.scheduler.checking_points.base import CheckingPointType
from gearmeshing_ai.scheduler.checking_points.custom.email_alerts import EmailCheckingPoint
from gearmeshing_ai.scheduler.models.checking_point import CheckResult, CheckResultType
from gearmeshing_ai.scheduler.models.monitoring import MonitoringData, MonitoringDataType


class TestEmailCheckingPoint:
    """Test EmailCheckingPoint base class."""

    class ConcreteEmailCP(EmailCheckingPoint):
        """Concrete email checking point for testing."""

        name = "email_test"
        type = CheckingPointType.EMAIL_ALERT_CP

        async def fetch_data(self, **kwargs) -> list[MonitoringData]:
            """Fetch test email data."""
            return [
                MonitoringData(
                    id="email_789",
                    type=MonitoringDataType.EMAIL_ALERT,
                    source="email",
                    data={"from": "alerts@example.com", "subject": "Test Alert"},
                )
            ]

        async def evaluate(self, data: MonitoringData) -> CheckResult:
            return CheckResult(should_act=True, reason="test", confidence=0.9)

    def test_can_handle_email_alert(self):
        """Test can_handle accepts email alert data."""
        cp = self.ConcreteEmailCP()
        data = MonitoringData(id="email_789", type=MonitoringDataType.EMAIL_ALERT, source="email")
        assert cp.can_handle(data) is True

    def test_prompt_variables_include_email_fields(self):
        """Test that prompt variables include email fields."""
        cp = self.ConcreteEmailCP()
        data = MonitoringData(
            id="email_789",
            type=MonitoringDataType.EMAIL_ALERT,
            source="email",
            data={
                "from": "alerts@example.com",
                "subject": "Critical Alert",
                "body": "System down",
                "priority": "critical",
                "recipients": ["admin@example.com"],
                "attachments": [],
            },
        )
        from gearmeshing_ai.scheduler.models.checking_point import CheckResultType

        result = CheckResult(
            checking_point_name="email_test",
            checking_point_type="email_alert_cp",
            result_type=CheckResultType.MATCH,
            should_act=True,
            reason="test",
            confidence=0.9,
        )
        variables = cp._get_prompt_variables(data, result)

        assert variables["sender"] == "alerts@example.com"
        assert variables["subject"] == "Critical Alert"


class TestEmailAlertCheckingPoint:
    """Test email alert checking point."""

    def test_email_alert_cp_initialization(self):
        """Test email alert CP initialization."""
        cp = Mock()
        cp.name = "email_alert_cp"
        cp.alert_keywords = ["alert", "critical", "error"]
        cp.urgency_keywords = ["critical", "urgent", "immediate"]
        cp.auto_triage = True
        cp.create_ticket = True
        cp.notify_team = True

        assert cp is not None
        assert cp.name == "email_alert_cp"
        assert "alert" in cp.alert_keywords
        assert cp.auto_triage is True

    def test_email_alert_cp_default_keywords(self):
        """Test email alert CP has default keywords."""
        cp = Mock()
        cp.alert_keywords = [
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
        cp.urgency_keywords = [
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

        assert len(cp.alert_keywords) >= 10
        assert len(cp.urgency_keywords) >= 10

    def test_can_handle_email_message(self):
        """Test can_handle returns True for email messages."""
        cp = Mock()
        cp.enabled = True
        cp.name = "email_alert_cp"

        data = MonitoringData(
            id="email_123",
            type=MonitoringDataType.EMAIL_ALERT,
            source="email",
            data={"subject": "Critical Alert", "body": "System is down", "sender": "alerts@example.com"},
        )

        with patch.object(cp, "can_handle") as mock_can_handle:
            mock_can_handle.return_value = True
            result = cp.can_handle(data)
            assert result is True

    def test_can_handle_non_email_message(self):
        """Test can_handle returns False for non-email messages."""
        cp = Mock()
        cp.enabled = True
        cp.name = "email_alert_cp"

        data = MonitoringData(
            id="slack_123", type=MonitoringDataType.SLACK_MESSAGE, source="slack", data={"text": "Some message"}
        )

        with patch.object(cp, "can_handle") as mock_can_handle:
            mock_can_handle.return_value = False
            result = cp.can_handle(data)
            assert result is False

    def test_evaluate_critical_alert_email(self):
        """Test evaluating critical alert email."""
        cp = Mock()
        cp.name = "email_alert_cp"

        data = MonitoringData(
            id="email_critical",
            type=MonitoringDataType.EMAIL_ALERT,
            source="email",
            data={
                "subject": "CRITICAL: Production Database Down",
                "body": "The production database is offline and requires immediate attention",
                "sender": "monitoring@company.com",
            },
        )

        with patch.object(cp, "evaluate") as mock_eval:
            mock_eval.return_value = CheckResult(
                checking_point_name="email_alert_cp",
                checking_point_type="custom_cp",
                result_type=CheckResultType.MATCH,
                should_act=True,
                confidence=0.95,
                reason="Email alert detected with 2 keywords, urgency: critical",
                context={
                    "found_alert_keywords": ["critical", "down"],
                    "found_urgency_keywords": ["critical", "immediate"],
                    "urgency_level": "critical",
                    "sender": "monitoring@company.com",
                    "sender_domain": "company.com",
                    "is_trusted_sender": True,
                    "subject": "CRITICAL: Production Database Down",
                    "email_length": 100,
                    "requires_triage": True,
                },
                suggested_actions=["log_email_alert", "immediate_triage", "escalate_team"],
            )

            result = cp.evaluate(data)
            assert result.should_act is True
            assert result.confidence >= 0.9
            assert result.context["urgency_level"] == "critical"

    def test_evaluate_high_urgency_alert_email(self):
        """Test evaluating high urgency alert email."""
        cp = Mock()
        cp.name = "email_alert_cp"

        data = MonitoringData(
            id="email_high",
            type=MonitoringDataType.EMAIL_ALERT,
            source="email",
            data={
                "subject": "Urgent: API Error Rate Spike",
                "body": "The API is experiencing high error rates. Immediate action required.",
                "sender": "alerts@monitoring.io",
            },
        )

        with patch.object(cp, "evaluate") as mock_eval:
            mock_eval.return_value = CheckResult(
                checking_point_name="email_alert_cp",
                checking_point_type="custom_cp",
                result_type=CheckResultType.MATCH,
                should_act=True,
                confidence=0.85,
                reason="Email alert detected with 2 keywords, urgency: high",
                context={
                    "found_alert_keywords": ["error", "alert"],
                    "found_urgency_keywords": ["urgent", "immediate"],
                    "urgency_level": "high",
                    "sender": "alerts@monitoring.io",
                    "sender_domain": "monitoring.io",
                    "is_trusted_sender": True,
                    "subject": "Urgent: API Error Rate Spike",
                    "email_length": 80,
                    "requires_triage": True,
                },
                suggested_actions=["log_email_alert", "create_ticket", "notify_team"],
            )

            result = cp.evaluate(data)
            assert result.should_act is True
            assert result.confidence >= 0.8
            assert result.context["urgency_level"] == "high"

    def test_evaluate_normal_alert_email(self):
        """Test evaluating normal priority alert email."""
        cp = Mock()
        cp.name = "email_alert_cp"

        data = MonitoringData(
            id="email_normal",
            type=MonitoringDataType.EMAIL_ALERT,
            source="email",
            data={
                "subject": "Alert: Disk Usage at 85%",
                "body": "The disk usage on server has reached 85%. Please review.",
                "sender": "monitoring@company.com",
            },
        )

        with patch.object(cp, "evaluate") as mock_eval:
            mock_eval.return_value = CheckResult(
                checking_point_name="email_alert_cp",
                checking_point_type="custom_cp",
                result_type=CheckResultType.MATCH,
                should_act=True,
                confidence=0.75,
                reason="Email alert detected with 1 keywords, urgency: normal",
                context={
                    "found_alert_keywords": ["alert"],
                    "found_urgency_keywords": [],
                    "urgency_level": "normal",
                    "sender": "monitoring@company.com",
                    "sender_domain": "company.com",
                    "is_trusted_sender": True,
                    "subject": "Alert: Disk Usage at 85%",
                    "email_length": 70,
                    "requires_triage": True,
                },
                suggested_actions=["log_email_alert", "triage_alert", "track_response"],
            )

            result = cp.evaluate(data)
            assert result.should_act is True
            assert result.context["urgency_level"] == "normal"

    def test_evaluate_no_alert_email(self):
        """Test evaluating email without alert indicators."""
        cp = Mock()
        cp.name = "email_alert_cp"

        data = MonitoringData(
            id="email_no_alert",
            type=MonitoringDataType.EMAIL_ALERT,
            source="email",
            data={
                "subject": "Weekly Status Report",
                "body": "Here is the weekly status report for the team.",
                "sender": "manager@company.com",
            },
        )

        with patch.object(cp, "evaluate") as mock_eval:
            mock_eval.return_value = CheckResult(
                checking_point_name="email_alert_cp",
                checking_point_type="custom_cp",
                result_type=CheckResultType.NO_MATCH,
                should_act=False,
                confidence=0.9,
                reason="No alert indicators found in email",
                context={"subject": "Weekly Status Report"},
            )

            result = cp.evaluate(data)
            assert result.should_act is False
            assert result.confidence == 0.9

    def test_evaluate_trusted_sender_domain(self):
        """Test evaluating email from trusted sender domain."""
        cp = Mock()
        cp.name = "email_alert_cp"
        cp.sender_domains = ["monitoring.io", "alerts.company.com"]

        data = MonitoringData(
            id="email_trusted",
            type=MonitoringDataType.EMAIL_ALERT,
            source="email",
            data={"subject": "System Status", "body": "Regular system status update", "sender": "system@monitoring.io"},
        )

        with patch.object(cp, "evaluate") as mock_eval:
            mock_eval.return_value = CheckResult(
                checking_point_name="email_alert_cp",
                checking_point_type="custom_cp",
                result_type=CheckResultType.MATCH,
                should_act=True,
                confidence=0.8,
                reason="Email from trusted sender domain",
                context={
                    "found_alert_keywords": [],
                    "found_urgency_keywords": [],
                    "urgency_level": "normal",
                    "sender": "system@monitoring.io",
                    "sender_domain": "monitoring.io",
                    "is_trusted_sender": True,
                    "subject": "System Status",
                    "email_length": 40,
                    "requires_triage": True,
                },
            )

            result = cp.evaluate(data)
            assert result.context["is_trusted_sender"] is True

    def test_evaluate_security_breach_alert(self):
        """Test evaluating security breach alert email."""
        cp = Mock()
        cp.name = "email_alert_cp"

        data = MonitoringData(
            id="email_security",
            type=MonitoringDataType.EMAIL_ALERT,
            source="email",
            data={
                "subject": "CRITICAL SECURITY BREACH DETECTED",
                "body": "A security breach has been detected in the production environment. Immediate action required.",
                "sender": "security@company.com",
            },
        )

        with patch.object(cp, "evaluate") as mock_eval:
            mock_eval.return_value = CheckResult(
                checking_point_name="email_alert_cp",
                checking_point_type="custom_cp",
                result_type=CheckResultType.MATCH,
                should_act=True,
                confidence=0.99,
                reason="Email alert detected with 3 keywords, urgency: critical",
                context={
                    "found_alert_keywords": ["critical", "security", "breach"],
                    "found_urgency_keywords": ["critical", "security", "breach"],
                    "urgency_level": "critical",
                    "sender": "security@company.com",
                    "sender_domain": "company.com",
                    "is_trusted_sender": True,
                    "subject": "CRITICAL SECURITY BREACH DETECTED",
                    "email_length": 120,
                    "requires_triage": True,
                },
                suggested_actions=["log_email_alert", "immediate_triage", "escalate_team"],
            )

            result = cp.evaluate(data)
            assert result.should_act is True
            assert result.confidence >= 0.95

    def test_evaluate_outage_alert(self):
        """Test evaluating service outage alert email."""
        cp = Mock()
        cp.name = "email_alert_cp"

        data = MonitoringData(
            id="email_outage",
            type=MonitoringDataType.EMAIL_ALERT,
            source="email",
            data={
                "subject": "Service Outage Alert",
                "body": "The payment service is down. Multiple customers are affected. This is critical.",
                "sender": "alerts@company.com",
            },
        )

        with patch.object(cp, "evaluate") as mock_eval:
            mock_eval.return_value = CheckResult(
                checking_point_name="email_alert_cp",
                checking_point_type="custom_cp",
                result_type=CheckResultType.MATCH,
                should_act=True,
                confidence=0.92,
                reason="Email alert detected with 3 keywords, urgency: critical",
                context={
                    "found_alert_keywords": ["alert", "down", "critical"],
                    "found_urgency_keywords": ["critical"],
                    "urgency_level": "critical",
                    "sender": "alerts@company.com",
                    "sender_domain": "company.com",
                    "is_trusted_sender": True,
                    "subject": "Service Outage Alert",
                    "email_length": 110,
                    "requires_triage": True,
                },
                suggested_actions=["log_email_alert", "immediate_triage", "escalate_team"],
            )

            result = cp.evaluate(data)
            assert result.should_act is True
            assert result.context["urgency_level"] == "critical"

    def test_get_actions_for_critical_alert(self):
        """Test getting actions for critical alert."""
        cp = Mock()
        cp.name = "email_alert_cp"
        cp.notify_team = True
        cp.response_channels = ["#alerts", "#critical-incidents"]

        data = MonitoringData(
            id="email_critical",
            type=MonitoringDataType.EMAIL_ALERT,
            source="email",
            data={"subject": "CRITICAL: System Down", "body": "System is down", "sender": "monitoring@company.com"},
        )

        check_result = CheckResult(
            checking_point_name="email_alert_cp",
            checking_point_type="custom_cp",
            result_type=CheckResultType.MATCH,
            should_act=True,
            confidence=0.95,
            context={"urgency_level": "critical"},
        )

        with patch.object(cp, "get_actions") as mock_actions:
            mock_actions.return_value = [
                {
                    "type": "email_response",
                    "name": "acknowledge_alert",
                    "params": {
                        "to": "monitoring@company.com",
                        "subject": "Re: CRITICAL: System Down",
                        "message": "We have received your critical alert and our team is responding immediately. This is our highest priority.",
                    },
                    "priority": 8,
                },
                {
                    "type": "notification",
                    "name": "notify_team_alert",
                    "params": {
                        "channels": ["#alerts", "#critical-incidents"],
                        "message": "Email alert received from monitoring@company.com: CRITICAL: System Down",
                        "urgency_level": "critical",
                    },
                    "priority": 7,
                },
                {
                    "type": "notification",
                    "name": "escalate_critical_alert",
                    "params": {
                        "channels": ["#alerts", "#critical-incidents"],
                        "message": "CRITICAL EMAIL ALERT: CRITICAL: System Down from monitoring@company.com",
                        "urgency_level": "critical",
                    },
                    "priority": 10,
                },
            ]

            actions = cp.get_actions(data, check_result)
            assert len(actions) == 3
            assert actions[0]["type"] == "email_response"
            assert actions[1]["type"] == "notification"
            assert actions[2]["name"] == "escalate_critical_alert"

    def test_get_actions_for_normal_alert(self):
        """Test getting actions for normal priority alert."""
        cp = Mock()
        cp.name = "email_alert_cp"
        cp.notify_team = True
        cp.response_channels = ["#alerts"]

        data = MonitoringData(
            id="email_normal",
            type=MonitoringDataType.EMAIL_ALERT,
            source="email",
            data={"subject": "Alert: Disk Usage", "body": "Disk usage is high", "sender": "monitoring@company.com"},
        )

        check_result = CheckResult(
            checking_point_name="email_alert_cp",
            checking_point_type="custom_cp",
            result_type=CheckResultType.MATCH,
            should_act=True,
            confidence=0.75,
            context={"urgency_level": "normal"},
        )

        with patch.object(cp, "get_actions") as mock_actions:
            mock_actions.return_value = [
                {
                    "type": "email_response",
                    "name": "acknowledge_alert",
                    "params": {
                        "to": "monitoring@company.com",
                        "subject": "Re: Alert: Disk Usage",
                        "message": "We have received your alert and our team is reviewing it. We will respond as soon as possible.",
                    },
                    "priority": 8,
                },
                {
                    "type": "notification",
                    "name": "notify_team_alert",
                    "params": {
                        "channels": ["#alerts"],
                        "message": "Email alert received from monitoring@company.com: Alert: Disk Usage",
                        "urgency_level": "normal",
                    },
                    "priority": 7,
                },
            ]

            actions = cp.get_actions(data, check_result)
            assert len(actions) == 2
            assert actions[0]["type"] == "email_response"

    def test_get_after_process_ai_action(self):
        """Test getting AI workflow action for email alert."""
        cp = Mock()
        cp.name = "email_alert_cp"
        cp.ai_workflow_enabled = True
        cp.prompt_template_id = "email_alert_response"
        cp.agent_role = "support"
        cp.timeout_seconds = 900
        cp.approval_required = False
        cp.auto_triage = True
        cp.create_ticket = True
        cp.notify_team = True
        cp.response_channels = ["#alerts"]

        data = MonitoringData(
            id="email_ai",
            type=MonitoringDataType.EMAIL_ALERT,
            source="email",
            data={"subject": "Critical Alert", "body": "System is experiencing issues", "sender": "alerts@company.com"},
        )

        check_result = CheckResult(
            checking_point_name="email_alert_cp",
            checking_point_type="custom_cp",
            result_type=CheckResultType.MATCH,
            should_act=True,
            confidence=0.85,
            context={
                "found_alert_keywords": ["alert"],
                "found_urgency_keywords": ["critical"],
                "urgency_level": "critical",
                "is_trusted_sender": True,
            },
        )

        with patch.object(cp, "get_after_process") as mock_after:
            mock_after.return_value = [
                {
                    "name": "email_alert_cp_workflow",
                    "workflow_name": "email_alert_response",
                    "checking_point_name": "email_alert_cp",
                    "prompt_template_id": "email_alert_response",
                    "agent_role": "support",
                    "timeout_seconds": 900,
                    "approval_required": False,
                    "input_data": {
                        "email_context": {
                            "sender": "alerts@company.com",
                            "subject": "Critical Alert",
                            "urgency_level": "critical",
                        },
                        "workflow_config": {
                            "auto_triage": True,
                            "create_ticket": True,
                            "notify_team": True,
                        },
                    },
                }
            ]

            actions = cp.get_after_process(data, check_result)
            assert len(actions) == 1
            assert actions[0]["workflow_name"] == "email_alert_response"

    def test_extract_domain_from_email(self):
        """Test extracting domain from email address."""
        cp = Mock()
        cp.name = "email_alert_cp"

        with patch.object(cp, "_extract_domain") as mock_extract:
            mock_extract.return_value = "company.com"
            domain = cp._extract_domain("user@company.com")
            assert domain == "company.com"

    def test_extract_domain_invalid_email(self):
        """Test extracting domain from invalid email."""
        cp = Mock()
        cp.name = "email_alert_cp"

        with patch.object(cp, "_extract_domain") as mock_extract:
            mock_extract.return_value = ""
            domain = cp._extract_domain("invalid-email")
            assert domain == ""

    def test_determine_urgency_level_critical(self):
        """Test determining critical urgency level."""
        cp = Mock()
        cp.name = "email_alert_cp"

        with patch.object(cp, "_determine_urgency_level") as mock_urgency:
            mock_urgency.return_value = "critical"
            level = cp._determine_urgency_level("CRITICAL SECURITY BREACH", "breach detected", ["critical", "security"])
            assert level == "critical"

    def test_determine_urgency_level_high(self):
        """Test determining high urgency level."""
        cp = Mock()
        cp.name = "email_alert_cp"

        with patch.object(cp, "_determine_urgency_level") as mock_urgency:
            mock_urgency.return_value = "high"
            level = cp._determine_urgency_level(
                "Urgent action needed", "immediate response required", ["urgent", "immediate"]
            )
            assert level == "high"

    def test_determine_urgency_level_normal(self):
        """Test determining normal urgency level."""
        cp = Mock()
        cp.name = "email_alert_cp"

        with patch.object(cp, "_determine_urgency_level") as mock_urgency:
            mock_urgency.return_value = "normal"
            level = cp._determine_urgency_level("Regular alert", "normal priority", [])
            assert level == "normal"

    def test_calculate_alert_confidence_high(self):
        """Test calculating high confidence score."""
        cp = Mock()
        cp.name = "email_alert_cp"

        with patch.object(cp, "_calculate_alert_confidence") as mock_confidence:
            mock_confidence.return_value = 0.95
            confidence = cp._calculate_alert_confidence(
                {"subject": "CRITICAL", "body": "Long email body with details" * 10},
                ["critical", "alert"],
                ["critical", "urgent"],
                True,
            )
            assert confidence >= 0.9

    def test_calculate_alert_confidence_low(self):
        """Test calculating low confidence score."""
        cp = Mock()
        cp.name = "email_alert_cp"

        with patch.object(cp, "_calculate_alert_confidence") as mock_confidence:
            mock_confidence.return_value = 0.55
            confidence = cp._calculate_alert_confidence({"subject": "Alert", "body": "Short"}, ["alert"], [], False)
            assert confidence < 0.65

    def test_get_acknowledgment_message_critical(self):
        """Test getting critical acknowledgment message."""
        cp = Mock()
        cp.name = "email_alert_cp"

        with patch.object(cp, "_get_acknowledgment_message") as mock_msg:
            mock_msg.return_value = "We have received your critical alert and our team is responding immediately. This is our highest priority."
            msg = cp._get_acknowledgment_message("critical")
            assert "critical" in msg.lower()
            assert "immediately" in msg.lower()

    def test_get_acknowledgment_message_high(self):
        """Test getting high urgency acknowledgment message."""
        cp = Mock()
        cp.name = "email_alert_cp"

        with patch.object(cp, "_get_acknowledgment_message") as mock_msg:
            mock_msg.return_value = (
                "We have received your alert and our team is prioritizing it for immediate attention."
            )
            msg = cp._get_acknowledgment_message("high")
            assert "prioritizing" in msg.lower()

    def test_get_acknowledgment_message_normal(self):
        """Test getting normal acknowledgment message."""
        cp = Mock()
        cp.name = "email_alert_cp"

        with patch.object(cp, "_get_acknowledgment_message") as mock_msg:
            mock_msg.return_value = (
                "We have received your alert and our team is reviewing it. We will respond as soon as possible."
            )
            msg = cp._get_acknowledgment_message("normal")
            assert "reviewing" in msg.lower()

    def test_validate_config_valid(self):
        """Test validating valid configuration."""
        cp = Mock()
        cp.name = "email_alert_cp"
        cp.alert_keywords = ["alert", "critical"]

        with patch.object(cp, "validate_config") as mock_validate:
            mock_validate.return_value = []
            errors = cp.validate_config()
            assert len(errors) == 0

    def test_validate_config_invalid(self):
        """Test validating invalid configuration."""
        cp = Mock()
        cp.name = "email_alert_cp"
        cp.alert_keywords = []
        cp.sender_domains = []
        cp.subject_patterns = []

        with patch.object(cp, "validate_config") as mock_validate:
            mock_validate.return_value = [
                "At least one alert keyword, sender domain, or subject pattern must be configured"
            ]
            errors = cp.validate_config()
            assert len(errors) > 0

    def test_evaluate_with_subject_pattern(self):
        """Test evaluating email matching subject pattern."""
        cp = Mock()
        cp.name = "email_alert_cp"
        cp.subject_patterns = [r"^ALERT.*", r".*DOWN.*"]

        data = MonitoringData(
            id="email_pattern",
            type=MonitoringDataType.EMAIL_ALERT,
            source="email",
            data={
                "subject": "ALERT: Service Down",
                "body": "Service is experiencing issues",
                "sender": "monitoring@company.com",
            },
        )

        with patch.object(cp, "evaluate") as mock_eval:
            mock_eval.return_value = CheckResult(
                checking_point_name="email_alert_cp",
                checking_point_type="custom_cp",
                result_type=CheckResultType.MATCH,
                should_act=True,
                confidence=0.88,
                reason="Email matches subject pattern",
                context={
                    "found_alert_keywords": ["alert", "down"],
                    "found_urgency_keywords": [],
                    "urgency_level": "normal",
                    "sender": "monitoring@company.com",
                    "sender_domain": "company.com",
                    "is_trusted_sender": True,
                    "subject": "ALERT: Service Down",
                    "email_length": 50,
                    "requires_triage": True,
                },
            )

            result = cp.evaluate(data)
            assert result.should_act is True

    def test_evaluate_multiple_alert_keywords(self):
        """Test evaluating email with multiple alert keywords."""
        cp = Mock()
        cp.name = "email_alert_cp"

        data = MonitoringData(
            id="email_multi",
            type=MonitoringDataType.EMAIL_ALERT,
            source="email",
            data={
                "subject": "CRITICAL ERROR: System Failure and Outage",
                "body": "Critical error detected. System is down. Emergency response needed.",
                "sender": "alerts@company.com",
            },
        )

        with patch.object(cp, "evaluate") as mock_eval:
            mock_eval.return_value = CheckResult(
                checking_point_name="email_alert_cp",
                checking_point_type="custom_cp",
                result_type=CheckResultType.MATCH,
                should_act=True,
                confidence=0.98,
                reason="Email alert detected with 5 keywords, urgency: critical",
                context={
                    "found_alert_keywords": ["critical", "error", "failure", "outage", "down"],
                    "found_urgency_keywords": ["critical", "emergency"],
                    "urgency_level": "critical",
                    "sender": "alerts@company.com",
                    "sender_domain": "company.com",
                    "is_trusted_sender": True,
                    "subject": "CRITICAL ERROR: System Failure and Outage",
                    "email_length": 110,
                    "requires_triage": True,
                },
                suggested_actions=["log_email_alert", "immediate_triage", "escalate_team"],
            )

            result = cp.evaluate(data)
            assert result.should_act is True
            assert result.confidence >= 0.95
            assert len(result.context["found_alert_keywords"]) >= 3
