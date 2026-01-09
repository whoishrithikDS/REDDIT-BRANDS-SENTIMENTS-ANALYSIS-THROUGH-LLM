# Brand Monitoring & Sentiment Analysis App

## Overview

This project is a Python-based brand monitoring application that:

* Scrapes recent Reddit mentions of a brand
* Stores mentions in a SQLite database
* Uses a local LLM (via Ollama) to analyze **sentiment**, **topic**, and **urgency**
* Generates executive-style positive and negative feedback summaries
* Is designed to be used with **Streamlit** as the UI layer

The architecture is simple, local-first, and avoids external paid APIs for NLP.

---

## Tech Stack

* **Python 3.10+**
* **SQLite** – lightweight local database
* **PRAW** – Reddit API wrapper
* **Ollama** – local LLM inference
* **Qwen3:4B** – default LLM model
* **Pandas** – data manipulation
* **Streamlit** – UI & error reporting

---

## Database Schema

Database file: `scrap_brands_table.db`

### Table: `mentions`

| Column    | Type     | Description                                   |
| --------- | -------- | --------------------------------------------- |
| id        | INTEGER  | Primary key                                   |
| brand     | TEXT     | Brand name being monitored                    |
| source    | TEXT     | Data source (currently `reddit`)              |
| text      | TEXT     | Post title + body                             |
| url       | TEXT     | Canonical Reddit URL (used for deduplication) |
| timestamp | DATETIME | Post creation time                            |
| sentiment | TEXT     | Positive / Negative / Neutral                 |
| topic     | TEXT     | AI-classified topic                           |
| urgency   | TEXT     | High Urgency / Low Urgency                    |

---

## Core Functions

### `create_db()`

Creates the SQLite database and the `mentions` table if it does not already exist.

> **Important:** This function must be called once before inserting or querying data.

---

### `insert_mentions(brand, source, text, url, timestamp)`

Inserts a new mention into the database **only if the URL does not already exist**.

* Prevents duplicate Reddit posts
* Uses URL as the uniqueness check

> ⚠️ Bug: `url.fectone()` is invalid. It should be `cursor.fetchone()`.

---

### `extract_data_analysis(brand_name)`

Fetches all mentions for a given brand:

* Sorted by most recent
* Converts `timestamp` to `datetime`
* Returns a Pandas DataFrame

Used throughout the app for analysis and reporting.

---

### `fetch_reddit_mentions(brand_name, subreddit, client_id, client_secret)`

Scrapes Reddit for recent mentions of a brand.

**Process:**

1. Authenticates using PRAW
2. Searches each subreddit for the brand name
3. Pulls up to 20 posts per subreddit (last 24 hours)
4. Skips already-processed or stored URLs
5. Inserts new mentions into the database

**Returns:**

* Number of new mentions added

> ⚠️ Bugs / Issues:

* `cilent_username` is invalid; should be `client_secret`
* Function may silently fail on Reddit auth errors
* Early `return` inside subreddit loop stops processing remaining subreddits

---

## AI Analysis Functions (Ollama)

All AI calls use:

```python
model_name = "qwen3:4b"
```

---

### `get_sentiment(text)`

Classifies sentiment into:

* Positive
* Negative
* Neutral

Returns **exactly one word**.

Used for row-level sentiment tagging.

---

### `get_topic(text)`

Classifies text into **one** of the following categories:

* Customer Service Issue
* Product Defect/Bug
* High Price Complaint
* Positive Review
* Competitor Comparison
* Feature Request
* PR/News
* Other

Strict single-label classification.

---

### `get_urgency(text)`

Binary urgency classifier:

* High Urgency (PR risk, safety, viral potential)
* Low Urgency (isolated complaints or questions)

Designed for escalation logic and alerting.

---

### `update_mention_analysis(mention_id, sentiment, topic, urgency)`

Updates an existing mention with AI-derived metadata.

Typically run after new mentions are inserted.

---

## Report Generation

### `generate_positive_report_summary(df)`

Produces an **executive-level summary** of positive feedback:

* Exactly **3 bullet points**
* Focuses on:

  1. What customers like
  2. Why they like it
  3. How the brand can capitalize

Input text is truncated to 4,000 characters to avoid LLM overload.

---

### `generate_negative_report_summary(df)`

Produces a **3-bullet-point summary** of negative feedback:

* Top complaints
* Root causes or patterns
* Business impact or improvement areas

Designed for leadership and CX teams.

---

### `generate_report_summary(df)`

Despite the name, this function:

* Uses **negative sentiment only**
* Treats it as feature requests / suggestions
* Outputs:

  * Top user ideas
  * Future product opportunities

> ⚠️ Naming is misleading. This should be renamed to something like:
> `generate_feature_request_summary()`

---

## Known Issues (You Should Fix These)

1. **SQL Syntax Error**

   * `CREATE TABLE` statement is missing parentheses

2. **Deduplication Bug**

   * `url.fectone()` is invalid

3. **Reddit Auth Bug**

   * `cilent_username` is not a valid PRAW parameter

4. **Early Return Logic Error**

   * `return added_count` inside subreddit loop

5. **Function Name Collisions**

   * Two different "negative summary" functions with overlapping intent

6. **No Index on URL**

   * Should be indexed or UNIQUE for performance and integrity

---

## Intended Usage Flow

1. Call `create_db()`
2. Fetch Reddit mentions
3. Run sentiment/topic/urgency analysis per row
4. Update database records
5. Load data into Pandas
6. Generate summaries for reporting
7. Display results in Streamlit

---

## Future Improvements

* Add UNIQUE constraint on `url`
* Batch Ollama calls for speed
* Add retry/backoff logic
* Support Twitter / news scraping
* Add alerting for High Urgency items
* Normalize topics into a lookup table

---

## License

Internal / Prototype use. No license defined.
