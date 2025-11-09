
import streamlit as st
import requests
import json
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Schedule Chatbot",
    page_icon="📅",
    layout="wide"
)

# Custom CSS
st.markdown('''
<style>
    .main {background-color: #f5f7fa;}
    .stTextInput>div>div>input {border-radius: 20px;}
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .user-message {
        background-color: #e3f2fd;
        text-align: right;
    }
    .bot-message {
        background-color: #f5f5f5;
    }
</style>
''', unsafe_allow_html=True)

# App title
st.title("📅 Schedule Chatbot")
st.markdown("*AI-powered assistant for schedule management*")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    api_url = st.text_input("API URL", value="http://localhost:8000")
    
    st.header("📊 System Status")
    if st.button("Check Health"):
        try:
            response = requests.get(f"{api_url}/health")
            if response.status_code == 200:
                health = response.json()
                st.success(f"Status: {health['status']}")
                st.json(health['services'])
            else:
                st.error("Service unavailable")
        except:
            st.error("Cannot connect to API")
    
    st.header("📚 Quick Examples")
    examples = [
        "Cho mình xem thời khóa biểu CLB101",
        "TKB ABC123 có vi phạm gì không?",
        "So sánh lịch CLB101 và CLB102"
    ]
    for ex in examples:
        if st.button(ex, key=ex):
            st.session_state.query = ex

# Initialize chat history
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if query := st.chat_input("Nhập câu hỏi của bạn..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)
    
    # Get bot response
    with st.chat_message("assistant"):
        with st.spinner("Đang xử lý..."):
            try:
                response = requests.post(
                    f"{api_url}/api/query",
                    json={"query": query}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    bot_response = result['response']
                    
                    # Display response
                    st.markdown(bot_response)
                    
                    # Display metadata
                    with st.expander("Chi tiết"):
                        st.write(f"**Intent:** {result['intent']}")
                        st.write(f"**Entities:** {result['entities']}")
                        st.write(f"**Confidence:** {result['confidence']:.2%}")
                    
                    # Save to history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": bot_response
                    })
                else:
                    st.error("Lỗi khi xử lý yêu cầu")
            
            except Exception as e:
                st.error(f"Lỗi: {str(e)}")

# Clear chat button
if st.sidebar.button("🗑️ Clear Chat"):
    st.session_state.messages = []
    st.rerun()
