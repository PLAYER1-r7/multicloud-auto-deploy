import React, { useEffect, useState } from 'react';
import { Toaster } from 'react-hot-toast';
import { Header } from '../components/Header';
import { PostForm } from '../components/PostForm';
import { PostList } from '../components/PostList';
import { VersionModal } from '../components/VersionModal';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { useAuth } from '../hooks/useAuth';
import { usePosts } from '../hooks/usePosts';
import { useProfile, useUpdateProfile } from '../hooks/useProfile';
import { exchangeCodeForToken } from '../services/auth';
import { PAGINATION_CONFIG, PROFILE_CONFIG } from '../config/constants';
import type { VersionInfo } from '../types';

export const HomePage: React.FC = () => {
  const { isAuthenticated, updateAuth } = useAuth();
  const [tokenHistory, setTokenHistory] = useState<(string | undefined)[]>([undefined]);
  const [currentPageIndex, setCurrentPageIndex] = useState(0);
  const [pageSize, setPageSize] = useState(() => {
    const saved = localStorage.getItem(PAGINATION_CONFIG.STORAGE_KEY);
    return saved ? Number(saved) : PAGINATION_CONFIG.DEFAULT_PAGE_SIZE;
  });
  const [tagFilter, setTagFilter] = useState<string>('');
  const [searchKeyword, setSearchKeyword] = useState<string>('');
  const [showSearch, setShowSearch] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const currentToken = tokenHistory[currentPageIndex];
  const { data, isLoading, error: queryError, refetch } = usePosts(pageSize, currentToken, tagFilter);
  const [versionInfo, setVersionInfo] = useState<VersionInfo | null>(null);
  const [showVersionModal, setShowVersionModal] = useState(false);
  const [authError, setAuthError] = useState('');
  const [nicknameInput, setNicknameInput] = useState('');
  const profileQuery = useProfile(isAuthenticated);
  const updateProfileMutation = useUpdateProfile();

  // Handle page size change
  const handlePageSizeChange = (newSize: number) => {
    setPageSize(newSize);
    localStorage.setItem(PAGINATION_CONFIG.STORAGE_KEY, String(newSize));
    // Reset to first page when page size changes
    setTokenHistory([undefined]);
    setCurrentPageIndex(0);
  };

  // Handle OAuth callback
  useEffect(() => {
    const handleCallback = async () => {
      const params = new URLSearchParams(window.location.search);
      const code = params.get('code');
      
      if (code) {
        // Remove code from URL immediately
        window.history.replaceState({}, '', window.location.pathname);
        
        try {
          await exchangeCodeForToken(code);
          updateAuth();
        } catch (err) {
          console.error('Token exchange failed:', err);
          setAuthError(`認証エラー: ${err}`);
        }
      }
    };

    handleCallback();
  }, [updateAuth]);

  // Load version info
  useEffect(() => {
    const loadVersion = async () => {
      try {
        const res = await fetch('/version.json?v=' + Date.now());
        if (res.ok) {
          const data = await res.json();
          setVersionInfo(data);
        }
      } catch (err) {
        console.error('Failed to load version:', err);
      }
    };

    loadVersion();
  }, []);

  useEffect(() => {
    if (profileQuery.data?.nickname !== undefined) {
      setNicknameInput(profileQuery.data.nickname || '');
    }
  }, [profileQuery.data?.nickname]);

  const errorMessage = authError || (queryError ? `エラー: ${queryError}` : '');

  return (
    <ErrorBoundary>
      <Toaster
        position="top-center"
        toastOptions={{
          style: {
            background: 'var(--card-bg)',
            color: 'var(--text-color)',
            border: '1px solid var(--card-border)',
            backdropFilter: 'blur(10px)',
          },
        }}
      />
      <div className="wrap">
        <Header
          isAuthenticated={isAuthenticated}
          version={versionInfo?.currentVersion || ''}
          onReload={() => refetch()}
          onShowVersion={() => setShowVersionModal(true)}
          onToggleSearch={() => setShowSearch(!showSearch)}
          onToggleProfile={() => setShowProfile((prev) => !prev)}
        />

        {isAuthenticated && showProfile && (
          <div className="card" style={{ marginBottom: '20px' }}>
            <div style={{ fontSize: '14px', marginBottom: '8px', color: 'var(--text-secondary)' }}>
              👤 ニックネーム設定
            </div>
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <input
                type="text"
                placeholder="ニックネーム（最大50文字）"
                value={nicknameInput}
                onChange={(e) => setNicknameInput(e.target.value)}
                maxLength={PROFILE_CONFIG.MAX_NICKNAME_LENGTH}
                style={{
                  flex: 1,
                  padding: '8px 12px',
                  borderRadius: '8px',
                  border: '1px solid var(--input-border)',
                  background: 'var(--input-bg)',
                  color: 'var(--text-primary)',
                  fontSize: '14px',
                }}
              />
              <button
                onClick={() => updateProfileMutation.mutate(nicknameInput.trim())}
                disabled={updateProfileMutation.isPending || nicknameInput.trim().length === 0}
                className="secondary"
                title="ニックネームを保存"
              >
                保存
              </button>
            </div>
            {profileQuery.isLoading && (
              <div style={{ marginTop: '8px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                読み込み中...
              </div>
            )}
            {profileQuery.error && (
              <div style={{ marginTop: '8px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                ニックネームの取得に失敗しました
              </div>
            )}
          </div>
        )}

        {/* Search panel */}
        {showSearch && (
          <div className="card" style={{ marginBottom: '20px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {/* Tag search */}
              <div>
                <label htmlFor="tagFilter" style={{ display: 'block', fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  🏷️ タグ検索
                </label>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  <input
                    id="tagFilter"
                    type="text"
                    placeholder="タグを入力して絞り込み..."
                    value={tagFilter}
                    onChange={(e) => {
                      setTagFilter(e.target.value);
                      setTokenHistory([undefined]);
                      setCurrentPageIndex(0);
                    }}
                    style={{
                      flex: 1,
                      padding: '8px 12px',
                      borderRadius: '8px',
                      border: '1px solid var(--input-border)',
                      background: 'var(--input-bg)',
                      color: 'var(--text-primary)',
                      fontSize: '14px',
                    }}
                  />
                  {tagFilter && (
                    <button
                      onClick={() => {
                        setTagFilter('');
                        setTokenHistory([undefined]);
                        setCurrentPageIndex(0);
                      }}
                      style={{
                        padding: '8px 12px',
                        background: 'transparent',
                        color: 'var(--text-secondary)',
                        border: '1px solid var(--input-border)',
                        borderRadius: '8px',
                        cursor: 'pointer',
                        fontSize: '14px',
                      }}
                    >
                      クリア
                    </button>
                  )}
                </div>
              </div>

              {/* Content search */}
              <div>
                <label htmlFor="searchKeyword" style={{ display: 'block', fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  🔍 投稿内容検索
                </label>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  <input
                    id="searchKeyword"
                    type="text"
                    placeholder="投稿内容を検索..."
                    value={searchKeyword}
                    onChange={(e) => setSearchKeyword(e.target.value)}
                    style={{
                      flex: 1,
                      padding: '8px 12px',
                      borderRadius: '8px',
                      border: '1px solid var(--input-border)',
                      background: 'var(--input-bg)',
                      color: 'var(--text-primary)',
                      fontSize: '14px',
                    }}
                  />
                  {searchKeyword && (
                    <button
                      onClick={() => setSearchKeyword('')}
                      style={{
                        padding: '8px 12px',
                        background: 'transparent',
                        color: 'var(--text-secondary)',
                        border: '1px solid var(--input-border)',
                        borderRadius: '8px',
                        cursor: 'pointer',
                        fontSize: '14px',
                      }}
                    >
                      クリア
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {isAuthenticated && <PostForm 
          onPostCreated={() => {
            // 新しい投稿が作成されたら最初のページに戻る
            setTokenHistory([undefined]);
            setCurrentPageIndex(0);
            refetch();
          }}
        />}

        <PostList 
          posts={data?.items || []} 
          loading={isLoading} 
          error={errorMessage} 
          onRefresh={() => refetch()}
          nextToken={data?.nextToken}
          currentPage={currentPageIndex + 1}
          hasPrevious={currentPageIndex > 0}
          pageSize={pageSize}
          onPageSizeChange={handlePageSizeChange}
          searchKeyword={searchKeyword}
          onLoadMore={(token: string) => {
            // 次のページに進む
            setTokenHistory(prev => [...prev.slice(0, currentPageIndex + 1), token]);
            setCurrentPageIndex(prev => prev + 1);
          }}
          onLoadPrevious={() => {
            // 前のページに戻る
            setCurrentPageIndex(prev => prev - 1);
          }}
          onLoadFirst={() => {
            // 最初のページに戻る
            setCurrentPageIndex(0);
          }}
        />
      </div>

      <VersionModal
        isOpen={showVersionModal}
        onClose={() => setShowVersionModal(false)}
        versionInfo={versionInfo}
      />
    </ErrorBoundary>
  );
};
