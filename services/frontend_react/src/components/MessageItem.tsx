import { useState } from 'react';
import type { Message } from '../types/message';
import { useUpdateMessage, useDeleteMessage } from '../hooks/useMessages';

interface MessageItemProps {
  message: Message;
}

export default function MessageItem({ message }: MessageItemProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(message.content);
  const [editAuthor, setEditAuthor] = useState(message.author);
  
  const updateMessage = useUpdateMessage();
  const deleteMessage = useDeleteMessage();

  const handleUpdate = async () => {
    if (!editContent.trim() || !editAuthor.trim()) {
      return;
    }

    try {
      await updateMessage.mutateAsync({
        id: message.id,
        data: {
          content: editContent.trim(),
          author: editAuthor.trim(),
        },
      });
      setIsEditing(false);
    } catch (error) {
      console.error('Failed to update message:', error);
    }
  };

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this message?')) {
      return;
    }

    try {
      await deleteMessage.mutateAsync(message.id);
    } catch (error) {
      console.error('Failed to delete message:', error);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  if (isEditing) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-4">
        <div className="mb-3">
          <input
            type="text"
            value={editAuthor}
            onChange={(e) => setEditAuthor(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-white mb-2"
            placeholder="Author"
          />
          <textarea
            value={editContent}
            onChange={(e) => setEditContent(e.target.value)}
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-white resize-none"
            placeholder="Content"
          />
        </div>
        
        <div className="flex gap-2">
          <button
            onClick={handleUpdate}
            disabled={updateMessage.isPending}
            className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors disabled:opacity-50"
          >
            {updateMessage.isPending ? 'Saving...' : '💾 Save'}
          </button>
          <button
            onClick={() => {
              setIsEditing(false);
              setEditContent(message.content);
              setEditAuthor(message.author);
            }}
            className="px-4 py-2 bg-gray-500 hover:bg-gray-600 text-white rounded-lg transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-4 hover:shadow-lg transition-shadow">
      <div className="flex justify-between items-start mb-3">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-white mb-1">
            {message.author}
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {formatDate(message.created_at)}
          </p>
        </div>
        
        <div className="flex gap-2">
          <button
            onClick={() => setIsEditing(true)}
            className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 transition-colors"
            title="Edit"
          >
            ✏️
          </button>
          <button
            onClick={handleDelete}
            disabled={deleteMessage.isPending}
            className="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300 transition-colors disabled:opacity-50"
            title="Delete"
          >
            🗑️
          </button>
        </div>
      </div>

      <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap break-words">
        {message.content}
      </p>

      {message.image_url && (
        <div className="mt-4">
          <img
            src={message.image_url}
            alt="Message attachment"
            className="rounded-lg max-w-full h-auto"
          />
        </div>
      )}

      {message.updated_at && message.updated_at !== message.created_at && (
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-3">
          Edited: {formatDate(message.updated_at)}
        </p>
      )}
    </div>
  );
}
