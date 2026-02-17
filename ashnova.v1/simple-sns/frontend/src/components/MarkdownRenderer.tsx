import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import remarkBreaks from 'remark-breaks';
import remarkGithubAlerts from 'remark-github-alerts';
import remarkDirective from 'remark-directive';
import rehypeKatex from 'rehype-katex';
import { remarkQiitaNote } from '../utils/remarkQiitaNote';
import { CodeBlock } from './CodeBlock';

interface MarkdownRendererProps {
  content: string;
  onImageClick?: (src: string) => void;
  className?: string;
}

/**
 * Markdownレンダリング用の共通コンポーネント
 * PostList, PostDetailModal, PostFormで使用
 */
export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
  onImageClick,
  className = '',
}) => {
  return (
    <div className={`prose prose-invert max-w-none ${className}`}>
      <ReactMarkdown
        remarkPlugins={[
          remarkGfm,
          remarkMath,
          remarkGithubAlerts,
          remarkDirective,
          remarkQiitaNote,
          remarkBreaks,
        ]}
        rehypePlugins={[rehypeKatex]}
        components={{
          code: (props) => {
            return <CodeBlock {...props} />;
          },
          img: ({ src, alt }) => (
            <img
              src={src}
              alt={alt}
              className="max-w-full h-auto rounded cursor-pointer hover:opacity-80 transition"
              onClick={(e) => {
                e.stopPropagation();
                onImageClick?.(src || '');
              }}
            />
          ),
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-400 hover:text-blue-300 hover:underline"
            >
              {children}
            </a>
          ),
          table: ({ children }) => (
            <div className="overflow-x-auto my-4">
              <table className="min-w-full border-collapse">
                {children}
              </table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border border-gray-600 px-4 py-2 bg-gray-700 text-left font-semibold">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border border-gray-600 px-4 py-2">
              {children}
            </td>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};

