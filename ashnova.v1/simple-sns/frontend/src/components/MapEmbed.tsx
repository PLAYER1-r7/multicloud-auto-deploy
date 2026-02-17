import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix for default marker icon in Leaflet with Webpack/Vite
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

// @ts-ignore
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
});

interface MapEmbedProps {
  latitude: number;
  longitude: number;
  title?: string;
  zoom?: number;
  height?: number | string;
}

/**
 * 地図を埋め込むコンポーネント
 * 緯度・経度を指定してマーカー付き地図を表示
 */
export const MapEmbed: React.FC<MapEmbedProps> = ({ 
  latitude, 
  longitude, 
  title,
  zoom = 13,
  height = 300,
}) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);

  useEffect(() => {
    if (!mapRef.current) return;

    // 既存のマップインスタンスを削除
    if (mapInstanceRef.current) {
      mapInstanceRef.current.remove();
    }

    // 新しいマップを作成
    const map = L.map(mapRef.current, {
      center: [latitude, longitude],
      zoom: zoom,
      scrollWheelZoom: false, // スクロールでズームしない（ページスクロールを優先）
    });

    // OpenStreetMapタイルレイヤーを追加
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map);

    // マーカーを追加
    const marker = L.marker([latitude, longitude]).addTo(map);
    if (title) {
      marker.bindPopup(title);
    }

    mapInstanceRef.current = map;

    // クリーンアップ
    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [latitude, longitude, zoom, title]);

  return (
    <div 
      ref={mapRef} 
      style={{ 
        height: typeof height === 'number' ? `${height}px` : height,
        width: '100%',
        borderRadius: '8px',
        overflow: 'hidden',
        marginTop: '8px',
        marginBottom: '8px',
      }}
    />
  );
};
