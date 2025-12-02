# nim_web.py

from flask import Flask, render_template

from nim_core import (
    load_previous_data,
    save_current_data,
    compute_deltas_all,
    get_top_videos_by_delta,
    build_snapshot_from_channels_and_keywords,
)

app = Flask(__name__)


@app.route("/")
def index():
    # 1) Load existing snapshot if present
    snapshot = load_previous_data()

    # 2) If none, build from channels + keywords (like option 5)
    if snapshot is None or not snapshot.get("videos"):
        print("[WEB] No snapshot found. Building from channels + keywords...")
        snapshot = build_snapshot_from_channels_and_keywords(
            max_per_channel=5,
            max_per_keyword=3,
        )

        if snapshot.get("videos"):
            save_current_data(snapshot)
        else:
            # Hard failure: no data (quota, config, etc.)
            top_list = []
            return render_template("dashboard.html", top_list=top_list)

    # 3) For web we often just want “top by current views”.
    # We can fake deltas so that delta == current views, then reuse the helper.
    fake_deltas = {"videos": {}}
    for video_key, metrics in snapshot.get("videos", {}).items():
        fake_deltas["videos"][video_key] = {
            "views_delta": metrics.get("views", 0),
            "likes_delta": 0,
            "comments_delta": 0,
            "subscribers_delta": 0,
            "views_delta_pct": "N/A",
        }

    top_list = get_top_videos_by_delta(
        snapshot,
        fake_deltas,
        metric="views_delta",  # i.e. “sort by current views”
        top_n=16,
    )

    return render_template("dashboard.html", top_list=top_list)


if __name__ == "__main__":
    # For local testing only; Render uses gunicorn as per your start command
    app.run(debug=True, host="0.0.0.0", port=5000)
