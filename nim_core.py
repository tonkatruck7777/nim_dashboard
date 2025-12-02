# nim_core.py

import json
import os
from datetime import datetime

import requests
from requests.exceptions import HTTPError

from config import YOUTUBE_API_KEY

# -------------------------------------------------------------------
# Paths for config and snapshot
# -------------------------------------------------------------------

DATA_FILE_PATH = "youtube_metrics.json"
CHANNELS_CONFIG_PATH = "channels.json"
KEYWORDS_CONFIG_PATH = "keywords.json"


# -------------------------------------------------------------------
# Static tracked videos (for options 1 & 4)
# -------------------------------------------------------------------

TRACKED_VIDEOS = {
    "hasan_x8d6K399WW4": {
        "channel_name": "HasanAbi",
        "video_id": "x8d6K399WW4",
        "label": "HasanAbi – we are Charlie Kirk",
    },
    "boyboy_Sfrjpy5cJCs": {
        "channel_name": "Boy Boy",
        "video_id": "Sfrjpy5cJCs",
        "label": "BoyBoy – I snuck into a major arms dealer conference",
    },
    "NavaraMedia_UC2VT3RkiYo": {
        "channel_name": "Navara Media",
        "video_id": "UC2VT3RkiYo",
        "label": "NavaraMedia – The blueprint for an actual revolution",
    },
    "Zeteo_MEtvCw1LzRc": {
        "channel_name": "Zeteo",
        "video_id": "MEtvCw1LzRc",
        "label": "Zeteo – Will Mamdami Challenge the Democratic Leadership",
    },
    "SecularTalk_0YrNUANVel8": {
        "channel_name": "Secular Talk",
        "video_id": "0YrNUANVel8",
        "label": "Secular Talk – The Rogansphere is fucked",
    },
    "PuntersPolitics_3oLIodU0BCU": {
        "channel_name": "Punters Politics",
        "video_id": "3oLIodU0BCU",
        "label": "Punters Politics – Australia gets played by Santos",
    },
    "TimDillon_khKJS50odJw": {
        "channel_name": "Tim Dillon",
        "video_id": "khKJS50odJw",
        "label": "Tim Dillon – Wicked Terrible Life Golden Age of Travel",
    },
    "LBC_DAshS2Tl4yw": {
        "channel_name": "LBC",
        "video_id": "DAshS2Tl4yw",
        "label": "LBC – A plan translated from Russian",
    },
    "CaspianReport_cVCDjEfPzII": {
        "channel_name": "Caspian Report",
        "video_id": "cVCDjEfPzII",
        "label": "Caspian Report – Vietnam is beating China at its own game",
    },
    "TuckerCarlson_rDOsm-CYUwQ": {
        "channel_name": "Tucker Carlson",
        "video_id": "rDOsm-CYUwQ",
        "label": "Tucker Carlson – Testing Piers Morgan free speech",
    },
    "AlexJones_NIRVzbgYk0s": {
        "channel_name": "Alex Jones",
        "video_id": "NIRVzbgYk0s",
        "label": "Alex Jones – Deep State Plotting to overthrow state",
    },
    "BenShapiro_R5qWmHn7SUY": {
        "channel_name": "Ben Shapiro",
        "video_id": "R5qWmHn7SUY",
        "label": "Ben Shapiro – Bannon Epstein connection revealed",
    },
    "MattWalsh_YMsJGnn-h_4": {
        "channel_name": "Matt Walsh",
        "video_id": "YMsJGnn-h_4",
        "label": "Matt Walsh – Ken Burns lies revealed",
    },
    "TimPool_Gku5vUy0K88": {
        "channel_name": "Tim Pool",
        "video_id": "Gku5vUy0K88",
        "label": "Tim Pool – MAGA Civil War",
    },
    "BennyJohnson_Uu7PamYxEHA": {
        "channel_name": "Benny Johnson",
        "video_id": "Uu7PamYxEHA",
        "label": "Benny Johnson – Trump advisor bombshell Somali fraud scandal in Minnesota",
    },
    "Flagrant_buIc5vRqWOQ": {
        "channel_name": "Flagrant",
        "video_id": "buIc5vRqWOQ",
        "label": "Flagrant – America vs Arabic culture",
    },
    "TheoVon_SDq7akQIPMw": {
        "channel_name": "Theo Von",
        "video_id": "SDq7akQIPMw",
        "label": "Theo Von – This Past Weekend 626",
    },
}


# -------------------------------------------------------------------
# Config loaders: channels.json & keywords.json
# -------------------------------------------------------------------

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


# -------------------------------------------------------------------
# File I/O for snapshot
# -------------------------------------------------------------------

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


# -------------------------------------------------------------------
# Delta computations (raw + percentage)
# -------------------------------------------------------------------

