# ui_clean.py - Clean working version

import streamlit as st
import requests
import json
import time
import os

# --- Page Configuration ---
st.set_page_config(
    page_title="DevOps Sentinel",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS ---
st.markdown("""
<style>
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #0D1117;
        color: #FFFFFF;
        border: 1px solid #30363d;
        margin: 1rem 0;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# --- App Title and Description ---
st.title("🤖 DevOps Sentinel Agent")
st.markdown("**Ask a question about a DevOps issue, and the agent will consult its knowledge base to find a solution.**")

# --- API Configuration ---
API_BASE_URL = os.getenv("API_BASE_URL", "https://devops-sentinel-production.up.railway.app")
QUERY_ENDPOINT = f"{API_BASE_URL}/process-input/"
HEALTH_ENDPOINT = f"{API_BASE_URL}/health"
STATS_ENDPOINT = f"{API_BASE_URL}/stats"
SLACK_ENDPOINT = f"{API_BASE_URL}/notify-slack/"

# --- Sidebar Information ---
with st.sidebar:
    st.header("🔧 System Status")
    
    # Health Check
    try:
        health_response = requests.get(HEALTH_ENDPOINT, timeout=5)
        if health_response.status_code == 200:
            health_data = health_response.json()
            if health_data.get("status") == "healthy":
                st.success("✅ System Online")
                st.write(f"📊 Database: {health_data.get('database', 'Unknown')}")
                st.write(f"🤖 Gemini: {health_data.get('gemini', 'Unknown')}")
            else:
                st.error("❌ System Issues")
        else:
            st.error("❌ Backend Offline")
    except:
        st.error("❌ Cannot Connect")
    
    # Stats
    try:
        stats_response = requests.get(STATS_ENDPOINT, timeout=5)
        if stats_response.status_code == 200:
            stats_data = stats_response.json()
            st.header("📈 Knowledge Base Stats")
            st.metric("Total Documents", stats_data.get('total_chunks', 0))
            st.metric("Sources", stats_data.get('unique_sources', 0))
            st.write(f"🧠 Model: {stats_data.get('llm_model', 'Unknown')}")
    except:
        st.write("📊 Stats unavailable")
    
    st.header("ℹ️ About")
    st.info(
        "This UI demonstrates the 'DevOps Sentinel', an AI agent for a TiDB Hackathon project. "
        "It uses a RAG pipeline with TiDB Cloud for vector search and Google's Gemini for answer generation."
    )

# --- Main Interface ---
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("💬 Ask Your Question")
    
    # Predefined questions
    quick_questions = [
        "What should I do about database connection timeouts?",
        "How do I troubleshoot high CPU usage on the database?",
        "What are the steps to resolve memory issues?",
        "How do I handle database lock timeouts?",
        "Custom question..."
    ]
    
    selected_question = st.selectbox(
        "Choose a quick question or select 'Custom question...' to write your own:",
        quick_questions
    )
    
    if selected_question == "Custom question...":
        user_question = st.text_area(
            "Enter your custom question:",
            height=100,
            placeholder="Type your DevOps question here..."
        )
    else:
        user_question = st.text_area(
            "Selected question (you can edit it):",
            value=selected_question,
            height=100
        )

    # Submit button
    if st.button("🔍 Ask the Sentinel", key="ask_sentinel", type="primary"):
        if user_question and user_question.strip():
            with st.spinner("🧠 The Sentinel is consulting its knowledge base..."):
                try:
                    payload = {"question": user_question.strip()}
                    
                    response = requests.post(
                        QUERY_ENDPOINT, 
                        json=payload, 
                        timeout=60,
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if data.get("success", False):
                            st.success("✅ Answer Found!")
                            
                            # Display the answer
                            st.subheader("🎯 Recommended Solution:")
                            with st.container():
                                st.markdown(f"""
                                <div class="success-box">
                                    {data.get("answer", "No answer provided")}
                                </div>
                                """, unsafe_allow_html=True)
                            
                            # Display source context
                            with st.expander("📖 View Source Context", expanded=False):
                                source_context = data.get("source_context", "No context available.")
                                if isinstance(source_context, str):
                                    lines = source_context.split('\n')
                                    for line in lines:
                                        if line.strip():
                                            if line.startswith('Source:'):
                                                st.markdown(f"**{line}**")
                                            else:
                                                st.markdown(line)
                                else:
                                    st.json(source_context)
                            
                            # Save to session state
                            st.session_state['last_answer'] = data.get("answer", "")
                            st.session_state['last_question'] = user_question.strip()
                            
                        else:
                            st.error("❌ Query failed - no successful response from agent")
                            
                    elif response.status_code == 400:
                        st.error("❌ Bad Request - Please check your question format")
                        st.error(f"Error details: {response.text}")
                        
                    elif response.status_code == 502:
                        st.error("🔧 Backend temporarily unavailable. Please try again in a moment.")
                        
                    elif response.status_code == 504:
                        st.error("⏱️ Request timed out. Please try a shorter question.")
                        
                    else:
                        st.error(f"❌ Server Error: {response.status_code}")
                        st.error(f"Response: {response.text}")
                    
                except requests.exceptions.Timeout:
                    st.error("⏱️ Request timed out after 60 seconds. The AI is working hard on your question!")
                    st.info("💡 Try asking a more specific or shorter question.")
                    
                except requests.exceptions.ConnectionError:
                    st.error("🔌 Connection error. Please check if the backend is running.")
                    st.info("💡 Try refreshing the page or try again in a few moments.")
                    
                except Exception as e:
                    st.error(f"❌ Unexpected error: {str(e)}")
                    st.info("💡 Please try again or contact support.")

        else:
            st.warning("⚠️ Please enter a question before submitting.")

with col2:
    st.subheader("🚀 Quick Actions")
    
    if st.button("🔄 Test Connection"):
        with st.spinner("Testing connection..."):
            try:
                test_response = requests.get(HEALTH_ENDPOINT, timeout=5)
                if test_response.status_code == 200:
                    st.success("✅ Connection successful!")
                else:
                    st.error(f"❌ Connection failed: {test_response.status_code}")
            except Exception as e:
                st.error(f"❌ Test failed: {str(e)}")
    
    st.subheader("📬 Slack Integration")
    if 'last_answer' in st.session_state:
        slack_message = st.text_area(
            "Send solution to Slack:",
            value=f"DevOps Issue: {st.session_state.get('last_question', '')}\n\nSolution:\n{st.session_state.get('last_answer', '')}",
            height=100
        )
        
        if st.button("📤 Send to Slack"):
            if slack_message.strip():
                try:
                    slack_payload = {"message": slack_message.strip()}
                    slack_response = requests.post(SLACK_ENDPOINT, json=slack_payload, timeout=10)
                    if slack_response.status_code == 200:
                        st.success("✅ Message sent to Slack!")
                    else:
                        st.error(f"❌ Failed to send to Slack: {slack_response.status_code}")
                except Exception as e:
                    st.error(f"❌ Slack error: {str(e)}")
            else:
                st.warning("⚠️ Please enter a message.")
    else:
        st.info("🤖 Ask a question first to enable Slack sharing!")

# --- Footer ---
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        <p>🤖 DevOps Sentinel - AI-Powered Infrastructure Assistant</p>
        <p>Built with FastAPI, Streamlit, TiDB Cloud, and Google Gemini</p>
    </div>
    """, 
    unsafe_allow_html=True
)
