from ...core import _ITERATOR_CORE_STATE


class IteratorList:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "iterator_id": ("STRING", {"default": "default_iterator"}),
                "reset": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "item1": ("ITERATOR_ITEM",),
                "item2": ("ITERATOR_ITEM",),
                "item3": ("ITERATOR_ITEM",),
                "item4": ("ITERATOR_ITEM",),
                "item5": ("ITERATOR_ITEM",),
                "item6": ("ITERATOR_ITEM",),
                "trigger": ("*",),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "BOOLEAN")
    RETURN_NAMES = ("IMAGE", "AUDIO_TEXT", "VIDEO_PROMPT", "IS_FINISHED")
    FUNCTION = "iterate"
    CATEGORY = "Iterator"

    @classmethod
    def IS_CHANGED(s, iterator_id, **kwargs):
        from ...core import _ITERATOR_CORE_STATE

        val = _ITERATOR_CORE_STATE.get(iterator_id, 0)
        print(f"[IteratorList] IS_CHANGED called for {iterator_id}. State: {val}")
        return val

    def iterate(self, iterator_id, reset, trigger=None, **kwargs):
        global _ITERATOR_CORE_STATE
        print(f"[IteratorList] Iterate called for {iterator_id}. Reset: {reset}")

        items = []
        for i in range(1, 7):
            it = kwargs.get(f"item{i}")
            if it:
                items.append(it)

        if reset:
            _ITERATOR_CORE_STATE[iterator_id] = 0

        if not items:
            return (None, "", "", True)

        idx = _ITERATOR_CORE_STATE.get(iterator_id, 0)
        print(f"[IteratorList] Processing {iterator_id}. Index: {idx} / {len(items)}")

        # Ensure index is within bounds (can happen if items list changed)
        if idx >= len(items):
            # If we are past the end, we are finished.
            # Do NOT reset here automatically, otherwise we loop forever.
            # We will cap it at the last item for safety, but is_finished will be True.
            idx = len(items) - 1
            if idx < 0:
                idx = 0  # Handle empty list case safely

        item = items[idx]
        image = item.get("image")
        audio_text = item.get("audio_text", "")
        video_prompt = item.get("video_prompt", "")

        is_finished = (idx + 1) >= len(items)

        return (image, audio_text, video_prompt, is_finished)
