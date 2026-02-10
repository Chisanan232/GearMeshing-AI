"""ApprovalSimulator fixture for E2E tests - simulates approval workflow."""

import asyncio
import time
from datetime import datetime

from gearmeshing_ai.agent_core.runtime.approval_manager import ApprovalRequest


class ApprovalSimulator:
    """Simulate approval request creation and resolution."""

    def __init__(self):
        """Initialize approval simulator."""
        self.pending_approvals: dict[str, ApprovalRequest] = {}
        self.auto_approve = False
        self.approval_delay = 0.0
        self.rejection_on_approval: dict[str, Exception] = {}
        self.approval_history: list[dict] = []

    async def create_approval_request(self, approval_request: ApprovalRequest) -> str:
        """Create approval request."""
        approval_id = approval_request.id
        self.pending_approvals[approval_id] = approval_request
        return approval_id

    async def submit_approval(self, approval_id: str, decision: str) -> dict:
        """Submit approval decision."""
        if approval_id not in self.pending_approvals:
            raise ValueError(f"Approval {approval_id} not found")

        # Check if should reject
        if approval_id in self.rejection_on_approval:
            error = self.rejection_on_approval[approval_id]
            del self.rejection_on_approval[approval_id]
            raise error

        # Simulate delay
        if self.approval_delay > 0:
            await asyncio.sleep(self.approval_delay)

        # Remove from pending
        approval = self.pending_approvals.pop(approval_id)

        # Record in history
        self.approval_history.append(
            {
                "approval_id": approval_id,
                "decision": decision,
                "timestamp": datetime.now().isoformat(),
            }
        )

        return {
            "approval_id": approval_id,
            "decision": decision,
            "timestamp": datetime.now().isoformat(),
        }

    async def wait_for_approval(self, approval_id: str, timeout: int = 3600) -> dict:
        """Wait for approval (with timeout)."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            if approval_id not in self.pending_approvals:
                # Approval was submitted
                return {"status": "approved"}

            if self.auto_approve:
                # Auto-approve
                await self.submit_approval(approval_id, "approved")
                return {"status": "approved"}

            await asyncio.sleep(0.1)

        # Timeout
        raise TimeoutError(f"Approval {approval_id} timed out after {timeout}s")

    def set_auto_approve(self, auto_approve: bool = True) -> None:
        """Enable/disable auto-approval."""
        self.auto_approve = auto_approve

    def set_approval_delay(self, delay: float) -> None:
        """Set delay before approval."""
        self.approval_delay = delay

    def set_approval_rejection(self, approval_id: str, error: Exception) -> None:
        """Configure approval to be rejected."""
        self.rejection_on_approval[approval_id] = error

    def get_pending_approvals(self) -> list[ApprovalRequest]:
        """Get list of pending approvals."""
        return list(self.pending_approvals.values())

    def get_approval_history(self) -> list[dict]:
        """Get approval history."""
        return self.approval_history

    def clear_history(self) -> None:
        """Clear approval history."""
        self.approval_history = []

    def assert_approval_requested(self, tool_name: str | None = None) -> None:
        """Assert approval was requested."""
        if not self.pending_approvals and not self.approval_history:
            raise AssertionError("No approvals requested")

        if tool_name:
            all_approvals = list(self.pending_approvals.values()) + [a for a in self.approval_history]
            for approval in all_approvals:
                if tool_name in str(approval):
                    return
            raise AssertionError(f"No approval requested for {tool_name}")

    def assert_approval_count(self, count: int) -> None:
        """Assert specific number of approvals requested."""
        total = len(self.pending_approvals) + len(self.approval_history)
        assert total == count, f"Expected {count} approvals, got {total}"
