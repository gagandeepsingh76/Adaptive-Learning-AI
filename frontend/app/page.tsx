import {
  ArrowRight,
  Bot,
  CheckCircle2,
  Database,
  Gauge,
  Layers3,
  Map,
  MessageSquare,
  Rocket,
  Server,
  ShieldCheck,
  Sparkles,
  Target,
  TrendingUp
} from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const features = [
  {
    title: "Personalized roadmap generation",
    description:
      "Turns a goal, experience level, time budget, existing skills, and constraints into a sequenced learning plan.",
    icon: Map
  },
  {
    title: "Portfolio project recommendation",
    description:
      "Creates a buildable project with requirements, deliverables, acceptance criteria, effort, and skill coverage.",
    icon: Target
  },
  {
    title: "Roadmap-grounded RAG chat",
    description:
      "Answers questions from retrieved roadmap context and returns source cards for traceable learning support.",
    icon: MessageSquare
  },
  {
    title: "Progress intelligence",
    description:
      "Tracks completion, time spent, pending work, remaining effort, and learner momentum across the roadmap.",
    icon: TrendingUp
  }
];

const stack = [
  "Next.js",
  "React",
  "TypeScript",
  "FastAPI",
  "SQLModel",
  "ChromaDB",
  "Gemini",
  "Ruff",
  "MyPy",
  "Pytest"
];

const workflow = [
  "Define the learning goal",
  "Generate a structured roadmap",
  "Ask grounded questions",
  "Create a portfolio project",
  "Track progress to completion"
];

const architecture = [
  {
    title: "Typed product surface",
    description: "Next.js forms, validation helpers, API client retries, and local workflow state.",
    icon: Layers3
  },
  {
    title: "Service backend",
    description: "FastAPI routes delegate to focused services with SQL persistence and domain validation.",
    icon: Server
  },
  {
    title: "AI and retrieval layer",
    description: "Gemini generation, embeddings, prompt versions, Chroma retrieval, and citation assembly.",
    icon: Database
  }
];

