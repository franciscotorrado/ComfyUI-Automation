import os
import datetime
import folder_paths
from .video_output import VideoOutput
from .path_utils import extract_paths, resolve_video_paths
from .ffmpeg_process import probe_video, simple_concat, xfade_concat


class VideoConcatenation:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "transition_type": (
                    [
                        "none",
                        "fade",
                        "slideleft",
                        "slideright",
                        "slideup",
                        "slidedown",
                        "wipeleft",
                        "wiperight",
                        "wipeup",
                        "wipedown",
                        "dissolve",
                        "circlecrop",
                        "rectcrop",
                        "distance",
                        "radial",
                        "pixelize",
                        "hblur",
                    ],
                    {"default": "none"},
                ),
                "transition_time": (
                    "FLOAT",
                    {"default": 1.0, "min": 0.1, "max": 10.0, "step": 0.1},
                ),
                "output_format": (
                    ["mp4", "mkv", "mov", "webm", "avi", "gif"],
                    {"default": "mp4"},
                ),
            },
            "optional": {
                "video1": ("VIDEO",),
                "video2": ("VIDEO",),
                "video3": ("VIDEO",),
                "video4": ("VIDEO",),
                "video5": ("VIDEO",),
            },
        }

    RETURN_TYPES = ("VIDEO",)
    RETURN_NAMES = ("video",)
    OUTPUT_NODE = False
    FUNCTION = "merge_videos"
    CATEGORY = "Video Concatenation"

    def merge_videos(self, **kwargs):
        # Collect all provided video paths
        video_list = []
        for i in range(1, 6):
            v = kwargs.get(f"video{i}")
            if v is None:
                continue

            print(f"[Video Concatenation] Concatenation input video{i} type: {type(v)}")

            extracted = extract_paths(v)
            if not extracted:
                print(
                    f"[Video Concatenation] Concatenation input video{i} could not be parsed: {v}"
                )
            video_list.extend(extracted)

        if not video_list:
            print(
                "[Video Concatenation] VideoConcatenation: No video paths recognized in the inputs"
            )
            return (None,)

        # Resolve paths
        valid_videos = resolve_video_paths(video_list)

        if not valid_videos:
            print(
                "[Video Concatenation] VideoConcatenation: No valid video files found on disk among the recognized paths"
            )
            return (None,)

        # Get output directory from ComfyUI (used for temp file)
        output_dir = folder_paths.get_temp_directory()
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # Generate temp filename
        today = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        output_format = kwargs.get("output_format", "mp4")
        output_path = os.path.join(output_dir, f"concat_temp_{today}.{output_format}")

        # Probe video durations if transitions are enabled
        transition_mode = kwargs.get("transition_type", "none")
        transition_time = kwargs.get("transition_time", 1.0)

        # Validate probing
        video_durations = []
        if transition_mode != "none":
            for v_path in valid_videos:
                duration = probe_video(v_path)
                if duration is not None:
                    video_durations.append(duration)
                else:
                    # Fallback to none if probing fails
                    transition_mode = "none"
                    break

        print(
            f"[Video Concatenation] Merging {len(valid_videos)} videos... (Transition: {transition_mode})"
        )

        success = False
        if transition_mode == "none":
            success = simple_concat(valid_videos, output_path, output_format)
        else:
            success = xfade_concat(
                valid_videos,
                output_path,
                output_format,
                transition_mode,
                transition_time,
                video_durations,
            )
            if not success:
                print(
                    f"[Video Concatenation] Xfade failed, falling back to simple concat video only."
                )
                # The original code had a fallback to video-only simple concat if audio stuff failed in xfade path.
                # My ffmpeg_process wrapper handles exceptions but returns False.
                # Let's try the video-only simple concat if xfade returned False.
                from .ffmpeg_process import simple_concat_video_only

                success = simple_concat_video_only(
                    valid_videos, output_path, output_format
                )

        if success and os.path.exists(output_path):
            return (VideoOutput(output_path),)

        return (None,)
