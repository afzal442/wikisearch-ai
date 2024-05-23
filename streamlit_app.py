import streamlit as st
from llm_model import llm_answer_streaming
import ldclient
from ldclient import Context
from ldclient.config import Config
import wikipedia
import os

# Initialize LaunchDarkly client
sdk_key = os.getenv("LAUNCHDARKLY_SDK_KEY")
feature_flag_key = "wikisearch"

if not sdk_key:
    st.error("Please set the LAUNCHDARKLY_SDK_KEY environment variable.")
    st.stop()

ldclient.set_config(Config(sdk_key))

if not ldclient.get().is_initialized():
    st.error("LaunchDarkly SDK failed to initialize. Check your internet connection and SDK credentials.")
    st.stop()

context = Context.builder('wiki').kind('user').name('Saan').build()
model_flag = ldclient.get().variation(feature_flag_key, context, "default_model")

# Helper functions
def link(i, item):
    return f"**[{i + 1}. {item['title']}]({item['url']})**"

def aggregate(items):
    groups = {}
    for item in items:
        groups.setdefault(item["url"], []).append(item)
    results = []
    for group in groups.values():
        result = {}
        result["url"] = group[0]["url"]
        result["title"] = group[0]["title"]
        result["text"] = "\n\n".join([item["text"] for item in group])
        results.append(result)
    return results

def render_suggestions():
    def set_query(query):
        st.session_state.suggestion = query

    suggestions = [
        "Travel destinations known for their beaches",
        "Time travel movies with a twist",
        "Book authors explaining Physics",
    ]
    columns = st.columns(len(suggestions))
    for i, column in enumerate(columns):
        with column:
            st.button(suggestions[i], on_click=set_query, args=[suggestions[i]])

def render_query():
    st.text_input(
        "Search",
        placeholder="Search, e.g. 'Backpacking in Asia'",
        key="user_query",
        label_visibility="collapsed",
    )

def get_query():
    if "suggestion" not in st.session_state:
        st.session_state.suggestion = None
    if "user_query" not in st.session_state:
        st.session_state.user_query = ""
    user_query = st.session_state.suggestion or st.session_state.user_query
    st.session_state.suggestion = None
    return user_query

# Streamlit app layout
st.title(":rainbow: Wiki Search with Bedrock Streaming API")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

st.balloons()

st.info("Search Wikipedia and summarize the results using Bedrock API. Type a query to start or pick one of these suggestions:")
render_suggestions()
render_query()

user_query = get_query()

if not user_query:
    st.stop()

MAX_ITEMS = 3

container = st.container()
header = container.empty()
header.write(f"Looking for results for: _{user_query}_")
placeholders = []
for i in range(MAX_ITEMS):
    placeholder = container.empty()
    placeholder.write("Searching...")
    placeholders.append(placeholder)

def search_wikipedia(query, limit):
    wikipedia.set_lang("en")
    search_results = wikipedia.search(query, results=limit)
    results = []
    for title in search_results:
        try:
            page = wikipedia.page(title)
            results.append({"url": page.url, "title": page.title, "text": page.summary})
        except wikipedia.PageError:
            continue
    return results

items = search_wikipedia(user_query, limit=3)
items = aggregate(items)[:MAX_ITEMS]

header.write(f"That's what I found about: _{user_query}_. **Summarizing results...**")
for i, item in enumerate(items):
    placeholders[i].markdown(f"{link(i, item)}")
    placeholders[i].markdown(f"**Content:** {item['text']}")

for i, item in enumerate(items):
    with placeholders[i]:
        prompt = f"Summarize the following text:\n\n{item['text']}"
        response = llm_answer_streaming(prompt)
        summary = ''.join(response)
        placeholders[i].success(f"{link(i, item)}\n\n**Summary:** {summary}")

header.write("Search finished. Try something else!")
