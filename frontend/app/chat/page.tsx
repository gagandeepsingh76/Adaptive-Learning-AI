"use client";

import {
  AlertCircle,
  BookOpen,
  Bot,
  BrainCircuit,
  CheckCircle2,
  Loader2,
  MessageSquare,
  RefreshCcw,
  Send,
  Sparkles,
  User
} from "lucide-react";
import * as React from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ApiErrorCard } from "@/components/shared/api-error-card";
import { useToast } from "@/components/shared/toast-provider";
import { useLatestRoadmap } from "@/hooks/use-latest-roadmap";
import { createApiClient } from "@/lib/api-client";
import { getApiDiagnostic } from "@/lib/api-diagnostics";
import {
  getStoredChatMessages,
  getStoredConversationId,
  setStoredConversationId,
  storeChatMessages,
  type StoredChatMessage
} from "@/lib/storage";
import { sentenceCase } from "@/lib/utils";
import { chatFormSchema } from "@/lib/validation";
import type { CitationResponse } from "@/types/api";

function id() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export default function ChatPage() {
  const { roadmap, roadmapId } = useLatestRoadmap();
  const { notify } = useToast();
  const [messages, setMessages] = React.useState<StoredChatMessage[]>([]);
  const [conversationId, setConversationId] = React.useState<string | null>(null);
  const [question, setQuestion] = React.useState("");
  const [activeRoadmapId, setActiveRoadmapId] = React.useState("");
  const [errors, setErrors] = React.useState<Record<string, string>>({});
  const [isSending, setIsSending] = React.useState(false);
  const [chatError, setChatError] = React.useState<unknown>(null);
  const [lastFailedQuestion, setLastFailedQuestion] = React.useState("");
  const messagesEndRef = React.useRef<HTMLDivElement | null>(null);

  React.useEffect(() => {
    setMessages(getStoredChatMessages().filter((message) => message.status !== "loading"));
    setConversationId(getStoredConversationId());
  }, []);

  React.useEffect(() => {
    if (roadmapId) {
      setActiveRoadmapId(roadmapId);
    }
  }, [roadmapId]);

  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    storeChatMessages(messages.filter((message) => message.status !== "loading"));
  }, [messages]);

  async function sendQuestion(nextQuestion: string) {
    const parsed = chatFormSchema.safeParse({
      roadmap_id: activeRoadmapId,
      question: nextQuestion
    });
    if (!parsed.success) {
      const nextErrors: Record<string, string> = {};
      for (const issue of parsed.error.issues) {
        const key = issue.path[0]?.toString() ?? "form";
        nextErrors[key] = issue.message;
      }
      setErrors(nextErrors);
      setChatError(null);
      return;
    }

    setErrors({});
    setChatError(null);
    setIsSending(true);
    const userMessage: StoredChatMessage = {
      id: id(),
      role: "user",
      content: parsed.data.question,
      status: "sent"
    };
    const assistantMessage: StoredChatMessage = {
      id: id(),
      role: "assistant",
      content: "Retrieving roadmap context and drafting a grounded answer...",
      status: "loading"
    };
    setMessages((current) => [...current, userMessage, assistantMessage]);
    setQuestion("");

    try {
      const response = await createApiClient().chat({
        roadmap_id: parsed.data.roadmap_id,
        question: parsed.data.question,
        conversation_id: conversationId
      });
      setConversationId(response.conversation_id);
      setStoredConversationId(response.conversation_id);
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantMessage.id
            ? {
                ...message,
                content: response.answer,
                citations: response.citations,
                followUpQuestions: response.follow_up_questions,
                status: "sent"
              }
            : message
        )
      );
      notify({
        tone: "success",
        title: "RAG answer ready",
        description: `${response.citations.length} citations returned from retrieved context.`
      });
    } catch (error) {
      const diagnostic = getApiDiagnostic(
        error,
        "Chat request failed",
        "The chat request failed. Please try again."
      );
      const description = diagnostic.explanation;
      setChatError(error);
      setLastFailedQuestion(parsed.data.question);
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantMessage.id
            ? { ...message, content: description, status: "error" }
            : message
        )
      );
      notify({ tone: "error", title: diagnostic.title, description });
    } finally {
      setIsSending(false);
    }
  }

  function submitChat(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void sendQuestion(question);
  }

  const lastAssistant = [...messages].reverse().find((message) => message.role === "assistant");
  const suggestedQuestions = [
    ...(lastAssistant?.followUpQuestions ?? []),
    `What should I learn first for ${roadmap?.goal_title ?? "this roadmap"}?`,
    "Which tasks are most important for a portfolio demo?",
    "What mistakes should I avoid while following this roadmap?"
  ].slice(0, 5);

  return (
    <div className="app-section">
      <div>
        <Badge variant="secondary" className="mb-3">
          <MessageSquare className="mr-1 h-3.5 w-3.5" aria-hidden="true" />
          AI Chat
        </Badge>
        <h1 className="text-3xl font-semibold md:text-4xl">Ask roadmap-grounded questions</h1>
        <p className="mt-2 max-w-3xl text-muted-foreground">
          Answers come from retrieval over the generated roadmap hierarchy. Citation cards show
          which skills, tasks, or subtasks were used as context.
        </p>
      </div>

      <div className="grid min-w-0 gap-6 lg:grid-cols-[minmax(0,0.75fr)_minmax(0,1.25fr)]">
        <Card>
          <CardHeader>
            <CardTitle className="text-xl">Conversation controls</CardTitle>
            <CardDescription>
              Provide a roadmap ID, ask a question, and keep the conversation threaded for follow-up
              responses.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="rounded-lg border bg-background p-4">
              <div className="mb-2 flex items-center gap-2">
                <BrainCircuit className="h-4 w-4 text-primary" aria-hidden="true" />
                <p className="font-semibold">Retrieved context indicator</p>
              </div>
              <p className="text-sm text-muted-foreground">
                {lastAssistant?.citations?.length
                  ? `${lastAssistant.citations.length} citation cards are attached to the latest answer.`
                  : "No citations yet. Ask a question to retrieve roadmap context."}
              </p>
            </div>

            {chatError ? (
              <ApiErrorCard
                error={chatError}
                title="Chat request failed"
                explanation="The chat request failed. Please try again."
                onRetry={
                  lastFailedQuestion ? () => void sendQuestion(lastFailedQuestion) : undefined
                }
              />
            ) : null}

            <form className="space-y-4" onSubmit={submitChat}>
              <div className="space-y-2">
                <Label htmlFor="roadmap_id">Roadmap ID</Label>
                <Input
                  id="roadmap_id"
                  value={activeRoadmapId}
                  onChange={(event) => setActiveRoadmapId(event.target.value)}
                  placeholder="Generate a roadmap first"
                  aria-invalid={Boolean(errors.roadmap_id)}
                />
                {errors.roadmap_id ? <p className="text-sm text-destructive">{errors.roadmap_id}</p> : null}
                {!roadmapId ? (
                  <p className="text-sm text-muted-foreground">
                    No saved roadmap found.{" "}
                    <Link href="/roadmap" className="font-medium text-primary underline">
                      Generate one
                    </Link>{" "}
                    to unlock grounded chat.
                  </p>
                ) : null}
              </div>
              <div className="space-y-2">
                <Label htmlFor="question">Question</Label>
                <Textarea
                  id="question"
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  placeholder="Ask how to sequence a skill, unblock a task, or prepare for a demo"
                  aria-invalid={Boolean(errors.question)}
                />
                {errors.question ? <p className="text-sm text-destructive">{errors.question}</p> : null}
              </div>
              <Button type="submit" className="w-full" disabled={isSending}>
                {isSending ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                ) : (
                  <Send className="h-4 w-4" aria-hidden="true" />
                )}
                {isSending ? "Retrieving context" : "Send question"}
              </Button>
            </form>

            <div>
              <h2 className="mb-3 font-semibold">Suggested questions</h2>
              <div className="space-y-2">
                {suggestedQuestions.map((item) => (
                  <Button
                    key={item}
                    type="button"
                    variant="outline"
                    className="h-auto w-full justify-start whitespace-normal py-3 text-left"
                    disabled={isSending}
                    onClick={() => void sendQuestion(item)}
                  >
                    <Sparkles className="h-4 w-4 shrink-0" aria-hidden="true" />
                    {item}
                  </Button>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="min-h-[620px]">
          <CardHeader>
            <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <div>
                <CardTitle className="text-xl">Conversation history</CardTitle>
                <CardDescription>
                  {conversationId ? `Thread ${conversationId}` : "A thread starts after the first answer."}
                </CardDescription>
              </div>
              <Badge variant={lastAssistant?.citations?.length ? "success" : "secondary"}>
                {lastAssistant?.citations?.length ? "RAG context retrieved" : "Awaiting retrieval"}
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex max-h-[65vh] min-h-[440px] flex-col gap-4 overflow-y-auto rounded-lg border bg-background p-4">
              {messages.length === 0 ? (
                <div className="m-auto max-w-md text-center">
                  <Bot className="mx-auto mb-3 h-10 w-10 text-primary" aria-hidden="true" />
                  <h2 className="font-semibold">No messages yet</h2>
                  <p className="mt-2 text-sm text-muted-foreground">
                    Start with a suggested question or ask something specific about the generated
                    roadmap. The assistant will cite retrieved context when available.
                  </p>
                </div>
              ) : (
                messages.map((message, index) => {
                  const previousUser = [...messages.slice(0, index)]
                    .reverse()
                    .find((candidate) => candidate.role === "user");
                  return (
                    <MessageBubble
                      key={message.id}
                      message={message}
                      onRetry={
                        message.status === "error" && previousUser
                          ? () => void sendQuestion(previousUser.content)
                          : undefined
                      }
                    />
                  );
                })
              )}
              <div ref={messagesEndRef} />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function MessageBubble({
  message,
  onRetry
}: {
  message: StoredChatMessage;
  onRetry?: () => void;
}) {
  const isUser = message.role === "user";
  const Icon = isUser ? User : Bot;
  return (
    <div className={isUser ? "ml-auto max-w-[88%]" : "mr-auto max-w-[92%]"}>
      <div
        className={
          isUser
            ? "rounded-lg bg-primary p-4 text-primary-foreground"
            : "rounded-lg border bg-card p-4 text-card-foreground"
        }
      >
        <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
          <Icon className="h-4 w-4" aria-hidden="true" />
          {isUser ? "You" : "Adaptive Learning AI"}
          {message.status === "loading" ? (
            <Badge variant="secondary">
              <Loader2 className="mr-1 h-3 w-3 animate-spin" aria-hidden="true" />
              Typing
            </Badge>
          ) : null}
          {message.status === "error" ? (
            <Badge variant="warning">
              <AlertCircle className="mr-1 h-3 w-3" aria-hidden="true" />
              Recovery available
            </Badge>
          ) : null}
        </div>
        <p className="whitespace-pre-wrap break-words text-sm leading-6">{message.content}</p>
        {message.status === "error" && onRetry ? (
          <Button type="button" variant="outline" size="sm" className="mt-3" onClick={onRetry}>
            <RefreshCcw className="h-4 w-4" aria-hidden="true" />
            Retry
          </Button>
        ) : null}
      </div>
      {!isUser && message.citations?.length ? (
        <CitationCards citations={message.citations} />
      ) : null}
      {!isUser && message.followUpQuestions?.length ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {message.followUpQuestions.map((question) => (
            <Badge key={question} variant="outline">
              {question}
            </Badge>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function CitationCards({ citations }: { citations: CitationResponse[] }) {
  return (
    <div className="mt-3 grid gap-2 md:grid-cols-2">
      {citations.map((citation) => (
        <div key={`${citation.source_id}-${citation.entity_id}`} className="rounded-lg border bg-background p-3">
          <div className="mb-2 flex items-center justify-between gap-3">
            <Badge variant="secondary">
              <BookOpen className="mr-1 h-3 w-3" aria-hidden="true" />
              {sentenceCase(citation.entity_type)}
            </Badge>
            <span className="text-xs text-muted-foreground">
              {Math.round(citation.relevance * 100)}% relevant
            </span>
          </div>
          <p className="break-words text-xs text-muted-foreground">Source: {citation.source_id}</p>
          <p className="mt-1 break-words text-xs text-muted-foreground">Entity: {citation.entity_id}</p>
          <div className="mt-2 flex items-center gap-2 text-xs text-primary">
            <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
            Retrieved from roadmap context
          </div>
        </div>
      ))}
    </div>
  );
}
