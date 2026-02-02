import os
import datetime
import ffmpeg
import folder_paths


class VideoOutput:
    def __init__(self, video_path):
        self.video_path = video_path

    def get_dimensions(self):
        try:
            probe = ffmpeg.probe(self.video_path)
            video_info = next(s for s in probe["streams"] if s["codec_type"] == "video")
            return int(video_info["width"]), int(video_info["height"])
        except Exception:
            return 0, 0

    def save_to(self, path, format=None, codec=None, metadata=None):
        # Simply copy the concatenation result to the final path
        # If format conversion is requested by SaveVideo, we might need ffmpeg here
        # But usually VideoConcatenation already did the hard work.

        # Determine if we need to re-encode or just copy
        # The internal file is already in a temp path with a format.
        try:
            # We will use ffmpeg to ensure the target format/codec is respected
            # if provided by the save node.

            stream = ffmpeg.input(self.video_path)
            # Basic copy if no specific codec requested or if it matches
            output_args = {"c": "copy"}

            # If codec/format is strictly requested by the SaveVideo node (which usually passes objects)
            # The 'format' arg here is likely a complicated Comfy object based on the traceback (Types.VideoContainer)
            # We'll do a simple copy for now as a robust baseline,
            # assuming the user set the right extension in VideoConcatenation.
            # If strictly needed, we can re-encode.

            ffmpeg.output(stream, path, **output_args).overwrite_output().run()
        except Exception as e:
            print(f"[Video Concatenation] Error saving to final path: {e}")
            # Fallback copy
            import shutil

            shutil.copy(self.video_path, path)


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

            def extract_paths(obj):
                paths = []
                if isinstance(obj, str):
                    paths.append(obj)
                elif isinstance(obj, list):
                    for item in obj:
                        paths.extend(extract_paths(item))
                elif isinstance(obj, dict):
                    # Local VHS support
                    if "filenames" in obj:
                        paths.extend(extract_paths(obj["filenames"]))
                    # Some nodes return {'video': 'path'}
                    elif "video" in obj:
                        paths.extend(extract_paths(obj["video"]))
                else:
                    # Handle new ComfyUI API objects (like VideoFromFile/VideoInput)
                    if hasattr(obj, "get_stream_source"):
                        try:
                            source = obj.get_stream_source()
                            if isinstance(source, str):
                                paths.append(source)
                            else:
                                print(
                                    f"[Video Concatenation] Concatenation: get_stream_source returned non-string: {type(source)}"
                                )
                        except Exception as e:
                            print(
                                f"[Video Concatenation] Concatenation error calling get_stream_source: {e}"
                            )
                    # Handle our own VideoOutput class (recursive concatenation)
                    elif hasattr(obj, "video_path"):
                        paths.append(obj.video_path)

                    if not paths:
                        # Fallback: check common attributes
                        for attr in ["video", "filename", "path", "full_path"]:
                            if hasattr(obj, attr):
                                val = getattr(obj, attr)
                                if isinstance(val, (str, list, dict)):
                                    paths.extend(extract_paths(val))
                                    break

                    if not paths:
                        # Final debug: list public attributes
                        attrs = [a for a in dir(obj) if not a.startswith("_")]
                        print(
                            f"[Video Concatenation] Concatenation could not parse {type(obj).__name__}. Attributes: {attrs}"
                        )

                return paths

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

        # Resolve paths accurately using ComfyUI's folder_paths
        valid_videos = []
        for v in video_list:
            if not v or not isinstance(v, str):
                continue

            # 1. Try absolute path
            if os.path.isabs(v) and os.path.exists(v):
                valid_videos.append(v)
                continue

            # 2. Try ComfyUI output directory
            out_path = os.path.join(folder_paths.get_output_directory(), v)
            if os.path.exists(out_path):
                valid_videos.append(out_path)
                continue

            # 3. Try ComfyUI input directory
            in_path = os.path.join(folder_paths.get_input_directory(), v)
            if os.path.exists(in_path):
                valid_videos.append(in_path)
                continue

            # 4. Use folder_paths helper if available
            try:
                resolved = folder_paths.get_annotated_filepath(v)
                if resolved and os.path.exists(resolved):
                    valid_videos.append(resolved)
                    continue
            except Exception:
                pass

            print(
                f"[Video Concatenation] VideoConcatenation: Skipping invalid or missing path: {v}"
            )

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
                try:
                    probe = ffmpeg.probe(v_path)
                    duration = float(probe["format"]["duration"])
                    video_durations.append(duration)
                except Exception as e:
                    print(f"[Video Concatenation] Error probing video {v_path}: {e}")
                    # Fallback to none if probing fails
                    transition_mode = "none"
                    break

        print(
            f"[Video Concatenation] Merging {len(valid_videos)} videos... (Transition: {transition_mode})"
        )

        success = False
        try:
            if transition_mode == "none":
                # Original simple concat
                streams = []
                for v in valid_videos:
                    input_node = ffmpeg.input(v)
                    streams.append(input_node.video)
                    streams.append(input_node.audio)

                joined = ffmpeg.concat(*streams, v=1, a=1).node

                # Define encoding arguments based on format
                output_args = {}
                if output_format in ["mp4", "mkv", "mov"]:
                    output_args = {
                        "vcodec": "libx264",
                        "crf": "23",
                        "preset": "medium",
                        "pix_fmt": "yuv420p",  # Critical for Windows 11 compatibility
                    }
                elif output_format == "avi":
                    output_args = {
                        "vcodec": "mpeg4",
                        "qscale:v": "3",  # High quality variable bitrate
                    }
                elif output_format == "webm":
                    output_args = {
                        "vcodec": "libvpx-vp9",
                        "crf": "30",
                        "b:v": "0",
                    }

                out = ffmpeg.output(joined[0], joined[1], output_path, **output_args)
                out.overwrite_output().run(capture_stdout=True, capture_stderr=True)
            else:
                # Advanced xfade concat
                # 1. Create input streams
                v_streams = []
                a_streams = []
                for v in valid_videos:
                    inp = ffmpeg.input(v)
                    v_streams.append(inp.video)
                    a_streams.append(inp.audio)  # Assuming audio exists for now

                # 2. Build filter graph
                curr_v = v_streams[0]
                curr_a = a_streams[0]
                current_offset = video_durations[0] - transition_time

                for i in range(1, len(valid_videos)):
                    next_v = v_streams[i]
                    next_a = a_streams[i]

                    # Apply xfade
                    curr_v = ffmpeg.filter(
                        [curr_v, next_v],
                        "xfade",
                        transition=transition_mode,
                        duration=transition_time,
                        offset=current_offset,
                    )

                    # Apply acrossfade for audio
                    curr_a = ffmpeg.filter(
                        [curr_a, next_a], "acrossfade", d=transition_time
                    )

                    # Update offset for the next iteration
                    if i < len(video_durations) - 1:
                        current_offset += video_durations[i] - transition_time

                # 3. Output
                output_args = {}
                if output_format in ["mp4", "mkv", "mov"]:
                    output_args = {
                        "vcodec": "libx264",
                        "crf": "23",
                        "preset": "medium",
                        "pix_fmt": "yuv420p",  # Critical for Windows 11 compatibility
                    }
                elif output_format == "avi":
                    output_args = {
                        "vcodec": "mpeg4",
                        "qscale:v": "3",
                    }
                elif output_format == "webm":
                    output_args = {
                        "vcodec": "libvpx-vp9",
                        "crf": "30",
                        "b:v": "0",
                    }

                out = ffmpeg.output(curr_v, curr_a, output_path, **output_args)
                out.overwrite_output().run(capture_stdout=True, capture_stderr=True)
            success = True

        except ffmpeg.Error as e:
            print(
                f"[Video Concatenation] Error with audio concat, trying video-only. Error: {e.stderr.decode() if e.stderr else 'unknown'}"
            )
            try:
                streams = [ffmpeg.input(v).video for v in valid_videos]
                output_args = {}
                if output_format in ["mp4", "mkv", "mov"]:
                    output_args = {
                        "vcodec": "libx264",
                        "crf": "23",
                        "preset": "medium",
                        "pix_fmt": "yuv420p",
                    }
                elif output_format == "avi":
                    output_args = {
                        "vcodec": "mpeg4",
                        "qscale:v": "3",
                    }
                elif output_format == "webm":
                    output_args = {
                        "vcodec": "libvpx-vp9",
                        "crf": "30",
                        "b:v": "0",
                    }
                ffmpeg.concat(*streams, v=1, a=0).output(
                    output_path, **output_args
                ).overwrite_output().run(capture_stdout=True, capture_stderr=True)
                success = True
            except ffmpeg.Error as e2:
                print(
                    f"[Video Concatenation] Critical error merging videos: {e2.stderr.decode() if e2.stderr else 'unknown'}"
                )
                return (None,)
        except Exception as e:
            print(f"[Video Concatenation] Unexpected error: {str(e)}")
            return (None,)

        if success and os.path.exists(output_path):
            return (VideoOutput(output_path),)

        return (None,)
