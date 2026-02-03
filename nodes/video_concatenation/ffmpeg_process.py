import ffmpeg


def probe_video(video_path):
    try:
        probe = ffmpeg.probe(video_path)
        return float(probe["format"]["duration"])
    except Exception as e:
        print(f"[Video Concatenation] Error probing video {video_path}: {e}")
        return None


def get_output_args(output_format):
    if output_format in ["mp4", "mkv", "mov"]:
        return {
            "vcodec": "libx264",
            "crf": "23",
            "preset": "medium",
            "pix_fmt": "yuv420p",  # Critical for Windows 11 compatibility
        }
    elif output_format == "avi":
        return {
            "vcodec": "mpeg4",
            "qscale:v": "3",  # High quality variable bitrate
        }
    elif output_format == "webm":
        return {
            "vcodec": "libvpx-vp9",
            "crf": "30",
            "b:v": "0",
        }
    return {}


def simple_concat(video_paths, output_path, output_format):
    try:
        streams = []
        for v in video_paths:
            input_node = ffmpeg.input(v)
            streams.append(input_node.video)
            streams.append(input_node.audio)

        joined = ffmpeg.concat(*streams, v=1, a=1).node
        output_args = get_output_args(output_format)

        out = ffmpeg.output(joined[0], joined[1], output_path, **output_args)
        out.overwrite_output().run(capture_stdout=True, capture_stderr=True)
        return True
    except ffmpeg.Error as e:
        print(
            f"[Video Concatenation] Simple concat failed: {e.stderr.decode() if e.stderr else str(e)}"
        )
        # Try video only
        return simple_concat_video_only(video_paths, output_path, output_format)
    except Exception as e:
        print(f"[Video Concatenation] Unexpected error in simple concat: {e}")
        return False


def simple_concat_video_only(video_paths, output_path, output_format):
    try:
        print("[Video Concatenation] Trying video-only simple concat...")
        streams = [ffmpeg.input(v).video for v in video_paths]
        output_args = get_output_args(output_format)

        ffmpeg.concat(*streams, v=1, a=0).output(
            output_path, **output_args
        ).overwrite_output().run(capture_stdout=True, capture_stderr=True)
        return True
    except ffmpeg.Error as e:
        print(
            f"[Video Concatenation] Video-only simple concat failed: {e.stderr.decode() if e.stderr else str(e)}"
        )
        return False


def xfade_concat(
    video_paths,
    output_path,
    output_format,
    transition_type,
    transition_time,
    video_durations,
):
    try:
        # 1. Create input streams
        v_streams = []
        a_streams = []
        for v in video_paths:
            inp = ffmpeg.input(v)
            v_streams.append(inp.video)
            a_streams.append(inp.audio)

        # 2. Build filter graph
        curr_v = v_streams[0]
        curr_a = a_streams[0]
        current_offset = video_durations[0] - transition_time

        for i in range(1, len(video_paths)):
            next_v = v_streams[i]
            next_a = a_streams[i]

            # Apply xfade
            curr_v = ffmpeg.filter(
                [curr_v, next_v],
                "xfade",
                transition=transition_type,
                duration=transition_time,
                offset=current_offset,
            )

            # Apply acrossfade for audio
            curr_a = ffmpeg.filter([curr_a, next_a], "acrossfade", d=transition_time)

            # Update offset for the next iteration
            if i < len(video_durations) - 1:
                current_offset += video_durations[i] - transition_time

        # 3. Output
        output_args = get_output_args(output_format)
        out = ffmpeg.output(curr_v, curr_a, output_path, **output_args)
        out.overwrite_output().run(capture_stdout=True, capture_stderr=True)
        return True

    except ffmpeg.Error as e:
        print(
            f"[Video Concatenation] Xfade concat failed: {e.stderr.decode() if e.stderr else str(e)}"
        )
        # Fallback to simple concat video only? Or maybe just simple concat total?
        # Let's fallback to video-only simple concat as a safe net if audio was the issue,
        # or maybe the user prefers a hard cut over a failed xfade.
        # For now, let's try video-only xfade if that was the issue, or just return False to let caller handle fallback.
        return False
