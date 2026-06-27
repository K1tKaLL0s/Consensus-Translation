export type WorkflowMode = "standard" | "learning" | "review";

export const WORKFLOW_MODES: readonly WorkflowMode[] = [
  "standard",
  "learning",
  "review",
] as const;

