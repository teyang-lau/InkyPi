from plugins.base_plugin.base_plugin import BasePlugin
from openai import OpenAI
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
from datetime import datetime
import base64
import requests
import logging
import os

logger = logging.getLogger(__name__)

IMAGE_MODELS = ["dall-e-3", "dall-e-2", "gpt-image-1", "nano-banana"]
DEFAULT_IMAGE_MODEL = "dall-e-3"
DEFAULT_IMAGE_QUALITY = "standard"


class AIImage(BasePlugin):
    def generate_settings_template(self):
        template_params = super().generate_settings_template()
        template_params["api_key"] = {
            "required": True,
            "service": "OpenAI",
            "expected_key": "OPEN_AI_SECRET",
        }
        return template_params

    def generate_image(self, settings, device_config):

        api_key = device_config.load_env_key("OPEN_AI_SECRET")
        g_api_key = device_config.load_env_key("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("OPEN AI API Key not configured.")
        if not g_api_key:
            raise RuntimeError("Gemini API Key not configured.")

        text_prompt = settings.get("textPrompt", "")

        image_model = settings.get("imageModel", DEFAULT_IMAGE_MODEL)
        if image_model not in IMAGE_MODELS:
            raise RuntimeError("Invalid Image Model provided.")
        image_quality = settings.get(
            "quality", "medium" if image_model == "gpt-image-1" else "standard"
        )
        randomize_prompt = settings.get("randomizePrompt") == "true"

        image = None
        try:
            if image_model == "nano-banana":
                ai_client = genai.Client(api_key=g_api_key)
            else:
                ai_client = OpenAI(api_key=api_key)
            if randomize_prompt:
                text_prompt = AIImage.fetch_image_prompt(
                    ai_client, text_prompt, image_model
                )

            image = AIImage.fetch_image(
                ai_client,
                text_prompt,
                model=image_model,
                quality=image_quality,
                orientation=device_config.get_config("orientation"),
            )
        except Exception as e:
            logger.error(f"Failed to make Open AI request: {str(e)}")
            raise RuntimeError("Open AI request failure, please check logs.")
        return image

    @staticmethod
    def fetch_image(
        ai_client,
        prompt,
        model="dall-e-3",
        quality="standard",
        orientation="horizontal",
    ):
        logger.info(
            f"Generating image for prompt: {prompt}, model: {model}, quality: {quality}"
        )
        prompt += (
            ". The image should fully occupy the entire canvas without any frames, "
            "borders, or cropped areas. No blank spaces or artificial framing."
        )
        prompt += (
            "Focus on simplicity, bold shapes, and strong contrast to enhance clarity "
            "and visual appeal. Avoid excessive detail or complex gradients, ensuring "
            "the design works well with flat, vibrant colors of E-ink Spectra 6"
        )
        args = {
            "model": model,
            "prompt": prompt,
            "size": "1024x1024",
        }
        if model == "dall-e-3":
            args["size"] = "1792x1024" if orientation == "horizontal" else "1024x1792"
            args["quality"] = quality
        elif model == "gpt-image-1":
            args["size"] = "1536x1024" if orientation == "horizontal" else "1024x1536"
            args["quality"] = quality

        if model == "nano-banana":
            response = ai_client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=[prompt],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(
                        aspect_ratio="16:9",
                    ),
                ),
            )
            for part in response.parts:
                if part.inline_data is not None:
                    generated_image = part.as_image()
                    # img = Image.open(BytesIO(generated_image.image_bytes))
                    generated_image = generated_image._pil_image
                    img = generated_image.resize((1792, 1024), Image.LANCZOS)

        else:
            response = ai_client.images.generate(**args)
            if model in ["dall-e-3", "dall-e-2"]:
                image_url = response.data[0].url
                response = requests.get(image_url)
                img = Image.open(BytesIO(response.content))
            elif model == "gpt-image-1":
                image_base64 = response.data[0].b64_json
                image_bytes = base64.b64decode(image_base64)
                img = Image.open(BytesIO(image_bytes))

        # save image to folder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        directory = "/home/teyang/InkyPi/outputs/ai_images"
        path = f"{directory}/{model}_{quality}_{orientation}_{timestamp}.png"
        os.makedirs(directory, exist_ok=True)
        img.save(path)
        logger.info(f"Current directory: {os.getcwd()}")
        logger.info(f"Saved image to {path}")
        return img

    @staticmethod
    def fetch_image_prompt(
        ai_client, from_prompt=None, image_model=DEFAULT_IMAGE_MODEL
    ):
        logger.info(f"Getting random image prompt...")

        system_content = (
            "You are a creative assistant generating extremely random and unique image prompts. "
            "Avoid common themes like koi fish. Focus on unexpected, unconventional, and bizarre combinations "
            "of art style, medium, subjects, time periods, and moods. No repetition. Prompts "
            "should be 20 words or less and specify random artist, movie, tv show, game, comic, "
            "manga or time period for the theme. Do not provide any headers or repeat the request, "
            f"just provide the updated prompt in your response. {datetime.now().strftime('%Y_%m_%d_%H%M%S')}"
        )
        user_content = (
            "Give me a completely random image prompt, something unexpected, unique, and creative! "
            "Include vivid imagery and descriptive details."
        )
        if from_prompt and from_prompt.strip():
            system_content = (
                "You are a creative assistant specializing in generating highly descriptive "
                "and unique prompts for creating images. When given a short or simple image "
                "description, your job is to rewrite it into a more detailed, imaginative, "
                "and descriptive version that captures the essence of the original while "
                "making it unique and vivid. Avoid adding irrelevant details but feel free "
                "to include creative and visual enhancements. Avoid common themes. Focus on "
                "unexpected, unconventional, and bizarre combinations of art style, medium, "
                "subjects, time periods, and moods. Do not provide any headers or repeat the "
                "request, just provide your updated prompt in the response. Prompts "
                "should be 30 words or less and specify random artist, movie, tv show, game, "
                "comic, manga or time period for the theme."
            )
            user_content = (
                f'Original prompt: "{from_prompt}"\n'
                "Rewrite it to make it more detailed, imaginative, and unique while staying "
                "true to the original idea. Include vivid imagery and descriptive details. "
                "Avoid changing the subject of the prompt."
            )

        # Make the API call
        if image_model == "nano-banana":
            response = ai_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system_content,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )
            prompt = response.text.strip()
        else:
            response = ai_client.chat.completions.create(
                model="gpt-5-nano",
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_content},
                ],
                temperature=1,
                reasoning_effort="minimal",
            )

            prompt = response.choices[0].message.content.strip()
        logger.info(f"Generated random image prompt: {prompt}")
        return prompt
