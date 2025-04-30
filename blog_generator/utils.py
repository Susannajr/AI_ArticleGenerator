import os
import random
import logging
from dotenv import load_dotenv
# from huggingface_hub import InferenceClient
import google.generativeai as genai

logger = logging.getLogger(__name__)

# Явно указываем путь к .env
ENV_PATH = "/mnt/c/Users/User_/Desktop/ai_blog_generator-main/.env"
logger.debug(f"Attempting to load .env from: {ENV_PATH}")

# Загрузка переменных окружения
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)
    logger.debug(f"Loaded .env from: {ENV_PATH}")
else:
    logger.error(f".env file not found at: {ENV_PATH}")

# Логируем все переменные окружения для диагностики (без вывода значений ключей)
logger.debug(f"Environment variables: {[key for key in os.environ.keys()]}")

# # Получение API-ключа для Hugging Face
# api_key = os.getenv('HUGGINGFACEHUB_API_TOKEN')
# logger.debug(f"HUGGINGFACEHUB_API_TOKEN: {'Set' if api_key else 'Not set'}")
#
# # Временно заменяем raise на предупреждение, чтобы сервер запустился
# if not api_key:
#     logger.warning(
#         "API-ключ Hugging Face не найден! Проверьте переменную HUGGINGFACEHUB_API_TOKEN в файле .env. "
#         "Генерация контента будет недоступна до исправления."
#     )
#     api_key = None  # Продолжаем с None, генерация выдаст ошибку только при вызове

# Получение API-ключа для Gemini
api_key = os.getenv('GEMINI_API_KEY')
logger.debug(f"GEMINI_API_KEY: {'Set' if api_key else 'Not set'}")

if not api_key:
    logger.error(
        "API-ключ Gemini не найден! Проверьте переменную GEMINI_API_KEY в файле .env. "
        "Генерация контента будет недоступна до исправления."
    )
    raise ValueError("GEMINI_API_KEY is not set")

# Конфигурация Gemini API
genai.configure(api_key=api_key)

# ID модели
# MODEL = "distilgpt2"
# MAX_CONTEXT_LENGTH = 1024  # Максимальный лимит токенов для distilgpt2
MODEL = "gemini-1.5-flash"  # Используем бесплатную модель Gemini
MAX_CONTEXT_LENGTH = 8192  # Gemini имеет больший контекстный лимит

def format_prompt(message, custom_instructions=None):
    """Форматирование промпта для модели."""
    prompt = ""
    if custom_instructions:
        prompt += f"{custom_instructions}\n\n"
    prompt += f"{message}"
    return prompt

def estimate_token_count(text):
    """Примерная оценка количества токенов (1 токен ~ 4 символа)."""
    return len(text) // 4 + 1

def generate(transcript_text, temperature=0.7, max_new_tokens=500, top_p=0.95):
    """Генерация контента на основе текста транскрипта."""
    try:
        logger.debug("Starting content generation")

        # # Проверка API-ключа для Hugging Face
        # if not api_key:
        #     raise ValueError("Cannot generate content: HUGGINGFACEHUB_API_TOKEN is not set")

        # Валидация параметров
        temperature = max(float(temperature), 0.01)
        top_p = float(top_p)

        # Формирование инструкций
        custom_instructions = (
            "You are a professional article writer. "
            "Based on the following YouTube video transcript, create a comprehensive article. "
            "Requirements:\n"
            "- No titles or headings\n"
            "- Natural flow between paragraphs\n"
            "- Professional but engaging tone\n"
            "- Use markdown formatting\n"
            "- Minimum 500 words\n\n"
            f"Transcript:\n{transcript_text}"
        )

        # Формирование промпта
        formatted_prompt = format_prompt(transcript_text, custom_instructions)
        logger.debug("Prompt formatted")

        # Оценка длины промпта
        prompt_tokens = estimate_token_count(formatted_prompt)
        logger.debug(f"Estimated prompt tokens: {prompt_tokens}")

        # Проверка и обрезка, если промпт слишком длинный
        if prompt_tokens > MAX_CONTEXT_LENGTH - 100:  # Оставляем минимум 100 токенов для генерации
            logger.warning(f"Prompt too long ({prompt_tokens} tokens). Truncating transcript.")
            # Примерная обрезка: укорачиваем транскрипт
            max_transcript_chars = (MAX_CONTEXT_LENGTH - 100 - estimate_token_count(custom_instructions)) * 4
            transcript_text = transcript_text[:max_transcript_chars]
            formatted_prompt = format_prompt(transcript_text, custom_instructions)
            prompt_tokens = estimate_token_count(formatted_prompt)
            logger.debug(f"After truncation: Estimated prompt tokens: {prompt_tokens}")

        # Динамическая настройка max_new_tokens
        max_new_tokens = min(int(max_new_tokens), MAX_CONTEXT_LENGTH - prompt_tokens)
        if max_new_tokens < 100:
            logger.error(f"Insufficient tokens for generation: {max_new_tokens} available")
            raise ValueError(f"Prompt too long, only {max_new_tokens} tokens available for generation")

        # # Инициализация клиента Hugging Face
        # client = InferenceClient(model=MODEL, token=api_key)
        # logger.debug("InferenceClient initialized")
        #
        # # Генерация текста с Hugging Face
        # response = client.text_generation(
        #     prompt=formatted_prompt,
        #     temperature=temperature,
        #     max_new_tokens=max_new_tokens,
        #     top_p=top_p,
        #     seed=random.randint(0, 10**7),
        # )

        # Инициализация модели Gemini
        model = genai.GenerativeModel(MODEL)
        logger.debug("Gemini model initialized")

        # Настройка параметров генерации
        generation_config = {
            "temperature": temperature,
            "top_p": top_p,
            "max_output_tokens": max_new_tokens,
        }

        # Генерация текста с Gemini
        response = model.generate_content(
            formatted_prompt,
            generation_config=generation_config
        )
        logger.debug("Content generation completed")

        # Извлечение сгенерированного текста
        generated_text = response.text.strip()
        return generated_text

    except Exception as e:
        logger.error(f"Generation error: {str(e)}", exc_info=True)
        raise