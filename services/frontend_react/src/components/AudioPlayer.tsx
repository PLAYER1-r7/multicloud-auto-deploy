/** Polly 音声再生コンポーネント（PHASE 2） */

import React, { useState, useRef } from "react";
import type { AudioResponse } from "../types/learning";

interface AudioPlayerProps {
  audioData: AudioResponse;
  materialId: string;
}

interface AudioTrack {
  name: string;
  url: string;
  label: string;
}

/**
 * 音声再生コンポーネント
 * - Polly で生成された複数の音声トラックを再生
 * - 字幕表示、ダウンロード機能
 */
export default function AudioPlayer({
  audioData,
  materialId,
}: AudioPlayerProps) {
  const initialTrack = Object.keys(audioData.audio_urls)[0] ?? null;
  const [currentTrack, setCurrentTrack] = useState<string | null>(initialTrack);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [loading, setLoading] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);

  // オーディオトラック一覧を構成
  const tracks: AudioTrack[] = Object.entries(audioData.audio_urls).map(
    ([key, url]) => ({
      name: key,
      url,
      label: formatTrackLabel(key),
    }),
  );

  function formatTrackLabel(trackName: string): string {
    const labels: Record<string, string> = {
      explanation: "詳細説明",
      outline: "アウトライン",
      concept_1: "概念 1",
      concept_2: "概念 2",
      step_1: "ステップ 1",
      step_2: "ステップ 2",
      step_3: "ステップ 3",
      step_4: "ステップ 4",
      quiz: "クイズ",
    };
    return labels[trackName] || trackName;
  }

  // トラック選択時の処理
  const handleSelectTrack = async (trackName: string) => {
    const track = tracks.find((t) => t.name === trackName);
    if (!track) return;

    setCurrentTrack(trackName);
    setLoading(true);
    setIsPlaying(false);
    setCurrentTime(0);

    if (audioRef.current) {
      audioRef.current.src = track.url;
      audioRef.current.load();
    }

    setLoading(false);
  };

  // 再生/一時停止
  const togglePlayPause = () => {
    if (!audioRef.current || !currentTrack) return;

    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play().catch((err) => {
        console.error("再生エラー:", err);
        setIsPlaying(false);
      });
      setIsPlaying(true);
    }
  };

  // メタデータ読み込み時
  const handleLoadedMetadata = () => {
    if (audioRef.current) {
      setDuration(audioRef.current.duration);
    }
  };

  // 時間更新時
  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
    }
  };

  // 再生終了時
  const handleEnded = () => {
    setIsPlaying(false);
  };

  // ボリューム変更
  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newVolume = parseFloat(e.target.value);
    setVolume(newVolume);
    if (audioRef.current) {
      audioRef.current.volume = newVolume;
    }
  };

  // シークバー変更
  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newTime = parseFloat(e.target.value);
    setCurrentTime(newTime);
    if (audioRef.current) {
      audioRef.current.currentTime = newTime;
    }
  };

  // ダウンロード
  const handleDownload = async (trackName: string) => {
    const track = tracks.find((t) => t.name === trackName);
    if (!track) return;

    try {
      const response = await fetch(track.url);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${materialId}-${trackName}.mp3`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error("ダウンロード失敗:", err);
    }
  };

  const formatTime = (seconds: number): string => {
    if (!isFinite(seconds)) return "0:00";
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div className="w-full bg-gradient-to-br from-blue-50 to-purple-50 rounded-lg shadow-lg overflow-hidden">
      {/* ── ヘッダー ──────────────────────────────────── */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 px-6 py-4 text-white">
        <div className="flex items-center gap-3">
          <span aria-hidden="true">🔊</span>
          <div>
            <h3 className="font-bold text-lg">音声教材</h3>
            <p className="text-sm text-blue-100">
              Polly で生成された音声を再生
            </p>
          </div>
        </div>
      </div>

      {/* ── トラック選択 ──────────────────────────────────── */}
      <div className="px-6 py-4 border-b border-blue-200">
        <p className="text-sm text-gray-600 mb-3 font-semibold">
          トラックを選択:
        </p>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
          {tracks.map((track) => (
            <button
              key={track.name}
              onClick={() => handleSelectTrack(track.name)}
              className={`px-4 py-2 rounded text-sm font-medium transition ${
                currentTrack === track.name
                  ? "bg-blue-600 text-white"
                  : "bg-white text-gray-700 border border-gray-300 hover:border-blue-400"
              }`}
            >
              {track.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── 再生コントロール ──────────────────────────────────── */}
      {currentTrack && (
        <div className="px-6 py-6">
          {/* ── 再生状態表示 ──────────────────────────────────── */}
          {loading && (
            <div className="mb-4 p-3 bg-blue-100 rounded text-sm text-blue-700">
              🔄 読み込み中...
            </div>
          )}

          {/* ── プレイヤー ──────────────────────────────────── */}
          <div className="space-y-4">
            {/* ── ボタン ──────────────────────────────────── */}
            <div className="flex items-center justify-center gap-4">
              <button
                onClick={togglePlayPause}
                disabled={loading || !currentTrack}
                className={`p-3 rounded-full transition ${
                  isPlaying
                    ? "bg-red-500 hover:bg-red-600 text-white"
                    : "bg-blue-600 hover:bg-blue-700 text-white"
                } disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                {isPlaying ? (
                  <span aria-hidden="true">⏸️</span>
                ) : (
                  <span aria-hidden="true">▶️</span>
                )}
              </button>

              {/* ── 時間表示 ──────────────────────────────────── */}
              <div className="text-sm text-gray-600 min-w-12">
                {formatTime(currentTime)}
              </div>

              {/* ── プログレスバー ──────────────────────────────────── */}
              <input
                type="range"
                min="0"
                max={duration || 0}
                value={currentTime}
                onChange={handleSeek}
                className="flex-1 h-2 bg-gray-300 rounded-lg appearance-none cursor-pointer"
                disabled={!duration}
              />

              {/* ── 合計時間 ──────────────────────────────────── */}
              <div className="text-sm text-gray-600 min-w-12 text-right">
                {formatTime(duration)}
              </div>
            </div>

            {/* ── ボリューム＆ダウンロード ──────────────────────────────────── */}
            <div className="flex items-center gap-4 justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-600">🔊</span>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={volume}
                  onChange={handleVolumeChange}
                  className="w-20 h-2 bg-gray-300 rounded-lg appearance-none cursor-pointer"
                />
              </div>

              <button
                onClick={() => handleDownload(currentTrack)}
                className="flex items-center gap-2 px-3 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition text-sm"
              >
                <span aria-hidden="true">⬇️</span>
                ダウンロード
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── オーディオ要素（非表示） ──────────────────────────────────── */}
      <audio
        ref={audioRef}
        onLoadedMetadata={handleLoadedMetadata}
        onTimeUpdate={handleTimeUpdate}
        onEnded={handleEnded}
        crossOrigin="anonymous"
      />

      {/* ── フッター ──────────────────────────────────── */}
      <div className="px-6 py-3 bg-gray-100 border-t border-gray-300">
        <p className="text-xs text-gray-600">
          📄 フォーマット: {audioData.audio_format.toUpperCase()} · 生成時刻:{" "}
          {new Date(audioData.generated_at).toLocaleString("ja-JP")}
        </p>
      </div>
    </div>
  );
}
