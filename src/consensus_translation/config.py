from pydantic import BaseModel, Field


class AppSettings(BaseModel):
    contract_version: str = "1.0.0"
    default_granularity: list[str] = Field(
        default_factory=lambda: ["token", "sentence", "segment"]
    )
    mdwc_weights: dict[str, float] = Field(
        default_factory=lambda: {
            "token": 0.4,
            "sentence": 0.35,
            "segment": 0.2,
            "user_prior": 0.05,
        }
    )
