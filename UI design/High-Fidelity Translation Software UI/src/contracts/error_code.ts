export type ErrorCode =
  | "none"
  | "validation_required"
  | "human_confirmation_required"
  | "provider_unavailable"
  | "mock_provider_blocked"
  | "budget_exceeded"
  | "unsupported_capability"
  | "store_commit_failed";

