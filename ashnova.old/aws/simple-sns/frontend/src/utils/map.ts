/**
 * 地図関連のユーティリティ関数
 */

export interface MapLocation {
  latitude: number;
  longitude: number;
  title?: string;
}

/**
 * テキストから地図情報を抽出
 * 
 * サポート形式:
 * 1. マークダウン記法: [map:緯度,経度] または [map:緯度,経度,タイトル]
 * 2. Google Maps URL: https://www.google.com/maps/@35.6762,139.6503,15z
 * 3. Google Maps URL (place): https://www.google.com/maps/place/.../@35.6762,139.6503
 * 4. 座標のみ: 35.6762, 139.6503
 */
export const extractMapLocations = (text: string): MapLocation[] => {
  const locations: MapLocation[] = [];

  // 1. マークダウン記法: [map:lat,lng] または [map:lat,lng,title]
  const markdownPattern = /\[map:([-\d.]+),([-\d.]+)(?:,([^\]]+))?\]/g;
  let match;
  while ((match = markdownPattern.exec(text)) !== null) {
    const latitude = parseFloat(match[1]);
    const longitude = parseFloat(match[2]);
    const title = match[3]?.trim();
    
    if (isValidCoordinate(latitude, longitude)) {
      locations.push({ latitude, longitude, title });
    }
  }

  // 2. Google Maps URL
  const googleMapsPatterns = [
    // https://www.google.com/maps/@35.6762,139.6503,15z
    /@([-\d.]+),([-\d.]+),\d+z/g,
    // https://www.google.com/maps/place/.../@35.6762,139.6503
    /@([-\d.]+),([-\d.]+)/g,
    // https://maps.google.com/?q=35.6762,139.6503
    /[?&]q=([-\d.]+),([-\d.]+)/g,
  ];

  for (const pattern of googleMapsPatterns) {
    pattern.lastIndex = 0; // リセット
    while ((match = pattern.exec(text)) !== null) {
      const latitude = parseFloat(match[1]);
      const longitude = parseFloat(match[2]);
      
      if (isValidCoordinate(latitude, longitude)) {
        // 既に同じ座標が追加されていないか確認
        const exists = locations.some(
          loc => Math.abs(loc.latitude - latitude) < 0.0001 && 
                 Math.abs(loc.longitude - longitude) < 0.0001
        );
        if (!exists) {
          locations.push({ latitude, longitude });
        }
      }
    }
  }

  return locations;
};

/**
 * 座標が有効な範囲内かチェック
 */
const isValidCoordinate = (latitude: number, longitude: number): boolean => {
  return (
    !isNaN(latitude) &&
    !isNaN(longitude) &&
    latitude >= -90 &&
    latitude <= 90 &&
    longitude >= -180 &&
    longitude <= 180
  );
};

/**
 * テキストから地図記法を削除（プレーンテキスト表示用）
 */
export const removeMapNotation = (text: string): string => {
  // [map:lat,lng,title] を削除
  return text.replace(/\[map:[-\d.]+,[-\d.]+(?:,[^\]]+)?\]/g, '');
};

/**
 * 地図のプレビューテキストを生成
 */
export const getMapPreviewText = (location: MapLocation): string => {
  const coords = `${location.latitude.toFixed(4)}, ${location.longitude.toFixed(4)}`;
  return location.title ? `📍 ${location.title} (${coords})` : `📍 ${coords}`;
};
