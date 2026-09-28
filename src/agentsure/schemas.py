from pydantic import BaseModel, Field


class EvaluationCase(BaseModel):
    case_id: str
    category: str

    response_text: str = ""

    expected_answer_keywords: list[str] = Field(
        default_factory=list
    )

    grounded: bool = True
    citation_valid: bool = True

    tool_calls: list[str] = Field(
        default_factory=list
    )

    allowed_tools: list[str] = Field(
        default_factory=list
    )

    pii_detected: bool = False
    prompt_injection: bool = False
    unauthorized_tool_use: bool = False
    loop_detected: bool = False

    goal_completed: bool = True

    latency_ms: float = 250.0
    cost_usd: float = 0.01

    # ---------------------------------------------------------
    # Human-in-the-loop approval state
    # ---------------------------------------------------------
    approval_required: bool = False

    approval_status: str = "NOT_REQUIRED"

    approval_id: str | None = None

    approval_risk_level: str | None = None


class EvaluationRequest(BaseModel):
    agent_id: str

    model_version: str = "unknown"
    prompt_version: str = "unknown"
    dataset_version: str = "unknown"
    test_suite_version: str = "v1"

    cases: list[EvaluationCase] = Field(
        min_length=1
    )


class EvaluationResponse(BaseModel):
    run_id: str

    arai_score: float
    release_decision: str
    critical_failure_count: int

    summary: dict