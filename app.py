from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import bcrypt
import markdown  # Add this import
import os
from dotenv import load_dotenv
from search_module import SnippetGoogleSearch  # Changed to actual filename

load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)



# Initialize the search processor once
processor = SnippetGoogleSearch(
    google_api_key=os.environ.get('GOOGLE_API_KEY'),
    cx_id=os.environ.get('CX_ID'),
    deepseek_api_key=os.environ.get('DEEPSEEK_API_KEY'),
    k=10,
    enable_extra_snippets=False
)

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        query = request.form.get('search')
        return redirect(url_for('search', query=query))
    return render_template('index.html')

@app.route('/search')
def search():
    query = request.args.get('query', '')
    if not query:
        return redirect(url_for('home'))
    
    try:
        result = processor.process_query(query)
        # Convert markdown to HTML
        # Use these markdown extensions
        analysis_html = markdown.markdown(
            result['analysis'],
            extensions=['tables', 'md_in_html'],
            extension_configs={
                'tables': {
                    'use_align_attribute': True
                }
            }
        )
        return render_template('results.html', 
                            analysis=analysis_html,
                            sources=result['sources'],
                            query=query)
    except Exception as e:
        app.logger.error(f"Search error: {str(e)}")
        return render_template('error.html', 
                            error=f"Search Error: {str(e)}")

# Keep your existing about and howto routes
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/howto')
def howto():
    return render_template('howto.html')

if __name__ == '__main__':
    app.run(debug=True, port=5001)