import logging
import json
import re
from urllib.parse import urlparse, parse_qs
from pytube import YouTube
from pytube import exceptions as pytube_exceptions
from youtube_transcript_api import YouTubeTranscriptApi
import requests
from bs4 import BeautifulSoup
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .utils import generate
from .models import BlogPost

logger = logging.getLogger(__name__)

# ============== ВАЛИДАЦИЯ URL ==============
VALID_YOUTUBE_DOMAINS = [
    'youtube.com',
    'youtu.be',
    'www.youtube.com',
    'm.youtube.com'
]

def is_valid_youtube_url(url):
    """Проверяет валидность YouTube ссылки."""
    try:
        parsed = urlparse(url)
        return any(d in parsed.netloc for d in VALID_YOUTUBE_DOMAINS)
    except Exception as e:
        logger.error(f"URL validation error: {str(e)}")
        return False

def sanitize_youtube_url(url):
    """Нормализует YouTube-ссылку и извлекает ID видео."""
    try:
        # Парсим URL
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        
        # Проверяем, является ли домен валидным для YouTube
        if not any(d in netloc for d in VALID_YOUTUBE_DOMAINS):
            logger.error(f"Invalid YouTube domain: {netloc}")
            return None

        # Извлекаем параметры запроса
        query_params = parse_qs(parsed.query)
        
        # Проверяем стандартный формат: youtube.com/watch?v=VIDEO_ID
        if 'v' in query_params and len(query_params['v'][0]) == 11:
            return f"https://www.youtube.com/watch?v={query_params['v'][0]}"
        
        # Проверяем короткие ссылки: youtu.be/VIDEO_ID
        if 'youtu.be' in netloc:
            video_id = parsed.path.lstrip('/')
            if len(video_id) == 11:
                return f"https://www.youtube.com/watch?v={video_id}"
        
        # Проверяем другие форматы через регулярные выражения
        patterns = [
            r"(?:v=|be\/|embed\/|shorts\/)([0-9A-Za-z_-]{11})",
            r"(?:watch\?v=)([0-9A-Za-z_-]{11})",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match and len(match.groups()) >= 1:
                video_id = match.group(1)
                if len(video_id) == 11:
                    return f"https://www.youtube.com/watch?v={video_id}"
        
        logger.error(f"Invalid YouTube URL format: {url}")
        return None

    except Exception as e:
        logger.error(f"URL sanitization error: {str(e)}")
        return None

# ============== ОСНОВНЫЕ ФУНКЦИИ ==============
@login_required
def index(request):
    """Главная страница."""
    return render(request, 'index.html')

def yt_title(url):
    """Получение заголовка через альтернативный метод."""
    return yt_title_alternative(url)

def yt_title_alternative(url):
    """Альтернативный способ получения заголовка видео."""
    try:
        video_id = get_video_id(url)
        if not video_id:
            logger.error(f"No video ID extracted from URL: {url}")
            return None
            
        # Отправляем запрос к странице видео
        response = requests.get(f'https://www.youtube.com/watch?v={video_id}', headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code != 200:
            logger.error(f"Failed to fetch video page, status code: {response.status_code}")
            return None
            
        # Парсим HTML для получения заголовка
        soup = BeautifulSoup(response.text, 'html.parser')
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.text.replace(' - YouTube', '').strip()
            logger.debug(f"Successfully fetched title: {title}")
            return title
        else:
            logger.error(f"No title tag found for video: {video_id}")
            return None
            
    except Exception as e:
        logger.error(f"Alternative title fetch error for {url}: {str(e)}", exc_info=True)
        return None

def get_video_id(url):
    """Извлечение ID видео с улучшенной валидацией."""
    try:
        clean_url = sanitize_youtube_url(url)
        if not clean_url:
            return None
            
        # Извлекаем ID из нормализованного URL
        parsed = urlparse(clean_url)
        query = parse_qs(parsed.query)
        if 'v' in query and len(query['v'][0]) == 11:
            return query['v'][0]
        
        logger.error(f"Failed to extract video ID from: {clean_url}")
        return None
    except Exception as e:
        logger.error(f"Video ID extraction failed: {str(e)}")
        return None

def get_transcript(video_id):
    """Получение транскрипта с улучшенной обработкой ошибок."""
    try:
        logger.debug(f"Attempting to fetch transcript for video ID: {video_id}")
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Логируем доступные транскрипты
        available_transcripts = [(t.language_code, t.is_generated) for t in transcript_list]
        logger.debug(f"Available transcripts: {available_transcripts}")
        
        # Приоритеты: английские -> русские -> любые автоматические
        for lang in ['en', 'ru', None]:
            try:
                if lang:
                    transcript = transcript_list.find_transcript([lang])
                    logger.debug(f"Found transcript for language: {lang}")
                else:
                    transcript = transcript_list.find_generated_transcript(['en'])
                    logger.debug("Found generated transcript for English")
                
                # Получаем данные транскрипта
                transcript_data = transcript.fetch()
                logger.debug(f"Transcript fetched with {len(transcript_data)} lines")
                
                # Проверяем формат данных
                transcript_lines = []
                if isinstance(transcript_data, list):
                    # Обрабатываем как список словарей
                    for item in transcript_data:
                        if isinstance(item, dict) and 'text' in item:
                            transcript_lines.append(item['text'])
                        else:
                            logger.debug(f"Skipping invalid transcript item: {item}")
                else:
                    # Пробуем обработать как объект FetchedTranscript
                    logger.debug(f"Handling transcript data as FetchedTranscript: {type(transcript_data)}")
                    # Извлекаем текст через итерацию или преобразование
                    try:
                        # Проверяем, есть ли атрибут или метод для получения текста
                        for segment in transcript_data:  # FetchedTranscript может быть итерируемым
                            if hasattr(segment, 'text'):
                                transcript_lines.append(segment.text)
                            elif isinstance(segment, dict) and 'text' in segment:
                                transcript_lines.append(segment['text'])
                            else:
                                logger.debug(f"Skipping invalid segment: {segment}")
                    except Exception as e:
                        logger.error(f"Failed to extract text from transcript data: {str(e)}")
                        continue
                
                if transcript_lines:
                    logger.debug(f"Extracted {len(transcript_lines)} valid transcript lines")
                    return transcript_lines
                else:
                    logger.error(f"No valid text found in transcript for language: {lang}")
                    continue
                    
            except Exception as e:
                logger.debug(f"Failed to fetch transcript for language {lang}: {str(e)}")
                continue
                
        logger.error(f"No suitable transcript found for video ID: {video_id}")
        return None
    except Exception as e:
        logger.error(f"Transcript fetch error for video ID: {video_id}: {str(e)}", exc_info=True)
        return None

# ============== ГЕНЕРАЦИЯ БЛОГА ==============
@csrf_exempt
@login_required
def generate_blog(request):
    if request.method == 'POST':
        try:
            # Проверка и парсинг данных
            try:
                data = json.loads(request.body)
                yt_link = data.get('link')
                if not yt_link:
                    logger.error("Missing 'link' parameter")
                    return JsonResponse({'error': 'YouTube link is required'}, status=400)
            except Exception as e:
                logger.error(f"JSON parsing error: {str(e)}")
                return JsonResponse({'error': 'Invalid request format'}, status=400)

            # Валидация URL
            if not is_valid_youtube_url(yt_link):
                logger.error(f"Invalid YouTube URL: {yt_link}")
                return JsonResponse({'error': 'Invalid YouTube URL'}, status=400)

            # Нормализация URL
            clean_url = sanitize_youtube_url(yt_link)
            if not clean_url:
                logger.error(f"Unsupported URL format: {yt_link}")
                return JsonResponse({'error': 'Unsupported URL format'}, status=400)

            # Получение метаданных
            title = yt_title(clean_url)  # Теперь используем только альтернативный метод
            video_id = get_video_id(clean_url)
            if not title or not video_id:
                logger.error(f"Failed to get metadata for: {clean_url}")
                return JsonResponse({'error': 'Unable to retrieve video information. The video may be unavailable or restricted.'}, status=400)

            # Получение транскрипта
            transcript = get_transcript(video_id)
            if not transcript:
                logger.error(f"No transcript found for: {video_id}")
                return JsonResponse({'error': 'No transcript available. The video may not have subtitles or they are disabled.'}, status=400)
                
            if len(transcript) < 3:
                logger.error(f"Transcript too short: {len(transcript)} lines")
                return JsonResponse({'error': 'Transcript is too short'}, status=400)

            # Генерация контента
            try:
                transcript_text = " ".join(transcript)
                blog_content = generate(transcript_text)
                if not blog_content.strip():
                    raise ValueError("Empty content generated")
            except Exception as e:
                logger.error(f"Generation failed: {str(e)}")
                return JsonResponse({'error': 'Content generation failed'}, status=500)

            # Сохранение в БД
            try:
                BlogPost.objects.create(
                    user=request.user,
                    youtube_title=title[:255],  # Обеспечиваем соответствие длине CharField
                    youtube_link=clean_url,
                    generated_content=blog_content
                )
            except Exception as e:
                logger.error(f"Database error: {str(e)}")
                return JsonResponse({'error': 'Failed to save article'}, status=500)

            return JsonResponse({'content': blog_content})

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return JsonResponse({'error': 'Internal server error'}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)

# ============== УПРАВЛЕНИЕ БЛОГОМ ==============
@login_required
def blog_list(request):
    """Список блогов пользователя."""
    blog_articles = BlogPost.objects.filter(user=request.user)
    return render(request, "all-blogs.html", {'blog_articles': blog_articles})

@login_required
def blog_details(request, pk):
    """Детали блога по ID."""
    try:
        blog_article_detail = BlogPost.objects.get(id=pk)
        if request.user == blog_article_detail.user:
            return render(request, 'blog-details.html', {'blog_article_detail': blog_article_detail})
        return redirect('/')
    except BlogPost.DoesNotExist:
        logger.error(f"Blog post with ID {pk} not found")
        return redirect('/')

# ============== АУТЕНТИФИКАЦИЯ ==============
def user_login(request):
    """Авторизация пользователя."""
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('/')
        return render(request, 'login.html', {'error_message': 'Invalid credentials'})
    return render(request, 'login.html')

def user_signup(request):
    """Регистрация нового пользователя."""
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        repeat_password = request.POST['repeatPassword']
        
        if password != repeat_password:
            return render(request, 'signup.html', {'error_message': 'Passwords do not match'})
        
        try:
            user = User.objects.create_user(username, email, password)
            login(request, user)
            return redirect('/')
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return render(request, 'signup.html', {'error_message': 'Username already exists'})
    
    return render(request, 'signup.html')

@login_required
def user_logout(request):
    """Выход пользователя."""
    logout(request)
    return redirect('/')