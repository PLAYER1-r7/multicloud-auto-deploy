import type { APIGatewayProxyEvent, APIGatewayProxyResult } from 'aws-lambda';
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient, DeleteCommand, QueryCommand } from '@aws-sdk/lib-dynamodb';
import { S3Client, DeleteObjectCommand } from '@aws-sdk/client-s3';
import { json, requireEnv } from './common';
import { handleError, extractUserInfo } from './middleware/errorHandler';
import { AuthenticationError, AuthorizationError, NotFoundError, ValidationError } from './utils/errors';
import { validatePostId } from './utils/validation';
import { logger } from './utils/logger';

const client = new DynamoDBClient({});
const docClient = DynamoDBDocumentClient.from(client);
const s3Client = new S3Client({});

export const handler = async (event: APIGatewayProxyEvent): Promise<APIGatewayProxyResult> => {
  try {
    const POSTS_TABLE_NAME = requireEnv('POSTS_TABLE_NAME');
    const IMAGES_BUCKET_NAME = requireEnv('IMAGES_BUCKET_NAME');

    // Check authentication
    const userInfo = extractUserInfo(event.requestContext.authorizer?.claims);
    if (!userInfo) {
      throw new AuthenticationError();
    }

    const { userId, isAdmin } = userInfo;

    // Get and validate postId from path parameters
    const postId = event.pathParameters?.postId;
    if (!postId) {
      throw new ValidationError('postIdが必要です');
    }

    const validationError = validatePostId(postId);
    if (validationError) {
      throw new ValidationError(validationError);
    }

    // Get post to check ownership and image
    const queryResult = await docClient.send(
      new QueryCommand({
        TableName: POSTS_TABLE_NAME,
        IndexName: 'PostIdIndex',
        KeyConditionExpression: 'postId = :postId',
        ExpressionAttributeValues: {
          ':postId': postId,
        },
      })
    );

    if (!queryResult.Items || queryResult.Items.length === 0) {
      throw new NotFoundError('投稿が見つかりません');
    }

    const post = queryResult.Items[0];

    // Check authorization: Admin or post owner
    if (!isAdmin && post.userId !== userId) {
      logger.warn('Unauthorized delete attempt', { 
        attemptedBy: userId, 
        postOwner: post.userId,
        postId 
      });
      throw new AuthorizationError('自分の投稿または管理者のみ削除できます');
    }

    // Delete images from S3 if exists (support both single and multiple images)
    const imageKeys = post.imageKeys as string[] | undefined;
    const singleImageKey = post.imageKey as string | undefined;
    
    const keysToDelete = imageKeys || (singleImageKey ? [singleImageKey] : []);
    
    if (keysToDelete.length > 0) {
      await Promise.allSettled(
        keysToDelete.map(async (key) => {
          try {
            await s3Client.send(
              new DeleteObjectCommand({
                Bucket: IMAGES_BUCKET_NAME,
                Key: key,
              })
            );
            logger.info('Image deleted from S3', { imageKey: key, postId });
          } catch (err) {
            logger.error('Failed to delete image from S3', { error: err, imageKey: key, postId });
            // Continue with other deletions
          }
        })
      );
    }

    // Delete post from DynamoDB using actual PK and SK
    await docClient.send(
      new DeleteCommand({
        TableName: POSTS_TABLE_NAME,
        Key: {
          PK: post.PK,
          SK: post.SK,
        },
      })
    );

    logger.info('Post deleted successfully', { postId, userId });
    return json(200, { message: '投稿を削除しました', postId });
  } catch (err: unknown) {
    return handleError(err, 'deletePost');
  }
};
