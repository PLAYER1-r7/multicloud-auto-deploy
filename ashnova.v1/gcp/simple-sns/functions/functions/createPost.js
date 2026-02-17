"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.createPost = createPost;
const common_1 = require("../common");
const nanoid_1 = require("nanoid");
/**
 * Cloud Function: Create Post
 * POST /api/posts
 */
async function createPost(req, res) {
    if ((0, common_1.handleCorsOptions)(req, res))
        return;
    try {
        // Authentication
        const userInfo = await (0, common_1.extractUserInfo)(req);
        if (!userInfo) {
            return (0, common_1.jsonResponse)(res, 401, { message: 'Unauthorized' });
        }
        // Validation
        const { content, imageKeys, isMarkdown, tags } = req.body;
        if (!content || typeof content !== 'string') {
            return (0, common_1.jsonResponse)(res, 400, { message: 'Content is required' });
        }
        if (content.length > common_1.MAX_CONTENT_LENGTH) {
            return (0, common_1.jsonResponse)(res, 400, { message: `Content must be less than ${common_1.MAX_CONTENT_LENGTH} characters` });
        }
        if (imageKeys && (!Array.isArray(imageKeys) || imageKeys.length > common_1.MAX_IMAGES_PER_POST)) {
            return (0, common_1.jsonResponse)(res, 400, { message: `Maximum ${common_1.MAX_IMAGES_PER_POST} images allowed` });
        }
        if (tags && (!Array.isArray(tags) || tags.length > common_1.MAX_TAGS_PER_POST)) {
            return (0, common_1.jsonResponse)(res, 400, { message: `Maximum ${common_1.MAX_TAGS_PER_POST} tags allowed` });
        }
        // Create post
        const postId = (0, nanoid_1.nanoid)();
        const createdAt = new Date().toISOString();
        const post = {
            postId,
            userId: userInfo.userId,
            content,
            createdAt,
            ...(imageKeys && imageKeys.length > 0 && { imageKeys }),
            ...(isMarkdown && { isMarkdown: true }),
            ...(tags && tags.length > 0 && { tags }),
        };
        // Save to Firestore
        await common_1.db.collection('posts').doc(postId).set(post);
        console.log('Post created:', { postId, userId: userInfo.userId });
        return (0, common_1.jsonResponse)(res, 201, { item: post });
    }
    catch (error) {
        console.error('Error creating post:', error);
        return (0, common_1.jsonResponse)(res, 500, { message: 'Internal server error' });
    }
}
