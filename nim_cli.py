# nim_cli.py

import json
import os
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


# -------------------------------------------------------------------
# Option 5 run tracking (24h guard)
# -------------------------------------------------------------------

def get_last_option5_run():
    if not os.path.exists(LAST_RUN_FILE):
        return None
    try:
        with open(LAST_RUN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return datetime.fromisoformat(data.get("last_run"))
    except Exception:
        return None


def set_last_option5_run():
    now = datetime.now().isoformat(timespec="seconds")
    with open(LAST_RUN_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_run": now}, f, indent=2)


# -------------------------------------------------------------------
# Manual input (option 1)
# -------------------------------------------------------------------

def fetch_current_data_for_all_videos():
    """
    Manual stats entry for each TRACKED_VIDEOS item.
    Returns snapshot dict.
    """
    snapshot = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "videos": {},
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


# -------------------------------------------------------------------
# CLI grid display
# -------------------------------------------------------------------

def display_top_movers_grid(top_list, metric_name="Δ"):
    """
    Displays up to 16 videos in a 4x4 grid based on delta ranking.
    Each cell shows:
      - label
      - delta (formatted)
    """
    print("\n" * 3)
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
            label = item["label"][:20]
            print(f"{label:<22}", end=" | ")
        print("")

        # Second line: deltas
        for item in row:
            delta = item["delta"]
            if isinstance(delta, float):
                # Format percentage-ish deltas nicely
                delta_str = f"{delta:.2f}"
            else:
                delta_str = str(delta)
            print(f"{metric_name} {delta_str:<15}", end=" | ")
        print("\n")

    input("\nPress ENTER to return to menu...")


# -------------------------------------------------------------------
# Main menu
# -------------------------------------------------------------------

def main_menu():
    running = True

    while running:
        print("\n===== YOUTUBE DASHBOARD =====")
        print("1. Capture ALL tracked videos (manual) + show top movers")
        print("2. View last snapshot only")
        print("3. Exit")
        print("4. Fetch ALL tracked videos from YouTube API + show top movers")
        print("5. Build snapshot from channels + keywords config + show top movers")
        choice = input("Select an option: ").strip()

        # --------------------------------------------------------------
        # Option 1: manual entry for TRACKED_VIDEOS
        # --------------------------------------------------------------
        if choice == "1":
            previous_snapshot = load_previous_data()
            current_snapshot = fetch_current_data_for_all_videos()
            deltas_all = compute_deltas_all(previous_snapshot, current_snapshot)

            top_list = get_top_videos_by_delta(
                current_snapshot, deltas_all, "views_delta", 16
            )
            display_top_movers_grid(top_list, metric_name="Δ")

            save_current_data(current_snapshot)

        # --------------------------------------------------------------
        # Option 2: view last snapshot only
        # --------------------------------------------------------------
        elif choice == "2":
            snapshot = load_previous_data()
            if snapshot is None or not snapshot.get("videos"):
                print("No saved data found.")
                input("Press ENTER to return to menu...")
            else:
                # Fake deltas = current views so we can reuse the ranking helper
                fake_deltas = {"videos": {}}
                for key, metrics in snapshot["videos"].items():
                    fake_deltas["videos"][key] = {
                        "views_delta": metrics.get("views", 0),
                        "likes_delta": 0,
                        "comments_delta": 0,
                        "subscribers_delta": 0,
                        "views_delta_pct": "N/A",
                    }

                top_list = get_top_videos_by_delta(
                    snapshot, fake_deltas, "views_delta", 16
                )
                display_top_movers_grid(top_list, metric_name="Views")

        # --------------------------------------------------------------
        # Option 3: exit
        # --------------------------------------------------------------
        elif choice == "3":
            running = False

        # --------------------------------------------------------------
        # Option 4: LIVE stats for TRACKED_VIDEOS via API
        # --------------------------------------------------------------
        elif choice == "4":
            print("Fetching stats from YouTube API for TRACKED_VIDEOS...")
            previous_snapshot = load_previous_data()
            current_snapshot = fetch_current_snapshot_from_youtube()
            deltas_all = compute_deltas_all(previous_snapshot, current_snapshot)

            top_list = get_top_videos_by_delta(
                current_snapshot, deltas_all, "views_delta", 16
            )
            display_top_movers_grid(top_list, metric_name="Δ")

            save_current_data(current_snapshot)

        # --------------------------------------------------------------
        # Option 5: channels + keywords (subject to 24h guard)
        # --------------------------------------------------------------
        elif choice == "5":
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

            if not current_snapshot.get("videos"):
                print("\n[INFO] No videos were fetched this run (likely quota or config issue).")
                print("       Keeping previous snapshot on disk, not overwriting.")
                input("\nPress ENTER to return to menu...")
                continue

            previous_snapshot = load_previous_data()
            deltas_all = compute_deltas_all(previous_snapshot, current_snapshot)

            # Rank by percentage view delta for this mode
            top_list = get_top_videos_by_delta(
                current_snapshot,
                deltas_all,
                "views_delta_pct",
                16,
            )

            display_top_movers_grid(top_list, metric_name="Δ%")
            save_current_data(current_snapshot)
            set_last_option5_run()

        else:
            print("Invalid option. Please try again.")


if __name__ == "__main__":
    main_menu()
