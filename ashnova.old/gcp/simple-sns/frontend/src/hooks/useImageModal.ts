import { useState, useCallback } from 'react';

/**
 * 画像モーダルの状態管理用カスタムフック
 * PostList, PostDetailModal, PostFormで共通使用
 * 複数画像のナビゲーションにも対応
 */
export const useImageModal = () => {
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [imageUrls, setImageUrls] = useState<string[]>([]);
  const [currentIndex, setCurrentIndex] = useState<number>(0);

  const openImage = useCallback((imageUrl: string, allImageUrls?: string[]) => {
    setSelectedImage(imageUrl);
    
    if (allImageUrls && allImageUrls.length > 0) {
      setImageUrls(allImageUrls);
      const index = allImageUrls.indexOf(imageUrl);
      setCurrentIndex(index >= 0 ? index : 0);
    } else {
      setImageUrls([imageUrl]);
      setCurrentIndex(0);
    }
  }, []);

  const closeImage = useCallback(() => {
    setSelectedImage(null);
    setImageUrls([]);
    setCurrentIndex(0);
  }, []);

  const navigateImage = useCallback((direction: 'prev' | 'next') => {
    if (imageUrls.length === 0) return;

    const newIndex = direction === 'prev' 
      ? Math.max(0, currentIndex - 1)
      : Math.min(imageUrls.length - 1, currentIndex + 1);
    
    setCurrentIndex(newIndex);
    setSelectedImage(imageUrls[newIndex]);
  }, [imageUrls, currentIndex]);

  return {
    selectedImage,
    imageUrls,
    currentIndex,
    openImage,
    closeImage,
    navigateImage,
  };
};
