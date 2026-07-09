"use client";

import {
  CheckCircle2,
  Clock,
  Loader2,
  Map,
  PlayCircle,
  RotateCcw,
  Sparkles
} from "lucide-react";
import * as React from "react";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ApiErrorCard } from "@/components/shared/api-error-card";
import { useToast } from "@/components/shared/toast-provider";
import { useLatestRoadmap } from "@/hooks/use-latest-roadmap";
import { createApiClient } from "@/lib/api-client";
import { getApiDiagnostic } from "@/lib/api-diagnostics";
import { formatHours, sentenceCase, toNumber } from "@/lib/utils";
import {
  roadmapFormSchema,
  toRoadmapRequest,
  type RoadmapFormValues
} from "@/lib/validation";
import type {
  ProgressStatus,
  ProgressSummaryResponse,
  RoadmapResponse,
  SkillResponse,
  SubtaskResponse,
  TaskResponse
} from "@/types/api";

type RoadmapFormState = Omit<RoadmapFormValues, "weekly_hours"> & { weekly_hours: string };

const initialForm: RoadmapFormState = {
  goal_title: "AI Engineer",
  goal_description: "Build production AI systems with RAG, evaluation, deployment, and monitoring.",
  experience_level: "intermediate",
  learning_style: "hands_on",
  weekly_hours: "10",
  existing_skills: "Python, TypeScript, APIs",
  constraints: "portfolio-ready, interview-friendly, production deployment"
};

function errorMessage(error: unknown) {
  return getApiDiagnostic(
    error,
    "Roadmap generation failed",
    "The roadmap could not be generated. Please try again."
  ).explanation;
}

function collectSubtasks(skill: SkillResponse) {
  return skill.tasks.flatMap((task) => task.subtasks);
}

function statusFromProgress(
  progress: ProgressSummaryResponse | null,
  targetId: string
): ProgressStatus {
  return progress?.records.find((record) => record.target_id === targetId)?.status ?? "pending";
}

function completionForSkill(skill: SkillResponse, progress: ProgressSummaryResponse | null) {
  const subtasks = collectSubtasks(skill);
  if (subtasks.length === 0) {
    return 0;
  }
  const completed = subtasks.filter(
    (subtask) => statusFromProgress(progress, subtask.id) === "completed"
  ).length;
  return Math.round((completed / subtasks.length) * 100);
}

function roadmapTotals(roadmap: RoadmapResponse) {
  const tasks = roadmap.skills.flatMap((skill) => skill.tasks);
  const subtasks = tasks.flatMap((task) => task.subtasks);
  return {
    skills: roadmap.skills.length,
    tasks: tasks.length,
    subtasks: subtasks.length
  };
}

