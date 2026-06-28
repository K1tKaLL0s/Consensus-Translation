export type TaskStatus =
  | "idle"
  | "queued"
  | "running"
  | "awaiting_confirmation"
  | "completed"
  | "failed"
  | "cancelled";

export const TASK_STATUSES: readonly TaskStatus[] = [
  "idle",
  "queued",
  "running",
  "awaiting_confirmation",
  "completed",
  "failed",
  "cancelled",
] as const;

export function map_task_status(status: string | null | undefined): TaskStatus {
  switch ((status ?? "").trim().toLowerCase()) {
    case "idle":
      return "idle";
    case "queued":
      return "queued";
    case "running":
      return "running";
    case "awaiting_human_confirmation":
    case "needs_review":
    case "review":
      return "awaiting_confirmation";
    case "finalized":
    case "completed":
      return "completed";
    case "rejected":
    case "cancelled":
      return "cancelled";
    case "budget_exceeded":
    case "failed":
      return "failed";
    default:
      return "failed";
  }
}

