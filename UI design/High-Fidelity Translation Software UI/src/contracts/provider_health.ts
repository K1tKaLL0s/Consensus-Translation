export interface ProviderHealthDTO {
  status: "ready" | "degraded" | "unavailable" | "mock";
  latency: number;
  reliability_score: number;
  fallback_chain: string[];
  is_mock: boolean;
  is_production_ready: boolean;
}

