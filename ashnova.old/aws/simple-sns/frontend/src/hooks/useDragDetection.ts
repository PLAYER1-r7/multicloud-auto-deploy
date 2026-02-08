import { useState, useCallback } from 'react';

/**
 * ドラッグ検出の閾値（ピクセル）
 * この値以上マウスが移動した場合、ドラッグと判定する
 */
const DRAG_THRESHOLD = 5;

interface DragDetectionHandlers {
  onMouseDown: (e: React.MouseEvent) => void;
  onMouseUp: (e: React.MouseEvent) => void;
}

/**
 * ドラッグとクリックを区別するためのカスタムフック
 * 
 * @param onClick - クリック時に実行するコールバック（ドラッグでない場合のみ実行）
 * @returns マウスイベントハンドラー
 * 
 * @example
 * ```tsx
 * const handleClick = () => console.log('clicked!');
 * const { onMouseDown, onMouseUp } = useDragDetection(handleClick);
 * 
 * <div onMouseDown={onMouseDown} onMouseUp={onMouseUp}>
 *   Click or drag me
 * </div>
 * ```
 */
export const useDragDetection = (onClick: () => void): DragDetectionHandlers => {
  const [dragStart, setDragStart] = useState<{ x: number; y: number } | null>(null);

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    setDragStart({ x: e.clientX, y: e.clientY });
  }, []);

  const onMouseUp = useCallback((e: React.MouseEvent) => {
    if (dragStart) {
      const deltaX = Math.abs(e.clientX - dragStart.x);
      const deltaY = Math.abs(e.clientY - dragStart.y);
      const isDrag = deltaX > DRAG_THRESHOLD || deltaY > DRAG_THRESHOLD;
      
      if (!isDrag) {
        onClick();
      }
      
      setDragStart(null);
    }
  }, [dragStart, onClick]);

  return { onMouseDown, onMouseUp };
};
