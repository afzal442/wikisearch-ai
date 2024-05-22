import streamlit as st
from llm_model import llm_answer_streaming
import ldclient
from ldclient import Context
from ldclient.config import Config
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

# Streamlit app layout
st.title(":rainbow: Wiki Search with Bedrock Streaming API")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

st.balloons()

if question := st.chat_input("Enter a Wikipedia topic to search..."):
    with st.chat_message("user"):
        st.markdown(question)
    st.session_state.messages.append({"role": "user", "content": question})

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        answer = st.write_stream(llm_answer_streaming(question))
    
    st.session_state.messages.append({"role": "assistant", "content": answer})
