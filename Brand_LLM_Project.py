import ollama
import sqlite3
import praw
import pandas as pd
from datetime import datetime
import streamlit as st
from pandas import DataFrame

db_name="scrap_brands_table.db"
model_name="qwen3:4b"

def create_db():
    conn=sqlite3.connect(db_name)
    cursor=conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mentions
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
     brand TEXT NOT NULL,  
     source TEXT NOT NULL,
     text TEXT NOT NULL,
     url TEXT,
     timestamp DATETIME,
     sentiment TEXT,
     topic TEXT,
     urgency TEXT   
        """)


def insert_mentions(brand,source,text,url,timestamp):
    conn=sqlite3.connect(db_name)
    cursor=conn.cursor()

    cursor.execute("select * from mentions where url=?",(url,))
    if not  url.fectone():
        cursor.execute("INSERT into mentions (brand,source,text,url,timestamp) values (?,?,?,?,?)" ,(brand,source,text,url,timestamp))


def extract_data_analysis(brand_name):

    with sqlite3.connect(db_name) as conn:
        df=pd.read_sql_query("select * from mentions where brand=? order by timestamp desc",conn,params=(brand_name,))
        if "timestamp" in df.columns:
            df["timestamp"]=pd.to_datetime(df["timestamp"])

        return df


def fetch_reddit_mentions(brand_name,subreddit,client_id, client_secret):

    try:
        reddit = praw.Reddit(client_id=client_id,
                             cilent_username=client_secret,
                             user_agent="BrandMonitorApp v1.1 by /u/LocalUser",
                             read_only=True)

        added_count=0
        processed_url=set()

        existing_df=extract_data_analysis(brand_name)
        existing_urls=set(existing_df["url"].tolist())

        for subname  in subreddit:
            try:
                subreddit=reddit.subreddit(subname)
                for post in subreddit.search(query=brand_name, sort="new", limit=20,
                                             time_filter="day"):

                    post_url=f"https://reddit.com{post.permalink}"

                    if post_url not in processed_url and post_url not in existing_urls:
                         text_to_add=f"{post.title} {post.selftext}"
                         if insert_mentions(brand_name,"reddit",text_to_add,post_url,
                                           datetime.fromtimestamp(post.created_utc)):
                            added_count+=1
                            processed_url.add(post_url)
            except Exception as e:
                st.warning(
                    f"Could not fetch from r/{subname}: {e}")  # if anything goes wring handling catch the error.
                return added_count  # After processing all subreddits successfully, return how many new mentions were added in total.
    except Exception as e:
        if "401" in str(e):
            st.error(f"Invalid credentials",{e})
        else :
            st.error(f"Reddit Error",{e})


# get sentiment
def get_sentiment(text):  # get text as an input [ text will be an row ]
    # Define the instruction prompt
    prompt_template = "Analyze the sentiment of the following text. Is it Positive, Negative, or Neutral? Answer with only one word."

    # Combine the instruction and the text into a single prompt
    full_prompt = f"{prompt_template}\n\nText to analyze:\n{text}"

    try:
        response = ollama.generate(
            model=model_name,
            prompt=full_prompt
        )
        # The response key is 'response' for ollama.generate
        return response["response"].strip()
    except Exception as e:
        st.error(f"Ollama error (Sentiment): {e}")
        return None


# get topic.
def get_topic(text):
    """Classifies the text into topics using ollama.generate."""

    # Define the instruction prompt
    prompt_template = """
    You are a text analysis engine. Your task is to read the following text and assign the **single best-fitting** category from the list below.
    **Categories & Definitions:**

    * **Customer Service Issue**: Problems with support, billing, shipping, or account interaction.
    * **Product Defect/Bug**: The product is broken, crashing, or not working as intended.
    * **High Price Complaint**: Feedback that the product or service is too expensive.
    * **Positive Review**: General praise, compliments, or success stories.
    * **Competitor Comparison**: The text explicitly mentions a competitor.
    * **Feature Request**: A suggestion for a new feature or an improvement to an existing one.
    * **PR/News**: Text that appears to be a press release, news article, or public announcement.
    * **Other**: Any other topic that does not clearly fit one of the categories above (e.g., general inquiry, spam, wrong email).

    **Rules:**
    1.  Choose only **one** category.
    2.  If none of the specific categories are a good match, you must use **'Other'**.
    3.  Output only the category name.
    """

    # Combine the instruction and the text into a single prompt
    full_prompt = f"{prompt_template}\n\nText to analyze:\n{text}"

    try:
        response = ollama.generate(
            model=model_name,
            prompt=full_prompt
        )
        return response["response"].strip()
    except Exception as e:
        st.error(f"Ollama error (Topic): {e}")
        return None


# get urgency
def get_urgency(text):
    """Determines the urgency of a text using ollama.generate."""

    # Define the instruction prompt
    prompt_template = """
    You are a PR crisis manager. Read this text. Is this a 'High Urgency' issue
    (e.g., safety risk, potential PR crisis, going viral) or a 'Low Urgency'
    issue (e.g., single user complaint, question)? Answer with 'High Urgency' or 'Low Urgency'.
    """

    # Combine the instruction and the text into a single prompt
    full_prompt = f"{prompt_template}\n\nText to analyze:\n{text}"

    try:
        response = ollama.generate(
            model=model_name,
            prompt=full_prompt
        )
        return response["response"].strip()
    except Exception as e:
        st.error(f"Ollama error (Urgency): {e}")
        return None


# IN OUR TABLE , WE HAVE INSERTED FEW COLUMNS  USING THE FUNCTION FETCH DATA ,
# REMAINING VALUES WE HAVE FOUND , LETS INSERT THEM NOW.


# UPDATION FUNCTION
def update_mention_analysis(mention_id, sentiment, topic, urgency):
    """Updates a mention with its AI analysis."""
    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE mentions
            SET sentiment = ?,
                topic     = ?,
                urgency   = ?
            WHERE id = ?
            """,
            (sentiment, topic, urgency, mention_id)
        )
        conn.commit()


