import { useEffect, useRef } from 'react';
import mermaid from 'mermaid';

interface MermaidDiagramProps {
  chart: string;
}

// Initialize mermaid with custom theme
mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  themeVariables: {
    primaryColor: '#667eea',
    primaryTextColor: '#fff',
    primaryBorderColor: '#667eea',
    lineColor: '#667eea',
    secondaryColor: '#764ba2',
    tertiaryColor: '#1a1a2e',
    background: '#1a1a2e',
    mainBkg: '#1a1a2e',
    secondBkg: '#16213e',
    clusterBkg: '#16213e',
    clusterBorder: '#667eea',
    edgeLabelBackground: '#16213e',
    textColor: '#e0e0e0',
    fontFamily: 'system-ui, -apple-system, sans-serif',
  },
  flowchart: {
    useMaxWidth: true,
    htmlLabels: true,
    curve: 'basis',
  },
});

export const MermaidDiagram = ({ chart }: MermaidDiagramProps) => {
  const ref = useRef<HTMLDivElement>(null);
  const idRef = useRef(`mermaid-${Math.random().toString(36).substr(2, 9)}`);

  useEffect(() => {
    if (ref.current && chart) {
      const renderDiagram = async () => {
        try {
          ref.current!.innerHTML = '';
          const { svg } = await mermaid.render(idRef.current, chart);
          if (ref.current) {
            ref.current.innerHTML = svg;
          }
        } catch (error) {
          console.error('Mermaid rendering error:', error);
          if (ref.current) {
            ref.current.innerHTML = `<pre style="color: #ff6b6b; padding: 12px; background: #2d1b1b; border-radius: 4px;">Mermaid rendering error: ${error instanceof Error ? error.message : 'Unknown error'}</pre>`;
          }
        }
      };
      
      renderDiagram();
    }
  }, [chart]);

  return (
    <div
      ref={ref}
      style={{
        margin: '0.5em 0',
        padding: '12px',
        background: '#1a1a2e',
        borderRadius: '4px',
        overflow: 'auto',
      }}
    />
  );
};
