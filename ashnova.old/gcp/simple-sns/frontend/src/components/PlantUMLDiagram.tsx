import { useEffect, useState } from 'react';
import plantumlEncoder from 'plantuml-encoder';

interface PlantUMLDiagramProps {
  code: string;
}

export function PlantUMLDiagram({ code }: PlantUMLDiagramProps) {
  const [svgUrl, setSvgUrl] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const renderDiagram = async () => {
      try {
        setLoading(true);
        setError('');
        
        // PlantUMLコードをエンコード
        const encoded = plantumlEncoder.encode(code);
        
        // PlantUML公式サーバーのURLを生成
        const url = `https://www.plantuml.com/plantuml/svg/${encoded}`;
        
        // SVGが正常に取得できるか確認
        const response = await fetch(url);
        if (!response.ok) {
          throw new Error('PlantUML diagram rendering failed');
        }
        
        setSvgUrl(url);
      } catch (err) {
        console.error('PlantUML rendering error:', err);
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    renderDiagram();
  }, [code]);

  if (loading) {
    return (
      <div style={{
        padding: '1rem',
        background: 'var(--input-bg)',
        borderRadius: '4px',
        color: 'var(--text-secondary)',
        textAlign: 'center'
      }}>
        Loading PlantUML diagram...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        padding: '1rem',
        background: '#1a1a2e',
        borderRadius: '4px',
        color: '#ef4444',
        fontFamily: 'monospace',
        fontSize: '0.875rem',
        whiteSpace: 'pre-wrap',
        border: '1px solid #ef4444'
      }}>
        PlantUML Error: {error}
      </div>
    );
  }

  return (
    <div style={{
      padding: '1rem',
      background: '#1a1a2e',
      borderRadius: '4px',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center'
    }}>
      <img 
        src={svgUrl} 
        alt="PlantUML Diagram" 
        style={{ maxWidth: '100%', height: 'auto' }}
      />
    </div>
  );
}
