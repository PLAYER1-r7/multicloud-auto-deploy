import { useRef, useState } from "react";
import { postsApi } from "../api/posts";
import { uploadsApi } from "../api/uploads";
import Alert from "./Alert";

const ALLOWED_TYPES = new Set([
  "image/jpeg",
  "image/png",
  "image/heic",
  "image/heif",
]);

interface PostFormProps {
  onCreated?: () => void;
}

export default function PostForm({ onCreated }: PostFormProps) {
  const [content, setContent] = useState("");
  const [tags, setTags] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFiles = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files ?? []);
    const invalid = selected.filter((f) => !ALLOWED_TYPES.has(f.type));
    if (invalid.length > 0) {
      setError("JPEG/PNG/HEIC/HEIF のみ対応しています");
      return;
    }
    if (selected.length > 16) {
      setError("画像は最大16枚までです");
      return;
    }
    setError("");
    setFiles(selected);
    setPreviews(selected.map((f) => URL.createObjectURL(f)));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) {
      setError("投稿内容を入力してください");
      return;
    }
    setError("");
    setSubmitting(true);

    try {
      let imageKeys: string[] = [];

      if (files.length > 0) {
        setStatus("画像をアップロード中...");
        const contentTypes = files.map((f) => f.type);
        const { urls } = await uploadsApi.getPresignedUrls(
          files.length,
          contentTypes,
        );
        if (urls.length !== files.length)
          throw new Error("URL数が一致しません");

        imageKeys = await Promise.all(
          files.map(async (file, i) => {
            await uploadsApi.uploadFile(urls[i].url, file);
            return urls[i].key;
          }),
        );
      }

      setStatus("投稿中...");
      const tagList = tags
        .split(/[\s,]+/)
        .map((t) => t.trim())
        .filter(Boolean);

      await postsApi.createPost({
        content: content.trim(),
        ...(tagList.length > 0 ? { tags: tagList } : {}),
        ...(imageKeys.length > 0 ? { imageKeys } : {}),
      });

      // Reset form
      setContent("");
      setTags("");
      setFiles([]);
      setPreviews([]);
      if (fileRef.current) fileRef.current.value = "";
      setStatus("");
      onCreated?.();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ??
        (err instanceof Error ? err.message : "投稿に失敗しました");
      setError(msg);
      setStatus("");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="panel">
      <h2>新規投稿</h2>
      <Alert type="error" message={error} />
      <form className="form" id="post-form" onSubmit={handleSubmit}>
        <div className="field">
          <label className="label" htmlFor="content">
            投稿内容
          </label>
          <textarea
            className="input textarea"
            id="content"
            rows={4}
            maxLength={5000}
            required
            value={content}
            onChange={(e) => setContent(e.target.value)}
          />
        </div>

        <div className="field">
          <label className="label" htmlFor="tags">
            タグ (スペース区切り)
          </label>
          <input
            className="input"
            id="tags"
            type="text"
            maxLength={200}
            placeholder="例: React TypeScript AWS"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
          />
        </div>

        <div className="field">
          <label className="label" htmlFor="images">
            画像 (JPEG/PNG/HEIC/HEIF, 最大16枚)
          </label>
          <input
            className="input"
            id="images"
            type="file"
            accept="image/jpeg,image/png,image/heic,image/heif"
            multiple
            ref={fileRef}
            onChange={handleFiles}
          />
          <p className="muted">JPEG/PNG/HEIC/HEIF に対応。</p>
          {previews.length > 0 && (
            <div className="preview-grid">
              {previews.map((src, i) => (
                <img
                  key={i}
                  src={src}
                  alt={`Preview ${i + 1}`}
                  className="preview-image"
                />
              ))}
            </div>
          )}
        </div>

        <div className="actions">
          {status && (
            <span className="muted" style={{ marginRight: 10 }}>
              {status}
            </span>
          )}
          <button
            className="button icon-only"
            type="submit"
            disabled={submitting}
            aria-label="Post"
          >
            <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M22 2L11 13" />
              <path d="M22 2L15 22l-4-9-9-4 20-7z" />
            </svg>
            <span className="sr-only">投稿する</span>
          </button>
        </div>
      </form>
    </section>
  );
}
