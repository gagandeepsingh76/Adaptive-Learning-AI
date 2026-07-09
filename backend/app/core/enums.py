"""String enums shared by persistence and transport layers."""

from enum import StrEnum


class ExperienceLevel(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class LearningStyle(StrEnum):
    VISUAL = "visual"
    READING = "reading"
    HANDS_ON = "hands_on"
    MIXED = "mixed"


class Difficulty(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class RoadmapStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class IndexStatus(StrEnum):
    PENDING = "pending"
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"


class ProjectStatus(StrEnum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ConversationStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ProcessingStatus(StrEnum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


class ProgressStatus(StrEnum):
    PENDING = "pending"
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class ProgressTargetType(StrEnum):
    ROADMAP = "roadmap"
    SKILL = "skill"
    TASK = "task"
    SUBTASK = "subtask"


class ResourceType(StrEnum):
    DOCUMENTATION = "documentation"
    ARTICLE = "article"
    VIDEO = "video"
    COURSE = "course"
    BOOK = "book"
    INTERACTIVE = "interactive"


class ResourceStatus(StrEnum):
    RECOMMENDED = "recommended"
    SAVED = "saved"
    COMPLETED = "completed"
    DISMISSED = "dismissed"


class PromptStatus(StrEnum):
    ACTIVE = "active"
    RETIRED = "retired"


class CacheNamespace(StrEnum):
    ROADMAP = "roadmap"
    PROJECT = "project"
    QUERY_EXPANSION = "query_expansion"
    FOLLOW_UP = "follow_up"


class EntityType(StrEnum):
    ROADMAP = "roadmap"
    SKILL = "skill"
    TASK = "task"
    SUBTASK = "subtask"
    PROJECT = "project"
    RESOURCE = "resource"
