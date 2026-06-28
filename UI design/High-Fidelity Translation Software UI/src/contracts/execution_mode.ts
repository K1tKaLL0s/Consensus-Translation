export type ExecutionMode =
  | "local"
  | "ai_assisted"
  | "learning"
  | "self_iterative"
  | "self_decision"
  | "pretraining";

export const EXECUTION_MODES: readonly ExecutionMode[] = [
  "local",
  "ai_assisted",
  "learning",
  "self_iterative",
  "self_decision",
  "pretraining",
] as const;

