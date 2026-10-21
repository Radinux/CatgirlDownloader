import base64
import requests
import time
from typing import Optional

from .types import NSFWOption
from .danbooru import DanbooruDownloaderAPI, _REQUEST_HEADERS, _BATCH_SIZE, _displayable_extensions

_MAX_TAGS = 6
# Same idea as Danbooru's censored tags, plus e621's own tags for minors.
_FORBIDDEN_TAGS = tuple(
    base64.b64decode(tag.encode('utf-8')).decode('utf-8')
    for tag in ('c2hvdGE=', 'bG9saQ==', 'eW91bmc=', 'Y3Vi')
)
# Tags e621 files under "artist" that are not artists.
_NOT_ARTISTS = {"conditional_dnp", "sound_warning", "epilepsy_warning", "unknown_artist"}


class E621DownloaderAPI(DanbooruDownloaderAPI):
    """e621 runs a Danbooru fork: same tag search and settings window,
    different post format."""

    _site_name = "e621"
    _tags_preference = "e621_tags"
    _max_tags = _MAX_TAGS
    _tag_limit_hint = f"You can use at most {_MAX_TAGS} tags."
    _forbidden_tags = _FORBIDDEN_TAGS
    _forbidden_tags_message = "Some tags are not allowed in CatgirlDownloader and have been automatically removed from your settings."
    _safe_rating = "rating:s"
    _explicit_rating = "rating:e"

    def __init__(self, settings=None) -> None:
        super().__init__(settings)
        self.endpoint = "https://e621.net"

    @staticmethod
    def _post_tags(post: dict) -> list[str]:
        return [tag for group in (post.get("tags") or {}).values() for tag in group]

    def get_random_post(self, nsfw_mode: NSFWOption = NSFWOption.BLOCK_NSFW, max_retries: int = 3) -> Optional[dict]:
        self.last_error = None
        if len(self.tags.split()) > _MAX_TAGS:
            self.last_error = f"e621: use at most {_MAX_TAGS} tags"
            return None
        tags = self._build_tags_query(nsfw_mode)
        params = {
            "limit": _BATCH_SIZE,
            "tags": f"{tags} order:random".strip(),
        }
        displayable = _displayable_extensions()

        for attempt in range(max_retries):
            try:
                r = requests.get(
                    f"{self.endpoint}/posts.json",
                    params=params,
                    headers=_REQUEST_HEADERS,
                    timeout=10,
                )
            except Exception as e:
                print(e)
                self.last_error = "Could not reach e621"
                return None
            if r.status_code != 200:
                self.last_error = self._error_from_response(r).replace("Danbooru", "e621")
                print(self.last_error)
                return None
            try:
                posts = r.json().get("posts")
            except (ValueError, AttributeError):
                self.last_error = "e621 sent an invalid response"
                return None
            if not isinstance(posts, list) or not posts:
                self.last_error = "No e621 posts match these tags"
                return None

            for post in posts:
                if any(tag in self._forbidden_tags for tag in self._post_tags(post)):
                    continue
                file = post.get("file") or {}
                if not file.get("url"):
                    continue
                if (file.get("ext") or "").lower() not in displayable:
                    continue
                self.info = post
                return post
            print(f'Attempt {attempt + 1}: no displayable post in batch, retrying...')

        print(f'Could not find suitable post after {max_retries} attempts')
        self.last_error = "No displayable e621 image found for these tags"
        return None

    def get_image_url(self, nsfw_mode: NSFWOption = NSFWOption.BLOCK_NSFW) -> Optional[str]:
        post = self.get_random_post(nsfw_mode)
        if post:
            return post["file"]["url"]
        return None

    def get_artist(self, info: Optional[dict] = None) -> Optional[str]:
        data = info if info else self.info
        if not data:
            return None
        artists = (data.get("tags") or {}).get("artist") or []
        for artist in artists:
            if artist not in _NOT_ARTISTS:
                return artist
        return None

    def get_filename_suggestion(self, extension: Optional[str], info: Optional[dict] = None) -> str:
        data = info if info else self.info
        post_id = str(data.get("id", int(time.time()))) if data else str(int(time.time()))
        if extension:
            return f"e621_{post_id}.{extension}"
        return f"e621_{post_id}"
