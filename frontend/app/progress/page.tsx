"use client";

import {
  BarChart3,
  CheckCircle2,
  Clock,
  Loader2,
  Map,
  Timer,
  TrendingUp
} from "lucide-react";
import Link from "next/link";
import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { ApiErrorCard } from "@/components/shared/api-error-card";
import { useToast } from "@/components/shared/toast-provider";
import { useLatestRoadmap } from "@/hooks/use-latest-roadmap";
import { createApiClient } from "@/lib/api-client";
import { getApiDiagnostic } from "@/lib/api-diagnostics";
import { formatHours, sentenceCase, toNumber } from "@/lib/utils";
import type {
  ProgressSummaryResponse,
  RoadmapResponse,
  SkillResponse,
  SubtaskResponse,
  TaskResponse
} from "@/types/api";

function subtasksForTask(task: TaskResponse) {
  return task.subtasks;
}

function subtasksForSkill(skill: SkillResponse) {
  return skill.tasks.flatMap(subtasksForTask);
}

function allSubtasks(roadmap: RoadmapResponse) {
  return roadmap.skills.flatMap(subtasksForSkill);
}

function allTasks(roadmap: RoadmapResponse) {
  return roadmap.skills.flatMap((skill) => skill.tasks);
}

function isCompletedSubtask(progress: ProgressSummaryResponse | null, subtask: SubtaskResponse) {
  return progress?.records.some(
    (record) => record.target_id === subtask.id && record.status === "completed"
  );
}

function isCompletedTask(progress: ProgressSummaryResponse | null, task: TaskResponse) {
  const subtasks = subtasksForTask(task);
  return subtasks.length > 0 && subtasks.every((subtask) => isCompletedSubtask(progress, subtask));
}

function isCompletedSkill(progress: ProgressSummaryResponse | null, skill: SkillResponse) {
  const subtasks = subtasksForSkill(skill);
  return subtasks.length > 0 && subtasks.every((subtask) => isCompletedSubtask(progress, subtask));
}

function minutesToHours(minutes: number) {
  return `${Math.round((minutes / 60) * 10) / 10} hrs`;
}

