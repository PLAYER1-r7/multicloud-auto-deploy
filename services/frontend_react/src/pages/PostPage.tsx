import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { postsApi } from "../api/posts";
import type { Post } from "../types/message";
import PostCard from "../components/PostCard";
import Alert from "../components/Alert";

export default function PostPage() {
  const { postId } = useParams<{ postId: string }>();
  const [post, setPost] = useState<Post | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!postId) return;
    postsApi
      .getPost(postId)
      .then((p) => {
        setPost(p);
        setLoading(false);
      })
      .catch((e: unknown) => {
        setError((e as Error).message ?? "Post not found");
        setLoading(false);
      });
  }, [postId]);

  return (
    <section>
      <h1 className="sr-only">投稿詳細</h1>
      <Alert type="error" message={error} />
      {loading ? (
        <p className="muted">読み込み中...</p>
      ) : post ? (
        <PostCard post={post} detail />
      ) : (
        <p className="muted">投稿が見つかりません。</p>
      )}
    </section>
  );
}
