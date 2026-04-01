from dataclasses import dataclass


@dataclass
class YoutubeVideo:
    title: str
    thumbnail_url: str
    channel_name: str
    published_at: str
    video_url: str
