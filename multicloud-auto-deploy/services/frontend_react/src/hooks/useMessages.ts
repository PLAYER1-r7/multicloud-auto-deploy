import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { messagesApi } from '../api/client';
import type { CreateMessageInput, UpdateMessageInput } from '../types/message';

// Query keys
const MESSAGES_KEY = ['messages'] as const;

// Hook to get all messages
export function useMessages(page: number = 1, pageSize: number = 20) {
  return useQuery({
    queryKey: [...MESSAGES_KEY, page, pageSize],
    queryFn: () => messagesApi.getMessages(page, pageSize),
    staleTime: 30000, // 30 seconds
  });
}

// Hook to get a single message
export function useMessage(id: string) {
  return useQuery({
    queryKey: [...MESSAGES_KEY, id],
    queryFn: () => messagesApi.getMessage(id),
    enabled: !!id,
  });
}

// Hook to create a message
export function useCreateMessage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateMessageInput) => messagesApi.createMessage(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: MESSAGES_KEY });
    },
  });
}

// Hook to update a message
export function useUpdateMessage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateMessageInput }) =>
      messagesApi.updateMessage(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: MESSAGES_KEY });
    },
  });
}

// Hook to delete a message
export function useDeleteMessage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => messagesApi.deleteMessage(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: MESSAGES_KEY });
    },
  });
}
