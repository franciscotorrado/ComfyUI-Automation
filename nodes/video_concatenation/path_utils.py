import os
import folder_paths


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


def resolve_video_paths(video_list):
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
    return valid_videos
