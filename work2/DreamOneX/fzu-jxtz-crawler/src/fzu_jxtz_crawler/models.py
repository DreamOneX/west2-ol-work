"""
Data models for the FZU announcement crawler.
"""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Attachment:
    """
    Represents an attachment in an announcement.
    
    If local_path is not None, it means the attachment has been downloaded.

    attachment_id: 22-character identifier
        Format: zfill12(owner_code) + zfill10(file_code)
    """
    attachment_id: str
    name: str
    download_times: int
    url: str
    owner_code: str
    file_code: str
    local_path: str | None


@dataclass
class AnnouncementEntry:
    """
    Represents an announcement entry.

    Note:
        `body` and `attachments` may be None. This can indicate either:
        (1) the crawler has not fetched the detail page yet, or
        (2) the announcement has no body/attachments.

    Supported URL formats:
        1) https://jwch.fzu.edu.cn/content.jsp?urltype=news.NewsContentUrl&wbtreeid=1036&wbnewsid=14278
        2) https://jwch.fzu.edu.cn/info/1040/14402.htm

    ID derivation:
        The `id` is a 12-character identifier formed by concatenating:
        - the second-to-last numeric part (tree/category id), left-padded to 6 digits, and
        - the last numeric part (news/content id), left-padded to 6 digits.

        In formula form:
            id = zfill6(tree_id) + zfill6(news_id)

        Examples:
            - wbtreeid=1036, wbnewsid=14278  -> "001036" + "014278" -> "001036014278"
            - /info/1040/14402.htm          -> "001040" + "014402" -> "001040014402"
    """
    announcement_id: str
    url: str
    title: str
    issuer: str
    pub_date: datetime

    body: str | None
    attachments: list[Attachment] | None
