from abc import ABC, abstractmethod


class BaseProviderAdapter(ABC):
    provider_name: str

    @abstractmethod
    def generate(self, prompt: str, api_key: str) -> str:
        raise NotImplementedError