export default function RoadmapPage() {
  const { roadmap, saveRoadmap, isReady } = useLatestRoadmap();
  const { notify } = useToast();
  const [form, setForm] = React.useState<RoadmapFormState>(initialForm);
  const [errors, setErrors] = React.useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [isProgressLoading, setIsProgressLoading] = React.useState(false);
  const [progress, setProgress] = React.useState<ProgressSummaryResponse | null>(null);
  const [pendingTarget, setPendingTarget] = React.useState<string | null>(null);
  const [generationError, setGenerationError] = React.useState<unknown>(null);

  const weeklyHours = Math.max(1, Number.parseFloat(form.weekly_hours) || 10);
  const estimatedWeeks = roadmap
    ? Math.max(1, Math.ceil(toNumber(roadmap.estimated_hours) / weeklyHours))
    : 0;

  React.useEffect(() => {
    if (!roadmap?.roadmap_id) {
      return;
    }
    let isMounted = true;
    setIsProgressLoading(true);
    createApiClient()
      .getProgress(roadmap.roadmap_id)
      .then((summary) => {
        if (isMounted) {
          setProgress(summary);
        }
      })
      .catch(() => {
        if (isMounted) {
          setProgress(null);
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsProgressLoading(false);
        }
      });
    return () => {
      isMounted = false;
    };
  }, [roadmap?.roadmap_id]);

  function updateField(
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function generateRoadmap() {
    const parsed = roadmapFormSchema.safeParse(form);
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
      const generated = await createApiClient().createRoadmap(toRoadmapRequest(parsed.data));
      saveRoadmap(generated);
      setProgress(null);
      notify({
        tone: "success",
        title: "Roadmap generated",
        description: `${generated.skills.length} skills are ready for sequencing and progress tracking.`
      });
    } catch (error) {
      const diagnostic = getApiDiagnostic(
        error,
        "Roadmap generation failed",
        "The roadmap could not be generated. Please try again."
      );
      setGenerationError(error);
      notify({ tone: "error", title: diagnostic.title, description: diagnostic.explanation });
    } finally {
      setIsSubmitting(false);
    }
  }

  function submitRoadmap(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void generateRoadmap();
  }

  async function updateSubtask(subtask: SubtaskResponse, status: ProgressStatus) {
    if (!roadmap) {
      return;
    }
    setPendingTarget(subtask.id);
    try {
      const summary = await createApiClient().updateProgress(roadmap.roadmap_id, {
        target_type: "subtask",
        target_id: subtask.id,
        status,
        progress_percent: status === "completed" ? 100 : status === "in_progress" ? 50 : 0,
        time_spent_minutes: status === "completed" ? Math.round(toNumber(subtask.estimated_hours) * 60) : 0,
        notes: status === "completed" ? `Completed ${subtask.title}` : null
      });
      setProgress(summary);
      notify({
        tone: "success",
        title: status === "completed" ? "Subtask completed" : "Subtask reopened",
        description: subtask.title
      });
    } catch (error) {
      notify({ tone: "error", title: "Progress update failed", description: errorMessage(error) });
    } finally {
      setPendingTarget(null);
    }
  }

  const totals = roadmap ? roadmapTotals(roadmap) : null;

  return (
    <div className="app-section">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <Badge variant="secondary" className="mb-3">
            <Map className="mr-1 h-3.5 w-3.5" aria-hidden="true" />
            Roadmap Generator
          </Badge>
          <h1 className="text-3xl font-semibold md:text-4xl">Generate a sequenced learning plan</h1>
          <p className="mt-2 max-w-3xl text-muted-foreground">
            Create a backend-generated roadmap with skills, tasks, subtasks, estimated effort, and
            completion-ready checkpoints.
          </p>
        </div>
      </div>

      <div className="content-grid">
        <Card>
          <CardHeader>
            <CardTitle className="text-xl">Learning goal</CardTitle>
            <CardDescription>
              The backend validates this request and persists the generated roadmap hierarchy.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={submitRoadmap}>
              <div className="space-y-2">
                <Label htmlFor="goal_title">Goal title</Label>
                <Input
                  id="goal_title"
                  name="goal_title"
                  value={form.goal_title}
                  onChange={updateField}
                  aria-invalid={Boolean(errors.goal_title)}
                />
                {errors.goal_title ? <p className="text-sm text-destructive">{errors.goal_title}</p> : null}
              </div>
              <div className="space-y-2">
                <Label htmlFor="goal_description">Goal description</Label>
                <Textarea
                  id="goal_description"
                  name="goal_description"
                  value={form.goal_description ?? ""}
                  onChange={updateField}
                  aria-invalid={Boolean(errors.goal_description)}
                />
                {errors.goal_description ? (
                  <p className="text-sm text-destructive">{errors.goal_description}</p>
                ) : null}
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="experience_level">Experience</Label>
                  <Select
                    id="experience_level"
                    name="experience_level"
                    value={form.experience_level}
                    onChange={updateField}
                  >
                    <option value="beginner">Beginner</option>
                    <option value="intermediate">Intermediate</option>
                    <option value="advanced">Advanced</option>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="learning_style">Learning style</Label>
                  <Select
                    id="learning_style"
                    name="learning_style"
                    value={form.learning_style}
                    onChange={updateField}
                  >
                    <option value="visual">Visual</option>
                    <option value="reading">Reading</option>
                    <option value="hands_on">Hands on</option>
                    <option value="mixed">Mixed</option>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="weekly_hours">Weekly hours</Label>
                <Input
                  id="weekly_hours"
                  name="weekly_hours"
                  type="number"
                  min="1"
                  max="168"
                  value={form.weekly_hours}
                  onChange={updateField}
                  aria-invalid={Boolean(errors.weekly_hours)}
                />
                {errors.weekly_hours ? <p className="text-sm text-destructive">{errors.weekly_hours}</p> : null}
              </div>
              <div className="space-y-2">
                <Label htmlFor="existing_skills">Existing skills</Label>
                <Input
                  id="existing_skills"
                  name="existing_skills"
                  value={form.existing_skills ?? ""}
                  onChange={updateField}
                  placeholder="Python, SQL, React"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="constraints">Constraints</Label>
                <Textarea
                  id="constraints"
                  name="constraints"
                  value={form.constraints ?? ""}
                  onChange={updateField}
                  placeholder="Comma-separated constraints"
                />
              </div>
              <Button type="submit" className="w-full" disabled={isSubmitting}>
                {isSubmitting ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                ) : (
                  <Sparkles className="h-4 w-4" aria-hidden="true" />
                )}
                {isSubmitting ? "Generating roadmap" : "Generate roadmap"}
              </Button>
            </form>
          </CardContent>
        </Card>

        <section className="space-y-5" aria-label="Generated roadmap">
          {generationError ? (
            <ApiErrorCard
              error={generationError}
              title="Roadmap generation failed"
              explanation="The roadmap could not be generated. Please try again."
              onRetry={() => void generateRoadmap()}
            />
          ) : null}
          {!isReady ? (
            <RoadmapSkeleton />
          ) : roadmap ? (
            <>
              <div className="metric-grid">
                <MetricCard label="Estimated hours" value={formatHours(roadmap.estimated_hours)} icon={Clock} />
                <MetricCard label="Estimated weeks" value={`${estimatedWeeks}`} icon={PlayCircle} />
                <MetricCard label="Skills" value={`${totals?.skills ?? 0}`} icon={Map} />
                <MetricCard label="Subtasks" value={`${totals?.subtasks ?? 0}`} icon={CheckCircle2} />
              </div>

              <Card>
                <CardHeader>
                  <CardTitle className="text-xl">{roadmap.goal_title}</CardTitle>
                  <CardDescription>
                    {isProgressLoading
                      ? "Loading completion data..."
                      : `${Math.round(toNumber(progress?.completion_percentage ?? 0))}% complete across ${progress?.total_subtasks ?? totals?.subtasks ?? 0} subtasks.`}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-5">
                  <Progress value={toNumber(progress?.completion_percentage ?? 0)} />
                  <LearningTimeline roadmap={roadmap} weeklyHours={weeklyHours} progress={progress} />
                  <RoadmapAccordion
                    roadmap={roadmap}
                    progress={progress}
                    pendingTarget={pendingTarget}
                    onUpdateSubtask={updateSubtask}
                  />
                </CardContent>
              </Card>
            </>
          ) : (
            <Card>
              <CardHeader>
                <CardTitle className="text-xl">No roadmap yet</CardTitle>
                <CardDescription>
                  Fill out the goal form to generate a roadmap. The latest result is saved locally
                  so project, chat, and progress pages can use it.
                </CardDescription>
              </CardHeader>
            </Card>
          )}
        </section>
      </div>
    </div>
  );
}