export default function ProgressPage() {
  const { roadmap, roadmapId, isReady } = useLatestRoadmap();
  const { notify } = useToast();
  const [activeRoadmapId, setActiveRoadmapId] = React.useState("");
  const [progress, setProgress] = React.useState<ProgressSummaryResponse | null>(null);
  const [isLoading, setIsLoading] = React.useState(false);
  const [progressError, setProgressError] = React.useState<unknown>(null);

  React.useEffect(() => {
    if (roadmapId) {
      setActiveRoadmapId(roadmapId);
    }
  }, [roadmapId]);

  const loadProgress = React.useCallback(
    async (targetRoadmapId = activeRoadmapId, showToast = true) => {
      if (!targetRoadmapId) {
        notify({
          tone: "error",
          title: "Roadmap ID required",
          description: "Generate a roadmap or paste a roadmap ID before loading progress."
        });
        return;
      }
      setProgressError(null);
      setIsLoading(true);
      try {
        const summary = await createApiClient().getProgress(targetRoadmapId);
        setProgress(summary);
        if (showToast) {
          notify({
            tone: "success",
            title: "Progress loaded",
            description: `${Math.round(toNumber(summary.completion_percentage))}% complete.`
          });
        }
      } catch (error) {
        const diagnostic = getApiDiagnostic(
          error,
          "Progress load failed",
          "Progress could not be loaded. Please try again."
        );
        setProgressError(error);
        notify({ tone: "error", title: diagnostic.title, description: diagnostic.explanation });
      } finally {
        setIsLoading(false);
      }
    },
    [activeRoadmapId, notify]
  );

  React.useEffect(() => {
    if (roadmapId) {
      void loadProgress(roadmapId, false);
    }
  }, [loadProgress, roadmapId]);

  const summary = roadmap ? buildProgressSummary(roadmap, progress) : null;

  return (
    <div className="app-section">
      <div>
        <Badge variant="secondary" className="mb-3">
          <TrendingUp className="mr-1 h-3.5 w-3.5" aria-hidden="true" />
          Progress Tracking
        </Badge>
        <h1 className="text-3xl font-semibold md:text-4xl">Track learning completion</h1>
        <p className="mt-2 max-w-3xl text-muted-foreground">
          Monitor completion percentage, completed skills, pending work, time spent, and estimated
          effort remaining for the active roadmap.
        </p>
      </div>

      <Card>
        <CardContent className="grid gap-4 p-5 md:grid-cols-[1fr_auto] md:items-end">
          <div className="space-y-2">
            <Label htmlFor="roadmap_id">Roadmap ID</Label>
            <Input
              id="roadmap_id"
              value={activeRoadmapId}
              onChange={(event) => setActiveRoadmapId(event.target.value)}
              placeholder="Generate a roadmap first"
            />
          </div>
          <Button type="button" onClick={() => void loadProgress()} disabled={isLoading}>
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            ) : (
              <BarChart3 className="h-4 w-4" aria-hidden="true" />
            )}
            Load progress
          </Button>
        </CardContent>
      </Card>

      {progressError ? (
        <ApiErrorCard
          error={progressError}
          title="Progress load failed"
          explanation="Progress could not be loaded. Please try again."
          onRetry={() => void loadProgress()}
        />
      ) : null}

      {!isReady ? null : roadmap && summary ? (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                <div>
                  <CardTitle className="text-2xl">{roadmap.goal_title}</CardTitle>
                  <CardDescription>
                    {summary.completedSubtasks} of {summary.totalSubtasks} subtasks completed.
                  </CardDescription>
                </div>
                <Badge variant={summary.completionPercentage === 100 ? "success" : "secondary"}>
                  {summary.completionPercentage}% complete
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-5">
              <Progress value={summary.completionPercentage} />
              <div className="metric-grid">
                <StatCard label="Completed skills" value={`${summary.completedSkills.length}`} icon={CheckCircle2} />
                <StatCard label="Pending skills" value={`${summary.pendingSkills.length}`} icon={Map} />
                <StatCard label="Time spent" value={minutesToHours(progress?.total_time_spent_minutes ?? 0)} icon={Timer} />
                <StatCard label="Time remaining" value={formatHours(summary.remainingHours)} icon={Clock} />
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-6 lg:grid-cols-2">
            <ListPanel title="Completed skills" items={summary.completedSkills.map((skill) => skill.title)} empty="No skills completed yet." tone="success" />
            <ListPanel title="Pending skills" items={summary.pendingSkills.map((skill) => skill.title)} empty="All skills are complete." tone="secondary" />
            <ListPanel title="Completed tasks" items={summary.completedTasks.map((task) => task.title)} empty="Complete subtasks to finish tasks." tone="success" />
            <LearningStats summary={summary} progress={progress} />
          </div>
        </div>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="text-xl">No roadmap available</CardTitle>
            <CardDescription>
              Generate a roadmap first, then return here to load progress and time estimates.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild>
              <Link href="/roadmap">
                <Map className="h-4 w-4" aria-hidden="true" />
                Create roadmap
              </Link>
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function buildProgressSummary(roadmap: RoadmapResponse, progress: ProgressSummaryResponse | null) {
  const tasks = allTasks(roadmap);
  const subtasks = allSubtasks(roadmap);
  const completedSubtasks = subtasks.filter((subtask) => isCompletedSubtask(progress, subtask));
  const completedSkills = roadmap.skills.filter((skill) => isCompletedSkill(progress, skill));
  const pendingSkills = roadmap.skills.filter((skill) => !isCompletedSkill(progress, skill));
  const completedTasks = tasks.filter((task) => isCompletedTask(progress, task));
  const remainingHours = subtasks
    .filter((subtask) => !isCompletedSubtask(progress, subtask))
    .reduce((total, subtask) => total + toNumber(subtask.estimated_hours), 0);
  return {
    totalTasks: tasks.length,
    totalSubtasks: subtasks.length,
    completedSubtasks: progress?.completed_subtasks ?? completedSubtasks.length,
    completionPercentage: Math.round(
      toNumber(
        progress?.completion_percentage ??
          (subtasks.length ? (completedSubtasks.length / subtasks.length) * 100 : 0)
      )
    ),
    completedSkills,
    pendingSkills,
    completedTasks,
    remainingHours
  };
}

function StatCard({
  label,
  value,
  icon: Icon
}: {
  label: string;
  value: string;
  icon: React.ElementType;
}) {
  return (
    <div className="rounded-lg border bg-background p-4">
      <div className="mb-3 flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{label}</p>
        <Icon className="h-4 w-4 text-primary" aria-hidden="true" />
      </div>
      <p className="text-2xl font-semibold">{value}</p>
    </div>
  );
}

function ListPanel({
  title,
  items,
  empty,
  tone
}: {
  title: string;
  items: string[];
  empty: string;
  tone: "success" | "secondary";
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {items.length ? (
          <div className="space-y-2">
            {items.map((item) => (
              <div key={item} className="flex items-center justify-between gap-3 rounded-lg border bg-background p-3">
                <span className="text-sm font-medium">{item}</span>
                <Badge variant={tone}>{tone === "success" ? "Complete" : "Pending"}</Badge>
              </div>
            ))}
          </div>
        ) : (
          <p className="rounded-lg border bg-background p-4 text-sm text-muted-foreground">{empty}</p>
        )}
      </CardContent>
    </Card>
  );
}

function LearningStats({
  summary,
  progress
}: {
  summary: ReturnType<typeof buildProgressSummary>;
  progress: ProgressSummaryResponse | null;
}) {
  const statusCounts = progress?.records.reduce<Record<string, number>>((counts, record) => {
    counts[record.status] = (counts[record.status] ?? 0) + 1;
    return counts;
  }, {});

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl">Learning statistics</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="rounded-lg border bg-background p-3">
            <p className="text-muted-foreground">Total tasks</p>
            <p className="mt-1 text-lg font-semibold">{summary.totalTasks}</p>
          </div>
          <div className="rounded-lg border bg-background p-3">
            <p className="text-muted-foreground">Total subtasks</p>
            <p className="mt-1 text-lg font-semibold">{summary.totalSubtasks}</p>
          </div>
        </div>
        <div className="space-y-2">
          {["pending", "in_progress", "completed"].map((status) => (
            <div key={status} className="flex items-center justify-between rounded-lg border bg-background p-3">
              <span className="text-sm">{sentenceCase(status)}</span>
              <Badge variant={status === "completed" ? "success" : status === "in_progress" ? "warning" : "secondary"}>
                {statusCounts?.[status] ?? 0}
              </Badge>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
