import React, { useState } from 'react';
import toast from 'react-hot-toast';
import { getToken } from '../services/api';
import { useCreatePost, useGetUploadUrls } from '../hooks/usePosts';
import { 
  resizeImage, 
  validateImageFile, 
  validateCompressedImageSize,
  validateTotalImagesSize,
  IMAGE_CONSTRAINTS,
  IMAGE_ERRORS 
} from '../utils/image';
import { validatePostContent } from '../utils/validation';
import { MarkdownRenderer } from './MarkdownRenderer';

interface PostFormProps {
  onPostCreated: () => void;
}

export const PostForm: React.FC<PostFormProps> = ({ onPostCreated }) => {
  const [content, setContent] = useState('');
  const [error, setError] = useState('');
  const [selectedImages, setSelectedImages] = useState<string[]>([]);
  const [isMarkdownMode, setIsMarkdownMode] = useState(false);
  const [tagsInput, setTagsInput] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const createPostMutation = useCreatePost();
  const getUploadUrlsMutation = useGetUploadUrls();

  const handleImageChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    // Check total count
    if (selectedImages.length + files.length > 16) {
      setError(`画像は最大16枚までです（現在${selectedImages.length}枚選択中）`);
      return;
    }

    const newImages: string[] = [];
    
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      
      // Validate file
      const validationError = validateImageFile(file);
      if (validationError) {
        setError(validationError);
        continue;
      }

      try {
        // Resize and compress image
        const resizedDataUrl = await resizeImage(file);
        
        // Validate compressed size
        const sizeError = validateCompressedImageSize(resizedDataUrl);
        if (sizeError) {
          setError(sizeError);
          continue;
        }
        
        newImages.push(resizedDataUrl);
      } catch (err) {
        console.error('Image processing error:', err);
        setError(IMAGE_ERRORS.PROCESSING_FAILED);
      }
    }

    if (newImages.length > 0) {
      const combinedImages = [...selectedImages, ...newImages];
      
      // Validate total size
      const totalSizeError = validateTotalImagesSize(combinedImages);
      if (totalSizeError) {
        setError(totalSizeError);
        return;
      }
      
      setSelectedImages(combinedImages);
      setError('');
    }
  };

  const handleRemoveImage = (index: number) => {
    setSelectedImages(selectedImages.filter((_, i) => i !== index));
  };

  const handleSubmit = async () => {
    setError('');
    const trimmedContent = content.trim();

    if (!getToken()) {
      toast.error('先にログインしてください。');
      return;
    }

    // Validate: content or images must be provided
    if (!trimmedContent && selectedImages.length === 0) {
      toast.error('投稿内容または画像を入力してください。');
      return;
    }

    // Validate content length if provided
    if (trimmedContent) {
      const contentError = validatePostContent(trimmedContent);
      if (contentError) {
        toast.error(contentError);
        return;
      }
    }

    // Validate total image size before submission
    if (selectedImages.length > 0) {
      const totalSizeError = validateTotalImagesSize(selectedImages);
      if (totalSizeError) {
        toast.error(totalSizeError);
        return;
      }
    }

    setIsUploading(true);

    try {
      const tags = tagsInput.trim() 
        ? tagsInput.trim().split(/\s+/).filter(Boolean)
        : undefined;
      
      // Validate tag count
      if (tags && tags.length > 100) {
        toast.error('タグは100個まで指定できます。');
        setIsUploading(false);
        return;
      }

      let imageKeys: string[] | undefined;

      // Phase 1: Upload images to S3 if present
      if (selectedImages.length > 0) {
        toast.loading('画像をアップロード中...', { id: 'upload' });
        
        // Get presigned URLs
        const uploadUrlsResponse = await getUploadUrlsMutation.mutateAsync(selectedImages.length);
        
        // Convert base64 to Blob and upload to S3
        const uploadPromises = selectedImages.map(async (dataUrl, index) => {
          const base64Data = dataUrl.split(',')[1];
          const blob = await fetch(`data:image/jpeg;base64,${base64Data}`).then(r => r.blob());
          
          // Upload to S3 using presigned URL
          await fetch(uploadUrlsResponse.urls[index].url, {
            method: 'PUT',
            body: blob,
            headers: {
              'Content-Type': 'image/jpeg',
            },
          });
          
          return uploadUrlsResponse.urls[index].key;
        });

        imageKeys = await Promise.all(uploadPromises);
        toast.success('画像のアップロード完了', { id: 'upload' });
      }

      // Phase 2: Create post with image keys
      await createPostMutation.mutateAsync({
        content: trimmedContent || ' ', // 画像のみの場合はスペースを送信
        isMarkdown: isMarkdownMode,
        ...(imageKeys && { imageKeys }),
        ...(tags && { tags }),
      });

      setContent('');
      setSelectedImages([]);
      setTagsInput('');
      setIsUploading(false);
      onPostCreated();
    } catch (err: any) {
      console.error('Post creation error:', err);
      setIsUploading(false);
      toast.dismiss('upload');
      // Error is already handled by the mutation
    }
  };

  return (
    <div className="card">
      <div className="row" style={{ marginBottom: '10px', display: 'flex', gap: '10px', alignItems: 'center' }}>
        <button
          type="button"
          onClick={() => setIsMarkdownMode(false)}
          style={{
            padding: '6px 12px',
            background: !isMarkdownMode ? 'var(--button-bg)' : 'transparent',
            color: !isMarkdownMode ? '#fff' : 'var(--text-primary)',
            border: '1px solid var(--button-bg)',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '14px',
          }}
        >
          シンプル
        </button>
        <button
          type="button"
          onClick={() => setIsMarkdownMode(true)}
          style={{
            padding: '6px 12px',
            background: isMarkdownMode ? 'var(--button-bg)' : 'transparent',
            color: isMarkdownMode ? '#fff' : 'var(--text-primary)',
            border: '1px solid var(--button-bg)',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '14px',
          }}
        >
          Markdown
        </button>
        {isMarkdownMode && (
          <>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              プレビュー付き
            </span>
            <button
              type="button"
              onClick={() => window.open('/guide/index.html', '_blank', 'noopener,noreferrer')}
              style={{
                padding: '6px 12px',
                background: 'transparent',
                color: 'var(--button-bg)',
                border: '1px solid var(--button-bg)',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '14px',
                marginLeft: 'auto',
              }}
              title="Markdown記法ガイド（別ウィンドウで開く）"
            >
              📝 記法ガイド
            </button>
          </>
        )}
      </div>
      <div className="row" style={{ display: 'flex', gap: '10px', alignItems: 'stretch' }}>
        <textarea
          id="contentInput"
          maxLength={5000}
          placeholder={isMarkdownMode ? "Markdown記法で入力..." : "投稿内容(5000文字まで)"}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          style={{
            flex: isMarkdownMode ? '1' : 'auto',
            width: isMarkdownMode ? 'auto' : '100%',
            minHeight: isMarkdownMode ? '200px' : 'auto',
          }}
        />
        {isMarkdownMode && (
          <div
            style={{
              flex: '1',
              minHeight: '200px',
              padding: '12px',
              background: 'var(--input-bg)',
              border: '1px solid var(--input-border)',
              borderRadius: '8px',
              overflow: 'auto',
              fontSize: '14px',
              lineHeight: '1.5',
            }}
          >
            <div style={{ color: 'var(--text-secondary)', fontSize: '12px', marginBottom: '8px' }}>
              プレビュー
            </div>
            <div className="content">
              <MarkdownRenderer 
                content={content || '*プレビューがここに表示されます*'}
              />
            </div>
          </div>
        )}
      </div>
      <div className="row" style={{ marginTop: '10px' }}>
        <label htmlFor="tagsInput" style={{ display: 'block', marginBottom: '4px', fontSize: '14px', color: 'var(--text-secondary)' }}>
          🏷️ タグ (スペース区切り、最大100個)
        </label>
        <input
          id="tagsInput"
          type="text"
          placeholder="例: React TypeScript AWS"
          value={tagsInput}
          onChange={(e) => setTagsInput(e.target.value)}
          style={{
            width: '100%',
            padding: '8px',
            borderRadius: '8px',
            border: '1px solid var(--input-border)',
            background: 'var(--input-bg)',
            fontSize: '14px',
            color: 'var(--text-primary)',
          }}
        />
        {tagsInput.trim() && (
          <div style={{ marginTop: '6px', fontSize: '12px', color: 'var(--text-secondary)' }}>
            タグプレビュー: {tagsInput.trim().split(/\s+/).filter(Boolean).map((tag, i) => (
              <span key={i} style={{ 
                display: 'inline-block',
                background: 'var(--hover-bg)',
                padding: '4px 10px',
                borderRadius: '12px',
                border: '2px solid var(--card-border)',
                color: 'var(--text-primary)',
                marginRight: '4px',
                marginTop: '4px'
              }}>
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>
      <div className="row" style={{ marginTop: '10px' }}>
        <label htmlFor="imageInput" style={{ cursor: 'pointer', color: '#667eea' }}>
          📷 画像を選択 (最大16枚、自動で最適化)
        </label>
        <input
          id="imageInput"
          type="file"
          accept="image/*"
          multiple
          onChange={handleImageChange}
          style={{ display: 'none' }}
        />
      </div>
      {selectedImages.length > 0 && (
        <div className="row" style={{ marginTop: '10px' }}>
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', 
            gap: '10px',
            width: '100%'
          }}>
            {selectedImages.map((img, index) => (
              <div key={index} style={{ position: 'relative' }}>
                <img 
                  src={img} 
                  alt={`Preview ${index + 1}`} 
                  style={{ 
                    width: '100%', 
                    height: '120px',
                    borderRadius: '8px',
                    objectFit: 'cover'
                  }} 
                />
                <button 
                  onClick={() => handleRemoveImage(index)}
                  style={{ 
                    position: 'absolute', 
                    top: '5px', 
                    right: '5px',
                    background: 'rgba(255, 255, 255, 0.95)',
                    border: '2px solid #ef4444',
                    borderRadius: '50%',
                    width: '32px',
                    height: '32px',
                    cursor: 'pointer',
                    fontSize: '20px',
                    fontWeight: 'bold',
                    color: '#ef4444',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    boxShadow: '0 2px 4px rgba(0, 0, 0, 0.2)',
                    transition: 'all 0.2s ease'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = '#ef4444';
                    e.currentTarget.style.color = 'white';
                    e.currentTarget.style.transform = 'scale(1.1)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.95)';
                    e.currentTarget.style.color = '#ef4444';
                    e.currentTarget.style.transform = 'scale(1)';
                  }}
                  title="この画像を削除"
                >
                  ×
                </button>
                <div style={{
                  position: 'absolute',
                  bottom: '5px',
                  left: '5px',
                  background: 'rgba(0, 0, 0, 0.6)',
                  color: 'white',
                  padding: '2px 6px',
                  borderRadius: '4px',
                  fontSize: '12px'
                }}>
                  {index + 1}
                </div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: '8px', fontSize: '12px', color: 'var(--text-secondary)' }}>
            {selectedImages.length}/16枚選択中
          </div>
        </div>
      )}
      <div className="row" style={{ marginTop: '10px', justifyContent: 'space-between' }}>
        <button onClick={handleSubmit} disabled={isUploading || createPostMutation.isPending}>
          {isUploading ? 'アップロード中...' : '投稿する'}
        </button>
        <span className="hint">{content.length}/5000</span>
      </div>
      {error && <div className="error">{error}</div>}
    </div>
  );
};
