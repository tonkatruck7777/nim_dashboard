from flask import Flask, render_template
from nim_core import (
    load_previous_data,
    TRACKED_VIDEOS,
    get_top_videos_by_delta,
)

app = Flask(__name__)


@app.route("/")
def dashboard():
    # Load the last saved snapshot (from the CLI runs)
    snapshot = load_previous_data()

    if snapshot is None or "videos" not in snapshot:
        top_list = []
    else:
        # For now we don't have a previous snapshot history in JSON,
        # so we'll fake "delta = current views" just to reuse the same
        # get_top_videos_by_delta() function and show a ranked board.
        fake_deltas = {"videos": {}}
        for key, metrics in snapshot["videos"].items():
            fake_deltas["videos"][key] = {
                "views_delta": metrics["views"],       # treat views as "delta"
                "likes_delta": metrics["likes"],
                "comments_delta": metrics["comments"],
                "subscribers_delta": metrics["subscribers"],
            }

        top_list = get_top_videos_by_delta(
            snapshot,
            fake_deltas,
            metric="views_delta",
            top_n=16,
        )

    return render_template("dashboard.html", top_list=top_list)


if __name__ == "__main__":
    app.run(debug=True)
