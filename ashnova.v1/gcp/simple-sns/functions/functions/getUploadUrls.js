"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.getUploadUrls = getUploadUrls;
const common_1 = require("../common");
const nanoid_1 = require("nanoid");
/**
 * Cloud Function: Get Upload URLs
 * GET /api/upload-urls?count=3
 */
async function getUploadUrls(req, res) {
    if ((0, common_1.handleCorsOptions)(req, res))
        return;
    try {
        // Authentication
        const userInfo = await (0, common_1.extractUserInfo)(req);
        if (!userInfo) {
            return (0, common_1.jsonResponse)(res, 401, { message: 'Unauthorized' });
        }
        // Validation
        const count = Math.min(parseInt(req.query.count) || 1, common_1.MAX_IMAGES_PER_POST);
        if (count < 1) {
            return (0, common_1.jsonResponse)(res, 400, { message: 'Count must be at least 1' });
        }
        // Generate signed URLs for upload
        const bucket = common_1.storage.bucket(process.env.STORAGE_BUCKET || 'simple-sns-gcp-images');
        const uploadUrls = [];
        for (let i = 0; i < count; i++) {
            const imageId = (0, nanoid_1.nanoid)();
            const imageKey = `images/${userInfo.userId}/${imageId}.jpg`;
            const file = bucket.file(imageKey);
            const [uploadUrl] = await file.getSignedUrl({
                version: 'v4',
                action: 'write',
                expires: Date.now() + common_1.SAS_URL_EXPIRY_MINUTES * 60 * 1000,
                contentType: 'image/jpeg',
            });
            uploadUrls.push({ uploadUrl, imageKey });
        }
        console.log('Upload URLs generated:', { userId: userInfo.userId, count });
        return (0, common_1.jsonResponse)(res, 200, { uploadUrls });
    }
    catch (error) {
        console.error('Error generating upload URLs:', error);
        return (0, common_1.jsonResponse)(res, 500, { message: 'Internal server error' });
    }
}
