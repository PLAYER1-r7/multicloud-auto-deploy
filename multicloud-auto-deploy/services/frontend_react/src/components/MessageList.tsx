import { useState } from 'react';
import { usePosts } from '../hooks/useMessages';
import PostItem from './MessageItem';

export default function PostList() {
  const [nextToken, setNextToken] = useState<string | null>(null);
  const [prevTokens, setPrevTokens] = useState<(string | null)[]>([]);
  const [tagFilter, setTagFilter] = useState('');
  const limit = 20;

  const { data, isLoading, isError, error } = usePosts(
    limit,
    nextToken,
    tagFilter || null,
  );

  const handleNext = () => {
    if (data?.nextToken) {
      setPrevTokens((p) => [...p, nextToken]);
      setNextToken(data.nextToken ?? null);
    }
  };

  const handlePrev = () => {
    const tokens = [...prevTokens];
    const prev = tokens.pop() ?? null;
    setPrevTokens(tokens);
    setNextToken(prev);
  };

  const hasPrev = prevTokens.length > 0;
  const hasNext = !!data?.nextToken;

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
        <h3 className="font-semibold mb-2">⚠️ 投稿の読み込みエラー</h3>
        <p className="text-sm">{error instanceof Error ? error.message : '投稿の読み込みに失敗しました'}</p>
      </div>
    );
  }

  const posts = data?.items ?? [];

  return (
    <div>
      {/* タグフィルター */}
      <div className="mb-6 flex gap-2">
        <input
          type="text"
          value={tagFilter}
          onChange={(e) => { setTagFilter(e.target.value); setNextToken(null); setPrevTokens([]); }}
          placeholder="タグで絞り込み..."
          className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        {tagFilter && (
          <button
            onClick={() => { setTagFilter(''); setNextToken(null); setPrevTokens([]); }}
            className="px-3 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
          >
            クリア
          </button>
        )}
      </div>

      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-800 dark:text-white mb-2">
          💬 投稿一覧 ({data?.total ?? 0})
        </h2>
      </div>

      {posts.length === 0 ? (
        <div className="bg-gray-100 dark:bg-gray-800 rounded-lg p-12 text-center">
          <p className="text-gray-600 dark:text-gray-400 text-lg">
            📫 まだ投稿がありません。最初の投稿者になりましょう！
          </p>
        </div>
      ) : (
        <div className="space-y-4 mb-6">
          {posts.map((post) => (
            <PostItem key={post.postId} post={post} />
          ))}
        </div>
      )}

      {(hasPrev || hasNext) && (
        <div className="flex justify-center gap-2">
          <button
            onClick={handlePrev}
            disabled={!hasPrev}
            className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-white rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            ← 前のページ
          </button>
          <button
            onClick={handleNext}
            disabled={!hasNext}
            className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-white rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            次のページ →
          </button>
        </div>
      )}
    </div>
  );
}
