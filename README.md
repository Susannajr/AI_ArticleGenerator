# AI_ArticleGenerator

## Overview

The AI Blog Generator is a web application built with Django that automates the creation of blog articles from YouTube video transcripts. Leveraging the Gemini AI model (gemini-1.5-flash), the application fetches video transcripts, generates professional blog content, and stores it in a PostgreSQL database. The project includes a user-friendly frontend (HTML, CSS, JavaScript) for submitting YouTube links, viewing generated blogs, and managing user accounts.

## Features

* YouTube Integration: Validates and sanitizes YouTube URLs, extracts video IDs, and fetches video titles via web scraping.
* Transcript Processing: Retrieves video transcripts using the YouTubeTranscriptApi with support for multiple languages (prioritizing English and Russian).
* Content Generation: Uses the Gemini AI API to generate comprehensive, markdown-formatted blog articles (minimum 500 words) based on transcripts.
* User Authentication: Supports user registration, login, and logout using Django’s authentication system.
* Blog Management: Allows users to view their generated blogs and access detailed views of individual posts.
* Error Handling: Implements robust logging and error handling for reliable operation.
* Database Storage: Stores blog posts in a PostgreSQL database with fields for user, YouTube title, link, generated content, and creation timestamp.

## Prerequisites

* Python: 3.12.3 or higher
* PostgreSQL: 16.8 or higher
* WSL: Ubuntu (for Windows users)
* Dependencies:
Django
psycopg2
python-dotenv
youtube-transcript-api
pytube
requests
beautifulsoup4
google-generativeai
dj-database-url

## Setup Instructions

1. Clone the Repository

`git clone <repository-url>
cd projectS4`

2. Set Up Virtual Environment

`python3 -m venv aivenv
source aivenv/bin/activate`

3. Install Dependencies

`pip install -r requirements.txt`

4. Configure PostgreSQL
Ensure PostgreSQL is installed and running:

`sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql`
Create a database and user:

`sudo -u postgres psql`
`CREATE DATABASE mydatabase;
CREATE USER myuser WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE mydatabase TO myuser;
\q`

5. Configure Environment Variables
Create a .env file in the project root (/mnt/c/Users/spart/OneDrive/Bureau/projectS4/.env):

`DATABASE_URL=postgresql://myuser:your_secure_password@localhost:5432/mydatabase
GEMINI_API_KEY=your_gemini_api_key
HUGGINGFACEHUB_API_TOKEN=your_huggingface_api_key
SECRET_KEY=your_django_secret_key
DEBUG=True`
Obtain API keys from Google Gemini and Hugging Face. Generate a Django secret key.

6. Update Environment Path
Edit utils.py to correct the .env path:

`ENV_PATH = "/mnt/c/Users/spart/OneDrive/Bureau/projectS4/.env"`

7. Apply Migrations

`python3 manage.py makemigrations
python3 manage.py migrate`

8. Run the Server

`python3 manage.py runserver`
Access the application at http://localhost:8000.

## Project Structure

* models.py: Defines the BlogPost model for storing blog data.
* urls.py: Configures URL routes for home, blog generation, blog listing, blog details, and authentication.
* utils.py: Handles Gemini AI content generation, environment variable loading, and prompt formatting.
* views.py: Implements core logic for URL validation, transcript fetching, content generation, blog management, and user authentication.
* templates/: Contains HTML templates (index.html, all-blogs.html, blog-details.html, login.html, signup.html).
* static/: Includes CSS and JavaScript for the frontend.

## Usage

1. Register/Login: Create an account or log in at /signup or /login.
2. Generate Blog: Submit a YouTube video URL at the home page (/). The application fetches the transcript and generates a blog article.
3. View Blogs: Access all generated blogs at /blog-list.
4. Blog Details: View individual blog details at /blog-details/<id>.
5. Logout: Log out at /logout.

## Troubleshooting

* Database Connection Error:
Verify DATABASE_URL in .env matches PostgreSQL credentials.
Ensure PostgreSQL is running: sudo systemctl status postgresql.
Test connection: psql -U myuser -h localhost -d mydatabase.

* API Key Issues:
Confirm GEMINI_API_KEY is valid and set in .env.
Revoke and regenerate compromised keys.

* Incorrect .env Path:
Update utils.py if logs show attempts to load /mnt/c/Users/User_/Desktop/ai_blog_generator-main/.env.

## Future Improvements

* Replace web scraping for YouTube titles with a more robust API.
* Add support for additional AI models or providers.
* Enhance frontend with interactive features (e.g., real-time blog previews).
* Implement content editing for generated blogs.

## License

**This project is licensed under the MIT License.**
