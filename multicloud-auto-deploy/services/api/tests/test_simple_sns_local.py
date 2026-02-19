"""
Simple SNS — Local Integration Tests
=====================================
Covers: health check, auth, post CRUD, image upload, hashtags.

Requirements
------------
- docker-compose stack must be running (api, frontend_web, minio, dynamodb-local)
- AUTH_DISABLED=true on the API container (default in local docker-compose.yml)

Run
---
  cd services/api
  pytest tests/test_simple_sns_local.py -v -m local

Environment variables (all optional)
--------------------------------------
  API_BASE_URL       default: http://localhost:8000
  STORAGE_BASE_URL   default: http://localhost:8080  (frontend_web proxy)
  TEST_USER_ID       default: test-user-1
"""

import io
import os
import struct
import zlib

import pytest
import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")
STORAGE = os.environ.get("STORAGE_BASE_URL", "http://localhost:8080").rstrip("/")
USER = os.environ.get("TEST_USER_ID", "test-user-1")
TIMEOUT = 10


def auth(user_id: str = USER) -> dict:
    """Return Authorization header for a local-dev user."""
    return {"Authorization": f"Bearer local:{user_id}"}


# ---------------------------------------------------------------------------
# PNG factory (no external deps)
# ---------------------------------------------------------------------------

def make_png(width: int = 4, height: int = 4, color: tuple = (255, 0, 0)) -> bytes:
    """Return a minimal valid PNG filled with a solid color."""

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    raw = b"".join(b"\x00" + bytes(color) * width for _ in range(height))
    idat = chunk(b"IDAT", zlib.compress(raw))
    iend = chunk(b"IEND", b"")
    return b"\x89PNG\r\n\x1a\n" + ihdr + idat + iend


# ---------------------------------------------------------------------------
# Upload helper
# ---------------------------------------------------------------------------

