import { useState } from 'react';
import { useCreatePost } from '../hooks/useMessages';

export default function PostForm() {
  const [content, setContent] = useState('');
  const [tags, setTags] = useState('');
  const createPost = useCreatePost();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;

    const tagList = tags
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);

    try {
      await createPost.mutateAsync({
        content: content.trim(),
        tags: tagList,
        is_markdown: false,
      });
      setContent('');
      setTags('');
    } catch (error) {
      console.error('Failed to create post:', error);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
      <h2 className="text-2xl font-bold mb-4 text-gray-800 dark:text-white">
        📝 投稿する
      </h2>

      <div className="mb-4">
        <label htmlFor="content" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          内容
        </label>
        <textarea
          id="content"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={4}
          className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white resize-none"
          placeholder="今何を考えていますか？"
          required
        />
      </div>

      <div className="mb-4">
        <label htmlFor="tags" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          タグ（カンマ区切り）
        </label>
        <input
          type="text"
          id="tags"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
          placeholder="react, typescript, cloud"
        />
      </div>

      <button
        type="submit"
        disabled={createPost.isPending || !content.trim()}
        className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {createPost.isPending ? '📤 投稿中...' : '✉️ 投稿する'}
      </button>

      {createPost.isError && (
        <div className="mt-4 p-3 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-200 rounded-lg">
          投稿に失敗しました。もう一度お試しください。
        </div>
      )}
    </form>
  );
}
