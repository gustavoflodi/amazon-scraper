import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
from collections import Counter
from textblob import TextBlob
# from nltk.corpus import stopwords
# import nltk
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import threading
import plotly.express as px
import pandas as pd

st.set_page_config(page_title='Amazon Product Reviews Analysis', layout='wide')

# Initialize translator and set of stop words
# translator = Translator()
# stop_words = set(stopwords.words('english'))

# Download stopwords if not already downloaded
# nltk.download('stopwords')

# Headers for web scraping
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36",
    "Accept-Encoding": "gzip, deflate",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "DNT": "1",
    "Connection": "close",
    "Upgrade-Insecure-Requests": "1"
}

@st.cache
def scrape_products(search_words):
    search_words = search_words.strip().replace(' ', '+')
    product_dict = {}
    for num_page in range(1, 3):  # Reduced to 2 pages for faster demonstration
        url = f'https://www.amazon.com.br/s?k={search_words}&page={num_page}'
        st.write('Scraping this url:', url)

        page = requests.get(url, headers=headers)
        soup = BeautifulSoup(page.content, 'html.parser')

        products = soup.find_all('div', {'class': 'a-section a-spacing-base'})
        for product in products:
            try:
                if product.find('span', {'class': 'a-color-secondary'}).text == 'Patrocinado':
                    continue
                
                # Check if the product URL contains 'dp/' and extract the product ID
                product_url = product.find('a', {'class': 'a-link-normal s-no-outline'})['href']
                id_match = re.search(r'(?<=dp/)[^/]+', product_url)
                
                if id_match:
                    product_id = id_match[0]
                else:
                    continue  # Skip if no match found
                
                product_dict[product_id] = {
                    'name': product.find('span', {'class': 'a-size-base-plus a-color-base a-text-normal'}).text,
                    'image': product.find('img', {'class': 's-image'})['src'],
                    'price': product.find('span', {'class': 'a-offscreen'}).text,
                    'rating': float(product.find('span', {'class': 'a-icon-alt'}).text[:3].replace(',', '.')),
                    'votes': int(product.find('span', {'class': 'a-size-base s-underline-text'}).text.replace('.', ''))
                }
            except Exception as e:
                print(f"Exception while scraping product: {e}")
                continue

    return product_dict

def scrape_reviews_async(product_id, results):
    reviews = {}
    stars = ['one_star', 'two_star', 'three_star', 'four_star', 'five_star']

    # Initialize Selenium WebDriver
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Run in headless mode for faster execution
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    for star in stars:
        comments = []
        for num_page in range(1, 4):  # Limiting to 3 pages per star for demonstration
            url = f'https://www.amazon.com.br/product-reviews/{product_id}/ref=cm_cr_arp_d_viewopt_sr?filterByStar={star}&pageNumber={num_page}'
            st.write('Scraping this url:', url)

            driver.get(url)
            time.sleep(2)  # Adjust based on how fast the page loads

            # Locate all review elements
            reviews_elements = driver.find_elements(By.XPATH, '//span[@data-hook="review-body"]')

            if not reviews_elements:
                st.write(f"No reviews found for {star} page {num_page}")
                break

            for review in reviews_elements:
                comments.append(review.text.strip())

        reviews[star] = comments

    driver.quit()
    results[product_id] = reviews

def perform_sentiment_analysis(reviews_dict):
    sentiment_scores = {}
    for star, reviews in reviews_dict.items():
        sentiment = 0
        count = 0
        for review in reviews:
            blob = TextBlob(review)
            sentiment += blob.sentiment.polarity
            count += 1
        sentiment_scores[star] = sentiment / count if count > 0 else 0
    return sentiment_scores

def main():
    st.title('Amazon Product Reviews Analysis')

    if 'products_dict' not in st.session_state:
        st.session_state.products_dict = {}
    if 'reviews_fetched' not in st.session_state:
        st.session_state.reviews_fetched = False
    if 'current_product' not in st.session_state:
        st.session_state.current_product = None

    search_words = st.text_input('Enter product search words:')
    if st.button('Search Products'):
        with st.spinner('Scraping products...'):
            st.session_state.products_dict = scrape_products(search_words)
            st.session_state.reviews_fetched = False
            st.session_state.current_product = None
        if not st.session_state.products_dict:
            st.write(f"No products found")

    if st.session_state.current_product:
        product_info = st.session_state.products_dict[st.session_state.current_product]
        results = {}
        thread = threading.Thread(target=scrape_reviews_async, args=(st.session_state.current_product, results))
        thread.start()
        thread.join()

        reviews_dict = results.get(st.session_state.current_product, {})
        sentiment_scores = perform_sentiment_analysis(reviews_dict)
        st.session_state.reviews_fetched = True

        # Display reviews and sentiment scores
        st.subheader(f"Reviews for {product_info['name']}")
        for star, comments in reviews_dict.items():
            with st.expander(f"{star.capitalize()} Reviews:"):
                for comment in comments:
                    st.write(comment)
        st.subheader('Sentiment Scores:')
        sentiment_df = pd.DataFrame(sentiment_scores.items(), columns=['Star', 'Sentiment Score'])
        fig = px.bar(sentiment_df, x='Star', y='Sentiment Score', title='Sentiment Scores by Star Rating', color='Sentiment Score', color_continuous_scale='Bluered')
        st.plotly_chart(fig, use_container_width=True)

        if st.button('Go Back'):
            st.session_state.current_product = None

    elif st.session_state.products_dict:
        st.subheader('Products Found:')
        cols = st.columns(4)  # Use columns for better alignment
        for product_id, product_info in st.session_state.products_dict.items():
            col = cols[list(st.session_state.products_dict.keys()).index(product_id) % 4]
            with col:
                st.image(product_info['image'], caption=product_info['name'], use_column_width=True)
                st.write(f"**Price:** {product_info['price']}")
                st.write(f"**Rating:** {product_info['rating']}")
                st.write(f"**Votes:** {product_info['votes']}")
                if st.button(f"Fetch Reviews for {product_info['name']}", key=product_id):
                    st.session_state.current_product = product_id

    # Apply custom CSS for better styling
    st.markdown(
        """
        <style>
        .stButton>button {
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            font-size: 16px;
            margin: 4px 2px;
            cursor: pointer;
        }
        .stButton>button:hover {
            background-color: #45a049;
        }
        .st-expander {
            background-color: #f9f9f9;
            border-radius: 4px;
            padding: 8px;
        }
        .st-expander-header {
            font-size: 18px;
            font-weight: bold;
            color: #4CAF50;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
