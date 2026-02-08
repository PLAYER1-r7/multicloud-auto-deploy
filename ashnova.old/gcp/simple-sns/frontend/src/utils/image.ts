/**
 * Image processing constants
 */
export const IMAGE_CONSTRAINTS = {
  MAX_SIZE: 10 * 1024 * 1024, // 10MB
  MAX_DIMENSION: 3840, // Max width/height (4K resolution)
  QUALITY: 0.9, // JPEG quality (high quality)
  SINGLE_IMAGE_LIMIT: 5 * 1024 * 1024, // 5MB per image (Base64)
  TOTAL_IMAGES_LIMIT: 50 * 1024 * 1024, // 50MB total for all images
  API_GATEWAY_LIMIT: 10 * 1024 * 1024, // 10MB API Gateway limit (not used with presigned URLs)
  ALLOWED_TYPES: ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'] as const,
} as const;

/**
 * Error messages for image validation
 */
export const IMAGE_ERRORS = {
  INVALID_TYPE: '画像ファイルのみアップロード可能です（JPEG, PNG, GIF, WebP）',
  FILE_TOO_LARGE: 'ファイルサイズは10MB以下にしてください',
  COMPRESSED_TOO_LARGE: '画像が大きすぎます（1枚あたり5MB以下）。別の画像を選択してください。',
  TOTAL_SIZE_TOO_LARGE: '画像の合計サイズが大きすぎます（全体で50MB以下）。画像の枚数を減らしてください。',
  PROCESSING_FAILED: '画像の処理に失敗しました。',
  CANVAS_NOT_AVAILABLE: 'Canvasが利用できません',
} as const;

/**
 * Calculate base64 data size in bytes
 */
const calculateBase64Size = (base64: string): number => {
  // Remove data URI prefix
  const base64Data = base64.split(',')[1] || base64;
  // Base64 encoding increases size by ~33%
  return (base64Data.length * 3) / 4;
};

/**
 * Resize and compress an image file
 */
export const resizeImage = (
  file: File,
  maxWidth: number = IMAGE_CONSTRAINTS.MAX_DIMENSION,
  maxHeight: number = IMAGE_CONSTRAINTS.MAX_DIMENSION,
  quality: number = IMAGE_CONSTRAINTS.QUALITY
): Promise<string> => {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const reader = new FileReader();

    reader.onload = (e) => {
      img.src = e.target?.result as string;
    };
    reader.onerror = () => reject(new Error(IMAGE_ERRORS.PROCESSING_FAILED));

    img.onload = () => {
      const canvas = document.createElement('canvas');
      let width = img.width;
      let height = img.height;

      // Calculate new dimensions
      if (width > height) {
        if (width > maxWidth) {
          height = (height * maxWidth) / width;
          width = maxWidth;
        }
      } else {
        if (height > maxHeight) {
          width = (width * maxHeight) / height;
          height = maxHeight;
        }
      }

      canvas.width = width;
      canvas.height = height;

      const ctx = canvas.getContext('2d');
      if (!ctx) {
        reject(new Error(IMAGE_ERRORS.CANVAS_NOT_AVAILABLE));
        return;
      }

      ctx.drawImage(img, 0, 0, width, height);

      // Convert to base64
      const base64 = canvas.toDataURL('image/jpeg', quality);
      resolve(base64);
    };

    img.onerror = () => reject(new Error(IMAGE_ERRORS.PROCESSING_FAILED));
    reader.readAsDataURL(file);
  });
};

/**
 * Validate image file
 */
export const validateImageFile = (file: File): string | null => {
  if (!IMAGE_CONSTRAINTS.ALLOWED_TYPES.includes(file.type as any)) {
    return IMAGE_ERRORS.INVALID_TYPE;
  }

  if (file.size > IMAGE_CONSTRAINTS.MAX_SIZE) {
    return IMAGE_ERRORS.FILE_TOO_LARGE;
  }

  return null;
};

/**
 * Validate compressed image size for API Gateway
 */
export const validateCompressedImageSize = (base64: string): string | null => {
  const sizeInBytes = calculateBase64Size(base64);
  
  if (sizeInBytes > IMAGE_CONSTRAINTS.SINGLE_IMAGE_LIMIT) {
    return IMAGE_ERRORS.COMPRESSED_TOO_LARGE;
  }
  
  return null;
};

/**
 * Validate total size of multiple images
 */
export const validateTotalImagesSize = (base64Images: string[]): string | null => {
  const totalSize = base64Images.reduce((sum, img) => sum + calculateBase64Size(img), 0);
  
  if (totalSize > IMAGE_CONSTRAINTS.TOTAL_IMAGES_LIMIT) {
    return IMAGE_ERRORS.TOTAL_SIZE_TOO_LARGE;
  }
  
  return null;
};
