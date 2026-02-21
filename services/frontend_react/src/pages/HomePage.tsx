import { useCallback, useEffect, useState } from 'react';
import { postsApi } from '../api/posts';
import type { Post } from '../types/message';
import { useAuth } from '../contexts/AuthContext';
import PostCard from '../components/PostCard';
import PostForm from '../components/PostForm';
import Alert from '../components/Alert';

export default function HomePage() {
  const { isLoggedIn } = useAuth();
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [nextToken, setNextToken] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);

  // Search / filter
  const [showSearch, setShowSearch] = useState(false);
  const [tagFilter, setTagFilter] = useState('');
  const [keyword, setKeyword] = useState('');
  const [appliedTag, setAppliedTag] = useState('');
  const [appliedKeyword, setAppliedKeyword] = useState('');

  const loadPosts = useCallback(
    async (tag?: string, reset = true) => {
      if (reset) setLoading(true);
      try {
        const res = await postsApi.getPosts(20, null, tag || null);
        setPosts(res.items);
        setNextToken(res.nextToken ?? null);
        setError('');
      } catch (e: unknown) {
        setError((e as Error).message ?? 'Failed to load posts');
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    loadPosts();
  }, [loadPosts]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setAppliedTag(tagFilter);
    setAppliedKeyword(keyword);
    loadPosts(tagFilter);
  };

  const handleClear = () => {
    setTagFilter('');
    setKeyword('');
    setAppliedTag('');
    setAppliedKeyword('');
    loadPosts('');
  };

  const handleLoadMore = async () => {
    if (!nextToken || loadingMore) return;
    setLoadingMore(true);
    try {
      const res = await postsApi.getPosts(20, nextToken, appliedTag || null);
      setPosts((prev) => [...prev, ...res.items]);
      setNextToken(res.nextToken ?? null);
    } finally {
      setLoadingMore(false);
    }
  };

  // Client-side keyword filter
  const displayed = appliedKeyword
    ? posts.filter((p) =>
        p.content.toLowerCase().includes(appliedKeyword.toLowerCase()),
      )
    : posts;

  const handleDeleted = (postId: string) =>
    setPosts((prev) => prev.filter((p) => p.postId !== postId));

  return (
    <>
      <section className="hero">
        <h1>投稿一覧</h1>
        <p>最新の投稿を表示しています。</p>
        <div className="hero-actions">
          <button
            className="button ghost icon-only"
            type="button"
            onClick={() => setShowSearch((s) => !s)}
            aria-label="Search"
          >
            <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
              <circle cx="11" cy="11" r="7" />
              <path d="M20 20l-3.5-3.5" />
            </svg>
            <span className="sr-only">検索</span>
          </button>
        </div>
      </section>

      {showSearch && (
        <section className="panel search-panel">
          <h2>検索</h2>
          <form className="form" onSubmit={handleSearch}>
            <div className="field">
              <label className="label" htmlFor="tagFilter">タグ検索</label>
              <input
                className="input"
                id="tagFilter"
                type="text"
                value={tagFilter}
                onChange={(e) => setTagFilter(e.target.value)}
                placeholder="タグを入力して絞り込み..."
              />
            </div>
            <div className="field">
              <label className="label" htmlFor="searchKeyword">投稿内容検索</label>
              <input
                className="input"
                id="searchKeyword"
                type="text"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                placeholder="投稿内容を検索..."
              />
            </div>
            <div className="actions">
              <button className="button icon-only" type="submit" aria-label="Search">
                <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
                  <circle cx="11" cy="11" r="7" />
                  <path d="M20 20l-3.5-3.5" />
                </svg>
                <span className="sr-only">検索</span>
              </button>
              <button
                className="button ghost icon-only"
                type="button"
                onClick={handleClear}
                aria-label="Clear"
              >
                <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M18 6L6 18" /><path d="M6 6l12 12" />
                </svg>
                <span className="sr-only">クリア</span>
              </button>
            </div>
          </form>
        </section>
      )}

      {isLoggedIn ? (
        <PostForm onCreated={() => loadPosts(appliedTag)} />
      ) : (
        <section className="panel">
          <h2>新規投稿</h2>
          <p className="muted">投稿するにはログインしてください。</p>
        </section>
      )}

      <section className="panel">
        <h2>投稿一覧</h2>
        <Alert type="error" message={error} />
        {loading ? (
          <p className="muted">読み込み中...</p>
        ) : displayed.length === 0 ? (
          <p className="muted">投稿がありません。</p>
        ) : (
          <ul className="posts" style={{ margin: 0, padding: 0, listStyle: 'none' }}>
            {displayed.map((post) => (
              <li key={post.postId}>
                <PostCard post={post} onDeleted={handleDeleted} />
              </li>
            ))}
          </ul>
        )}
        {nextToken && !appliedKeyword && (
          <div className="actions" style={{ marginTop: '1rem' }}>
            <button
              className="button ghost"
              type="button"
              onClick={handleLoadMore}
              disabled={loadingMore}
            >
              {loadingMore ? '読み込み中...' : 'もっと見る'}
            </button>
          </div>
        )}
      </section>
    </>
  );
}
