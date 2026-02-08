import type { APIGatewayProxyHandler } from "aws-lambda";
import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";
import { json, requireEnv, getEnvOrDefault, PRESIGNED_URL_EXPIRY } from "./common";
import { handleError, extractUserInfo } from "./middleware/errorHandler";
import { AuthenticationError, ValidationError } from "./utils/errors";
import { validateGetUploadUrlsRequest } from "./utils/validation";
import { logger } from "./utils/logger";
import crypto from "crypto";

const s3 = new S3Client({
  region: getEnvOrDefault('AWS_REGION', 'ap-northeast-1')
});

interface UploadUrlResponse {
  postId: string;
  urls: Array<{
    url: string;
    key: string;
  }>;
  expiresIn: number;
}

export const handler: APIGatewayProxyHandler = async (event) => {
  try {
    const bucketName = requireEnv("IMAGES_BUCKET_NAME");
    
    // Authentication check
    const userInfo = extractUserInfo(event.requestContext.authorizer?.claims);
    if (!userInfo) {
      throw new AuthenticationError();
    }
    
    const { userId } = userInfo;
    
    // Parse and validate request body
    const body = event.body ? JSON.parse(event.body) : {};
    const validationResult = validateGetUploadUrlsRequest(body);
    
    if (!validationResult.success) {
      throw new ValidationError(validationResult.error);
    }
    
    const { count } = validationResult.data;
    
    // Generate unique post ID for this upload session
    const postId = crypto.randomUUID();
    const expiresIn = parseInt(getEnvOrDefault('PRESIGNED_URL_EXPIRY', String(PRESIGNED_URL_EXPIRY)), 10);
    
    // Generate presigned URLs for each image
    const urls = await Promise.all(
      Array.from({ length: count }, async (_, index) => {
        const randomSuffix = crypto.randomBytes(8).toString('hex');
        const key = `images/${postId}-${index}-${randomSuffix}.jpeg`;
        
        const command = new PutObjectCommand({
          Bucket: bucketName,
          Key: key,
          ContentType: 'image/jpeg',
          Metadata: {
            'uploaded-by': userId,
            'post-id': postId,
            'image-index': String(index)
          }
        });
        
        const url = await getSignedUrl(s3, command, { expiresIn });
        
        return { url, key };
      })
    );
    
    const response: UploadUrlResponse = {
      postId,
      urls,
      expiresIn
    };
    
    logger.info('Upload URLs generated', { 
      postId, 
      count, 
      userId,
      keys: urls.map(u => u.key)
    });
    
    return json(200, response);
  } catch (err: unknown) {
    return handleError(err, 'getUploadUrls');
  }
};
