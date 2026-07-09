"use client";

import {
  CheckCircle2,
  Clock,
  Code2,
  Layers3,
  Loader2,
  Rocket,
  Sparkles,
  Target
} from "lucide-react";
import * as React from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { ApiErrorCard } from "@/components/shared/api-error-card";
import { useToast } from "@/components/shared/toast-provider";
import { useLatestRoadmap } from "@/hooks/use-latest-roadmap";
import { createApiClient } from "@/lib/api-client";
import { getApiDiagnostic } from "@/lib/api-diagnostics";
import { getStoredProject, storeProject } from "@/lib/storage";
import { formatHours, sentenceCase } from "@/lib/utils";
import {
  projectFormSchema,
  toProjectRequest,
  type ProjectFormValues
} from "@/lib/validation";
import type { ProjectResponse } from "@/types/api";

type ProjectFormState = Omit<ProjectFormValues, "mode">;

const initialForm: ProjectFormState = {
  roadmap_id: "",
  goal_title: "Build production RAG applications",
  skills: "FastAPI, ChromaDB, Gemini, evaluation, deployment",
  difficulty: "intermediate",
  constraints: "portfolio-ready, testable, deployable"
};

function resourceRecommendations(project: ProjectResponse) {
  const primarySkills = project.skills.slice(0, 5);
  const skillResources = primarySkills.map((skill) => ({
    title: `${skill} implementation reference`,
    description: `Review official docs or maintained guides for ${skill}, then apply it directly to one deliverable.`,
    type: "Skill"
  }));
  return [
    ...skillResources,
    {
      title: "Acceptance criteria checklist",
      description: "Use the generated acceptance criteria as the final QA checklist before recording the demo.",
      type: "QA"
    },
    {
      title: "Architecture decision notes",
      description: "Write one paragraph per major technical choice so the project is interview-ready.",
      type: "Interview"
    }
  ];
}

