import { useState } from 'react';
import type { Post } from '../types/message';
import { useUpdatePost, useDeletePost } from '../hooks/useMessages';

interface PostItemProps {
  post: Post;
}

export default function PostItem({ post }: PostItemProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(post.content);
  const [editTags, setEditTags] = useState((post.tags ?? []).join(', '));

  const updatePost = useUpdatePost();
  const deletePost = useDeletePost();

  const handleUpdate = async () => {
    if (!editContent.trim()) return;
    const tagList = editTags
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);
    try {
      await updatePost.mutateAsync({
        postId: post.postId,
        data: { content: editContent.trim(), tags: tagList },
      });
      setIsEditing(false);
    } catch (error) {
      console.error('Failed to update post:', error);
    }
  };

  const handleDelete = async () => {
    if (!confirm('この投稿を削除しますか？')) return;
    try {
      await deletePost.mutateAsync(post.postId);
    } catch (error) {
      console.error('Failed to delete post:', error);
    }
  };

  const formatDate = (dateString: string) =>
    new Date(dateString).toLocaleString('ja-JP');

  if (isEditing) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-4">
        <textarea
          value={editContent}
          onChange={(e) => setEditContent(e.target.value)}
          rows={3}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-white resize-none mb-2"
          placeholder="内容"
        />
        <input
          type="text"
          value={editTags}
          onChange={(e) => setEditTags(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-white mb-3"
          placeholder="タグ（カンマ区切り）"
        />
        <div className="flex gap-2">
          <button
            onClick={handleUpdate}
            disabled={updatePost.isPending}
            className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors disabled:opacity-50"
          >
            {updatePost.isPending ? '保存中...' : '💾 保存'}
          </button>
          <button
            onClick={() => {
              setIsEditing(false);
              setEditContent(post.content);
              setEditTags((post.tags ?? []).join(', '));
            }}
            className="px-4 py-2 bg-gray-500 hover:bg-gray-600 text-white rounded-lg transition-colors"
          >
            キャンセル
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
            {post.nickname ?? post.userId}
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {formatDate(post.createdAt)}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setIsEditing(true)}
            className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 transition-colors"
            title="編集"
          >
            ✏️
          </button>
          <button
            onClick={handleDelete}
            disabled={deletePost.isPending}
            className="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300 transition-colors disabled:opacity-50"
            title="削除"
          >
            🗑️
          </button>
        </div>
      </div>

      <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap break-words">
        {post.content}
      </p>

      {post.tags && post.tags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {post.tags.map((tag) => (
            <span
              key={tag}
              className="inline-block px-2 py-0.5 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 text-xs rounded-full"
            >
              #{tag}
            </span>
          ))}
        </div>
      )}

      {post.imageUrls && post.imageUrls.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {post.imageUrls.map((url, i) => (
            <img key={i} src={url} alt="添付画像" className="rounded-lg max-w-xs h-auto" />
          ))}
        </div>
      )}

      {post.updatedAt && post.updatedAt !== post.createdAt && (
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-3">
          編集済: {formatDate(post.updatedAt)}
        </p>
      )}
    </div>
  );
}