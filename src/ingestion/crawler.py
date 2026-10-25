"""URL Crawler for fetching and snapshotting Groww HDFC mutual fund scheme pages."""

from datetime import datetime
import hashlib
import json
import logging
from pathlib import Path
from typing import List, Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.utils.logger import get_logger

logger = get_logger("src.ingestion.crawler")

# Standard desktop browser headers to prevent anti-scraping blocks
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
        "image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}


def compute_sha256(file_path: Path) -> str:
    """Compute the SHA-256 hash of a file on disk."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
    reraise=True,
)
def download_html(url: str, dest_path: Path, timeout: float = 15.0) -> bool:
    """Download HTML content from a URL and save to destination path.

    Args:
        url: The web URL to fetch.
        dest_path: Path where the HTML snapshot should be stored.
        timeout: Request timeout in seconds.

    Returns:
        True if download succeeded, False otherwise.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Fetching URL: {url}")

    with httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=timeout) as client:
        response = client.get(url)
        response.raise_for_status()
        html_content = response.text

    # Verify response contains valid HTML
    if not html_content or len(html_content.strip()) < 100:
        raise ValueError(f"Downloaded content from {url} is unexpectedly empty or short")

    dest_path.write_text(html_content, encoding="utf-8")
    logger.info(f"Successfully saved {len(html_content)} bytes to {dest_path}")
    return True


def is_update_needed(manifest_entry: dict, dest_path: Path) -> bool:
    """Check if a scheme page needs to be re-downloaded.

    Returns True if file does not exist, manifest sha256 is missing,
    or current file hash does not match stored hash.
    """
    if not dest_path.exists() or dest_path.stat().st_size == 0:
        return True

    stored_hash = manifest_entry.get("sha256")
    if not stored_hash:
        return True

    current_hash = compute_sha256(dest_path)
    return current_hash != stored_hash


def read_manifest(manifest_path: Path = Path("data/sources_manifest.json")) -> dict:
    """Read the sources manifest file."""
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest file not found at {manifest_path}")
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def crawl_scheme(
    entry: dict,
    force: bool = False,
    manifest_path: Path = Path("data/sources_manifest.json"),
) -> dict:
    """Crawl and snapshot a single scheme entry from manifest."""
    url = entry["url"]
    scheme_id = entry["scheme_id"]
    dest_path = Path(entry.get("download_path") or f"data/raw/{scheme_id}/groww_page.html")

    if force or is_update_needed(entry, dest_path):
        download_html(url, dest_path)
        new_hash = compute_sha256(dest_path)
        entry["sha256"] = new_hash
        entry["download_path"] = str(dest_path).replace("\\", "/")
        entry["downloaded_at"] = datetime.utcnow().isoformat() + "Z"
        logger.info(f"Updated {scheme_id} (SHA-256: {new_hash[:12]}...)")
    else:
        logger.info(f"Skipping {scheme_id}: Snapshot is up-to-date (idempotent)")

    return entry


def crawl_all(
    manifest_path: Path = Path("data/sources_manifest.json"),
    force: bool = False,
) -> List[dict]:
    """Crawl and snapshot all 5 canonical Groww schemes defined in manifest.

    Args:
        manifest_path: Path to the sources_manifest.json.
        force: If True, forces re-downloading even if hash matches.

    Returns:
        Updated list of source manifest entries.
    """
    manifest = read_manifest(manifest_path)
    sources = manifest.get("sources", [])
    logger.info(f"Starting crawl for {len(sources)} canonical Groww schemes (force={force})")

    updated_count = 0
    skipped_count = 0

    for entry in sources:
        url = entry["url"]
        scheme_id = entry["scheme_id"]
        dest_path = Path(entry.get("download_path") or f"data/raw/{scheme_id}/groww_page.html")

        if force or is_update_needed(entry, dest_path):
            try:
                crawl_scheme(entry, force=force, manifest_path=manifest_path)
                updated_count += 1
            except Exception as e:
                logger.error(f"Failed to crawl {scheme_id} ({url}): {e}")
                raise
        else:
            skipped_count += 1
            logger.info(f"Skipping {scheme_id}: Snapshot is up-to-date (idempotent)")

    # Persist updated hashes and timestamps
    manifest["last_updated"] = datetime.utcnow().strftime("%Y-%m-%d")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    logger.info(
        f"Crawl completed. Updated: {updated_count}, Skipped (unchanged): {skipped_count}"
    )
    return sources


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Groww Scheme URL Crawler")
    parser.add_argument("--force", action="store_true", help="Force re-download of all pages")
    args = parser.parse_args()

    crawl_all(force=args.force)