export default function ProjectPage() {
  const { roadmap, isReady } = useLatestRoadmap();
  const { notify } = useToast();
  const [mode, setMode] = React.useState<ProjectFormValues["mode"]>("roadmap");
  const [form, setForm] = React.useState<ProjectFormState>(initialForm);
  const [errors, setErrors] = React.useState<Record<string, string>>({});
  const [project, setProject] = React.useState<ProjectResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [generationError, setGenerationError] = React.useState<unknown>(null);

  React.useEffect(() => {
    setProject(getStoredProject());
  }, []);

  React.useEffect(() => {
    if (roadmap?.roadmap_id) {
      setForm((current) => ({ ...current, roadmap_id: roadmap.roadmap_id }));
    }
  }, [roadmap?.roadmap_id]);

  function updateField(
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function generateProject() {
    const parsed = projectFormSchema.safeParse({ ...form, mode });
    if (!parsed.success) {
      const nextErrors: Record<string, string> = {};
      for (const issue of parsed.error.issues) {
        const key = issue.path[0]?.toString() ?? "form";
        nextErrors[key] = issue.message;
      }
      setErrors(nextErrors);
      setGenerationError(null);
      return;
    }

    setErrors({});
    setGenerationError(null);
    setIsSubmitting(true);
    try {
      const generated = await createApiClient().createProject(toProjectRequest(parsed.data));
      setProject(generated);
      storeProject(generated);
      notify({
        tone: "success",
        title: "Project generated",
        description: `${generated.title} is ready for planning and demo prep.`
      });
    } catch (error) {
      const diagnostic = getApiDiagnostic(
        error,
        "Project generation failed",
        "The project could not be generated. Please try again."
      );
      setGenerationError(error);
      notify({ tone: "error", title: diagnostic.title, description: diagnostic.explanation });
    } finally {
      setIsSubmitting(false);
    }
  }

  function submitProject(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void generateProject();
  }

  const canUseRoadmap = Boolean(form.roadmap_id);

  return (
    <div className="app-section">
      <div>
        <Badge variant="secondary" className="mb-3">
          <Target className="mr-1 h-3.5 w-3.5" aria-hidden="true" />
          Project Recommendation
        </Badge>
        <h1 className="text-3xl font-semibold md:text-4xl">Generate a portfolio-grade project</h1>
        <p className="mt-2 max-w-3xl text-muted-foreground">
          Use either the latest roadmap or a direct goal-and-skills brief. The backend enforces the
          exclusive assignment modes and returns a complete project contract.
        </p>
      </div>

      <div className="content-grid">
        <Card>
          <CardHeader>
            <CardTitle className="text-xl">Assignment mode</CardTitle>
            <CardDescription>
              Roadmap mode uses generated context. Direct mode works when you already know the goal
              and skill set.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs value={mode} onValueChange={(value) => setMode(value as ProjectFormValues["mode"])}>
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="roadmap">From roadmap</TabsTrigger>
                <TabsTrigger value="direct">Goal + skills</TabsTrigger>
              </TabsList>
              <form className="mt-5 space-y-4" onSubmit={submitProject}>
                <TabsContent value="roadmap" className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="roadmap_id">Roadmap ID</Label>
                    <Input
                      id="roadmap_id"
                      name="roadmap_id"
                      value={form.roadmap_id ?? ""}
                      onChange={updateField}
                      placeholder="Generate a roadmap first"
                      aria-invalid={Boolean(errors.roadmap_id)}
                    />
                    {errors.roadmap_id ? <p className="text-sm text-destructive">{errors.roadmap_id}</p> : null}
                    {isReady && !roadmap ? (
                      <p className="text-sm text-muted-foreground">
                        No saved roadmap found.{" "}
                        <Link href="/roadmap" className="font-medium text-primary underline">
                          Generate one
                        </Link>{" "}
                        or switch to direct mode.
                      </p>
                    ) : null}
                  </div>
                </TabsContent>
                <TabsContent value="direct" className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="goal_title">Goal title</Label>
                    <Input
                      id="goal_title"
                      name="goal_title"
                      value={form.goal_title ?? ""}
                      onChange={updateField}
                      aria-invalid={Boolean(errors.goal_title)}
                    />
                    {errors.goal_title ? <p className="text-sm text-destructive">{errors.goal_title}</p> : null}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="skills">Skills</Label>
                    <Textarea
                      id="skills"
                      name="skills"
                      value={form.skills ?? ""}
                      onChange={updateField}
                      aria-invalid={Boolean(errors.skills)}
                    />
                    {errors.skills ? <p className="text-sm text-destructive">{errors.skills}</p> : null}
                  </div>
                </TabsContent>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="difficulty">Difficulty</Label>
                    <Select
                      id="difficulty"
                      name="difficulty"
                      value={form.difficulty}
                      onChange={updateField}
                    >
                      <option value="beginner">Beginner</option>
                      <option value="intermediate">Intermediate</option>
                      <option value="advanced">Advanced</option>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="constraints">Constraints</Label>
                    <Input
                      id="constraints"
                      name="constraints"
                      value={form.constraints ?? ""}
                      onChange={updateField}
                    />
                  </div>
                </div>
                <Button
                  type="submit"
                  className="w-full"
                  disabled={isSubmitting || (mode === "roadmap" && !canUseRoadmap)}
                >
                  {isSubmitting ? (
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                  ) : (
                    <Sparkles className="h-4 w-4" aria-hidden="true" />
                  )}
                  {isSubmitting ? "Generating project" : "Generate project"}
                </Button>
              </form>
            </Tabs>
          </CardContent>
        </Card>

        <section className="space-y-5" aria-label="Generated project">
          {generationError ? (
            <ApiErrorCard
              error={generationError}
              title="Project generation failed"
              explanation="The project could not be generated. Please try again."
              onRetry={() => void generateProject()}
            />
          ) : null}
          {project ? <ProjectResult project={project} /> : <EmptyProject />}
        </section>
      </div>
    </div>
  );
}

function EmptyProject() {
  return (
    <Card>
      <CardHeader>
        <div className="mb-2 flex h-11 w-11 items-center justify-center rounded-lg bg-secondary">
          <Rocket className="h-5 w-5 text-primary" aria-hidden="true" />
        </div>
        <CardTitle className="text-xl">No project generated yet</CardTitle>
        <CardDescription>
          Choose an assignment mode and generate a recommendation. The response will include
          difficulty, estimated effort, skills, features, rationale, deliverables, and acceptance
          criteria.
        </CardDescription>
      </CardHeader>
    </Card>
  );
}

function ProjectResult({ project }: { project: ProjectResponse }) {
  const resources = resourceRecommendations(project);
  const estimatedWeeks = Math.max(1, Math.ceil(Number(project.estimated_hours) / 8));
  const architectureFocus = project.skills.slice(0, 4).map((skill) => {
    return `Use ${skill} as an explicit implementation layer with tests or acceptance evidence.`;
  });
  const timeline = [
    "Milestone 1: confirm scope, data contracts, and acceptance criteria.",
    `Milestone 2: build the core flow over ${estimatedWeeks} focused week${estimatedWeeks > 1 ? "s" : ""}.`,
    "Milestone 3: verify, document, deploy, and record a concise demo walkthrough."
  ];
  return (
    <>
      <div className="metric-grid">
        <ProjectMetric label="Difficulty" value={sentenceCase(project.difficulty)} icon={Layers3} />
        <ProjectMetric label="Estimated hours" value={formatHours(project.estimated_hours)} icon={Clock} />
        <ProjectMetric label="Tech stack" value={`${project.skills.length} skills`} icon={Code2} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="break-words text-2xl">{project.title}</CardTitle>
          <CardDescription className="break-words">{project.description}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <section>
            <h2 className="mb-3 font-semibold">Tech stack</h2>
            <div className="flex flex-wrap gap-2">
              {project.skills.map((skill) => (
                <Badge key={skill} variant="secondary">
                  {skill}
                </Badge>
              ))}
            </div>
          </section>

          <section className="grid gap-4 md:grid-cols-2">
            <ListBlock title="Implementation timeline" items={timeline} icon={Clock} />
            <ListBlock title="Architecture focus" items={architectureFocus} icon={Layers3} />
          </section>

          <section className="grid gap-4 md:grid-cols-2">
            <ListBlock title="Core requirements" items={project.requirements} icon={CheckCircle2} />
            <ListBlock title="Features and deliverables" items={project.deliverables} icon={Rocket} />
          </section>

          <section>
            <h2 className="mb-3 font-semibold">Why this project</h2>
            <p className="rounded-lg border bg-background p-4 text-sm text-muted-foreground">
              It forces the learner to combine the generated skill set into a concrete artifact,
              demonstrate implementation judgment, and verify the result against acceptance
              criteria rather than only completing tutorials.
            </p>
          </section>

          <section>
            <h2 className="mb-3 font-semibold">Acceptance criteria</h2>
            <div className="space-y-2">
              {project.acceptance_criteria.map((criterion) => (
                <div key={criterion} className="flex gap-3 rounded-lg border bg-background p-3 text-sm">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
                  <span>{criterion}</span>
                </div>
              ))}
            </div>
          </section>

          <section>
            <h2 className="mb-3 font-semibold">Recommended learning resources</h2>
            <div className="grid gap-3 md:grid-cols-2">
              {resources.map((resource) => (
                <div key={`${resource.type}-${resource.title}`} className="rounded-lg border bg-background p-4">
                  <Badge variant="outline" className="mb-2">
                    {resource.type}
                  </Badge>
                  <p className="break-words font-medium">{resource.title}</p>
                  <p className="mt-1 text-sm text-muted-foreground">{resource.description}</p>
                </div>
              ))}
            </div>
          </section>
        </CardContent>
      </Card>
    </>
  );
}

function ProjectMetric({
  label,
  value,
  icon: Icon
}: {
  label: string;
  value: string;
  icon: React.ElementType;
}) {
  return (
    <Card>
      <CardHeader className="p-4">
        <div className="mb-2 flex items-center justify-between">
          <CardDescription>{label}</CardDescription>
          <Icon className="h-4 w-4 text-primary" aria-hidden="true" />
        </div>
        <CardTitle className="text-xl">{value}</CardTitle>
      </CardHeader>
    </Card>
  );
}

function ListBlock({
  title,
  items,
  icon: Icon
}: {
  title: string;
  items: string[];
  icon: React.ElementType;
}) {
  return (
    <div className="rounded-lg border bg-background p-4">
      <h2 className="mb-3 flex items-center gap-2 font-semibold">
        <Icon className="h-4 w-4 text-primary" aria-hidden="true" />
        {title}
      </h2>
      <ul className="space-y-2 text-sm text-muted-foreground">
        {items.map((item) => (
          <li key={item} className="rounded-md bg-card p-3">
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
