"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useTranslations, useLocale } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { useUserProgress } from "@/hooks/useAchievements";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { SkeletonCard } from "@/components/ui/Skeleton";
import {
  getChatSuggestions,
  clearConversation,
  sendChatMessageStream,
  getToolDisplayName,
} from "@/lib/api-client";
import { clsx } from "clsx";

// Constants
const REQUIRED_LEVEL = 8;

// Types for chat messages
interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  dataSources?: string[];
  intent?: string;
  // Error handling
  isError?: boolean;
  errorType?: string;
}

// Streaming state for showing status messages
interface StreamingState {
  isStreaming: boolean;
  statusMessage: string;
  activeTools: string[];
  content: string;
}

// Message Bubble Components
function UserMessage({ content }: { content: string }) {
  return (
    <div className="flex justify-end animate-slideUp">
      <div className="max-w-[85%] sm:max-w-[75%]">
        <div className="bg-teal-600 text-white rounded-2xl rounded-br-md px-4 py-3 shadow-md">
          <p className="text-sm sm:text-base whitespace-pre-wrap">{content}</p>
        </div>
      </div>
    </div>
  );
}

function AssistantMessage({
  content,
  dataSources,
  isError,
  errorType,
  t,
}: {
  content: string;
  dataSources?: string[];
  isError?: boolean;
  errorType?: string;
  t: ReturnType<typeof useTranslations<"chat">>;
}) {
  return (
    <div className="flex justify-start animate-slideUp">
      <div className="max-w-[85%] sm:max-w-[75%]">
        <div className="flex items-start gap-3">
          {/* Avatar - different style for errors */}
          <div className={clsx(
            "shrink-0 w-8 h-8 rounded-full flex items-center justify-center shadow-md",
            isError
              ? "bg-gradient-to-br from-amber-500 to-amber-600"
              : "bg-gradient-to-br from-teal-500 to-teal-600"
          )}>
            {isError ? (
              <svg
                className="w-4 h-4 text-white"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            ) : (
              <svg
                className="w-4 h-4 text-white"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                />
              </svg>
            )}
          </div>
          {/* Message */}
          <div className="flex-1">
            <div className={clsx(
              "rounded-2xl rounded-tl-md px-4 py-3 shadow-md border",
              isError
                ? "bg-amber-900/30 text-amber-100 border-amber-700/50"
                : "bg-gray-800 text-gray-100 border-gray-700"
            )}>
              <p className="text-sm sm:text-base whitespace-pre-wrap">
                {content}
              </p>
              {/* Error hint for user to try again */}
              {isError && errorType && (
                <p className="text-xs text-amber-400/70 mt-2">
                  {t("errorHint")}
                </p>
              )}
            </div>
            {/* Data Sources */}
            {dataSources && dataSources.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {dataSources.map((source, idx) => (
                  <span
                    key={idx}
                    className="text-xs px-2 py-0.5 bg-gray-800/50 text-gray-500 rounded-full border border-gray-700"
                  >
                    {source}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Streaming assistant message with status updates
function StreamingAssistantMessage({
  streamingState,
  t,
}: {
  streamingState: StreamingState;
  t: ReturnType<typeof useTranslations<"chat">>;
}) {
  const { statusMessage, activeTools, content } = streamingState;

  return (
    <div className="flex justify-start animate-slideUp">
      <div className="max-w-[85%] sm:max-w-[75%]">
        <div className="flex items-start gap-3">
          {/* Avatar */}
          <div className="shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-teal-500 to-teal-600 flex items-center justify-center shadow-md">
            <svg
              className="w-4 h-4 text-white"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
              />
            </svg>
          </div>
          {/* Message */}
          <div className="flex-1">
            <div className="bg-gray-800 text-gray-100 rounded-2xl rounded-tl-md px-4 py-3 shadow-md border border-gray-700">
              {/* Status message with spinner */}
              {!content && (
                <div className="flex items-center gap-2 mb-2">
                  <LoadingSpinner size="sm" />
                  <span className="text-teal-400 text-sm font-medium">
                    {statusMessage || t("thinking")}
                  </span>
                </div>
              )}

              {/* Active tools being used */}
              {activeTools.length > 0 && !content && (
                <div className="flex flex-wrap gap-1.5 mb-2">
                  {activeTools.map((tool, idx) => (
                    <span
                      key={idx}
                      className="inline-flex items-center gap-1 text-xs px-2 py-0.5 bg-teal-600/20 text-teal-400 rounded-full border border-teal-600/30 animate-pulse"
                    >
                      <svg
                        className="w-3 h-3"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                        />
                      </svg>
                      {getToolDisplayName(tool)}
                    </span>
                  ))}
                </div>
              )}

              {/* Streamed content */}
              {content && (
                <p className="text-sm sm:text-base whitespace-pre-wrap">
                  {content}
                  <span className="inline-block w-1 h-4 bg-teal-500 animate-pulse ml-0.5" />
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Suggested Questions Component
function SuggestedQuestions({
  questions,
  onSelect,
  isLoading,
  t,
}: {
  questions: string[];
  onSelect: (question: string) => void;
  isLoading: boolean;
  t: ReturnType<typeof useTranslations<"chat">>;
}) {
  return (
    <div className="space-y-4 animate-fadeIn">
      {/* Empty state illustration */}
      <div className="text-center py-8">
        <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gradient-to-br from-teal-500/20 to-teal-600/20 mb-4">
          <svg
            className="w-10 h-10 text-teal-500"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
            />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-gray-200 mb-2">
          {t("emptyTitle")}
        </h3>
        <p className="text-gray-400 text-sm max-w-md mx-auto">
          {t("emptyDescription")}
        </p>
      </div>

      {/* Suggested questions */}
      <div className="space-y-2">
        <p className="text-sm text-gray-500 font-medium">{t("suggestions")}</p>
        <div className="grid gap-2 sm:grid-cols-2">
          {isLoading ? (
            <>
              <div className="h-12 skeleton rounded-lg" />
              <div className="h-12 skeleton rounded-lg" />
              <div className="h-12 skeleton rounded-lg" />
              <div className="h-12 skeleton rounded-lg" />
            </>
          ) : (
            questions.map((question, idx) => (
              <button
                key={idx}
                onClick={() => onSelect(question)}
                className="text-left p-3 rounded-lg bg-gray-800/50 border border-gray-700 text-gray-300 text-sm hover:bg-gray-800 hover:border-teal-600/50 hover:text-gray-100 transition-all group"
              >
                <div className="flex items-center gap-2">
                  <span className="text-teal-500 group-hover:text-teal-400">
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                  </span>
                  <span className="flex-1">{question}</span>
                </div>
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

// Locked Feature Component
function LockedFeature({
  currentLevel,
  requiredLevel,
  t,
}: {
  currentLevel: number;
  requiredLevel: number;
  t: ReturnType<typeof useTranslations<"chat">>;
}) {
  const levelsToGo = requiredLevel - currentLevel;
  const progressPercent = (currentLevel / requiredLevel) * 100;

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <Card className="max-w-md w-full text-center p-8 animate-fadeIn">
        {/* Lock Icon */}
        <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gray-800 mb-6">
          <svg
            className="w-10 h-10 text-gray-500"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z"
              clipRule="evenodd"
            />
          </svg>
        </div>

        <h2 className="text-xl font-bold text-gray-100 mb-2">{t("locked")}</h2>
        <p className="text-gray-400 mb-6">
          {t("lockedDescription", { level: requiredLevel })}
        </p>

        {/* Progress */}
        <div className="space-y-3">
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">{t("currentLevel")}</span>
            <span className="text-teal-400 font-semibold">{currentLevel}</span>
          </div>
          <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-teal-600 to-teal-400 transition-all duration-500"
              style={{ width: `${Math.min(progressPercent, 100)}%` }}
            />
          </div>
          <p className="text-sm text-gray-500">
            {levelsToGo} {levelsToGo === 1 ? t("levelToGo") : t("levelsToGo")}
          </p>
        </div>
      </Card>
    </div>
  );
}

// Main Chat Page Component
export default function ChatPage() {
  const t = useTranslations("chat");
  const locale = useLocale();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [conversationId, setConversationId] = useState<string | undefined>();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const abortControllerRef = useRef<(() => void) | null>(null);

  // Streaming state
  const [streamingState, setStreamingState] = useState<StreamingState>({
    isStreaming: false,
    statusMessage: "",
    activeTools: [],
    content: "",
  });

  // Track tools used during the current streaming session
  const toolsUsedRef = useRef<string[]>([]);

  // Get user progress for level gating
  const { data: userProgress, isLoading: progressLoading } = useUserProgress();
  const currentLevel = userProgress?.level.level ?? 1;
  const isUnlocked = currentLevel >= REQUIRED_LEVEL;

  // Fetch suggested questions
  const {
    data: suggestionsData,
    isLoading: suggestionsLoading,
  } = useQuery({
    queryKey: ["chatSuggestions"],
    queryFn: getChatSuggestions,
    enabled: isUnlocked,
    staleTime: 10 * 60 * 1000, // 10 minutes
  });

  // Scroll to bottom when messages or streaming state changes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingState.content]);

  // Handle send message with streaming
  const handleSendMessage = useCallback(
    (messageText?: string) => {
      const text = (messageText || inputValue).trim();
      if (!text || streamingState.isStreaming) return;

      // Add user message
      const userMessage: ChatMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content: text,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setInputValue("");

      // Reset streaming state
      setStreamingState({
        isStreaming: true,
        statusMessage: t("thinking"),
        activeTools: [],
        content: "",
      });
      toolsUsedRef.current = [];

      // Start streaming
      const abort = sendChatMessageStream(
        {
          message: text,
          conversation_id: conversationId,
          language: locale,
        },
        {
          onStatus: (message) => {
            setStreamingState((prev) => ({
              ...prev,
              statusMessage: message,
            }));
          },
          onToolStart: (tool, message) => {
            toolsUsedRef.current.push(tool);
            setStreamingState((prev) => ({
              ...prev,
              statusMessage: message,
              activeTools: [...prev.activeTools, tool],
            }));
          },
          onToolEnd: (tool) => {
            setStreamingState((prev) => ({
              ...prev,
              activeTools: prev.activeTools.filter((t) => t !== tool),
            }));
          },
          onToken: (token) => {
            setStreamingState((prev) => ({
              ...prev,
              content: prev.content + token,
              statusMessage: "", // Clear status when content starts
            }));
          },
          onDone: (toolsUsed) => {
            // Finalize the message
            setStreamingState((prev) => {
              // Add the complete message
              const assistantMessage: ChatMessage = {
                id: `assistant-${Date.now()}`,
                role: "assistant",
                content: prev.content,
                timestamp: new Date(),
                dataSources: toolsUsed.map(getToolDisplayName),
              };
              setMessages((msgs) => [...msgs, assistantMessage]);

              return {
                isStreaming: false,
                statusMessage: "",
                activeTools: [],
                content: "",
              };
            });
          },
          onError: (error, errorMessage) => {
            console.error("Chat streaming error:", error, errorMessage);

            // Map backend error types to translation keys
            const errorTypeMap: Record<string, string> = {
              rate_limited: "errorRateLimited",
              quota_exceeded: "errorQuotaExceeded",
              ai_unavailable: "errorAiUnavailable",
              no_training_data: "errorNoData",
              context_error: "errorContext",
              tool_failure: "errorToolFailure",
              network_error: "errorNetwork",
              unknown: "errorMessage",
            };

            // Get the error type from the backend error string (which is error_type) or default to network_error
            const errorType = error && errorTypeMap[error] ? error : "network_error";
            const translationKey = errorTypeMap[errorType] || "errorMessage";

            // Use the message from the backend if provided, otherwise use the translation
            const displayMessage = errorMessage || t(translationKey as keyof typeof errorTypeMap);

            const chatErrorMessage: ChatMessage = {
              id: `error-${Date.now()}`,
              role: "assistant",
              content: displayMessage,
              timestamp: new Date(),
              isError: true,
              errorType: errorType,
            };
            setMessages((prev) => [...prev, chatErrorMessage]);
            setStreamingState({
              isStreaming: false,
              statusMessage: "",
              activeTools: [],
              content: "",
            });
          },
        }
      );

      abortControllerRef.current = abort;
    },
    [inputValue, conversationId, locale, streamingState.isStreaming, t]
  );

  // Handle new conversation
  const handleNewConversation = useCallback(() => {
    setMessages([]);
    setConversationId(undefined);
    if (conversationId) {
      clearConversation(conversationId).catch(console.error);
    }
  }, [conversationId]);

  // Handle key press
  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Auto-resize textarea
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value);
    // Reset height to auto to get the correct scrollHeight
    e.target.style.height = "auto";
    // Set to scrollHeight but cap at max height
    e.target.style.height = `${Math.min(e.target.scrollHeight, 150)}px`;
  };

  // Loading state
  if (progressLoading) {
    return (
      <div className="space-y-6">
        <div className="animate-fadeIn">
          <div className="h-8 w-48 skeleton rounded mb-2" />
          <div className="h-5 w-64 skeleton rounded" />
        </div>
        <SkeletonCard />
      </div>
    );
  }

  // Locked state
  if (!isUnlocked) {
    return (
      <div className="space-y-4 sm:space-y-6">
        {/* Header */}
        <div className="animate-fadeIn">
          <h1 className="text-xl sm:text-2xl font-bold text-gray-100">
            {t("title")}
          </h1>
          <p className="text-sm sm:text-base text-gray-400 mt-1">
            {t("subtitle")}
          </p>
        </div>

        <LockedFeature
          currentLevel={currentLevel}
          requiredLevel={REQUIRED_LEVEL}
          t={t}
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] sm:h-[calc(100vh-10rem)]">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 animate-fadeIn">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-100">
            {t("title")}
          </h1>
          <p className="text-sm sm:text-base text-gray-400 mt-1">
            {t("subtitle")}
          </p>
        </div>
        {messages.length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleNewConversation}
            leftIcon={
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 4v16m8-8H4"
                />
              </svg>
            }
          >
            {t("newConversation")}
          </Button>
        )}
      </div>

      {/* Chat Container */}
      <Card
        className="flex-1 flex flex-col overflow-hidden animate-slideUp"
        padding="none"
      >
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
          {messages.length === 0 ? (
            <SuggestedQuestions
              questions={suggestionsData?.questions ?? []}
              onSelect={(q) => handleSendMessage(q)}
              isLoading={suggestionsLoading}
              t={t}
            />
          ) : (
            <>
              {messages.map((message) =>
                message.role === "user" ? (
                  <UserMessage key={message.id} content={message.content} />
                ) : (
                  <AssistantMessage
                    key={message.id}
                    content={message.content}
                    dataSources={message.dataSources}
                    isError={message.isError}
                    errorType={message.errorType}
                    t={t}
                  />
                )
              )}
              {/* Streaming message with status updates */}
              {streamingState.isStreaming && (
                <StreamingAssistantMessage streamingState={streamingState} t={t} />
              )}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Input Area */}
        <div className="border-t border-gray-800 p-4 bg-gray-900/50">
          <div className="flex items-end gap-2 sm:gap-3">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={handleInputChange}
                onKeyDown={handleKeyPress}
                placeholder={t("placeholder")}
                disabled={streamingState.isStreaming}
                rows={1}
                className={clsx(
                  "w-full px-4 py-3 rounded-xl",
                  "bg-gray-800 text-gray-100 placeholder-gray-500",
                  "border border-gray-700 focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20",
                  "resize-none overflow-hidden",
                  "disabled:opacity-50 disabled:cursor-not-allowed",
                  "transition-colors focus:outline-none",
                  "text-sm sm:text-base"
                )}
                style={{ minHeight: "48px", maxHeight: "150px" }}
              />
            </div>
            <Button
              onClick={() => handleSendMessage()}
              disabled={!inputValue.trim() || streamingState.isStreaming}
              isLoading={streamingState.isStreaming}
              className="shrink-0"
              aria-label={t("send")}
            >
              <svg
                className="w-5 h-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                />
              </svg>
            </Button>
          </div>
          <p className="text-xs text-gray-500 mt-2 text-center">
            {t("disclaimer")}
          </p>
        </div>
      </Card>
    </div>
  );
}
