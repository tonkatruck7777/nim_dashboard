import json
import os
from datetime import datetime
import requests
from config import YOUTUBE_API_KEY
from requests.exceptions import HTTPError

CHANNELS_CONFIG_PATH = "channels.json"
KEYWORDS_CONFIG_PATH = "keywords.json"
DATA_FILE_PATH = "youtube_metrics.json"


# ---------- CONFIG LOADERS ----------

def load_channels_config():
    """
    Load list of channels from channels.json.
    Returns a list of dicts, or empty list if file missing/invalid.
    """
    if not os.path.exists(CHANNELS_CONFIG_PATH):
        return []

    try:
        with open(CHANNELS_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except json.JSONDecodeError:
        pass

    return []


def load_keywords_config():
    """
    Load list of keyword sources from keywords.json.
    Returns a list of dicts, or empty list if file missing/invalid.
    """
    if not os.path.exists(KEYWORDS_CONFIG_PATH):
        return []

    try:
        with open(KEYWORDS_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except json.JSONDecodeError:
        pass

    return []


# ---------- STATIC TRACKED VIDEOS (OPTION 1 / 4 PATH) ----------

TRACKED_VIDEOS = {
    "hasan_x8d6K399WW4": {
        "channel_name": "HasanAbi",
        "video_id": "x8d6K399WW4",
        "label": "HasanAbi – we are Charlie Kirk"
    },
    "boyboy_Sfrjpy5cJCs": {
        "channel_name": "Boy Boy",
        "video_id": "Sfrjpy5cJCs",
        "label": "BoyBoy – I snuck into a major arms dealer conference"
    },
    "NavaraMedia_UC2VT3RkiYo": {
        "channel_name": "Navara Media",
        "video_id": "UC2VT3RkiYo",
        "label": "NavaraMedia - The blueprint for an actual revolution"
    },
    "Zeteo_MEtvCw1LzRc": {
        "channel_name": "Zeteo",
        "video_id": "MEtvCw1LzRc",
        "label": "Zeteo - Will Mamdami Challenge the Democratic Leadership"
    },
    "SecularTalk_0YrNUANVel8": {
        "channel_name": "Secular Talk",
        "video_id": "0YrNUANVel8",
        "label": "Secular Talk - The Rogansphere is fucked"
    },
    "PuntersPolitics_3oLIodU0BCU": {
        "channel_name": "Punters Politics",
        "video_id": "3oLIodU0BCU",
        "label": "Punters Politics - Australia gets plaed by Santos"
    },
    "TimDillon_khKJS50odJw": {
        "channel_name": "Tim Dillon",
        "video_id": "khKJS50odJw",
        "label": "Tim Dillon - Wicked Terrible Life Golden Age of Travel"
    },
    "LBC_DAshS2Tl4yw": {
        "channel_name": "LBC",
        "video_id": "DAshS2Tl4yw",
        "label": "LBC - A plan translated from Russian"
    },
    "CaspianReport_cVCDjEfPzII": {
        "channel_name": "Caspian Report",
        "video_id": "cVCDjEfPzII",
        "label": "Caspian Report - Vietnam is beating China at its own game"
    },
    "TuckerCarlson_rDOsm-CYUwQ": {
        "channel_name": "Tucker Carlson",
        "video_id": "rDOsm-CYUwQ",
        "label": "Tucker Carlson - Testing Piers Morgan fee speech"
    },
    "AlexJones_NIRVzbgYk0s": {
        "channel_name": "Alex Jones",
        "video_id": "NIRVzbgYk0s",
        "label": "Alex Jones - Deep State Plotting to overthrow state"
    },
    "BenShapiro_R5qWmHn7SUY": {
        "channel_name": "Ben Shapiro",
        "video_id": "R5qWmHn7SUY",
        "label": "Ben Shapiro - Bannon Epstein connection revealed"
    },
    "MattWalsh_YMsJGnn-h_4": {
        "channel_name": "Matt Walsh",
        "video_id": "YMsJGnn-h_4",
        "label": "Matt Walsh - Ken Burns lies revealed"
    },
    "TimPool_Gku5vUy0K88": {
        "channel_name": "Tim Pool",
        "video_id": "Gku5vUy0K88",
        "label": "Tim Pool - MAGA Civil War"
    },
    "BennyJohnson_Uu7PamYxEHA": {
        "channel_name": "Benny Johnson",
        "video_id": "Uu7PamYxEHA",
        "label": "Benny Johnson - Trump advisor bombshell Somali fraud scandal in Minnesota"
    },
    "Flagrant_buIc5vRqWOQ": {
        "channel_name": "Flagrant",
        "video_id": "buIc5vRqWOQ",
        "label": "Flagrant - America vs Arabic culture"
    },
    "TheoVon_SDq7akQIPMw": {
        "channel_name": "Theo Von",
        "video_id": "SDq7akQIPMw",
        "label": "Theo Von - Past Weekend 626"
    },
}


# ---------- FILE I/O ----------

def load_previous_data():
    """
    Load the previously saved YouTube metrics snapshot from JSON file.
    Returns a dict if file exists, otherwise None.
    """
    if not os.path.exists(DATA_FILE_PATH):
        return None

    with open(DATA_FILE_PATH, "r", encoding="utf-8") as f:
        try:
            previous_data = json.load(f)
        except json.JSONDecodeError:
            return None

    return previous_data


def save_current_data(current_snapshot):
    """
    Save the current snapshot (multiple videos) to JSON file.
    """
    with open(DATA_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(current_snapshot, f, indent=2)


# ---------- DELTAS ----------

def compute_deltas_all(previous_snapshot, current_snapshot):
    """
    Compute deltas for every video between previous and current snapshot.
    Returns a dict:
    {
        "videos": {
            video_key: {
                "views_delta": int or "N/A",
                "views_delta_pct": float or "N/A",
                "likes_delta": ...,
                "comments_delta": ...,
                "subscribers_delta": ...
            },
            ...
        }
    }
    """
    deltas = {"videos": {}}

    if previous_snapshot is None or "videos" not in previous_snapshot:
        # No baseline – all deltas N/A
        for video_key in current_snapshot["videos"]:
            deltas["videos"][video_key] = {
                "views_delta": "N/A",
                "views_delta_pct": "N/A",
                "likes_delta": "N/A",
                "comments_delta": "N/A",
                "subscribers_delta": "N/A",
            }
        return deltas

    prev_videos = previous_snapshot["videos"]

    for video_key, curr_metrics in current_snapshot["videos"].items():
        if video_key in prev_videos:
            prev_metrics = prev_videos[video_key]

            views_delta = curr_metrics["views"] - prev_metrics["views"]
            likes_delta = curr_metrics["likes"] - prev_metrics["likes"]
            comments_delta = curr_metrics["comments"] - prev_metrics["comments"]
            subs_delta = curr_metrics["subscribers"] - prev_metrics["subscribers"]

            prev_views = prev_metrics["views"]
            if prev_views > 0:
                views_delta_pct = (views_delta / prev_views) * 100.0
            else:
                views_delta_pct = "N/A"

            deltas["videos"][video_key] = {
                "views_delta": views_delta,
                "views_delta_pct": views_delta_pct,
                "likes_delta": likes_delta,
                "comments_delta": comments_delta,
                "subscribers_delta": subs_delta,
            }
        else:
            # New video since last snapshot
            deltas["videos"][video_key] = {
                "views_delta": "N/A",
                "views_delta_pct": "N/A",
                "likes_delta": "N/A",
                "comments_delta": "N/A",
                "subscribers_delta": "N/A",
            }

    return deltas


# ---------- DISCOVERY HELPERS ----------

def fetch_latest_video_ids_for_channel_via_playlist(api_key, channel_id, max_results=5):
    """
    Get the latest video IDs from a channel using its uploads playlist
    instead of search.list. Much cheaper in quota:
    - channels.list: 1 unit
    - playlistItems.list: 1 unit
    """
    if not api_key:
        raise RuntimeError("No API key found in config.py")

    # 1) Get the uploads playlist for this channel
    channels_url = "https://www.googleapis.com/youtube/v3/channels"
    chan_params = {
        "part": "contentDetails",
        "id": channel_id,
        "key": api_key,
    }
    resp = requests.get(channels_url, params=chan_params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    items = data.get("items", [])
    if not items:
        print(f"[WARN] No channel found for id {channel_id}")
        return []

    uploads_playlist_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    # 2) Get latest items from the uploads playlist
    playlist_items_url = "https://www.googleapis.com/youtube/v3/playlistItems"
    pl_params = {
        "part": "contentDetails",
        "playlistId": uploads_playlist_id,
        "maxResults": max_results,
        "key": api_key,
    }
    resp = requests.get(playlist_items_url, params=pl_params, timeout=10)
    resp.raise_for_status()
    pl_data = resp.json()

    video_ids = []
    for item in pl_data.get("items", []):
        vid = item["contentDetails"]["videoId"]
        video_ids.append(vid)

    return video_ids


def fetch_video_ids_for_keyword(api_key, query, max_results=5):
    """
    Use YouTube Search API to get video IDs matching a text query.
    Returns a list of video IDs. On error, returns [] and logs.
    """
    if not api_key:
        raise RuntimeError("No API key found in config.py")

    base_url = "https://www.googleapis.com/youtube/v3/search"

    params = {
        "part": "snippet",
        "q": query,
        "order": "date",    # or 'relevance'
        "type": "video",
        "maxResults": max_results,
        "key": api_key,
    }

    try:
        resp = requests.get(base_url, params=params)
        resp.raise_for_status()
    except HTTPError as e:
        print("\n====================== API ERROR ======================")
        print(f"Error fetching videos for keyword '{query}': {e}")
        try:
            print("YouTube response snippet:")
            print(resp.text[:500])
        except Exception:
            pass
        print("Returning empty list for this keyword...")
        print("=======================================================\n")
        return []

    data = resp.json()
    video_ids = []

    for item in data.get("items", []):
        vid = item["id"].get("videoId")
        if vid:
            video_ids.append(vid)

    return video_ids


def fetch_youtube_stats_for_videos(api_key, video_ids):
    """
    Call the YouTube Data API to get stats for a list of video IDs.
    Returns a dict:
    {
        "video_id": {
            "title": "...",
            "channel_title": "...",
            "views": int,
            "likes": int,
            "comments": int,
        },
        ...
    }
    """
    if not api_key:
        raise RuntimeError("No API key found in config.py")

    stats_by_id = {}
    base_url = "https://www.googleapis.com/youtube/v3/videos"

    # YouTube API allows up to 50 IDs per request
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        params = {
            "part": "snippet,statistics",
            "id": ",".join(batch),
            "key": api_key,
        }

        try:
            resp = requests.get(base_url, params=params)
            resp.raise_for_status()
        except HTTPError as e:
            print("\n====================== API ERROR ======================")
            print(f"Error fetching stats batch: {e}")
            try:
                print("YouTube response snippet:")
                print(resp.text[:500])
            except Exception:
                pass
            print("Returning partial results so far...")
            print("=======================================================\n")
            return stats_by_id

        data = resp.json()

        for item in data.get("items", []):
            vid = item["id"]
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})

            stats_by_id[vid] = {
                "title": snippet.get("title", ""),
                "channel_title": snippet.get("channelTitle", ""),
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)) if "likeCount" in stats else 0,
                "comments": int(stats.get("commentCount", 0)) if "commentCount" in stats else 0,
            }

    return stats_by_id


