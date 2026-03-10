📁 YOUTUBE UPLOAD QUEUE
═══════════════════════════════════════════════════

Move your processed video folder here to have it
uploaded to YouTube automatically (one per day).

───────────────────────────────────────────────────
WHAT TO DROP IN HERE
───────────────────────────────────────────────────

After running the pipeline, your video lands in:
  youtube_automation/outputs/your_video_name/

Move that folder (your_video_name/) into this
upload_queue/ folder.

Each folder MUST contain:
  ✅ final_video.mp4    ← the video
  ✅ script.txt         ← the narration (used by AI to
                          generate YouTube title +
                          description + tags)

───────────────────────────────────────────────────
WHAT HAPPENS NEXT
───────────────────────────────────────────────────

On boot (or every 24 hours):

  1. autoupload_daily.sh runs automatically
  2. Picks the OLDEST folder in this queue
  3. AI generates title / description / tags
  4. Uploads to YouTube
  5. Moves folder  →  uploaded/
  6. Only ONE upload per calendar day

───────────────────────────────────────────────────
MULTIPLE VIDEOS
───────────────────────────────────────────────────

Drop as many folders as you want.
They upload one per day, oldest first.

═══════════════════════════════════════════════════
