"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.SAS_URL_EXPIRY_MINUTES = exports.MAX_CONTENT_LENGTH = exports.MAX_TAGS_PER_POST = exports.MAX_IMAGES_PER_POST = exports.storage = exports.db = void 0;
exports.extractUserInfo = extractUserInfo;
exports.jsonResponse = jsonResponse;
exports.setCorsHeaders = setCorsHeaders;
exports.handleCorsOptions = handleCorsOptions;
exports.requireEnv = requireEnv;
const admin = __importStar(require("firebase-admin"));
// Initialize Firebase Admin
if (!admin.apps.length) {
    admin.initializeApp();
}
exports.db = admin.firestore();
exports.storage = admin.storage();
exports.MAX_IMAGES_PER_POST = 5;
exports.MAX_TAGS_PER_POST = 10;
exports.MAX_CONTENT_LENGTH = 5000;
exports.SAS_URL_EXPIRY_MINUTES = 5;
/**
 * Extract user info from Firebase Auth token
 */
async function extractUserInfo(req) {
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
        return null;
    }
    const token = authHeader.substring(7);
    try {
        const decodedToken = await admin.auth().verifyIdToken(token);
        return {
            userId: decodedToken.uid,
            email: decodedToken.email,
        };
    }
    catch (error) {
        console.error('Token verification failed:', error);
        return null;
    }
}
/**
 * JSON response helper
 */
function jsonResponse(res, statusCode, data) {
    res.status(statusCode).json(data);
}
/**
 * CORS headers - Allow all origins for simplicity
 */
function setCorsHeaders(res, req) {
    const origin = req?.headers.origin;
    // Allow any HTTPS origin
    if (origin && (origin.startsWith('https://') || origin.startsWith('http://localhost'))) {
        res.set('Access-Control-Allow-Origin', origin);
    }
    else {
        res.set('Access-Control-Allow-Origin', '*');
    }
    res.set('Access-Control-Allow-Credentials', 'true');
    res.set('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS');
    res.set('Access-Control-Allow-Headers', 'Authorization, Content-Type');
}
/**
 * Handle OPTIONS requests for CORS
 */
function handleCorsOptions(req, res) {
    if (req.method === 'OPTIONS') {
        setCorsHeaders(res, req);
        res.status(204).send('');
        return true;
    }
    setCorsHeaders(res, req);
    return false;
}
/**
 * Require environment variable
 */
function requireEnv(name) {
    const value = process.env[name];
    if (!value) {
        throw new Error(`Missing required environment variable: ${name}`);
    }
    return value;
}