function MetricCard({
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
      <CardHeader className="space-y-2 p-4">
        <div className="flex items-center justify-between gap-3">
          <CardDescription>{label}</CardDescription>
          <Icon className="h-4 w-4 text-primary" aria-hidden="true" />
        </div>
        <CardTitle className="text-2xl">{value}</CardTitle>
      </CardHeader>
    </Card>
  );
}

function RoadmapSkeleton() {
  return (
    <div className="space-y-4">
      <div className="metric-grid">
        {[0, 1, 2, 3].map((item) => (
          <Skeleton key={item} className="h-28" />
        ))}
      </div>
      <Skeleton className="h-96" />
    </div>
  );
}

function LearningTimeline({
  roadmap,
  weeklyHours,
  progress
}: {
  roadmap: RoadmapResponse;
  weeklyHours: number;
  progress: ProgressSummaryResponse | null;
}) {
  let cumulativeHours = 0;
  return (
    <div className="rounded-lg border bg-background p-4">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="font-semibold">Learning timeline</h2>
        <Badge variant="outline">{weeklyHours} hrs/week</Badge>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {roadmap.skills.map((skill) => {
          const startWeek = Math.max(1, Math.floor(cumulativeHours / weeklyHours) + 1);
          cumulativeHours += toNumber(skill.estimated_hours);
          const endWeek = Math.max(startWeek, Math.ceil(cumulativeHours / weeklyHours));
          return (
            <div key={skill.id} className="rounded-lg border bg-card p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="break-words text-sm font-semibold">{skill.title}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Weeks {startWeek}-{endWeek} - {formatHours(skill.estimated_hours)}
                  </p>
                </div>
                <Badge variant={completionForSkill(skill, progress) === 100 ? "success" : "secondary"}>
                  {completionForSkill(skill, progress)}%
                </Badge>
              </div>
              <Progress value={completionForSkill(skill, progress)} className="mt-3" />
            </div>
          );
        })}
      </div>
    </div>
  );
}

