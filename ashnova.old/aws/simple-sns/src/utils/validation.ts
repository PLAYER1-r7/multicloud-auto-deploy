import { z } from 'zod';
import { MAX_CONTENT_LENGTH } from '../common';

/**
 * Validation schemas using Zod
 */

// Post content validation
export const postContentSchema = z
  .string()
  .min(1, 'content is required')
  .max(MAX_CONTENT_LENGTH, `content too long (max ${MAX_CONTENT_LENGTH} chars)`)
  .refine(
    (content) => {
      // Check for potentially malicious patterns
      const dangerousPatterns = [
        /<script[\s\S]*?>[\s\S]*?<\/script>/gi,
        /javascript:/gi,
        /on\w+\s*=/gi, // onclick, onerror, etc.
      ];
      return !dangerousPatterns.some((pattern) => pattern.test(content));
    },
    { message: 'Content contains potentially unsafe patterns' }
  );

// Tag validation
export const tagsSchema = z
  .array(z.string())
  .optional()
  .refine(
    (tags) => {
      if (!tags) return true;
      return tags.length <= 100;
    },
    { message: 'Too many tags (max 100)' }
  )
  .refine(
    (tags) => {
      if (!tags) return true;
      // Each tag must be 1-50 chars, alphanumeric + some special chars
      return tags.every((tag) => /^[\w\-\.あ-んア-ヶー一-龯]{1,50}$/.test(tag));
    },
    { message: 'Invalid tag format (1-50 chars, alphanumeric and Japanese allowed)' }
  )
  .refine(
    (tags) => {
      if (!tags) return true;
      // Check for duplicates
      return new Set(tags).size === tags.length;
    },
    { message: 'Duplicate tags are not allowed' }
  );

// Image keys validation (S3 keys from presigned URL upload)
export const imageKeysSchema = z
  .array(z.string())
  .optional()
  .refine(
    (keys) => {
      if (!keys) return true;
      return keys.length <= 16;
    },
    { message: 'Too many images (max 16)' }
  )
  .refine(
    (keys) => {
      if (!keys) return true;
      // Each key must be a valid S3 key pattern (images/*)
      // More strict pattern: images/{uuid}-{index}-{random}.jpeg
      return keys.every((key) => /^images\/[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}-\d+-[a-f0-9]{16}\.jpeg$/.test(key));
    },
    { message: 'Invalid image key format' }
  )
  .refine(
    (keys) => {
      if (!keys) return true;
      // Check for duplicate keys
      return new Set(keys).size === keys.length;
    },
    { message: 'Duplicate image keys are not allowed' }
  );

// Image validation (deprecated - for backward compatibility)
export const imageSchema = z
  .string()
  .optional()
  .refine(
    (image) => {
      if (!image) return true;
      const allowedTypes = ['jpeg', 'jpg', 'png', 'gif', 'webp'];
      const dataUrlPattern = new RegExp(`^data:image/(${allowedTypes.join('|')});base64,`);
      return dataUrlPattern.test(image);
    },
    { message: 'Invalid or unsupported image format' }
  )
  .refine(
    (image) => {
      if (!image) return true;
      const maxSize = 7 * 1024 * 1024; // 7MB
      return image.length <= maxSize;
    },
    { message: 'Image too large (max 7MB)' }
  )
  .refine(
    (image) => {
      if (!image) return true;
      try {
        const base64Data = image.split(',')[1];
        return base64Data && /^[A-Za-z0-9+/=]+$/.test(base64Data);
      } catch {
        return false;
      }
    },
    { message: 'Invalid base64 image data' }
  );

// Multiple images validation (deprecated - for backward compatibility)
export const imagesSchema = z
  .array(z.string())
  .optional()
  .refine(
    (images) => {
      if (!images) return true;
      return images.length <= 10;
    },
    { message: 'Too many images (max 10)' }
  )
  .refine(
    (images) => {
      if (!images) return true;
      const allowedTypes = ['jpeg', 'jpg', 'png', 'gif', 'webp'];
      const dataUrlPattern = new RegExp(`^data:image/(${allowedTypes.join('|')});base64,`);
      return images.every((img) => dataUrlPattern.test(img));
    },
    { message: 'Invalid or unsupported image format in one or more images' }
  )
  .refine(
    (images) => {
      if (!images) return true;
      const maxSize = 7 * 1024 * 1024; // 7MB per image
      return images.every((img) => img.length <= maxSize);
    },
    { message: 'One or more images too large (max 7MB per image)' }
  )
  .refine(
    (images) => {
      if (!images) return true;
      return images.every((img) => {
        try {
          const base64Data = img.split(',')[1];
          return base64Data && /^[A-Za-z0-9+/=]+$/.test(base64Data);
        } catch {
          return false;
        }
      });
    },
    { message: 'Invalid base64 image data in one or more images' }
  );

// Create post body schema
export const createPostBodySchema = z.object({
  content: postContentSchema,
  imageKeys: imageKeysSchema, // S3 keys from presigned URL upload
  image: imageSchema, // Backward compatibility (deprecated)
  images: imagesSchema, // Backward compatibility (deprecated)
  isMarkdown: z.boolean().optional(),
  tags: tagsSchema,
});

// Get upload URLs request schema
export const getUploadUrlsRequestSchema = z.object({
  count: z.number().int().min(1).max(16, 'Maximum 16 images allowed'),
});

// PostId validation (UUID format)
export const postIdSchema = z
  .string()
  .uuid('Invalid postId format');

// Query limit validation
export const limitSchema = z
  .number()
  .int()
  .positive()
  .max(50)
  .default(20);

/**
 * Validation helper functions
 */

export function validatePostContent(content: string): string | null {
  const result = postContentSchema.safeParse(content);
  if (!result.success) {
    return result.error.issues[0].message;
  }
  return null;
}

export function validateImage(image?: string): string | null {
  const result = imageSchema.safeParse(image);
  if (!result.success) {
    return result.error.issues[0].message;
  }
  return null;
}

export function validatePostId(postId: string): string | null {
  const result = postIdSchema.safeParse(postId);
  if (!result.success) {
    return result.error.issues[0].message;
  }
  return null;
}

export function validateCreatePostBody(body: unknown): { success: true; data: z.infer<typeof createPostBodySchema> } | { success: false; error: string } {
  const result = createPostBodySchema.safeParse(body);
  if (!result.success) {
    return {
      success: false,
      error: result.error.issues.map((e: any) => `${e.path.join('.')}: ${e.message}`).join(', '),
    };
  }
  return {
    success: true,
    data: result.data,
  };
}

export function validateGetUploadUrlsRequest(body: unknown): { success: true; data: z.infer<typeof getUploadUrlsRequestSchema> } | { success: false; error: string } {
  const result = getUploadUrlsRequestSchema.safeParse(body);
  if (!result.success) {
    return {
      success: false,
      error: result.error.issues.map((e: any) => `${e.path.join('.')}: ${e.message}`).join(', '),
    };
  }
  return {
    success: true,
    data: result.data,
  };
}
