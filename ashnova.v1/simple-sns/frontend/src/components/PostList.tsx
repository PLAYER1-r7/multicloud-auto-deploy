import React, { useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { ja } from 'date-fns/locale';
import { PostDetailModal } from './PostDetailModal';
import { MarkdownRenderer } from './MarkdownRenderer';
import { ImageModal } from './ImageModal';
import { MapEmbed } from './MapEmbed';
import { useImageModal } from '../hooks/useImageModal';
import { extractMapLocations } from '../utils/map';
import type { Post } from '../types';

interface PostListProps {
  posts: Post[];
  loading: boolean;
  error: string;
  onRefresh?: () => void;
  nextToken?: string;
  currentPage?: number;
  hasPrevious?: boolean;
  pageSize?: number;
  onPageSizeChange?: (size: number) => void;
  onLoadMore?: (token: string) => void;
  onLoadPrevious?: () => void;
  onLoadFirst?: () => void;
  searchKeyword?: string;
}

const escapeHtml = (s: string): string => {
  return String(s)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
};

const fmtTime = (iso: string): string => {
  try {
    const date = new Date(iso);
    return formatDistanceToNow(date, { addSuffix: true, locale: ja });
  } catch {
    return iso;
  }
};

const extractYouTubeId = (url: string): string | null => {
  const patterns = [
    /(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})/,
    /(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]{11})/,
    /(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]{11})/,
    /(?:https?:\/\/)?(?:m\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})/,
  ];

  for (const pattern of patterns) {
    const match = url.match(pattern);
    if (match && match[1]) {
      return match[1];
    }
  }
  return null;
};

const findYouTubeUrls = (text: string): string[] => {
  const urlPattern = /(https?:\/\/[^\s]+)/g;
  const urls = text.match(urlPattern) || [];
  return urls.filter(url => extractYouTubeId(url) !== null);
};

