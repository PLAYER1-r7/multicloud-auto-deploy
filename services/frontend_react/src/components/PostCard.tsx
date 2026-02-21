import { useState } from "react";
import { useNavigate } from "react-router-dom";
import type { Post } from "../types/message";
import { postsApi } from "../api/posts";
import { useAuth } from "../contexts/AuthContext";
import Lightbox from "./Lightbox";

interface PostCardProps {
  post: Post;
  onDeleted?: (postId: string) => void;
  /** When true, show full detail (no "open" link) */
  detail?: boolean;
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString("ja-JP", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export default function PostCard({
  post,
  onDeleted,
  detail = false,
}: PostCardProps) {
  const { isLoggedIn } = useAuth();
  const navigate = useNavigate();
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    if (!confirm("この投稿を削除しますか？")) return;
    setDeleting(true);
    try {
      await postsApi.deletePost(post.postId);
      onDeleted?.(post.postId);
    } catch (e) {
      console.error(e);
      alert("削除に失敗しました");
    } finally {
      setDeleting(false);
    }
  };

  const imageUrls = post.imageUrls ?? [];

  return (
    <article className={detail ? "post-detail" : "post"}>
      <div className="post-meta">
        <span className="post-user">{post.nickname || post.userId}</span>
        <span className="post-date">{formatDate(post.createdAt)}</span>
      </div>

      <p className="post-content">{post.content}</p>

      {imageUrls.length > 0 && (
        <div className="post-images">
          {imageUrls.map((url, i) => (
            <button
              key={url}
              className="thumb-button"
              type="button"
              onClick={() => setLightboxIndex(i)}
              aria-label="Open image"
            >
              <img
                className="post-image"
                src={url}
                alt="Post image"
                loading="lazy"
              />
              {imageUrls.length > 1 && (
                <span className="thumb-count">
                  {i + 1}/{imageUrls.length}
                </span>
              )}
            </button>
          ))}
        </div>
      )}

      {post.tags && post.tags.length > 0 && (
        <div className="tags">
          {post.tags.map((tag) => (
            <span key={tag} className="tag">
              {tag}
            </span>
          ))}
        </div>
      )}

      <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.75rem" }}>
        {!detail && (
          <button
            className="button ghost icon-only"
            type="button"
            onClick={() => navigate(`/post/${post.postId}`)}
            aria-label="Open post"
          >
            <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M9 18l6-6-6-6" />
            </svg>
            <span className="sr-only">詳細</span>
          </button>
        )}
        {detail && (
          <button
            className="button ghost icon-only"
            type="button"
            onClick={() => navigate("/")}
            aria-label="Back"
          >
            <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M15 18l-6-6 6-6" />
            </svg>
            <span className="sr-only">戻る</span>
          </button>
        )}
        {isLoggedIn && (
          <button
            className="button ghost icon-only"
            type="button"
            onClick={handleDelete}
            disabled={deleting}
            aria-label="Delete post"
          >
            <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
              <polyline points="3 6 5 6 21 6" />
              <path d="M19 6l-1 14H6L5 6" />
              <path d="M10 11v6" />
              <path d="M14 11v6" />
              <path d="M9 6V4h6v2" />
            </svg>
            <span className="sr-only">削除</span>
          </button>
        )}
      </div>

      {lightboxIndex !== null && (
        <Lightbox
          urls={imageUrls}
          initialIndex={lightboxIndex}
          onClose={() => setLightboxIndex(null)}
        />
      )}
    </article>
  );
}