export default function HomePage() {
  return (
    <div className="space-y-14 md:space-y-16">
      <section className="-mx-4 -mt-8 border-b bg-card md:-mx-8 md:-mt-10">
        <div className="mx-auto grid max-w-[1180px] gap-8 px-4 py-12 md:px-8 lg:grid-cols-[minmax(0,1fr)_minmax(320px,440px)] lg:items-center lg:py-16">
          <div className="min-w-0">
            <Badge className="mb-5 w-fit" variant="secondary">
              <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
              AI learning SaaS for roadmap-to-project execution
            </Badge>
            <h1 className="max-w-3xl text-4xl font-semibold leading-tight md:text-6xl">
              Adaptive Learning AI
            </h1>
            <p className="mt-5 max-w-2xl text-lg leading-8 text-muted-foreground md:text-xl">
              Generate a personalized learning roadmap, ask citation-backed questions, receive a
              portfolio project, and track progress in one production-ready AI workflow.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Button asChild size="lg">
                <Link href="/roadmap">
                  Generate roadmap
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link href="/settings">
                  Check system health
                  <Gauge className="h-4 w-4" aria-hidden="true" />
                </Link>
              </Button>
            </div>
          </div>

          <div className="min-w-0 rounded-lg border bg-background p-4 shadow-soft" aria-label="Product workflow preview">
            <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-semibold">Live product workflow</p>
                <p className="text-xs text-muted-foreground">
                  Roadmap, RAG chat, project, progress
                </p>
              </div>
              <Badge variant="success">Operational</Badge>
            </div>

            <div className="grid gap-3">
              {["Foundations", "Applied RAG", "Deployment"].map((item, index) => (
                <div key={item} className="rounded-md border bg-card p-3">
                  <div className="mb-2 flex items-center justify-between gap-3 text-xs">
                    <span className="font-medium">{item}</span>
                    <span className="text-muted-foreground">{(index + 1) * 28}%</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full rounded-full bg-primary"
                      style={{ width: `${(index + 1) * 28}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-3 rounded-md border bg-primary/10 p-3">
              <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
                <Bot className="h-4 w-4 text-primary" aria-hidden="true" />
                Grounded assistant
              </div>
              <p className="text-sm leading-6 text-muted-foreground">
                Start with chunking and retrieval evaluation, then move into answer synthesis with
                citations and progress-aware next steps.
              </p>
            </div>

            <div className="mt-3 grid grid-cols-2 gap-2 text-xs sm:grid-cols-4 lg:grid-cols-2">
              {["FastAPI", "ChromaDB", "Next.js", "Gemini"].map((item) => (
                <span key={item} className="rounded-md border bg-card p-2 font-medium">
                  {item}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="metric-grid">
        {[
          ["4", "AI-backed product flows"],
          ["Typed", "Frontend and backend contracts"],
          ["RAG", "Citation-based chat"],
          ["CI-ready", "Lint, type, and test commands"]
        ].map(([value, label]) => (
          <div key={label} className="rounded-lg border bg-card p-5 shadow-sm">
            <p className="text-2xl font-semibold">{value}</p>
            <p className="mt-1 text-sm text-muted-foreground">{label}</p>
          </div>
        ))}
      </section>

      <section className="grid gap-5 md:grid-cols-[minmax(0,1.2fr)_minmax(260px,0.8fr)] md:items-start">
        <div>
          <h2 className="text-3xl font-semibold">Built for an end-to-end demo</h2>
          <p className="mt-3 max-w-3xl leading-7 text-muted-foreground">
            The product connects goal intake, structured AI generation, persistence, retrieval,
            project recommendation, and progress tracking into a single flow that is easy to
            evaluate and hard to mistake for a prototype shell.
          </p>
        </div>
        <div className="rounded-lg border bg-card p-5">
          <div className="flex items-center gap-3">
            <ShieldCheck className="h-5 w-5 text-primary" aria-hidden="true" />
            <p className="font-semibold">Production posture</p>
          </div>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Health probes, request IDs, strict validation, typed responses, provider diagnostics,
            documented deployment paths, and focused verification commands are included.
          </p>
        </div>
      </section>

      <section>
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <h2 className="text-3xl font-semibold">Feature Set</h2>
            <p className="mt-2 max-w-2xl text-muted-foreground">
              Each page is part of the same learning workflow, not a disconnected demo screen.
            </p>
          </div>
        </div>
        <div className="surface-grid mt-5">
          {features.map((feature) => {
            const Icon = feature.icon;
            return (
              <Card key={feature.title}>
                <CardHeader>
                  <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-secondary">
                    <Icon className="h-5 w-5 text-primary" aria-hidden="true" />
                  </div>
                  <CardTitle className="text-xl leading-7">{feature.title}</CardTitle>
                  <CardDescription>{feature.description}</CardDescription>
                </CardHeader>
              </Card>
            );
          })}
        </div>
      </section>

      <section>
        <h2 className="text-3xl font-semibold">Architecture</h2>
        <div className="mt-5 grid gap-4 lg:grid-cols-3">
          {architecture.map((item) => {
            const Icon = item.icon;
            return (
              <div key={item.title} className="rounded-lg border bg-card p-5">
                <div className="mb-3 flex items-center gap-2">
                  <Icon className="h-5 w-5 text-primary" aria-hidden="true" />
                  <h3 className="font-semibold">{item.title}</h3>
                </div>
                <p className="text-sm leading-6 text-muted-foreground">{item.description}</p>
              </div>
            );
          })}
        </div>
      </section>

      <section className="grid gap-6 md:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]">
        <div>
          <h2 className="text-3xl font-semibold">Workflow</h2>
          <p className="mt-3 leading-7 text-muted-foreground">
            The demo path is short enough for review, but deep enough to show architecture,
            retrieval, AI generation, and UX polish working together.
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {workflow.map((step, index) => (
            <div key={step} className="rounded-lg border bg-card p-4">
              <div className="mb-3 flex h-8 w-8 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
                {index + 1}
              </div>
              <p className="text-sm font-medium">{step}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="grid gap-5 md:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)] md:items-start">
        <div>
          <h2 className="text-3xl font-semibold">Technology Stack</h2>
          <p className="mt-3 leading-7 text-muted-foreground">
            Familiar tools, strict contracts, and replaceable AI infrastructure keep the product
            credible for both frontend and backend review.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {stack.map((item) => (
            <Badge key={item} variant="outline" className="px-3 py-1">
              {item}
            </Badge>
          ))}
        </div>
      </section>

      <section className="rounded-lg border bg-primary p-6 text-primary-foreground md:p-7">
        <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="mb-2 flex items-center gap-2 text-sm font-medium text-primary-foreground/85">
              <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
              Ready for the full product flow
            </div>
            <h2 className="text-2xl font-semibold">Start with a roadmap, then evaluate the AI loop.</h2>
            <p className="mt-2 max-w-2xl text-primary-foreground/85">
              Move through roadmap generation, project recommendation, grounded chat, progress, and
              system health from the same navigation.
            </p>
          </div>
          <Button asChild size="lg" variant="secondary">
            <Link href="/roadmap">
              Begin demo flow
              <Rocket className="h-4 w-4" aria-hidden="true" />
            </Link>
          </Button>
        </div>
      </section>
    </div>
  );
}
