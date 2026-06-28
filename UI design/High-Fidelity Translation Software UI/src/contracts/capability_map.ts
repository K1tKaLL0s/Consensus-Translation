import type { SelfDecisionStatusDTO } from "./learning_strategy";

export type CapabilityId =
  | "text_translation"
  | "image_translation"
  | "file_translation"
  | "local_mode"
  | "ai_mode"
  | "learning_mode"
  | "self_iterative"
  | "self_decision"
  | "mock_provider"
  | "cloud_termbase";

export interface CapabilityDTO {
  id: CapabilityId;
  enabled: boolean;
  backend_status: "implemented" | "partial" | "missing" | "disabled";
  frontend_status: "implemented" | "partial" | "missing" | "hidden";
  contract_status: "matched" | "mismatched" | "missing";
  test_status: "covered" | "not_covered";
  production_status: "ready" | "blocked";
  reason: string;
  placeholder?: boolean;
  eligibility?: SelfDecisionStatusDTO;
}

export type CapabilityMap = Record<CapabilityId, CapabilityDTO>;

const blockedSelfDecision: SelfDecisionStatusDTO = {
  eligible: false,
  reason: "missing_validation",
  risk_level: "high",
  requires_ai_collaboration: true,
  requires_human_confirmation: true,
  rollback_supported: true,
};

export function get_capabilities(): CapabilityMap {
  return {
    text_translation: {
      id: "text_translation",
      enabled: true,
      backend_status: "implemented",
      frontend_status: "implemented",
      contract_status: "matched",
      test_status: "covered",
      production_status: "ready",
      reason: "Agent workflow exposes text translation.",
    },
    image_translation: {
      id: "image_translation",
      enabled: false,
      backend_status: "partial",
      frontend_status: "partial",
      contract_status: "matched",
      test_status: "covered",
      production_status: "blocked",
      reason: "OCR is partial; use the Windows connector/runtime path until the image UI is production-ready.",
    },
    file_translation: {
      id: "file_translation",
      enabled: true,
      backend_status: "implemented",
      frontend_status: "implemented",
      contract_status: "matched",
      test_status: "covered",
      production_status: "ready",
      reason: "File input is normalized before translation.",
    },
    local_mode: {
      id: "local_mode",
      enabled: true,
      backend_status: "implemented",
      frontend_status: "implemented",
      contract_status: "matched",
      test_status: "covered",
      production_status: "ready",
      reason: "Local mode wraps the existing local workflow.",
    },
    ai_mode: {
      id: "ai_mode",
      enabled: true,
      backend_status: "implemented",
      frontend_status: "implemented",
      contract_status: "matched",
      test_status: "covered",
      production_status: "ready",
      reason: "Remote providers require preflight confirmation.",
    },
    learning_mode: {
      id: "learning_mode",
      enabled: true,
      backend_status: "implemented",
      frontend_status: "implemented",
      contract_status: "matched",
      test_status: "covered",
      production_status: "ready",
      reason: "Learning mode proposes writeback behind human confirmation.",
    },
    self_iterative: {
      id: "self_iterative",
      enabled: true,
      backend_status: "implemented",
      frontend_status: "implemented",
      contract_status: "matched",
      test_status: "covered",
      production_status: "ready",
      reason: "Self-iterative mode is validation-gated.",
    },
    self_decision: {
      id: "self_decision",
      enabled: false,
      backend_status: "implemented",
      frontend_status: "implemented",
      contract_status: "matched",
      test_status: "covered",
      production_status: "blocked",
      reason: blockedSelfDecision.reason,
      eligibility: blockedSelfDecision,
    },
    mock_provider: {
      id: "mock_provider",
      enabled: false,
      backend_status: "implemented",
      frontend_status: "hidden",
      contract_status: "matched",
      test_status: "covered",
      production_status: "blocked",
      reason: "Mock providers are disabled for production runs.",
    },
    cloud_termbase: {
      id: "cloud_termbase",
      enabled: false,
      backend_status: "disabled",
      frontend_status: "hidden",
      contract_status: "matched",
      test_status: "covered",
      production_status: "blocked",
      reason: "Placeholder only; local termbase is active.",
      placeholder: true,
    },
  };
}
