import PostForm from './components/MessageForm';
import PostList from './components/MessageList';

function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Header */}
        <header className="text-center mb-8">
          <h1 className="text-4xl md:text-5xl font-bold text-gray-800 dark:text-white mb-3">
            🌐 Multi-Cloud SNS
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            AWS・ Azure・ GCP で動作するシンプルな SNS
          </p>
          <div className="mt-4 flex justify-center gap-4 text-sm text-gray-500 dark:text-gray-400">
            <span>☁️ AWS Lambda</span>
            <span>🔷 Azure Container Apps</span>
            <span>🌈 GCP Cloud Run</span>
          </div>
        </header>

        {/* Post Form */}
        <PostForm />

        {/* Post List */}
        <PostList />

        {/* Footer */}
        <footer className="mt-12 text-center text-sm text-gray-500 dark:text-gray-400">
          <p>Built with React, TypeScript, Vite &amp; Tailwind CSS</p>
          <p className="mt-1">
            Deployed to: S3 + CloudFront, Blob Storage + CDN, Cloud Storage + CDN
          </p>
        </footer>
      </div>
    </div>
  );
}

export default App;
