"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.deletePost = deletePost;
const common_1 = require("../common");
/**
 * Cloud Function: Delete Post
 * DELETE /api/posts/:postId
 */
async function deletePost(req, res) {
    if ((0, common_1.handleCorsOptions)(req, res))
        return;
    try {
        // Authentication
        const userInfo = await (0, common_1.extractUserInfo)(req);
        if (!userInfo) {
            return (0, common_1.jsonResponse)(res, 401, { message: 'Unauthorized' });
        }
        // Get postId from path
        const postId = req.path.split('/').pop();
        if (!postId) {
            return (0, common_1.jsonResponse)(res, 400, { message: 'Post ID is required' });
        }
        // Get post from Firestore
        const postDoc = await common_1.db.collection('posts').doc(postId).get();
        if (!postDoc.exists) {
            return (0, common_1.jsonResponse)(res, 404, { message: 'Post not found' });
        }
        const post = postDoc.data();
        // Check ownership
        if (post.userId !== userInfo.userId) {
            return (0, common_1.jsonResponse)(res, 403, { message: 'Forbidden: You can only delete your own posts' });
        }
        // Delete images from Cloud Storage
        if (post.imageKeys && post.imageKeys.length > 0) {
            const bucket = common_1.storage.bucket(process.env.STORAGE_BUCKET || 'simple-sns-gcp-images');
            await Promise.all(post.imageKeys.map((key) => bucket.file(key).delete().catch(() => { })));
        }
        // Delete post from Firestore
        await common_1.db.collection('posts').doc(postId).delete();
        console.log('Post deleted:', { postId, userId: userInfo.userId });
        return (0, common_1.jsonResponse)(res, 200, { message: 'Post deleted successfully' });
    }
    catch (error) {
        console.error('Error deleting post:', error);
        return (0, common_1.jsonResponse)(res, 500, { message: 'Internal server error' });
    }
}
