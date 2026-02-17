import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { FaTimes, FaChevronLeft, FaChevronRight } from 'react-icons/fa';

interface ImageModalProps {
  imageUrl: string | null;
  onClose: () => void;
  imageUrls?: string[];
  currentIndex?: number;
  onNavigate?: (direction: 'prev' | 'next') => void;
}

/**
 * 画像拡大表示用モーダルコンポーネント
 * React Portalを使用してdocument.bodyに直接マウント
 */
export const ImageModal: React.FC<ImageModalProps> = ({ 
  imageUrl, 
  onClose,
  imageUrls = [],
  currentIndex = 0,
  onNavigate
}) => {
  const hasMultipleImages = imageUrls.length > 1;
  const canGoPrev = hasMultipleImages && currentIndex > 0;
  const canGoNext = hasMultipleImages && currentIndex < imageUrls.length - 1;

  useEffect(() => {
    if (!imageUrl) return;
    
    // Escキーでモーダルを閉じる、矢印キーでナビゲート
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      } else if (e.key === 'ArrowLeft' && canGoPrev && onNavigate) {
        onNavigate('prev');
      } else if (e.key === 'ArrowRight' && canGoNext && onNavigate) {
        onNavigate('next');
      }
    };
    
    document.addEventListener('keydown', handleKeyDown);
    // ボディのスクロールを無効化
    document.body.style.overflow = 'hidden';
    
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [imageUrl, onClose, canGoPrev, canGoNext, onNavigate]);
  
  if (!imageUrl) return null;

  const modalContent = (
    <div
      style={{ 
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        zIndex: 9999,
        backgroundColor: 'rgba(0, 0, 0, 0.9)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}
      onClick={(e) => {
        e.stopPropagation();
        onClose();
      }}
    >
      {/* 閉じるボタン */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          onClose();
        }}
        style={{
          position: 'absolute',
          top: '1rem',
          right: '1rem',
          color: 'white',
          fontSize: '1.5rem',
          background: 'rgba(0, 0, 0, 0.5)',
          border: 'none',
          borderRadius: '50%',
          width: '40px',
          height: '40px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: 'pointer',
          transition: 'background 0.2s',
          zIndex: 10000
        }}
        onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(0, 0, 0, 0.7)'}
        onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(0, 0, 0, 0.5)'}
        aria-label="Close"
      >
        <FaTimes />
      </button>

      {/* 画像カウンター */}
      {hasMultipleImages && (
        <div
          style={{
            position: 'absolute',
            top: '1rem',
            left: '50%',
            transform: 'translateX(-50%)',
            color: 'white',
            fontSize: '1rem',
            background: 'rgba(0, 0, 0, 0.7)',
            padding: '8px 16px',
            borderRadius: '20px',
            zIndex: 10000
          }}
        >
          {currentIndex + 1} / {imageUrls.length}
        </div>
      )}

      {/* 前へボタン */}
      {canGoPrev && onNavigate && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onNavigate('prev');
          }}
          style={{
            position: 'absolute',
            left: '1rem',
            top: '50%',
            transform: 'translateY(-50%)',
            color: 'white',
            fontSize: '2rem',
            background: 'rgba(0, 0, 0, 0.5)',
            border: 'none',
            borderRadius: '50%',
            width: '50px',
            height: '50px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            transition: 'background 0.2s',
            zIndex: 10000
          }}
          onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(0, 0, 0, 0.7)'}
          onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(0, 0, 0, 0.5)'}
          aria-label="Previous image"
        >
          <FaChevronLeft />
        </button>
      )}

      {/* 次へボタン */}
      {canGoNext && onNavigate && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onNavigate('next');
          }}
          style={{
            position: 'absolute',
            right: '1rem',
            top: '50%',
            transform: 'translateY(-50%)',
            color: 'white',
            fontSize: '2rem',
            background: 'rgba(0, 0, 0, 0.5)',
            border: 'none',
            borderRadius: '50%',
            width: '50px',
            height: '50px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            transition: 'background 0.2s',
            zIndex: 10000
          }}
          onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(0, 0, 0, 0.7)'}
          onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(0, 0, 0, 0.5)'}
          aria-label="Next image"
        >
          <FaChevronRight />
        </button>
      )}

      <img
        src={imageUrl}
        alt="Full size"
        style={{
          maxWidth: '90%',
          maxHeight: '90%',
          objectFit: 'contain'
        }}
        onClick={(e) => e.stopPropagation()}
      />
    </div>
  );

  // document.bodyに直接マウント
  return createPortal(modalContent, document.body);
};

export default ImageModal;
