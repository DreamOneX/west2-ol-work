"""
URL utilities for constructing crawler URLs.
"""
from urllib.parse import ParseResult, urljoin, urlparse, parse_qs


BASE_URL = "https://jwch.fzu.edu.cn"
URL_TPL = "https://jwch.fzu.edu.cn/jxtz/{}.htm"
MAIN_PAGE_URL = "https://jwch.fzu.edu.cn/jxtz.htm"
DOWNLOAD_TIMES_URL_TPL = "https://jwch.fzu.edu.cn/system/resource/code/news/click/clicktimes.jsp?wbnewsid={file_code}&owner={owner}&type=wbnewsfile&randomid=nattach"


def construct_full_url(href: str, base_url: str = BASE_URL) -> str:
    """
    Construct a full URL from a possibly relative href.
    
    This function handles:
    - Relative URLs starting with '/' (e.g., '/info/1013/16745.htm')
    - Relative URLs without leading '/' (e.g., 'info/1013/16745.htm')
    - Already absolute URLs (e.g., 'https://example.com/page')
    - Fragment-only URLs (e.g., '#section')
    - Query-only URLs (e.g., '?param=value')
    
    Args:
        href: The URL or relative path to construct
        base_url: The base URL to use for relative URLs (default: BASE_URL)
    
    Returns:
        A fully qualified URL
    
    Examples:
        >>> construct_full_url('/info/1013/16745.htm')
        'https://jwch.fzu.edu.cn/info/1013/16745.htm'
        >>> construct_full_url('https://example.com/page')
        'https://example.com/page'
    """
    if not href:
        return base_url
    
    # urljoin properly handles all cases:
    # - Absolute URLs are returned as-is
    # - Relative URLs are joined with the base
    # - Handles edge cases like fragments, queries, etc.
    return urljoin(base_url, href)


def build_page_urls(max_page: int, start_page: int | None = None, end_page: int | None = None) -> list[str]:
    """
    Build a list of URLs to crawl, from latest to oldest.
    
    This is a pure function that does not make network requests.
    
    The url list includes (latest -> oldest):
        https://jwch.fzu.edu.cn/jxtz.htm  (newest page)
        https://jwch.fzu.edu.cn/jxtz/206.htm
        https://jwch.fzu.edu.cn/jxtz/205.htm
        ...
        https://jwch.fzu.edu.cn/jxtz/1.htm  (oldest page)
    
    Args:
        max_page: The maximum page number (typically total_pages - 1)
        start_page: Starting page number (inclusive). None means start from max_page.
        end_page: Ending page number (inclusive). None means end at page 1.
        
    Returns:
        List of URLs, sorted from newest to oldest.
        
    Examples:
        build_page_urls(206)  # Get all pages
        build_page_urls(206, start_page=206, end_page=200)  # Get pages 206-200
    """
    urls: list[str] = [MAIN_PAGE_URL]
    
    # Set default values
    actual_start = start_page if start_page is not None else max_page
    actual_end = end_page if end_page is not None else 1
    
    # Validate range
    actual_start = min(actual_start, max_page)
    actual_end = max(actual_end, 1)
    
    # Iterate from start_page to end_page in descending order (newest to oldest)
    for i in range(actual_start, actual_end - 1, -1):
        urls.append(URL_TPL.format(i))
    
    return urls


def derive_content_id_from_url(url: str) -> str:
    """
    Derive the 12-character identifier from a URL.

    For detail, see AnnouncementEntry.id.

    Format:
        id = zfill6(tree_id) + zfill6(news_id)
    
    Examples:
        derive_id_from_url("https://jwch.fzu.edu.cn/content.jsp?urltype=news.NewsContentUrl&wbtreeid=1036&wbnewsid=14278")
        -> "001036014278"
        derive_id_from_url("https://jwch.fzu.edu.cn/info/1040/14402.htm")
        -> "001040014402"
    """
    u: ParseResult = urlparse(url)
    
    if u.path.endswith(".htm"):
        parts = u.path.split("/")
        # Expected structure: .../tree_id/news_id.htm
        if len(parts) >= 2:
            tree_id = parts[-2]
            news_id = parts[-1].replace(".htm", "")
            return tree_id.zfill(6) + news_id.zfill(6)

    elif u.path.endswith("content.jsp"):
        query = parse_qs(u.query)
        tree_id_list = query.get("wbtreeid")
        news_id_list = query.get("wbnewsid")
        
        if tree_id_list and news_id_list:
            tree_id = tree_id_list[0]
            news_id = news_id_list[0]
            return tree_id.zfill(6) + news_id.zfill(6)

    raise ValueError(f"Invalid URL: {url}")


def derive_attachment_id_from_url(url: str) -> str:
    """
    Derive the 22-character identifier from a URL.

    For detail, see Attachment.id.

    Format:
        id = zfill12(owner_code) + zfill10(file_code)
    
    Examples:
        derive_attachment_id_from_url(
            "https://jwch.fzu.edu.cn/system/_content/download.jsp"
            "?urltype=news.DownloadAttachUrl&owner=1744984858&wbfileid=16761392"
        )
        -> "0017449848580016761392"
    """
    u: ParseResult = urlparse(url)
    query = parse_qs(u.query)
    owner_code_list = query.get("owner")
    file_code_list = query.get("wbfileid")
    
    if owner_code_list and file_code_list:
        owner_code = owner_code_list[0]
        file_code = file_code_list[0]
        return owner_code.zfill(12) + file_code.zfill(10)
    
    raise ValueError(f"Invalid URL: {url}")