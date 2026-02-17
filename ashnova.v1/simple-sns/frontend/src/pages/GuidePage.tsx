import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { MarkdownRenderer } from '../components/MarkdownRenderer';

export const GuidePage: React.FC = () => {
  const navigate = useNavigate();
  const [content, setContent] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);

  const handleClose = () => {
    // 別タブで開かれた場合はタブを閉じる、そうでなければホームに戻る
    if (window.opener) {
      window.close();
    } else {
      navigate('/');
    }
  };

  useEffect(() => {
    const loadGuide = async () => {
      try {
        const response = await fetch('/markdown-guide.md');
        const text = await response.text();
        setContent(text);
      } catch (error) {
        console.error('Failed to load markdown guide:', error);
        setContent('# エラー\n\nガイドの読み込みに失敗しました。');
      } finally {
        setIsLoading(false);
      }
    };

    loadGuide();
  }, []);

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: '#fff',
      zIndex: 9999,
      overflow: 'auto',
    }}>
      <div style={{
        maxWidth: '900px',
        margin: '0 auto',
        padding: '20px',
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '20px',
          paddingBottom: '10px',
          borderBottom: '2px solid #e0e0e0',
        }}>
          <h1 style={{ margin: 0, fontSize: '24px' }}>Markdown記法ガイド</h1>
          <button
            onClick={handleClose}
            style={{
              padding: '8px 16px',
              fontSize: '14px',
              cursor: 'pointer',
              backgroundColor: '#6c757d',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
            }}
          >
            ✕ 閉じる
          </button>
        </div>
        
        {isLoading ? (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            読み込み中...
          </div>
        ) : (
          <div style={{
            backgroundColor: '#f8f9fa',
            padding: '20px',
            borderRadius: '8px',
          }}>
            <MarkdownRenderer content={content} />
          </div>
        )}
      </div>
    </div>
  );
};
