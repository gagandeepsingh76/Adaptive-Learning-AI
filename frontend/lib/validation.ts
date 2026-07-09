import { z } from "zod";
import { splitCsv } from "@/lib/utils";
import type { ProjectCreateRequest, RoadmapCreateRequest } from "@/types/api";

const uuidMessage = "Use a valid roadmap UUID from a generated roadmap.";

export const roadmapFormSchema = z.object({
  goal_title: z
    .string()
    .trim()
    .min(3, "Goal must be at least 3 characters.")
    .max(200, "Goal must be 200 characters or fewer."),
  goal_description: z.string().trim().max(2000, "Description must be 2000 characters or fewer.").optional(),
  experience_level: z.enum(["beginner", "intermediate", "advanced"]),
  learning_style: z.enum(["visual", "reading", "hands_on", "mixed"]),
  weekly_hours: z.coerce
    .number({ invalid_type_error: "Weekly hours must be a number." })
    .positive("Weekly hours must be greater than 0.")
    .max(168, "Weekly hours cannot exceed 168."),
  existing_skills: z.string().optional(),
  constraints: z.string().optional()
});

export type RoadmapFormValues = z.infer<typeof roadmapFormSchema>;

export function toRoadmapRequest(values: RoadmapFormValues): RoadmapCreateRequest {
  return {
    goal_title: values.goal_title.trim(),
    goal_description: values.goal_description?.trim() || null,
    experience_level: values.experience_level,
    learning_style: values.learning_style,
    weekly_hours: values.weekly_hours,
    existing_skills: splitCsv(values.existing_skills),
    constraints: splitCsv(values.constraints)
  };
}

export const projectFormSchema = z
  .object({
    mode: z.enum(["roadmap", "direct"]),
    roadmap_id: z.string().trim().optional(),
    goal_title: z.string().trim().optional(),
    skills: z.string().optional(),
    difficulty: z.enum(["beginner", "intermediate", "advanced"]),
    constraints: z.string().optional()
  })
  .superRefine((value, context) => {
    if (value.mode === "roadmap") {
      if (!value.roadmap_id || !z.string().uuid().safeParse(value.roadmap_id).success) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["roadmap_id"],
          message: uuidMessage
        });
      }
      return;
    }

    if (!value.goal_title || value.goal_title.length < 3) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["goal_title"],
        message: "Goal must be at least 3 characters."
      });
    }

    if (splitCsv(value.skills).length === 0) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["skills"],
        message: "Add at least one skill."
      });
    }
  });

export type ProjectFormValues = z.infer<typeof projectFormSchema>;

export function toProjectRequest(values: ProjectFormValues): ProjectCreateRequest {
  if (values.mode === "roadmap") {
    return {
      roadmap_id: values.roadmap_id,
      difficulty: values.difficulty,
      constraints: splitCsv(values.constraints)
    };
  }

  return {
    goal_title: values.goal_title,
    skills: splitCsv(values.skills),
    difficulty: values.difficulty,
    constraints: splitCsv(values.constraints)
  };
}

export const chatFormSchema = z.object({
  roadmap_id: z.string().uuid(uuidMessage),
  question: z
    .string()
    .trim()
    .min(2, "Ask a question with at least 2 characters.")
    .max(4000, "Question must be 4000 characters or fewer.")
});

export type ChatFormValues = z.infer<typeof chatFormSchema>;

export const progressRoadmapSchema = z.object({
  roadmap_id: z.string().uuid(uuidMessage)
});

export const progressStatusSchema = z.enum(["pending", "in_progress", "completed"]);
