"""Parser configuration classes."""

from __future__ import annotations
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ParserInstance(BaseModel):
    id: str
    log_format: Optional[str] = Field(
        default="<Content>",
        description='Default is "<Content>" (i.e., the full message content).',
    )
    params: Optional[Dict[str, Any]] = None  # free-form, parser-type specific


class ParserConfig(BaseModel):
    type: str = Field(description="The parser implementation name.")
    instances: List[ParserInstance]
