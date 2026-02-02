class IteratorItem:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE",),
                "audio_text": ("STRING", {"multiline": True, "default": ""}),
                "video_prompt": ("STRING", {"multiline": True, "default": ""}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "ITERATOR_ITEM")
    RETURN_NAMES = ("IMAGE", "AUDIO_TEXT", "VIDEO_PROMPT", "ITERATOR_ITEM")
    FUNCTION = "process"
    CATEGORY = "Iterator"

    def process(self, image, audio_text, video_prompt):
        item = {"image": image, "audio_text": audio_text, "video_prompt": video_prompt}
        return (image, audio_text, video_prompt, item)
