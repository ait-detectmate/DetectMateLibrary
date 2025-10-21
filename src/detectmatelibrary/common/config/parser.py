from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from components.common.core import CoreConfig, List


class ParserInstance(BaseModel):
    id: str
    log_format: Optional[str] = Field(
        default="<Content>",
        description='Default is "<Content>" (i.e., the full message content).',
    )
    params: Optional[Dict[str, Any]] = None  # free-form, parser-type specific


class CoreParserConfig(CoreConfig):
    parserType: str = "<PLACEHOLDER>"
    parserID: str = "<PLACEHOLDER>"
    instances: List[ParserInstance] = []