# ---------- SNAPSHOT BUILDERS ----------

def fetch_current_snapshot_from_youtube():
    """
    Builds a snapshot dict from TRACKED_VIDEOS only:
    {
        "timestamp": "...",
        "videos": {
            video_key: {
                "channel_name": ...,
                "video_id": ...,
                "views": ...,
                "likes": ...,
                "comments": ...,
                "subscribers": 0
            },
            ...
        }
    }
    """
    if not YOUTUBE_API_KEY:
        raise RuntimeError("YOUTUBE_API_KEY is not set. Please export it before running.")

    video_ids = [meta["video_id"] for meta in TRACKED_VIDEOS.values()]
    stats_by_id = fetch_youtube_stats_for_videos(YOUTUBE_API_KEY, video_ids)

    snapshot = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "videos": {}
    }

    for video_key, meta in TRACKED_VIDEOS.items():
        vid = meta["video_id"]
        s = stats_by_id.get(vid)
        if s is None:
            continue

        snapshot["videos"][video_key] = {
            "channel_name": s["channel_title"] or meta["channel_name"],
            "video_id": vid,
            "views": s["views"],
            "likes": s["likes"],
            "comments": s["comments"],
            "subscribers": 0,
            "label": meta.get("label", vid),
        }

    return snapshot


