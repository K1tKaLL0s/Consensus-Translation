from src.core.providers.deepseek_adapter import DeepSeekAdapter
from src.core.providers.gemini_adapter import GeminiAdapter
from src.core.providers.watsonx_adapter import WatsonXAdapter


PROVIDER_ADAPTERS = {
    "deepseek": DeepSeekAdapter(),
    "gemini": GeminiAdapter(),
    "watsonx": WatsonXAdapter(),
}
