import { visit } from 'unist-util-visit';
import type { Plugin } from 'unified';
import type { Root } from 'mdast';

export const remarkQiitaNote: Plugin<[], Root> = () => {
  return (tree) => {
    visit(tree, (node: any) => {
      if (node.type === 'containerDirective' && node.name === 'note') {
        const data = node.data || (node.data = {});
        
        // Qiita記法: :::note の次の行にタイプを記述
        let noteType = 'info';
        
        // 子ノードを確認
        if (node.children && node.children.length > 0) {
          const firstChild = node.children[0];
          
          // 最初の子が段落で、その中にテキストがある場合
          if (firstChild.type === 'paragraph' && firstChild.children) {
            const textContent = firstChild.children
              .filter((child: any) => child.type === 'text')
              .map((child: any) => child.value)
              .join('');
            
            const trimmed = textContent.trim().toLowerCase();
            
            // 最初の行がタイプのみの場合（info, warn, alert のいずれか）
            if (['info', 'warn', 'alert'].includes(trimmed)) {
              noteType = trimmed;
              // この段落を削除（タイプ指定のため）
              node.children.shift();
            } else {
              // 最初の単語がタイプの場合
              const firstWord = trimmed.split(/\s+/)[0];
              if (['info', 'warn', 'alert'].includes(firstWord)) {
                noteType = firstWord;
                // 最初の単語を削除
                const remainingText = textContent.replace(/^\s*\w+\s*/, '');
                if (remainingText.trim()) {
                  // テキストが残っている場合は更新
                  const textNode = firstChild.children.find((c: any) => c.type === 'text');
                  if (textNode) {
                    textNode.value = remainingText;
                  }
                } else {
                  // テキストが残っていない場合は段落を削除
                  node.children.shift();
                }
              }
            }
          }
        }

        // Transform to a custom node that will be rendered with hast
        data.hName = 'div';
        data.hProperties = {
          className: ['qiita-note', `qiita-note-${noteType}`]
        };
      }
    });
  };
};