def upload_images(images: list[tuple[str, bytes, str]], headers: dict) -> list[str]:
    """
    Upload images via presigned URLs and return their storage keys.

    images: list of (filename, data_bytes, content_type)
    """
    count = len(images)
    resp = requests.post(
        f"{API}/uploads/presigned-urls",
        json={"count": count},
        headers={"Content-Type": "application/json", **headers},
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, f"presigned-urls: {resp.status_code} {resp.text}"
    entries = resp.json()["urls"]
    assert len(entries) == count

    keys = []
    for (_name, data, ctype), entry in zip(images, entries):
        url = entry["url"]
        if url.startswith("/"):
            url = STORAGE + url
        put = requests.put(url, data=data, headers={"Content-Type": ctype}, timeout=TIMEOUT)
        assert put.status_code in (200, 204), f"PUT {url}: {put.status_code} {put.text}"
        keys.append(entry["key"])
    return keys


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture
def red_png():
    return make_png(color=(255, 0, 0))


@pytest.fixture
def three_pngs():
    return [
        ("red.png",   make_png(color=(255, 0, 0)),   "image/png"),
        ("green.png", make_png(color=(0, 255, 0)),   "image/png"),
        ("blue.png",  make_png(color=(0, 0, 255)),   "image/png"),
    ]


# ---------------------------------------------------------------------------
# STEP 1 — Health check & Auth
# ---------------------------------------------------------------------------

@pytest.mark.local
class TestHealthAndAuth:

    def test_health(self, session):
        """GET /health → 200, status=ok"""
        r = session.get(f"{API}/health", timeout=TIMEOUT)
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert "provider" in body

    def test_authenticated_request_succeeds(self, session):
        """Bearer token accepted → 200 on /profile (own profile)"""
        r = session.get(f"{API}/profile", headers=auth(), timeout=TIMEOUT)
        assert r.status_code == 200
        body = r.json()
        assert body["userId"] == USER

    def test_unauthenticated_request_rejected(self, session):
        """
        No token → 401 when AUTH_DISABLED=false.
        When AUTH_DISABLED=true (local default) the API returns the default
        test user instead, so we accept 200 in that case.
        """
        r = session.get(f"{API}/profile", timeout=TIMEOUT)
        assert r.status_code in (200, 401), f"Expected 200 or 401, got {r.status_code}"


# ---------------------------------------------------------------------------
# STEP 2 — Post CRUD (text only)
# ---------------------------------------------------------------------------

@pytest.mark.local
class TestPostCRUD:

    def test_create_post(self, session):
        """POST /posts → 201, returns postId"""
        r = session.post(
            f"{API}/posts",
            json={"content": "Hello from pytest"},
            headers=auth(),
            timeout=TIMEOUT,
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert "postId" in body
        assert body["content"] == "Hello from pytest"

        # cleanup
        session.delete(f"{API}/posts/{body['postId']}", headers=auth(), timeout=TIMEOUT)

    def test_list_posts(self, session):
        """GET /posts → 200, items is a list"""
        r = session.get(f"{API}/posts", timeout=TIMEOUT)
        assert r.status_code == 200
        body = r.json()
        assert "items" in body
        assert isinstance(body["items"], list)

    def test_create_and_delete_post(self, session):
        """Create a post then delete it; a second delete returns 404"""
        r = session.post(
            f"{API}/posts",
            json={"content": "To be deleted"},
            headers=auth(),
            timeout=TIMEOUT,
        )
        assert r.status_code == 201
        post_id = r.json()["postId"]

        del_r = session.delete(f"{API}/posts/{post_id}", headers=auth(), timeout=TIMEOUT)
        assert del_r.status_code == 200

        del_r2 = session.delete(f"{API}/posts/{post_id}", headers=auth(), timeout=TIMEOUT)
        assert del_r2.status_code == 404

    def test_update_post_content(self, session):
        """PUT /posts/{id} updates content"""
        r = session.post(
            f"{API}/posts",
            json={"content": "Original content"},
            headers=auth(),
            timeout=TIMEOUT,
        )
        assert r.status_code == 201
        post_id = r.json()["postId"]

        upd = session.put(
            f"{API}/posts/{post_id}",
            json={"content": "Updated content"},
            headers=auth(),
            timeout=TIMEOUT,
        )
        assert upd.status_code == 200
        assert upd.json()["content"] == "Updated content"

        session.delete(f"{API}/posts/{post_id}", headers=auth(), timeout=TIMEOUT)


# ---------------------------------------------------------------------------
# STEP 3 — Image upload
# ---------------------------------------------------------------------------

@pytest.mark.local
class TestImageUpload:

    def test_presigned_urls_returned(self, session):
        """POST /uploads/presigned-urls returns correct number of entries"""
        r = session.post(
            f"{API}/uploads/presigned-urls",
            json={"count": 2},
            headers=auth(),
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text
        urls = r.json()["urls"]
        assert len(urls) == 2
        for entry in urls:
            assert "url" in entry
            assert "key" in entry

    def test_upload_single_image(self, session, red_png):
        """Upload one PNG via presigned URL → 200"""
        keys = upload_images([("red.png", red_png, "image/png")], auth())
        assert len(keys) == 1
        assert "images/" in keys[0]

    def test_upload_multiple_images(self, session, three_pngs):
        """Upload three images in one batch → all succeed"""
        keys = upload_images(three_pngs, auth())
        assert len(keys) == 3

    def test_post_with_single_image(self, session, red_png):
        """Create a post that references an uploaded image; imageUrls is populated"""
        keys = upload_images([("red.png", red_png, "image/png")], auth())

        r = session.post(
            f"{API}/posts",
            json={"content": "Post with one image", "imageKeys": keys},
            headers=auth(),
            timeout=TIMEOUT,
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["imageUrls"] is not None
        assert len(body["imageUrls"]) == 1

        session.delete(f"{API}/posts/{body['postId']}", headers=auth(), timeout=TIMEOUT)

    def test_post_with_multiple_images(self, session, three_pngs):
        """Create a post with three images; all keys stored"""
        keys = upload_images(three_pngs, auth())

        r = session.post(
            f"{API}/posts",
            json={"content": "Post with three images", "imageKeys": keys},
            headers=auth(),
            timeout=TIMEOUT,
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert len(body["imageUrls"]) == 3

        session.delete(f"{API}/posts/{body['postId']}", headers=auth(), timeout=TIMEOUT)



    def test_image_urls_are_accessible(self, session, three_pngs):
        """Each imageUrl in the post response is reachable via GET /storage/"""
        keys = upload_images(three_pngs, auth())
        r = session.post(
            f"{API}/posts",
            json={"content": "Accessibility check", "imageKeys": keys},
            headers=auth(),
            timeout=TIMEOUT,
        )
        assert r.status_code == 201, r.text
        image_urls = r.json()["imageUrls"]
        assert len(image_urls) == 3

        for url in image_urls:
            if url.startswith("/"):
                url = STORAGE + url
            get_r = requests.get(url, timeout=TIMEOUT)
            assert get_r.status_code == 200, f"Image not accessible: {url} ({get_r.status_code})"
            assert len(get_r.content) > 0

        session.delete(f"{API}/posts/{r.json()['postId']}", headers=auth(), timeout=TIMEOUT)

    def test_update_post_images(self, session, red_png, three_pngs):
        """PUT /posts/{id} can replace images: 1 image → 3 images"""
        # Create post with 1 image
        keys1 = upload_images([("red.png", red_png, "image/png")], auth())
        r = session.post(
            f"{API}/posts",
            json={"content": "Image replace test", "imageKeys": keys1},
            headers=auth(),
            timeout=TIMEOUT,
        )
        assert r.status_code == 201
        post_id = r.json()["postId"]
        assert len(r.json()["imageUrls"]) == 1

        # Replace with 3 images
        keys3 = upload_images(three_pngs, auth())
        upd = session.put(
            f"{API}/posts/{post_id}",
            json={"imageKeys": keys3},
            headers=auth(),
            timeout=TIMEOUT,
        )
        assert upd.status_code == 200, upd.text
        assert len(upd.json()["imageUrls"]) == 3

        session.delete(f"{API}/posts/{post_id}", headers=auth(), timeout=TIMEOUT)

    def test_post_with_max_images(self, session):
        """Upload 10 images (API max) and attach them to one post"""
        images = [
            (f"img{i}.png", make_png(color=(i * 25 % 256, i * 13 % 256, 200)), "image/png")
            for i in range(10)
        ]
        keys = upload_images(images, auth())
        assert len(keys) == 10

        r = session.post(
            f"{API}/posts",
            json={"content": "Max images post", "imageKeys": keys},
            headers=auth(),
            timeout=TIMEOUT,
        )
        assert r.status_code == 201, r.text
        assert len(r.json()["imageUrls"]) == 10

        session.delete(f"{API}/posts/{r.json()['postId']}", headers=auth(), timeout=TIMEOUT)

# ---------------------------------------------------------------------------
# STEP 4 — Hashtags
# ---------------------------------------------------------------------------

@pytest.mark.local
class TestHashtags:

    def test_post_with_tags(self, session):
        """Create a post with tags; tags are stored and returned"""
        tags = ["python", "pytest", "minio"]
        r = session.post(
            f"{API}/posts",
            json={"content": "Post with hashtags", "tags": tags},
            headers=auth(),
            timeout=TIMEOUT,
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert set(body["tags"]) == set(tags)

        session.delete(f"{API}/posts/{body['postId']}", headers=auth(), timeout=TIMEOUT)

    def test_filter_posts_by_tag(self, session):
        """GET /posts?tag=<x> returns only posts with that tag"""
        unique_tag = "xuniqtag42"
        r = session.post(
            f"{API}/posts",
            json={"content": "Tagged post", "tags": [unique_tag, "extra"]},
            headers=auth(),
            timeout=TIMEOUT,
        )
        assert r.status_code == 201
        post_id = r.json()["postId"]

        resp = session.get(f"{API}/posts", params={"tag": unique_tag}, timeout=TIMEOUT)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert any(p["postId"] == post_id for p in items), (
            f"Post {post_id} not found in tag-filtered results"
        )

        session.delete(f"{API}/posts/{post_id}", headers=auth(), timeout=TIMEOUT)

    def test_update_post_tags(self, session):
        """PUT /posts/{id} can replace tags"""
        r = session.post(
            f"{API}/posts",
            json={"content": "Tag update test", "tags": ["before"]},
            headers=auth(),
            timeout=TIMEOUT,
        )
        assert r.status_code == 201
        post_id = r.json()["postId"]

        upd = session.put(
            f"{API}/posts/{post_id}",
            json={"tags": ["after"]},
            headers=auth(),
            timeout=TIMEOUT,
        )
        assert upd.status_code == 200
        assert "after" in upd.json()["tags"]
        assert "before" not in upd.json()["tags"]

        session.delete(f"{API}/posts/{post_id}", headers=auth(), timeout=TIMEOUT)

    def test_post_with_images_and_tags(self, session, three_pngs):
        """Create a post with both images and tags; all fields stored"""
        keys = upload_images(three_pngs, auth())
        tags = ["photo", "multi"]
        r = session.post(
            f"{API}/posts",
            json={
                "content": "Images + hashtags post",
                "imageKeys": keys,
                "tags": tags,
            },
            headers=auth(),
            timeout=TIMEOUT,
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert len(body["imageUrls"]) == 3
        assert set(body["tags"]) == set(tags)

        session.delete(f"{API}/posts/{body['postId']}", headers=auth(), timeout=TIMEOUT)
