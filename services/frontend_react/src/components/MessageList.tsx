import { useState } from 'react';
import { useMessages } from '../hooks/useMessages';
import MessageItem from './MessageItem';

export default function MessageList() {
  const [page, setPage] = useState(1);
  const pageSize = 20;
  
  const { data, isLoading, isError, error } = useMessages(page, pageSize);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-200 rounded-lg p-6 mb-6">
        <h3 className="font-semibold mb-2">⚠️ Error Loading Messages</h3>
        <p className="text-sm">{error instanceof Error ? error.message : 'Failed to load messages'}</p>
      </div>
    );
  }

  if (!data || data.messages.length === 0) {
    return (
      <div className="bg-gray-100 dark:bg-gray-800 rounded-lg p-12 text-center">
        <p className="text-gray-600 dark:text-gray-400 text-lg">
          📭 No messages yet. Be the first to post!
        </p>
      </div>
    );
  }

  const totalPages = Math.ceil(data.total / pageSize);

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-800 dark:text-white mb-2">
          💬 Messages ({data.total})
        </h2>
        <p className="text-gray-600 dark:text-gray-400">
          Page {page} of {totalPages}
        </p>
      </div>

      <div className="space-y-4 mb-6">
        {data.messages.map((message) => (
          <MessageItem key={message.id} message={message} />
        ))}
      </div>

      {totalPages > 1 && (
        <div className="flex justify-center gap-2">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-white rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            ← Previous
          </button>
          
          <span className="px-4 py-2 bg-white dark:bg-gray-800 rounded-lg text-gray-800 dark:text-white">
            {page} / {totalPages}
          </span>
          
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-white rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
