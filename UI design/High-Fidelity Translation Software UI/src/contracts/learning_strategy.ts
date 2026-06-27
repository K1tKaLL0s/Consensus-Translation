export type LearningStrategy =
  | "training_set"
  | "validation_set"
  | "rounds"
  | "human_review"
  | "self_iterative"
  | "self_decision";

export interface SelfDecisionStatusDTO {
  eligible: boolean;
  reason: string;
  risk_level: "low" | "medium" | "high";
  requires_ai_collaboration: boolean;
  requires_human_confirmation: boolean;
  rollback_supported: boolean;
}

export interface LearningState {
  training_set: string;
  validation_set: string;
  rounds: number;
  human_review: boolean;
  self_iterative: boolean;
  self_decision: SelfDecisionStatusDTO;
}