def build_snapshot_from_channels_and_keywords(
    max_per_channel=5,
    max_per_keyword=5,
):
    """
    Build a snapshot using:
    - recent uploads from channels in channels.json
    - recent videos matching keyword queries in keywords.json
    """
    if not YOUTUBE_API_KEY:
        raise RuntimeError("No API key found in config.py")

    channels_cfg = load_channels_config()
    keywords_cfg = load_keywords_config()

    all_video_ids = set()
    video_meta_list = []  # maps video_id -> meta (source_type, source_label, etc.)

    # ---- Channels (using uploads playlist, not search.list) ----
    for ch in channels_cfg:
        ch_key = ch.get("key", "channel")
        ch_id = ch.get("channel_id")
        ch_label = ch.get("label", ch_key)

        if not ch_id:
            continue

        try:
            ids = fetch_latest_video_ids_for_channel_via_playlist(
                YOUTUBE_API_KEY,
                ch_id,
                max_results=max_per_channel,
            )
        except Exception as e:
            print(f"Error fetching channel {ch_key}: {e}")
            continue

        for vid in ids:
            if vid not in all_video_ids:
                all_video_ids.add(vid)
                video_meta_list.append({
                    "video_id": vid,
                    "source_type": "channel",
                    "source_key": ch_key,
                    "source_label": ch_label,
                })

    # ---- Keywords (still using search.list, but more controlled) ----
    for kw in keywords_cfg:
        kw_key = kw.get("key", "keyword")
        queries = kw.get("queries", [])
        kw_label = kw.get("label", kw_key)

        for q in queries:
            try:
                ids = fetch_video_ids_for_keyword(
                    YOUTUBE_API_KEY,
                    q,
                    max_results=max_per_keyword,
                )
            except Exception as e:
                print(f"Error fetching keyword '{q}': {e}")
                continue

            for vid in ids:
                if vid not in all_video_ids:
                    all_video_ids.add(vid)
                    video_meta_list.append({
                        "video_id": vid,
                        "source_type": "keyword",
                        "source_key": kw_key,
                        "source_label": kw_label,
                    })

    # 2) Fetch stats for all unique video IDs
    all_video_ids_list = list(all_video_ids)
    stats_by_id = fetch_youtube_stats_for_videos(
        YOUTUBE_API_KEY,
        all_video_ids_list,
    )

    # 3) Build snapshot structure
    snapshot = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "videos": {}
    }

    for meta in video_meta_list:
        vid = meta["video_id"]
        stats = stats_by_id.get(vid)
        if not stats:
            continue

        source_key = meta["source_key"]
        video_key = f"{meta['source_type']}_{source_key}_{vid}"

        # Label = actual YouTube video title (trimmed)
        title = stats["title"] or "(no title)"
        label = title[:80]

        snapshot["videos"][video_key] = {
            "channel_name": stats["channel_title"],
            "video_id": vid,
            "views": stats["views"],
            "likes": stats["likes"],
            "comments": stats["comments"],
            "subscribers": 0,
            "label": label,
        }

    return snapshot


# ---------- RANKING / GRID DATA ----------

def get_top_videos_by_delta(current_snapshot, deltas, metric="views_delta", top_n=16):
    """
    Build a list of videos sorted by a given delta metric (e.g. "views_delta" or "views_delta_pct").
    Returns a list of dicts ready for CLI grid or web UI.
    """
    rows = []

    for video_key, metrics in current_snapshot["videos"].items():
        delta_entry = deltas["videos"].get(video_key, {})
        delta_value = delta_entry.get(metric, "N/A")

        # Skip N/A if you only want ones with a real baseline
        if isinstance(delta_value, str):
            continue

        # Prefer the label stored in the snapshot (for channels/keywords),
        # fall back to TRACKED_VIDEOS, then to video_id.
        label = metrics.get("label")
        if not label:
            meta = TRACKED_VIDEOS.get(video_key, {})
            label = meta.get("label") or metrics.get("video_id") or video_key

        rows.append({
            "video_key": video_key,
            "channel_name": metrics["channel_name"],
            "video_id": metrics["video_id"],
            "label": label,
            "current_value": metrics["views"],
            "delta": delta_value,
        })

    rows.sort(key=lambda r: r["delta"], reverse=True)
    return rows[:top_n]
