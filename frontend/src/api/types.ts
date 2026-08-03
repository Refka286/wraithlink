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

export type UserRole = "admin" | "pentester" | "reader";

export interface Target {
  id: string;
  host: string;
  type: TargetType;
}

export interface Engagement {
  id: string;
  name: string;
  client_name: string | null;
  scope_validated: boolean;
  status: EngagementStatus;
  created_at: string;
  owner_id: string | null;
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
  error_summary: string | null;
  note: string | null;
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
  compliance_reference: string;
}

export interface ReportRecord {
  id: string;
  engagement_id: string;
  pdf_ref: string;
  created_at: string;
}

export type SuggestionPriority = "high" | "medium" | "low";

export interface Suggestion {
  tool: string;
  reasoning: string;
  priority: SuggestionPriority;
}

export interface SuggestionsResponse {
  suggestions: Suggestion[];
}

export interface ToolRisk {
  impact: number;
  detectability: number;
  reversibility: number;
  sensitive: boolean;
  score: number;
  tier: RiskTier | "forbidden";
  tier_reason: string;
}

export interface ToolProfile {
  profile: string;
  label: string;
  explanation: string;
  risk: ToolRisk;
}

export interface AnalyticsSummary {
  total_engagements: number;
  total_actions: number;
  total_approvals: number;
  findings_by_severity: Record<string, number>;
  tool_usage: Record<string, number>;
  tier_distribution: Record<string, number>;
  approval_option_ratio: Record<string, number>;
  average_approval_seconds: number | null;
}

export interface UserAccount {
  id: string;
  email: string;
  role: UserRole;
  created_at: string;
}

export interface Credential {
  id: string;
  label: string;
  domain: string | null;
  username: string;
  created_at: string;
}

export interface CredentialCreate {
  label: string;
  domain: string | null;
  username: string;
  password: string;
}

export interface ToolReference {
  tool: string;
  label: string;
  what_is: string;
  how_it_works: string;
  example_finding: { type: string; description: string };
  profiles: ToolProfile[];
}
