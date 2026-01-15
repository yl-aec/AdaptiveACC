"""WebSocket message models for real-time compliance check updates"""

from typing import Dict, Any, Optional, Literal, List
from pydantic import BaseModel, Field
from datetime import datetime


class WSMessage(BaseModel):
    """Base WebSocket message with timestamp"""
    type: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class WSIterationMessage(WSMessage):
    """Iteration update message - sent after each ReAct iteration

    Matches the iteration_entry structure from ComplianceAgent._run_react_iteration
    """
    type: Literal["iteration"] = "iteration"
    iteration: int
    active_subgoal_id: Optional[int] = None
    thought: str
    action: str
    action_input: Dict[str, Any]
    action_result: Dict[str, Any]


class WSSubgoalUpdateMessage(WSMessage):
    """Subgoal list update message - sent when subgoals are generated or updated"""
    type: Literal["subgoal_update"] = "subgoal_update"
    subgoals: List[Dict[str, Any]]


class WSCompletionMessage(WSMessage):
    """Task completion message - sent when compliance check is complete"""
    type: Literal["completion"] = "completion"
    status: str  # "success" | "timeout" | "failed"
    compliance_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class WSErrorMessage(WSMessage):
    """Error notification message"""
    type: Literal["error"] = "error"
    error: str


class WSConnectedMessage(WSMessage):
    """Connection confirmation message"""
    type: Literal["connected"] = "connected"
    session_id: str
