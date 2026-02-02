from ...core import _ITERATOR_CORE_STATE, _LAST_PROMPT_ID


class IteratorSignal:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE",),
                "iterator_id": ("STRING", {"default": "default_iterator"}),
                "active": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "is_finished": ("BOOLEAN", {"default": False}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ("BOOLEAN", "IMAGE")
    RETURN_NAMES = ("SIGNAL", "IMAGE")
    OUTPUT_NODE = True
    FUNCTION = "detect_and_advance"
    CATEGORY = "Iterator"

    @classmethod
    def IS_CHANGED(s, **kwargs):
        return float("NaN")

    def detect_and_advance(
        self,
        image,
        iterator_id,
        active,
        is_finished=False,
        prompt=None,
        extra_pnginfo=None,
        unique_id=None,
    ):
        global _ITERATOR_CORE_STATE, _LAST_PROMPT_ID

        print(
            f"[IteratorSignal] Executing for {iterator_id}. Active: {active}, Finished: {is_finished}"
        )

        # Check if the image exists and has content
        has_image = image is not None and len(image.shape) > 0 and image.shape[0] > 0

        if active and has_image:
            # 1. Advance the state
            current_idx = _ITERATOR_CORE_STATE.get(iterator_id, 0)

            # If we are NOT finished, we prepare for the next item
            if not is_finished:
                _ITERATOR_CORE_STATE[iterator_id] = current_idx + 1
                print(
                    f"[Iterator] Advanced {iterator_id} to index {_ITERATOR_CORE_STATE[iterator_id]}"
                )

                # 2. Trigger re-queue if available
                # We need to re-queue the exact same workflow.
                if prompt and unique_id:
                    import server
                    import nodes
                    import uuid

                    # 2.1 Identify output nodes to execute
                    # We want to re-execute everything that is an output (SaveImage, Preview, etc.)
                    # not just the Signal node.
                    output_node_ids = []
                    for nid, n_info in prompt.items():
                        cls_type = n_info.get("class_type")
                        if cls_type in nodes.NODE_CLASS_MAPPINGS:
                            cls = nodes.NODE_CLASS_MAPPINGS[cls_type]
                            if getattr(cls, "OUTPUT_NODE", False):
                                output_node_ids.append(nid)

                    # 2.2 Prepare execution payload
                    new_prompt_id = uuid.uuid4().hex
                    new_extra_data = {"extra_pnginfo": extra_pnginfo}

                    try:
                        p = server.PromptServer.instance
                        # Tuple: (number, prompt_id, prompt, extra_data, outputs_to_execute, sensitive_data)
                        p.prompt_queue.put(
                            (
                                0,
                                new_prompt_id,
                                prompt,
                                new_extra_data,
                                output_node_ids,
                                {},
                            )
                        )
                        print(
                            f"[IteratorSignal] Automatically queued next iteration for {iterator_id} (Prompt ID: {new_prompt_id})"
                        )
                    except Exception as e:
                        print(f"[IteratorSignal] Failed to auto-queue: {e}")

            else:
                print(f"[Iterator] Iterator {iterator_id} finished. Resetting state.")
                _ITERATOR_CORE_STATE[iterator_id] = 0

        return (has_image, image)
