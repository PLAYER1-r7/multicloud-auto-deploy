export interface Message {
  id: string;
  content: string;
  author: string;
  image_url?: string | null;
  created_at: string;
  updated_at?: string | null;
}

export interface MessagesResponse {
  messages: Message[];
  total: number;
  page: number;
  page_size: number;
}

export interface CreateMessageInput {
  content: string;
  author: string;
  image_url?: string | null;
}

export interface UpdateMessageInput {
  content?: string;
  author?: string;
  image_url?: string | null;
}
