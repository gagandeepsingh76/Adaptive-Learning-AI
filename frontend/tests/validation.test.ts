import { describe, expect, it } from "vitest";

import {
  toProjectRequest,
  toRoadmapRequest,
  type ProjectFormValues,
  type RoadmapFormValues
} from "@/lib/validation";

describe("request validation helpers", () => {
  it("normalizes roadmap form values into the backend contract", () => {
    const values: RoadmapFormValues = {
      goal_title: "  Machine Learning Engineer  ",
      goal_description: "  Build practical ML systems  ",
      experience_level: "intermediate",
      learning_style: "hands_on",
      weekly_hours: 12,
      existing_skills: " Python, SQL, , statistics ",
      constraints: " weekends, portfolio project "
    };

    expect(toRoadmapRequest(values)).toEqual({
      goal_title: "Machine Learning Engineer",
      goal_description: "Build practical ML systems",
      experience_level: "intermediate",
      learning_style: "hands_on",
      weekly_hours: 12,
      existing_skills: ["Python", "SQL", "statistics"],
      constraints: ["weekends", "portfolio project"]
    });
  });

  it("builds roadmap-mode project requests without direct-mode fields", () => {
    const values: ProjectFormValues = {
      mode: "roadmap",
      roadmap_id: "00000000-0000-4000-8000-000000000001",
      difficulty: "advanced",
      constraints: "deployable, tested"
    };

    expect(toProjectRequest(values)).toEqual({
      roadmap_id: "00000000-0000-4000-8000-000000000001",
      difficulty: "advanced",
      constraints: ["deployable", "tested"]
    });
  });

  it("builds direct-mode project requests with normalized skills", () => {
    const values: ProjectFormValues = {
      mode: "direct",
      goal_title: "AI Portfolio",
      skills: "RAG, FastAPI, React",
      difficulty: "intermediate",
      constraints: ""
    };

    expect(toProjectRequest(values)).toEqual({
      goal_title: "AI Portfolio",
      skills: ["RAG", "FastAPI", "React"],
      difficulty: "intermediate",
      constraints: []
    });
  });
});
