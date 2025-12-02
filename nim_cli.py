import os
import json
from datetime import datetime, timedelta

from nim_core import (
    TRACKED_VIDEOS,
    load_previous_data,
    save_current_data,
    compute_deltas_all,
    get_top_videos_by_delta,
    fetch_current_snapshot_from_youtube,
    build_snapshot_from_channels_and_keywords,
)

LAST_RUN_FILE = "last_option5_run.json"


# ---------- OPTION 5 LAST-RUN TRACKING ----------

def get_last_option5_run():
    if not os.path.exists(LAST_RUN_FILE):
        return None
    try:
        with open(LAST_RUN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        ts = data.get("last_run")
        if not ts:
            return None
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def set_last_option5_run():
    now = datetime.now().isoformat(timespec="seconds")
    with open(LAST_RUN_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_run": now}, f, indent=2)


# ---------- MANUAL INPUT SNAPSHOT (OPTION 1) ----------

def fetch_current_data_for_all_videos():
    """
    Loop through TRACKED_VIDEOS and ask for current stats
    for each one. Returns a snapshot dict:
    {
        "timestamp": "...",
        "videos": { video_key: {metrics...}, ... }
    }
    """
    snapshot = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "videos": {}
    }

    print("Enter current YouTube stats for tracked videos:")
    print("------------------------------------------------\n")

    for video_key, meta in TRACKED_VIDEOS.items():
        print(f"Channel: {meta['channel_name']}")
        print(f"Video ID: {meta['video_id']}")
        print(f"Label:    {meta.get('label', video_key)}")

        views = int(input("  Views: ").strip())
        likes = int(input("  Likes: ").strip())
        comments = int(input("  Comments: ").strip())
        subs = int(input("  Subscribers: ").strip())

        snapshot["videos"][video_key] = {
            "channel_name": meta["channel_name"],
            "video_id": meta["video_id"],
            "views": views,
            "likes": likes,
            "comments": comments,
            "subscribers": subs,
            "label": meta.get("label", video_key),
        }

        print("")  # blank line between videos

    return snapshot


# ---------- GRID DISPLAY ----------

def display_top_movers_grid(top_list, metric_name="views_delta"):
    """
    Displays up to 16 videos in a 4x4 grid based on delta ranking.
    Each cell shows:
    - label
    - delta (+formatted, optionally as %)
    """
    print("\n" * 50)
    print("===========================================")
    print("        TOP YOUTUBE DELTA MOVERS (16)      ")
    print("===========================================\n")

    if not top_list:
        print("No delta data to display.")
        input("\nPress ENTER to return to menu...")
        return

    row_size = 4
    for i in range(0, len(top_list), row_size):
        row = top_list[i:i + row_size]

        # First line: labels
        for item in row:
            label = item["label"][:20]  # truncate long labels
            print(f"{label:<22}", end=" | ")
        print("")

        # Second line: deltas
        for item in row:
            delta = item["delta"]

            if isinstance(delta, (int, float)) and metric_name.endswith("_pct"):
                # percentage delta
                delta_str = f"{delta:+.1f}%"
            elif isinstance(delta, (int, float)):
                # raw count delta
                delta_str = f"{delta:+}"
            else:
                delta_str = str(delta)

            print(f"Δ {delta_str:<18}", end=" | ")
        print("\n")  # blank line between rows

    input("\nPress ENTER to return to menu...")


# ---------- MAIN MENU ----------

def main_menu():
    running = True

    while running:
        print("\n===== YOUTUBE DASHBOARD =====")
        print("1. Capture ALL tracked videos + show top movers (manual input)")
        print("2. View last snapshot only")
        print("3. Exit")
        print("4. Fetch ALL tracked videos from YouTube API + show top movers")
        print("5. Build snapshot from channels + keywords config + show top movers")
        choice = input("Select an option: ").strip()

        if choice == "1":
            previous_snapshot = load_previous_data()
            current_snapshot = fetch_current_data_for_all_videos()
            deltas_all = compute_deltas_all(previous_snapshot, current_snapshot)
            top_list = get_top_videos_by_delta(
                current_snapshot, deltas_all, "views_delta", 16
            )
            display_top_movers_grid(top_list, metric_name="views_delta")
            save_current_data(current_snapshot)

        elif choice == "2":
            snapshot = load_previous_data()
            if snapshot is None:
                print("No saved data found.")
                input("Press ENTER to return to menu...")
            else:
                # Fake deltas as N/A when just viewing last snapshot
                fake_deltas = {"videos": {}}
                for key in snapshot.get("videos", {}):
                    fake_deltas["videos"][key] = {
                        "views_delta": "N/A",
                        "views_delta_pct": "N/A",
                        "likes_delta": "N/A",
                        "comments_delta": "N/A",
                        "subscribers_delta": "N/A",
                    }

                top_list = get_top_videos_by_delta(
                    snapshot, fake_deltas, "views_delta", 16
                )
                display_top_movers_grid(top_list, metric_name="views_delta")

        elif choice == "3":
            running = False

        elif choice == "4":
            # Live pull from YouTube API for TRACKED_VIDEOS only
            print("Fetching stats from YouTube API...")
            previous_snapshot = load_previous_data()
            current_snapshot = fetch_current_snapshot_from_youtube()
            deltas_all = compute_deltas_all(previous_snapshot, current_snapshot)
            top_list = get_top_videos_by_delta(
                current_snapshot, deltas_all, "views_delta", 16
            )
            display_top_movers_grid(top_list, metric_name="views_delta")
            save_current_data(current_snapshot)

        elif choice == "5":
            # Guard: only allow every 24 hours
            last_run = get_last_option5_run()
            if last_run is not None:
                elapsed = datetime.now() - last_run
                if elapsed < timedelta(hours=24):
                    print("\n[INFO] Option 5 was already run within the last 24 hours.")
                    print("      Skipping to avoid burning YouTube API quota.")
                    input("\nPress ENTER to return to menu...")
                    continue

            print("Building snapshot from channels.json + keywords.json...")
            current_snapshot = build_snapshot_from_channels_and_keywords(
                max_per_channel=5,
                max_per_keyword=3,
            )

            # Do not overwrite disk if this run is effectively empty
            if not current_snapshot.get("videos"):
                print("\n[INFO] No videos were fetched this run (likely quota or config issue).")
                print("       Keeping previous snapshot on disk, not overwriting.")
                input("\nPress ENTER to return to menu...")
                continue

            previous_snapshot = load_previous_data()
            deltas_all = compute_deltas_all(previous_snapshot, current_snapshot)

            # For the aggregated dashboard, rank by percentage growth
            top_list = get_top_videos_by_delta(
                current_snapshot,
                deltas_all,
                "views_delta_pct",
                16,
            )

            display_top_movers_grid(top_list, metric_name="views_delta_pct")
            save_current_data(current_snapshot)
            set_last_option5_run()

        else:
            print("Invalid option. Please try again.")


if __name__ == "__main__":
    main_menu()
