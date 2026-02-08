import { app } from '@azure/functions';

import './functions/createPost';
import './functions/listPosts';
import './functions/deletePost';
import './functions/getUploadUrls';

export default app;
