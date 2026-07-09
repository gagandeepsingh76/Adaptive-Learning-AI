export type DecimalLike = number | string;

export type ExperienceLevel = "beginner" | "intermediate" | "advanced";
export type LearningStyle = "visual" | "reading" | "hands_on" | "mixed";
export type Difficulty = "beginner" | "intermediate" | "advanced";
export type ProgressStatus = "pending" | "in_progress" | "completed";
export type ProgressTargetType = "roadmap" | "skill" | "task" | "subtask";

export interface RoadmapCreateRequest {
  goal_title: string;
  goal_description?: string | null;
  experience_level: ExperienceLevel;
  learning_style: LearningStyle;
  weekly_hours: number;
  existing_skills: string[];
  constraints: string[];
}

export interface SubtaskResponse {
  id: string;
  title: string;
  description: string;
  completion_criteria: string;
  estimated_hours: DecimalLike;
  order_index: number;
}

export interface TaskResponse {
  id: string;
  title: string;
  description: string;
  difficulty: string;
  estimated_hours: DecimalLike;
  order_index: number;
  learning_outcomes: string[];
  subtasks: SubtaskResponse[];
}

export interface SkillResponse {
  id: string;
  title: string;
  description: string;
  target_proficiency: string;
  estimated_hours: DecimalLike;
  order_index: number;
  tasks: TaskResponse[];
}

export interface RoadmapResponse {
  roadmap_id: string;
  goal_title: string;
  estimated_hours: DecimalLike;
  skills: SkillResponse[];
}

export interface ProjectCreateRequest {
  roadmap_id?: string | null;
  goal_title?: string | null;
  skills?: string[] | null;
  difficulty: Difficulty;
  constraints: string[];
}

export interface ProjectResponse {
  project_id: string;
  roadmap_id: string | null;
  title: string;
  description: string;
  difficulty: Difficulty;
  estimated_hours: DecimalLike;
  skills: string[];
  requirements: string[];
  deliverables: string[];
  acceptance_criteria: string[];
}

export interface ChatRequest {
  roadmap_id: string;
  question: string;
  conversation_id?: string | null;
}

export interface CitationResponse {
  source_id: string;
  entity_type: string;
  entity_id: string;
  relevance: number;
}

export interface ChatResponse {
  conversation_id: string;
  message_id: string;
  answer: string;
  citations: CitationResponse[];
  follow_up_questions: string[];
}

export interface ProgressUpdateRequest {
  target_type: ProgressTargetType;
  target_id?: string | null;
  status: ProgressStatus;
  progress_percent: number;
  time_spent_minutes?: number;
  notes?: string | null;
}

export interface ProgressItemResponse {
  target_type: ProgressTargetType;
  target_id: string;
  status: ProgressStatus;
  progress_percent: DecimalLike;
  time_spent_minutes: number;
}

export interface ProgressSummaryResponse {
  roadmap_id: string;
  completion_percentage: DecimalLike;
  total_subtasks: number;
  completed_subtasks: number;
  total_time_spent_minutes: number;
  records: ProgressItemResponse[];
}

export interface AIProviderStatus {
  provider: string;
  configured: boolean;
  status: "ready" | "unconfigured" | "unavailable" | string;
  llm_model: string;
  embedding_model: string;
  embedding_dimensions: number;
  reason?: string | null;
  action?: string | null;
  missing_env?: string | null;
}

export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
  ai_provider?: AIProviderStatus;
}
