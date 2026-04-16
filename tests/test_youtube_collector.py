"""单元测试：youtube_collector.py"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../bi/python_sdk/outdoor_collector"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../bi/python_sdk/outdoor_collector/collectors"))

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

import youtube_collector as yc


# ── 2.1 _is_youtube_url ───────────────────────────────────────────────────────

class TestIsYoutubeUrl:
    def test_watch_url(self):
        assert yc._is_youtube_url("https://www.youtube.com/watch?v=abc123") is True

    def test_youtu_be_url(self):
        assert yc._is_youtube_url("https://youtu.be/abc123") is True

    def test_shorts_url(self):
        assert yc._is_youtube_url("https://www.youtube.com/shorts/abc123") is True

    def test_youtube_without_www(self):
        assert yc._is_youtube_url("https://youtube.com/watch?v=abc") is True

    def test_instagram_url(self):
        assert yc._is_youtube_url("https://www.instagram.com/p/abc") is False

    def test_empty_string(self):
        assert yc._is_youtube_url("") is False

    def test_none(self):
        assert yc._is_youtube_url(None) is False

    def test_tiktok_url(self):
        assert yc._is_youtube_url("https://www.tiktok.com/@user/video/123") is False


# ── 2.2 _extract_video_id ─────────────────────────────────────────────────────

class TestExtractVideoId:
    def test_watch_format(self):
        assert yc._extract_video_id("https://www.youtube.com/watch?v=abc123") == "abc123"

    def test_youtu_be_format(self):
        assert yc._extract_video_id("https://youtu.be/abc123") == "abc123"

    def test_shorts_format(self):
        assert yc._extract_video_id("https://www.youtube.com/shorts/abc123") == "abc123"

    def test_watch_with_extra_params(self):
        assert yc._extract_video_id("https://www.youtube.com/watch?v=abc123&t=30s") == "abc123"

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError, match="无法从 URL 解析 video_id"):
            yc._extract_video_id("https://www.instagram.com/p/abc")

    def test_youtube_no_video_id_raises(self):
        with pytest.raises(ValueError):
            yc._extract_video_id("https://www.youtube.com/channel/UCxxx")


# ── 2.3 _transform ────────────────────────────────────────────────────────────

class TestTransform:
    def _make_item(self, video_id="vid1", view="1000", like="50", comment="10"):
        return {
            "id": video_id,
            "snippet": {"title": "Test Video", "publishedAt": "2026-01-01T00:00:00Z"},
            "statistics": {"viewCount": view, "likeCount": like, "commentCount": comment},
            "contentDetails": {"duration": "PT4M13S"},
        }

    def test_basic_mapping(self):
        raw = [self._make_item()]
        records = yc._transform(raw, {"vid1": "rec_001"})
        assert len(records) == 1
        r = records[0]
        assert r["video_id"] == "vid1"
        assert r["dingtalk_record_id"] == "rec_001"
        assert r["title"] == "Test Video"
        assert r["view_count"] == 1000
        assert r["like_count"] == 50
        assert r["comment_count"] == 10
        assert r["duration"] == "PT4M13S"
        assert isinstance(r["collected_at"], datetime)

    def test_like_count_none(self):
        """部分视频禁用点赞数，likeCount 不在 statistics 中。"""
        item = {
            "id": "vid2",
            "snippet": {"title": "T", "publishedAt": "2026-01-01T00:00:00Z"},
            "statistics": {"viewCount": "500", "commentCount": "5"},  # 无 likeCount
            "contentDetails": {"duration": "PT1M"},
        }
        records = yc._transform([item], {"vid2": "rec_002"})
        assert records[0]["like_count"] is None

    def test_comment_count_none(self):
        """commentCount 为 None 时写 NULL。"""
        item = {
            "id": "vid3",
            "snippet": {"title": "T", "publishedAt": "2026-01-01T00:00:00Z"},
            "statistics": {"viewCount": "100"},
            "contentDetails": {},
        }
        records = yc._transform([item], {})
        assert records[0]["comment_count"] is None
        assert records[0]["like_count"] is None

    def test_dingtalk_record_id_missing(self):
        """record_id_map 中无对应 video_id 时，dingtalk_record_id 为 None。"""
        raw = [self._make_item("vid_unknown")]
        records = yc._transform(raw, {})
        assert records[0]["dingtalk_record_id"] is None

    def test_multiple_items(self):
        raw = [self._make_item("v1"), self._make_item("v2")]
        records = yc._transform(raw, {"v1": "r1", "v2": "r2"})
        assert len(records) == 2
        assert records[0]["video_id"] == "v1"
        assert records[1]["video_id"] == "v2"


# ── 2.4 collect() 正常路径 ────────────────────────────────────────────────────

class TestCollectNormal:
    def _make_api_item(self, video_id="vid1"):
        return {
            "id": video_id,
            "snippet": {"title": "T", "publishedAt": "2026-01-01T00:00:00Z"},
            "statistics": {"viewCount": "100", "likeCount": "5", "commentCount": "2"},
            "contentDetails": {"duration": "PT1M"},
        }

    @patch("youtube_collector._fetch_urls_from_doris")
    @patch("youtube_collector._fetch_video_stats")
    @patch("youtube_collector.write_to_doris", return_value=3)
    @patch("youtube_collector.update_watermark")
    def test_normal_path(self, mock_wm, mock_write, mock_api, mock_doris):
        mock_doris.return_value = [
            {"record_id": "r1", "url": "https://www.youtube.com/watch?v=vid1"},
            {"record_id": "r2", "url": "https://www.instagram.com/p/abc"},  # 非 YouTube，跳过
        ]
        mock_api.return_value = [self._make_api_item("vid1")]

        with patch.dict(os.environ, {"YOUTUBE_API_KEY": "test_key"}):
            written = yc.collect()

        assert written == 3
        mock_write.assert_called_once()
        mock_wm.assert_called_once()
        # 确认只传了 YouTube URL 的 video_id 给 API
        call_args = mock_api.call_args[0]
        assert "vid1" in call_args[0]

    @patch("youtube_collector._fetch_urls_from_doris")
    @patch("youtube_collector._fetch_video_stats")
    @patch("youtube_collector.write_to_doris", return_value=1)
    @patch("youtube_collector.update_watermark")
    def test_dry_run_skips_write(self, mock_wm, mock_write, mock_api, mock_doris):
        mock_doris.return_value = [
            {"record_id": "r1", "url": "https://youtu.be/vid1"},
        ]
        mock_api.return_value = [self._make_api_item("vid1")]

        with patch.dict(os.environ, {"YOUTUBE_API_KEY": "test_key"}):
            written = yc.collect(dry_run=True)

        assert written == 0
        mock_write.assert_not_called()
        mock_wm.assert_not_called()

    @patch("youtube_collector._fetch_urls_from_doris", return_value=[])
    def test_no_rows_returns_zero(self, mock_doris):
        with patch.dict(os.environ, {"YOUTUBE_API_KEY": "test_key"}):
            written = yc.collect()
        assert written == 0

    @patch("youtube_collector._fetch_urls_from_doris")
    def test_no_youtube_urls_returns_zero(self, mock_doris):
        mock_doris.return_value = [
            {"record_id": "r1", "url": "https://www.instagram.com/p/abc"},
            {"record_id": "r2", "url": "https://www.tiktok.com/@user/video/123"},
        ]
        with patch.dict(os.environ, {"YOUTUBE_API_KEY": "test_key"}):
            written = yc.collect()
        assert written == 0

    def test_missing_api_key_raises(self):
        env = {k: v for k, v in os.environ.items() if k != "YOUTUBE_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(RuntimeError, match="未配置 YOUTUBE_API_KEY"):
                yc.collect()


# ── 2.5 URL 解析失败跳过 ──────────────────────────────────────────────────────

class TestCollectInvalidUrlSkipped:
    @patch("youtube_collector._fetch_urls_from_doris")
    @patch("youtube_collector._fetch_video_stats", return_value=[])
    def test_invalid_youtube_url_skipped(self, mock_api, mock_doris):
        """YouTube 域名但无法解析 video_id → warning 跳过，不中断。"""
        mock_doris.return_value = [
            {"record_id": "r1", "url": "https://www.youtube.com/channel/UCxxx"},
            {"record_id": "r2", "url": "https://www.youtube.com/watch?v=valid123"},
        ]
        mock_api.return_value = []

        with patch.dict(os.environ, {"YOUTUBE_API_KEY": "test_key"}):
            # valid123 会被提取，但 API 返回空，最终 written=0
            written = yc.collect()
        assert written == 0
        # API 被调用（有 valid123）
        mock_api.assert_called_once()


# ── 2.6 视频不存在跳过 ────────────────────────────────────────────────────────

class TestCollectVideoNotFound:
    @patch("youtube_collector._fetch_urls_from_doris")
    @patch("youtube_collector._fetch_video_stats", return_value=[])  # API 返回空 items
    def test_video_not_found_skipped(self, mock_api, mock_doris):
        """API 返回空 items（视频已删除/私有）→ warning 跳过，返回 0。"""
        mock_doris.return_value = [
            {"record_id": "r1", "url": "https://www.youtube.com/watch?v=deleted_vid"},
        ]
        with patch.dict(os.environ, {"YOUTUBE_API_KEY": "test_key"}):
            written = yc.collect()
        assert written == 0


# ── 2.7 API 配额超限 ──────────────────────────────────────────────────────────

class TestCollectQuotaExceeded:
    @patch("youtube_collector._fetch_urls_from_doris")
    @patch(
        "youtube_collector._fetch_video_stats",
        side_effect=RuntimeError("[youtube_collector] YouTube API 配额超限（HTTP 403）"),
    )
    def test_quota_exceeded_raises(self, mock_api, mock_doris):
        mock_doris.return_value = [
            {"record_id": "r1", "url": "https://www.youtube.com/watch?v=vid1"},
        ]
        with patch.dict(os.environ, {"YOUTUBE_API_KEY": "test_key"}):
            with pytest.raises(RuntimeError, match="配额超限"):
                yc.collect()
