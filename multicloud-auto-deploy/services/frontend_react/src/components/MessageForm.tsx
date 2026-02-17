import { useState } from 'react';
import { useCreateMessage } from '../hooks/useMessages';

export default function MessageForm() {
  const [content, setContent] = useState('');
  const [author, setAuthor] = useState('');
  const createMessage = useCreateMessage();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!content.trim() || !author.trim()) {
      return;
    }

    try {
      await createMessage.mutateAsync({
        content: content.trim(),
        author: author.trim(),
      });
      
      // Clear form after successful submission
      setContent('');
      setAuthor('');
    } catch (error) {
      console.error('Failed to create message:', error);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
      <h2 className="text-2xl font-bold mb-4 text-gray-800 dark:text-white">
        📝 Post a Message
      </h2>
      
      <div className="mb-4">
        <label htmlFor="author" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Your Name
        </label>
        <input
          type="text"
          id="author"
          value={author}
          onChange={(e) => setAuthor(e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
          placeholder="Enter your name"
          required
        />
      </div>

      <div className="mb-4">
        <label htmlFor="content" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Message
        </label>
        <textarea
          id="content"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={4}
          className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white resize-none"
          placeholder="What's on your mind?"
          required
        />
      </div>

      <button
        type="submit"
        disabled={createMessage.isPending || !content.trim() || !author.trim()}
        className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {createMessage.isPending ? '📤 Posting...' : '✉️ Post Message'}
      </button>

      {createMessage.isError && (
        <div className="mt-4 p-3 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-200 rounded-lg">
          Failed to post message. Please try again.
        </div>
      )}
    </form>
  );
}
