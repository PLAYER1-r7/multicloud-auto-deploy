import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { lazy, Suspense } from 'react';
import { LoadingSpinner } from './LoadingSpinner';

// 遅延ロード: Mermaidは大きいので、必要な時だけロード
const MermaidDiagram = lazy(() => import('./MermaidDiagram').then(m => ({ default: m.MermaidDiagram })));
const PlantUMLDiagram = lazy(() => import('./PlantUMLDiagram').then(m => ({ default: m.PlantUMLDiagram })));

interface CodeBlockProps {
  className?: string;
  children?: React.ReactNode;
  inline?: boolean;
}

export const CodeBlock = ({ className, children, inline }: CodeBlockProps) => {
  const match = /language-(\w+)(?::(.+))?/.exec(className || '');
  const language = match ? match[1] : '';
  const filename = match ? match[2] : '';
  
  const childrenStr = String(children);
  
  // Inline code (no language class or explicitly inline)
  if (inline || !className?.includes('language-')) {
    return (
      <code 
        style={{ 
          background: 'var(--code-bg)', 
          padding: '2px 4px', 
          borderRadius: '3px',
          fontSize: '0.9em',
        }}
      >
        {children}
      </code>
    );
  }

  // Mermaid diagram (遅延ロード)
  if (language === 'mermaid') {
    return (
      <Suspense fallback={<div style={{ padding: '20px', textAlign: 'center' }}><LoadingSpinner size="md" /></div>}>
        <MermaidDiagram chart={childrenStr} />
      </Suspense>
    );
  }

  // PlantUML diagram (遅延ロード)
  if (language === 'uml' || language === 'plantuml') {
    return (
      <Suspense fallback={<div style={{ padding: '20px', textAlign: 'center' }}><LoadingSpinner size="md" /></div>}>
        <PlantUMLDiagram code={childrenStr} />
      </Suspense>
    );
  }

  // Block code with syntax highlighting
  const code = childrenStr.replace(/^\n+/, '').replace(/\n+$/, '');
  
  return (
    <div style={{ margin: '0.5em 0', overflow: 'hidden', borderRadius: '4px' }}>
      {filename && (
        <div 
          style={{ 
            background: '#1e1e1e',
            color: '#d4d4d4',
            padding: '6px 12px',
            fontSize: '12px',
            borderBottom: '1px solid #404040',
            fontFamily: 'monospace',
          }}
        >
          {language}:{filename}
        </div>
      )}
      <div style={{ background: '#1e1e1e' }}>
        <SyntaxHighlighter
          style={vscDarkPlus}
          language={language}
          PreTag="div"
          customStyle={{
            margin: 0,
            padding: '12px',
            fontSize: '13px',
            lineHeight: '1.5',
            background: 'transparent',
            whiteSpace: 'pre',
          }}
          codeTagProps={{
            style: {
              fontFamily: 'Consolas, Monaco, "Courier New", monospace',
              background: 'transparent',
              display: 'block',
            }
          }}
          useInlineStyles={true}
        >
          {code}
        </SyntaxHighlighter>
      </div>
    </div>
  );
};
