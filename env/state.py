from pydantic import BaseModel, Field
from typing import List, Optional

class Observation(BaseModel):
    report_text: str = ""
    logs: List[str] = Field(default_factory=list)
    code_snippet: str = ""
    extracted_signals: List[str] = Field(default_factory=list)
    identified_vulnerability: Optional[str] = None
    severity: Optional[str] = None
    component: Optional[str] = None
    exploit_chain: List[str] = Field(default_factory=list)
    fix_suggestion: Optional[str] = None
    step_count: int = 0