function RoadmapAccordion({
  roadmap,
  progress,
  pendingTarget,
  onUpdateSubtask
}: {
  roadmap: RoadmapResponse;
  progress: ProgressSummaryResponse | null;
  pendingTarget: string | null;
  onUpdateSubtask: (subtask: SubtaskResponse, status: ProgressStatus) => Promise<void>;
}) {
  return (
    <Accordion type="multiple" className="space-y-4">
      {roadmap.skills.map((skill) => (
        <AccordionItem
          key={skill.id}
          value={skill.id}
          className="rounded-lg border bg-background px-4"
        >
          <AccordionTrigger className="gap-4 hover:no-underline">
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="break-words font-semibold">{skill.title}</span>
                <Badge variant="outline">{formatHours(skill.estimated_hours)}</Badge>
                <Badge variant={completionForSkill(skill, progress) === 100 ? "success" : "secondary"}>
                  {completionForSkill(skill, progress)}% complete
                </Badge>
              </div>
              <p className="mt-1 break-words text-sm text-muted-foreground">{skill.description}</p>
            </div>
          </AccordionTrigger>
          <AccordionContent className="space-y-4">
            <div className="rounded-lg border bg-card p-4 text-sm">
              <span className="font-medium">Target proficiency:</span> {skill.target_proficiency}
            </div>
            {skill.tasks.map((task) => (
              <TaskBlock
                key={task.id}
                task={task}
                progress={progress}
                pendingTarget={pendingTarget}
                onUpdateSubtask={onUpdateSubtask}
              />
            ))}
          </AccordionContent>
        </AccordionItem>
      ))}
    </Accordion>
  );
}

function TaskBlock({
  task,
  progress,
  pendingTarget,
  onUpdateSubtask
}: {
  task: TaskResponse;
  progress: ProgressSummaryResponse | null;
  pendingTarget: string | null;
  onUpdateSubtask: (subtask: SubtaskResponse, status: ProgressStatus) => Promise<void>;
}) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="break-words font-semibold">{task.title}</h3>
            <Badge variant="outline">{sentenceCase(task.difficulty)}</Badge>
            <Badge variant="secondary">{formatHours(task.estimated_hours)}</Badge>
          </div>
          <p className="mt-2 break-words text-sm text-muted-foreground">{task.description}</p>
        </div>
      </div>
      {task.learning_outcomes.length > 0 ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {task.learning_outcomes.map((outcome) => (
            <Badge key={outcome} variant="outline">
              {outcome}
            </Badge>
          ))}
        </div>
      ) : null}
      <div className="mt-4 space-y-3">
        {task.subtasks.map((subtask) => {
          const status = statusFromProgress(progress, subtask.id);
          const isCompleted = status === "completed";
          return (
            <div
              key={subtask.id}
              className="flex flex-col gap-3 rounded-lg border bg-background p-4 md:flex-row md:items-center md:justify-between"
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                <p className="break-words font-medium">{subtask.title}</p>
                  <Badge variant={isCompleted ? "success" : status === "in_progress" ? "warning" : "secondary"}>
                    {sentenceCase(status)}
                  </Badge>
                  <Badge variant="outline">{formatHours(subtask.estimated_hours)}</Badge>
                </div>
                <p className="mt-1 break-words text-sm text-muted-foreground">{subtask.description}</p>
                <p className="mt-2 break-words text-xs text-muted-foreground">
                  Completion: {subtask.completion_criteria}
                </p>
              </div>
              <Button
                type="button"
                variant={isCompleted ? "outline" : "default"}
                disabled={pendingTarget === subtask.id}
                className="shrink-0"
                onClick={() => onUpdateSubtask(subtask, isCompleted ? "pending" : "completed")}
              >
                {pendingTarget === subtask.id ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                ) : isCompleted ? (
                  <RotateCcw className="h-4 w-4" aria-hidden="true" />
                ) : (
                  <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                )}
                {isCompleted ? "Reopen" : "Complete"}
              </Button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
