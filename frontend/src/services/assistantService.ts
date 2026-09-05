import type {
  AssistantResponse,
  UserLocation,
} from "@/types/marine";

import { apiPost, endpoints } from "./apiClient";

interface QueryResponse {
  status: string;
  answer?: string;
  conversation_id?: string;
  [key: string]: unknown;
}

export async function queryAssistant(
  message: string,
  location: UserLocation,
  conversationId: string,
): Promise<AssistantResponse> {
  const response = await apiPost<QueryResponse>(
    endpoints.query,
    {
      query: message,
      latitude: location.latitude,
      longitude: location.longitude,
      conversation_id: conversationId,
    },
  );

  return {
    conversation_id:
      response.conversation_id ??
      conversationId,

    reply:
      response.answer ??
      "I couldn't generate an answer.",
  };
}

export function createConversationId() {
  return `conv_${Math.random()
    .toString(36)
    .slice(2, 10)}`;
}