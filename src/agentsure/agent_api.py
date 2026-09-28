from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .agents.serviceops import ServiceOpsAgent
from .api import get_db

router = APIRouter(prefix="/v1/agents", tags=["Agent Runtime"])
agent = ServiceOpsAgent()


class AgentRunRequest(BaseModel):
    incident_id: str = Field(min_length=1, max_length=64)
    user_message: str = Field(min_length=1, max_length=4000)


@router.post("/serviceops/run")
def run_serviceops_agent(request: AgentRunRequest, db: Session = Depends(get_db)):
    return agent.run(db, request.incident_id, request.user_message)