export const PostList: React.FC<PostListProps> = ({ 
  posts, 
  loading, 
  error, 
  onRefresh, 
  nextToken, 
  currentPage,
  hasPrevious,
  pageSize = 20,
  onPageSizeChange,
  onLoadMore,
  onLoadPrevious,
  onLoadFirst,
  searchKeyword = '',
}) => {
  const { selectedImage, imageUrls, currentIndex, openImage, closeImage, navigateImage } = useImageModal();
  const [selectedPost, setSelectedPost] = useState<Post | null>(null);
  const [dragStart, setDragStart] = useState<{ x: number; y: number } | null>(null);

  if (loading) {
    return <div className="hint">読み込み中...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  if (posts.length === 0) {
    return <div className="hint">投稿がまだありません。</div>;
  }

  // Filter posts by search keyword
  const filteredPosts = searchKeyword.trim()
    ? posts.filter(post => 
        post.content?.toLowerCase().includes(searchKeyword.toLowerCase())
      )
    : posts;

  return (
    <>
      <div style={{ maxWidth: '900px', margin: '0 auto', padding: '0 20px' }}>
        {/* Page size selector */}
        {onPageSizeChange && (
          <div style={{ marginBottom: '20px', display: 'flex', justifyContent: 'flex-end' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <label style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
                表示件数:
              </label>
              <select
                value={pageSize}
                onChange={(e) => onPageSizeChange(Number(e.target.value))}
                style={{
                  padding: '8px 12px',
                  fontSize: '14px',
                  borderRadius: '8px',
                  border: '1px solid var(--card-border)',
                  background: 'var(--input-bg)',
                  color: 'var(--text-color)',
                  cursor: 'pointer',
                }}
              >
                <option value="10">10件</option>
                <option value="20">20件</option>
                <option value="50">50件</option>
              </select>
            </div>
          </div>
        )}

        {searchKeyword.trim() && (
          <div className="hint" style={{ marginBottom: '12px' }}>
            {filteredPosts.length}件の投稿が見つかりました
          </div>
        )}

        {/* Pagination controls at top */}
        {(hasPrevious || nextToken) && (
          <div style={{ 
            display: 'flex', 
            justifyContent: 'center', 
            alignItems: 'center',
            gap: '10px',
            marginBottom: '20px',
            padding: '15px',
            background: 'var(--card-bg)',
            borderRadius: '12px',
            border: '1px solid var(--card-border)',
            backdropFilter: 'blur(10px)',
          }}>
            {hasPrevious && onLoadFirst && (
              <button
                onClick={onLoadFirst}
                className="secondary"
                style={{ padding: '8px 16px', fontSize: '14px' }}
                title="最初のページに戻る"
              >
                ⏮ 最初
              </button>
            )}
            {hasPrevious && onLoadPrevious && (
              <button
                onClick={onLoadPrevious}
                className="secondary"
                style={{ padding: '8px 16px', fontSize: '14px' }}
              >
                ← 前へ
              </button>
            )}
            {currentPage && (
              <span style={{ 
                padding: '8px 16px',
                color: 'var(--text-primary)',
                fontSize: '14px',
                fontWeight: 'bold'
              }}>
                ページ {currentPage}
              </span>
            )}
            {nextToken && onLoadMore && (
              <button
                onClick={() => onLoadMore(nextToken)}
                className="secondary"
                style={{ padding: '8px 16px', fontSize: '14px' }}
              >
                次へ →
              </button>
            )}
          </div>
        )}
      </div>

      <div className="posts">
        {filteredPosts.map((post) => {
          const youtubeUrls = findYouTubeUrls(post.content || '');
          const postImageUrls = (post.imageUrls && post.imageUrls.length > 0) 
            ? post.imageUrls 
            : (post.imageUrl ? [post.imageUrl] : []);
          
          return (
            <div 
              key={post.postId} 
              className="post"
              onMouseDown={(e) => {
                setDragStart({ x: e.clientX, y: e.clientY });
              }}
              onMouseUp={(e) => {
                if (dragStart) {
                  const deltaX = Math.abs(e.clientX - dragStart.x);
                  const deltaY = Math.abs(e.clientY - dragStart.y);
                  const isDrag = deltaX > 5 || deltaY > 5;
                  if (!isDrag) {
                    setSelectedPost(post);
                  }
                  setDragStart(null);
                }
              }}
              style={{ cursor: 'pointer' }}
            >
              <div className="meta">
                <div className="user">{escapeHtml(post.nickname || post.userId || '')}</div>
                <div className="time">{fmtTime(post.createdAt || '')}</div>
              </div>
              <div className="content">
                {post.isMarkdown ? (
                  <MarkdownRenderer 
                    content={post.content || ''} 
                    onImageClick={(src) => openImage(src)}
                  />
                ) : (
                  <div style={{ whiteSpace: 'pre-wrap' }}>{post.content || ''}</div>
                )}
              </div>
              
              {/* YouTube thumbnails */}
              {youtubeUrls.map((url, idx) => {
                const videoId = extractYouTubeId(url);
                if (!videoId) return null;
                
                return (
                  <div key={idx} style={{ marginTop: '10px' }}>
                    <a
                      href={url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ display: 'block', textDecoration: 'none' }}
                    >
                      <img
                        src={`https://img.youtube.com/vi/${videoId}/mqdefault.jpg`}
                        alt="YouTube thumbnail"
                        style={{
                          width: '100%',
                          maxWidth: '320px',
                          borderRadius: '8px',
                          cursor: 'pointer',
                          transition: 'transform 0.2s ease',
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.02)'}
                        onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
                      />
                    </a>
                  </div>
                );
              })}
              
              {/* Maps */}
              {(() => {
                const mapLocations = extractMapLocations(post.content || '');
                if (mapLocations.length === 0) return null;
                
                return (
                  <div style={{ marginTop: '10px' }}>
                    {mapLocations.map((location, idx) => (
                      <MapEmbed
                        key={idx}
                        latitude={location.latitude}
                        longitude={location.longitude}
                        title={location.title}
                        height={250}
                      />
                    ))}
                  </div>
                );
              })()}
              
              {/* Tags */}
              {post.tags && post.tags.length > 0 && (
                <div style={{ 
                  marginTop: '10px', 
                  display: 'flex', 
                  flexWrap: 'wrap', 
                  gap: '6px' 
                }}>
                  {post.tags.map((tag, idx) => (
                    <span
                      key={idx}
                      style={{
                        display: 'inline-block',
                        padding: '4px 10px',
                        fontSize: '12px',
                        background: 'var(--hover-bg)',
                        color: 'var(--text-primary)',
                        borderRadius: '12px',
                        border: '2px solid var(--card-border)',
                      }}
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}
              
              {/* User uploaded images */}
              {postImageUrls.length > 0 ? (
                <div style={{ marginTop: '10px' }}>
                  <div style={{ 
                    display: 'grid', 
                    gridTemplateColumns: 'repeat(auto-fill, minmax(100px, 1fr))', 
                    gap: '8px',
                    maxWidth: '600px'
                  }}>
                    {postImageUrls.map((url, idx) => (
                      <div key={idx} style={{ position: 'relative' }}>
                        <img
                          src={url}
                          alt={`投稿画像 ${idx + 1}`}
                          style={{
                            width: '100%',
                            height: '100px',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            objectFit: 'cover',
                            transition: 'transform 0.2s ease'
                          }}
                          onMouseDown={(e) => {
                            e.stopPropagation();
                          }}
                          onMouseUp={(e) => {
                            e.stopPropagation();
                          }}
                          onClick={(e) => {
                            e.stopPropagation();
                            openImage(url, postImageUrls);
                          }}
                          onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.05)'}
                          onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
                        />
                        {postImageUrls.length > 1 && (
                          <div style={{
                            position: 'absolute',
                            bottom: '5px',
                            right: '5px',
                            background: 'rgba(0, 0, 0, 0.7)',
                            color: 'white',
                            padding: '2px 6px',
                            borderRadius: '4px',
                            fontSize: '10px',
                            fontWeight: 'bold'
                          }}>
                            {idx + 1}/{postImageUrls.length}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          );
        })}
      </div>

      <ImageModal 
        imageUrl={selectedImage}
        imageUrls={imageUrls}
        currentIndex={currentIndex}
        onClose={closeImage}
        onNavigate={navigateImage}
      />

      <PostDetailModal
        isOpen={!!selectedPost}
        onClose={() => setSelectedPost(null)}
        post={selectedPost}
        onDeleted={() => {
          setSelectedPost(null);
          if (onRefresh) onRefresh();
        }}
      />
    </>
  );
};
