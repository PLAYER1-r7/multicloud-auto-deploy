import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import { ja } from 'date-fns/locale';
import { FiTrash2 } from 'react-icons/fi';
import { canDeletePost } from '../services/api';
import { useDeletePost } from '../hooks/usePosts';
import { MarkdownRenderer } from './MarkdownRenderer';
import { ImageModal } from './ImageModal';
import { MapEmbed } from './MapEmbed';
import { useImageModal } from '../hooks/useImageModal';
import { extractMapLocations } from '../utils/map';
import type { Post } from '../types';

interface PostDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  post: Post | null;
  onDeleted?: () => void;
}

const escapeHtml = (s: string): string => {
  return String(s)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
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

export const PostDetailModal: React.FC<PostDetailModalProps> = ({
  isOpen,
  onClose,
  post,
  onDeleted,
}) => {
  const { selectedImage, imageUrls, currentIndex, openImage, closeImage, navigateImage } = useImageModal();
  const deletePostMutation = useDeletePost();
  
  if (!isOpen || !post) return null;

  const handleDelete = async () => {
    if (!confirm('この投稿を削除しますか?')) return;
    
    try {
      await deletePostMutation.mutateAsync(post.postId);
      onClose();
      if (onDeleted) {
        onDeleted();
      }
    } catch (err) {
      // Error is already handled by the mutation
      console.error('Delete error:', err);
    }
  };

  const createdDate = new Date(post.createdAt || '');
  const relativeTime = formatDistanceToNow(createdDate, { addSuffix: true, locale: ja });
  const fullDateTime = createdDate.toLocaleString('ja-JP', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

  const youtubeUrls = findYouTubeUrls(post.content || '');

  // 投稿の全画像URLを取得
  const postImageUrls = (post.imageUrls && post.imageUrls.length > 0) 
    ? post.imageUrls 
    : (post.imageUrl ? [post.imageUrl] : []);

  return (
    <div className="modal show" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="close-btn" onClick={onClose}>
          ×
        </button>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 className="modal-title">投稿の詳細</h2>
          {canDeletePost(post.userId) && (
            <button
              onClick={handleDelete}
              disabled={deletePostMutation.isPending}
              style={{
                padding: '8px 16px',
                borderRadius: '8px',
                border: '1px solid #ef4444',
                background: 'rgba(239, 68, 68, 0.1)',
                color: '#ef4444',
                cursor: deletePostMutation.isPending ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '14px',
                fontWeight: 600,
                transition: 'all 0.2s ease',
              }}
              onMouseEnter={(e) => {
                if (!deletePostMutation.isPending) {
                  e.currentTarget.style.background = 'rgba(239, 68, 68, 0.2)';
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(239, 68, 68, 0.1)';
              }}
            >
              <FiTrash2 />
              削除
            </button>
          )}
        </div>
        
        <div style={{ marginTop: '24px' }}>
          <div style={{ marginBottom: '16px' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
              投稿ID
            </div>
            <div style={{ fontFamily: 'monospace', fontSize: '14px' }}>
              {post.postId}
            </div>
          </div>

          <div style={{ marginBottom: '16px' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
              投稿者
            </div>
            <div style={{ fontSize: '14px', fontWeight: 600 }}>
              {escapeHtml(post.nickname || post.userId || '')}
            </div>
          </div>

          <div style={{ marginBottom: '16px' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
              投稿日時
            </div>
            <div style={{ fontSize: '14px' }}>
              {fullDateTime}
              <span style={{ marginLeft: '8px', color: 'var(--text-secondary)' }}>
                ({relativeTime})
              </span>
            </div>
          </div>

          <div style={{ marginBottom: '16px' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
              投稿内容
            </div>
            <div style={{ 
              fontSize: '14px', 
              lineHeight: '1.6',
              padding: '12px',
              background: 'var(--input-bg)',
              borderRadius: '8px',
              border: '1px solid var(--card-border)',
            }}>
              {post.isMarkdown ? (
                <MarkdownRenderer 
                  content={post.content || ''} 
                  onImageClick={openImage}
                />
              ) : (
                <div style={{ whiteSpace: 'pre-wrap' }}>{post.content || ''}</div>
              )}

              {/* YouTube thumbnails */}
              {youtubeUrls.length > 0 && (
                <div style={{ marginTop: '12px' }}>
                  {youtubeUrls.map((url, idx) => {
                    const videoId = extractYouTubeId(url);
                    if (!videoId) return null;
                    
                    return (
                      <div key={idx} style={{ marginBottom: idx < youtubeUrls.length - 1 ? '10px' : 0 }}>
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
                              border: '1px solid var(--card-border)',
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.02)'}
                            onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
                          />
                        </a>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Maps */}
              {(() => {
                const mapLocations = extractMapLocations(post.content || '');
                if (mapLocations.length === 0) return null;
                
                return (
                  <div style={{ marginTop: '12px' }}>
                    {mapLocations.map((location, idx) => (
                      <MapEmbed
                        key={idx}
                        latitude={location.latitude}
                        longitude={location.longitude}
                        title={location.title}
                        height={300}
                      />
                    ))}
                  </div>
                );
              })()}

              {/* User uploaded images */}
              {postImageUrls.length > 0 ? (
                <div style={{ marginTop: '12px' }}>
                  <div style={{ 
                    display: 'grid', 
                    gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', 
                    gap: '12px',
                    maxWidth: '100%'
                  }}>
                    {postImageUrls.map((url, idx) => (
                      <div key={idx} style={{ position: 'relative' }}>
                        <img
                          src={url}
                          alt={`投稿画像 ${idx + 1}`}
                          style={{
                            width: '100%',
                            height: '150px',
                            borderRadius: '8px',
                            border: '1px solid var(--card-border)',
                            cursor: 'pointer',
                            objectFit: 'cover',
                            transition: 'transform 0.2s ease'
                          }}
                          onClick={() => openImage(url, postImageUrls)}
                          onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.05)'}
                          onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
                        />
                        {postImageUrls.length > 1 && (
                          <div style={{
                            position: 'absolute',
                            bottom: '8px',
                            right: '8px',
                            background: 'rgba(0, 0, 0, 0.7)',
                            color: 'white',
                            padding: '4px 8px',
                            borderRadius: '6px',
                            fontSize: '12px',
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
          </div>
          {/* Tags */}
          {post.tags && post.tags.length > 0 && (
            <div style={{ marginBottom: '16px' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                タグ
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {post.tags.map((tag, idx) => (
                  <span
                    key={idx}
                    style={{
                      display: 'inline-block',
                      padding: '6px 12px',
                      fontSize: '13px',
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
            </div>
          )}        </div>
      </div>

      <ImageModal 
        imageUrl={selectedImage}
        imageUrls={imageUrls}
        currentIndex={currentIndex}
        onClose={closeImage}
        onNavigate={navigateImage}
      />
    </div>
  );
};
