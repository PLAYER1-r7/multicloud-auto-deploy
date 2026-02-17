export interface Post {
    postId: string;
    userId: string;
    nickname?: string;
    content: string;
    createdAt: string;
    imageUrls?: string[];
    imageKeys?: string[];
    isMarkdown?: boolean;
    tags?: string[];
}
export interface PostDocument extends Post {
}
export interface UserInfo {
    userId: string;
    email?: string;
}