def generate_positive_report_summary(df):
    """Generates a detailed, high-level summary of POSITIVE feedback."""
    positive_texts = "\n---\n".join(df[df['sentiment'] == 'Positive']['text'].tolist())
    if not positive_texts:
        return "No positive feedback found to summarize."

    positive_texts_subset = positive_texts[:4000]
    full_prompt = f"""
    You are an expert customer experience analyst.
    Your task is to analyze the following POSITIVE customer feedback and identify the main strengths appreciated by customers.

    Please provide a concise, business-oriented summary in exactly 3 bullet points covering:
    1. The top recurring points or aspects customers praised.
    2. The underlying strengths or reasons behind this positive sentiment (e.g., product quality, service experience, brand trust, etc.).
    3. The potential opportunities for the brand to further capitalize on these strengths.

    Be objective, avoid repetition, and use short, impactful sentences.

    POSITIVE CUSTOMER FEEDBACK:
    {positive_texts_subset}
    """

    try:
        response = ollama.generate(
            model=model_name,
            prompt=full_prompt
        )
        return response["response"].strip()
    except Exception as e:
        st.error(f"Ollama error (Positive Summary): {e}")
        return "Error generating summary."






def generate_negative_report_summary(df):
    """Generates a detailed, high-level summary of NEGATIVE feedback."""
    negative_texts = "\n---\n".join(df[df['sentiment'] == 'Negative']['text'].tolist())
    if not negative_texts:
        return "No negative feedback found to summarize."

    negative_texts_subset = negative_texts[:4000]
    full_prompt = f"""
    You are an expert customer experience analyst.
    Your task is to analyze the following NEGATIVE customer feedback and identify the most common pain points.

    Please provide a concise, business-oriented summary in exactly 3 bullet points covering:
    1. The top recurring complaints or issues customers mentioned.
    2. The underlying cause or pattern behind these issues (if visible).
    3. The potential impact or area of improvement for the brand.

    Be objective, avoid repetition, and use short, impactful sentences.

    NEGATIVE CUSTOMER FEEDBACK:
    {negative_texts_subset}
    """

    try:
        response = ollama.generate(
            model=model_name,
            prompt=full_prompt
        )
        return response["response"].strip()
    except Exception as e:
        st.error(f"Ollama error (Negative Summary): {e}")
        return "Error generating summary."




def generate_report_summary(df):
    """Generates a high-level summary of NEGATIVE feedback using ollama.generate."""
    negative_texts = "\n---\n".join(df[df['sentiment'] == 'Negative']['text'].tolist())
    if not negative_texts:
        return "No negative feedback found to summarize."

    negative_texts_subset = negative_texts[:4000]

    # The prompt already contains the text, so it's the 'full_prompt'
    full_prompt = f"""
        You are a product strategist. Read the following customer suggestions and feature requests.
        Analyze the underlying needs and ideas.

        Based *only* on these comments, provide a bullet-point summary of:
        1.  **Top Suggestions:** What are the most common or impactful ideas users are asking for?
        2.  **Future Opportunities:** What new features or future directions should the company consider working on based on these suggestions?

        Group similar ideas together.

        CUSTOMER SUGGESTIONS:
        {negative_texts_subset}
        """

    try:
        response = ollama.generate(
            model=model_name,
            prompt=full_prompt
        )
        return response["response"].strip()
    except Exception as e:
        st.error(f"Ollama error (Negative Summary): {e}")
        return "Error generating summary."


