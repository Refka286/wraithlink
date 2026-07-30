export type EngagementStatus =
  | "scope_validation"
  | "reconnaissance"
  | "scan"
  | "approval_pending"
  | "exploitation"
  | "reporting"
  | "closed";

export type TargetType = "web" | "active_directory";

export type RiskTier = "automatic" | "approval" | "forbidden";

export type ActionStatus = "pending" | "blocked" | "awaiting_approval" | "running" | "completed" | "failed";

export type ApprovalOption = "A" | "B";

export type FindingSeverity = "info" | "low" | "medium" | "high" | "critical";

export type UserRole = "pentester" | "reader";

export interface Target {
  id: string;
  host: string;
  type: TargetType;
}

export interface Engagement {
  id: string;
  name: string;
  scope_validated: boolean;
  status: EngagementStatus;
  created_at: string;
  targets: Target[];
}

export interface Action {
  id: string;
  engagement_id: string;
  target_id: string | null;
  tool: string;
  params: Record<string, unknown>;
  risk_score: number | null;
  tier: RiskTier | null;
  status: ActionStatus;
  result: Record<string, unknown> | null;
  created_at: string;
}

export interface Approval {
  id: string;
  action_id: string;
  option_chosen: ApprovalOption;
  justification: string;
  approved_by: string;
  approved_at: string;
}

export interface Finding {
  id: string;
  action_id: string;
  type: string;
  severity: FindingSeverity;
  description: string;
  created_at: string;
}

export interface ReportRecord {
  id: string;
  engagement_id: string;
  pdf_ref: string;
  created_at: string;
}
