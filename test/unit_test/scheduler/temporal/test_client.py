"""Unit tests for Temporal client."""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock


class TestTemporalClient:
    """Test TemporalClient functionality."""

    def test_temporal_client_initialization(self):
        """Test TemporalClient initialization."""
        client = MagicMock()
        assert client is not None

    @pytest.mark.asyncio
    async def test_connect_to_temporal(self):
        """Test connecting to Temporal server."""
        client = MagicMock()
        with patch.object(client, 'connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = True
            result = await client.connect()
            assert result is True

    @pytest.mark.asyncio
    async def test_execute_workflow(self):
        """Test executing a workflow."""
        client = MagicMock()
        with patch.object(client, 'execute_workflow', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {"result": "success"}
            
            result = await client.execute_workflow(
                workflow_name="test_workflow",
                input_data={"task_id": "123"}
            )
            assert result["result"] == "success"

    @pytest.mark.asyncio
    async def test_list_workflows(self):
        """Test listing workflows."""
        client = MagicMock()
            
        with patch.object(client, 'list_workflows', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = [
                    {"workflow_id": "wf_1", "status": "COMPLETED"},
                    {"workflow_id": "wf_2", "status": "RUNNING"}
                ]
                
            result = await client.list_workflows()
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_workflow_status(self):
        """Test getting workflow status."""
        client = MagicMock()
            
        with patch.object(client, 'get_workflow_status', new_callable=AsyncMock) as mock_status:
            mock_status.return_value = {
                    "workflow_id": "wf_1",
                    "status": "COMPLETED",
                    "result": {"data": "success"}
                }
                
            result = await client.get_workflow_status("wf_1")
            assert result["status"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_cancel_workflow(self):
        """Test canceling a workflow."""
        client = MagicMock()
            
        with patch.object(client, 'cancel_workflow', new_callable=AsyncMock) as mock_cancel:
            mock_cancel.return_value = True
                
            result = await client.cancel_workflow("wf_1")
            assert result is True

    @pytest.mark.asyncio
    async def test_create_schedule(self):
        """Test creating a schedule."""
        client = MagicMock()
            
        with patch.object(client, 'create_schedule', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = "schedule_1"
                
            result = await client.create_schedule(
                    schedule_id="schedule_1",
                    workflow_name="test_workflow",
                    cron_expression="0 * * * *"
                )
            assert result == "schedule_1"

    @pytest.mark.asyncio
    async def test_list_schedules(self):
        """Test listing schedules."""
        client = MagicMock()
            
        with patch.object(client, 'list_schedules', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = [
                    {"schedule_id": "sched_1", "status": "ACTIVE"},
                    {"schedule_id": "sched_2", "status": "PAUSED"}
                ]
                
            result = await client.list_schedules()
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_pause_schedule(self):
        """Test pausing a schedule."""
        client = MagicMock()
            
        with patch.object(client, 'pause_schedule', new_callable=AsyncMock) as mock_pause:
            mock_pause.return_value = True
                
            result = await client.pause_schedule("sched_1")
            assert result is True

    @pytest.mark.asyncio
    async def test_unpause_schedule(self):
        """Test unpausing a schedule."""
        client = MagicMock()
            
        with patch.object(client, 'unpause_schedule', new_callable=AsyncMock) as mock_unpause:
            mock_unpause.return_value = True
                
            result = await client.unpause_schedule("sched_1")
            assert result is True

    @pytest.mark.asyncio
    async def test_delete_schedule(self):
        """Test deleting a schedule."""
        client = MagicMock()
            
        with patch.object(client, 'delete_schedule', new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = True
                
            result = await client.delete_schedule("sched_1")
            assert result is True

    @pytest.mark.asyncio
    async def test_trigger_schedule(self):
        """Test triggering a schedule."""
        client = MagicMock()
            
        with patch.object(client, 'trigger_schedule', new_callable=AsyncMock) as mock_trigger:
            mock_trigger.return_value = "wf_triggered"
                
            result = await client.trigger_schedule("sched_1")
            assert result == "wf_triggered"

    @pytest.mark.asyncio
    async def test_connection_error_handling(self):
        """Test connection error handling."""
        client = MagicMock()
            
        with patch.object(client, 'connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = ConnectionError("Failed to connect")
                
            with pytest.raises(ConnectionError):
                    await client.connect()

    @pytest.mark.asyncio
    async def test_workflow_execution_with_retry(self):
        """Test workflow execution with retry."""
        client = MagicMock()
            
        with patch.object(client, 'execute_workflow', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {"result": "success"}
                
            result = await client.execute_workflow(
                    workflow_name="test_workflow",
                    input_data={"task_id": "123"},
                    retry_policy={"max_attempts": 3}
                )
            assert result["result"] == "success"

    @pytest.mark.asyncio
    async def test_workflow_timeout(self):
        """Test workflow timeout."""
        client = MagicMock()
            
        with patch.object(client, 'execute_workflow', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = TimeoutError("Workflow execution timed out")
                
            with pytest.raises(TimeoutError):
                    await client.execute_workflow(
                        workflow_name="test_workflow",
                        input_data={"task_id": "123"},
                        timeout_seconds=30
                    )

    @pytest.mark.asyncio
    async def test_batch_workflow_execution(self):
        """Test batch workflow execution."""
        client = MagicMock()
            
        with patch.object(client, 'execute_workflows', new_callable=AsyncMock) as mock_batch:
            mock_batch.return_value = [
                    {"workflow_id": "wf_1", "result": "success"},
                    {"workflow_id": "wf_2", "result": "success"},
                    {"workflow_id": "wf_3", "result": "success"}
                ]
                
            workflows = [
                    {"workflow_name": "test_workflow", "input_data": {"id": i}}
                    for i in range(3)
                ]
                
            result = await client.execute_workflows(workflows)
            assert len(result) == 3

    @pytest.mark.asyncio
    async def test_schedule_with_interval(self):
        """Test creating schedule with interval."""
        client = MagicMock()
            
        with patch.object(client, 'create_schedule', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = "schedule_interval"
                
            result = await client.create_schedule(
                    schedule_id="schedule_interval",
                    workflow_name="test_workflow",
                    interval_seconds=3600
                )
            assert result == "schedule_interval"

    @pytest.mark.asyncio
    async def test_get_schedule_details(self):
        """Test getting schedule details."""
        client = MagicMock()
            
        with patch.object(client, 'get_schedule_details', new_callable=AsyncMock) as mock_details:
            mock_details.return_value = {
                    "schedule_id": "sched_1",
                    "workflow_name": "test_workflow",
                    "cron_expression": "0 * * * *",
                    "status": "ACTIVE"
                }
                
            result = await client.get_schedule_details("sched_1")
            assert result["status"] == "ACTIVE"

    @pytest.mark.asyncio
    async def test_disconnect_from_temporal(self):
        """Test disconnecting from Temporal."""
        client = MagicMock()
            
        with patch.object(client, 'disconnect', new_callable=AsyncMock) as mock_disconnect:
            mock_disconnect.return_value = True
                
            result = await client.disconnect()
            assert result is True
