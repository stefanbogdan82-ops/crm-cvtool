from abc import ABC, abstractmethod


class AIClient(ABC):
    @abstractmethod
    def enrich(self, cv_text: str) -> dict:
        raise NotImplementedError