def compute_deltas_all(previous_snapshot, current_snapshot):
    """
    Compute deltas for every video between previous and current snapshot.

    Returns:
    {
      "videos": {
        video_key: {
          "views_delta": int or "N/A",
          "likes_delta": int or "N/A",
          "comments_delta": int or "N/A",
          "subscribers_delta": int or "N/A",
          "views_delta_pct": float or "N/A",
        },
        ...
      }
    }
    """
    deltas = {"videos": {}}

    if previous_snapshot is None or "videos" not in previous_snapshot:
        # No baseline – all deltas N/A
        for video_key in current_snapshot.get("videos", {}):
            deltas["videos"][video_key] = {
                "views_delta": "N/A",
                "likes_delta": "N/A",
                "comments_delta": "N/A",
                "subscribers_delta": "N/A",
                "views_delta_pct": "N/A",
            }
        return deltas

    prev_videos = previous_snapshot.get("videos", {})

    for video_key, curr_metrics in current_snapshot.get("videos", {}).items():
        if video_key not in prev_videos:
            deltas["videos"][video_key] = {
                "views_delta": "N/A",
                "likes_delta": "N/A",
                "comments_delta": "N/A",
                "subscribers_delta": "N/A",
                "views_delta_pct": "N/A",
            }
            continue

        prev_metrics = prev_videos[video_key]

        def _delta(field):
            if field not in curr_metrics or field not in prev_metrics:
                return "N/A"
            return curr_metrics[field] - prev_metrics[field]

        views_delta = _delta("views")
        likes_delta = _delta("likes")
        comments_delta = _delta("comments")
        subs_delta = _delta("subscribers")

        # Percentage view delta, if possible
        if (
            isinstance(views_delta, int)
            and "views" in prev_metrics
            and prev_metrics["views"] > 0
        ):
            views_delta_pct = (views_delta / prev_metrics["views"]) * 100.0
        else:
            views_delta_pct = "N/A"

        deltas["videos"][video_key] = {
            "views_delta": views_delta,
            "likes_delta": likes_delta,
            "comments_delta": comments_delta,
            "subscribers_delta": subs_delta,
            "views_delta_pct": views_delta_pct,
        }

    return deltas


# -------------------------------------------------------------------
# YouTube API helpers
# -------------------------------------------------------------------

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
            resp = requests.get(base_url, params=params, timeout=10)
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


def fetch_latest_video_ids_for_channel_via_playlist(api_key, channel_id, max_results=5):
    """
    Get the latest video IDs from a channel using its uploads playlist
    instead of search.list (100x cheaper in quota).
    """
    if not api_key:
        raise RuntimeError("No API key found in config.py")

    # 1) Get uploads playlist id
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

    # 2) Get latest items from that playlist
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
        "order": "date",
        "type": "video",
        "maxResults": max_results,
        "key": api_key,
    }

    try:
        resp = requests.get(base_url, params=params, timeout=10)
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


def fetch_current_snapshot_from_youtube():
    """
    Build a snapshot using TRACKED_VIDEOS + live YouTube stats.
    Used for CLI option 4.
    """
    if not YOUTUBE_API_KEY:
        raise RuntimeError("YOUTUBE_API_KEY is not set. Please export it before running.")

    video_ids = [meta["video_id"] for meta in TRACKED_VIDEOS.values()]
    stats_by_id = fetch_youtube_stats_for_videos(YOUTUBE_API_KEY, video_ids)

    snapshot = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "videos": {},
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
            "subscribers": 0,  # placeholder
            "label": meta.get("label", video_key),
        }

    return snapshot


def build_snapshot_from_channels_and_keywords(
    max_per_channel=5,
    max_per_keyword=3,
):
    """
    Build a snapshot using:
    - recent uploads from channels in channels.json (playlistItems-based)
    - recent videos for keywords in keywords.json (search.list)
    """
    if not YOUTUBE_API_KEY:
        raise RuntimeError("No API key found in config.py")

    channels_cfg = load_channels_config()
    keywords_cfg = load_keywords_config()

    all_video_ids = set()
    video_meta_list = []  # mapping from video_id -> label/source

    # ---- Channels (via uploads playlist) ----
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

    # ---- Keywords (search.list) ----
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

    if not all_video_ids:
        # No videos found (quota, config, etc.)
        return {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "videos": {},
        }

    # Fetch stats for all unique video ids
    all_video_ids_list = list(all_video_ids)
    stats_by_id = fetch_youtube_stats_for_videos(
        YOUTUBE_API_KEY,
        all_video_ids_list,
    )

    snapshot = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "videos": {},
    }

    for meta in video_meta_list:
        vid = meta["video_id"]
        stats = stats_by_id.get(vid)
        if not stats:
            continue

        source_key = meta["source_key"]
        video_key = f"{meta['source_type']}_{source_key}_{vid}"

        label = f"{meta['source_label']} – {stats['title'][:50]}"

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


# -------------------------------------------------------------------
# Ranking helper (used by CLI + web)
# -------------------------------------------------------------------

def get_top_videos_by_delta(current_snapshot, deltas, metric="views_delta", top_n=16):
    """
    Build list sorted by a given delta metric.
    For web + option 5 we’ll often use "views_delta_pct".
    For simple “sort by views”, we can fake deltas to equal views.
    """
    rows = []

    videos = current_snapshot.get("videos", {})
    delta_videos = deltas.get("videos", {})

    for video_key, metrics in videos.items():
        delta_entry = delta_videos.get(video_key, {})
        delta_value = delta_entry.get(metric, "N/A")

        if isinstance(delta_value, str):
            # Skip N/A when ranking by numeric metric
            continue

        # Label priority: snapshot label → TRACKED_VIDEOS label → key
        label = (
            metrics.get("label")
            or TRACKED_VIDEOS.get(video_key, {}).get("label")
            or video_key
        )

        rows.append({
            "video_key": video_key,
            "channel_name": metrics.get("channel_name", ""),
            "video_id": metrics.get("video_id", ""),
            "label": label,
            "current_value": metrics.get("views", 0),
            "delta": delta_value,
        })

    rows.sort(key=lambda r: r["delta"], reverse=True)
    return rows[:top_n]
