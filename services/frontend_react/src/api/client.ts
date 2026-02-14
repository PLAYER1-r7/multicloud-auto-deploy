import axios from 'axios';
import type { Message, MessagesResponse, CreateMessageInput, UpdateMessageInput } from '../types/message';

// Get API URL from environment variable or use staging as default
const API_URL = import.meta.env.VITE_API_URL || 'https://mcad-staging-api-son5b3ml7a-an.a.run.app';

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

export const messagesApi = {
  // Get all messages with pagination
  async getMessages(page: number = 1, pageSize: number = 20): Promise<MessagesResponse> {
    const response = await apiClient.get<MessagesResponse>('/api/messages/', {
      params: { page, page_size: pageSize },
    });
    return response.data;
  },

  // Get a single message by ID
  async getMessage(id: string): Promise<Message> {
    const response = await apiClient.get<Message>(`/api/messages/${id}`);
    return response.data;
  },

  // Create a new message
  async createMessage(data: CreateMessageInput): Promise<Message> {
    const response = await apiClient.post<Message>('/api/messages/', data);
    return response.data;
  },

  // Update an existing message
  async updateMessage(id: string, data: UpdateMessageInput): Promise<Message> {
    const response = await apiClient.put<Message>(`/api/messages/${id}`, data);
    return response.data;
  },

  // Delete a message
  async deleteMessage(id: string): Promise<void> {
    await apiClient.delete(`/api/messages/${id}`);
  },
};

export default apiClient;
