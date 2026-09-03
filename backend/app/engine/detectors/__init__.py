from abc import ABC, abstractmethod
from typing import Optional
from app.engine.types import RiskSignal
from app.engine.features.extractor import FeatureContext

class BaseDetector(ABC):
    @abstractmethod
    def evaluate(self, context: FeatureContext) -> Optional[RiskSignal]:
        pass
