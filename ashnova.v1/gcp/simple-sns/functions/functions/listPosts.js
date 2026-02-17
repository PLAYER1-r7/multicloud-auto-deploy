"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.listPosts = listPosts;
const common_1 = require("../common");
/**
 * Cloud Function: List Posts
 * GET /api/posts?limit=20&continuationToken=...&tag=...
 */
async function listPosts(req, res) {
    if ((0, common_1.handleCorsOptions)(req, res))
        return;
    try {
        const limit = Math.min(parseInt(req.query.limit) || 20, 100);
        const tag = req.query.tag;
        const continuationToken = req.query.continuationToken;
        // Query Firestore
        let query = common_1.db.collection('posts').orderBy('createdAt', 'desc').limit(limit);
        // Filter by tag if provided
        if (tag) {
            query = query.where('tags', 'array-contains', tag);
        }
        // Start after continuation token if provided
        if (continuationToken) {
            const lastDoc = await common_1.db.collection('posts').doc(continuationToken).get();
            if (lastDoc.exists) {
                query = query.startAfter(lastDoc);
            }
        }
        const snapshot = await query.get();
        const posts = [];
        // Generate signed URLs for images
        const bucket = common_1.storage.bucket(process.env.STORAGE_BUCKET || 'simple-sns-gcp-images');
        for (const doc of snapshot.docs) {
            const data = doc.data();
            const post = { ...data };
            if (data.imageKeys && data.imageKeys.length > 0) {
                post.imageUrls = await Promise.all(data.imageKeys.map(async (key) => {
                    const file = bucket.file(key);
                    const [url] = await file.getSignedUrl({
                        version: 'v4',
                        action: 'read',
                        expires: Date.now() + common_1.SAS_URL_EXPIRY_MINUTES * 60 * 1000,
                    });
                    return url;
                }));
            }
            posts.push(post);
        }
        const response = { items: posts, limit };
        // Set continuation token if there are more results
        if (snapshot.docs.length === limit) {
            const lastDoc = snapshot.docs[snapshot.docs.length - 1];
            response.continuationToken = lastDoc.id;
        }
        return (0, common_1.jsonResponse)(res, 200, response);
    }
    catch (error) {
        console.error('Error listing posts:', error);
        return (0, common_1.jsonResponse)(res, 500, { message: 'Internal server error' });
    }
}
