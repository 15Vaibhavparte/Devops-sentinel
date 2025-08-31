# ui.py

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
        background-color: #0D1117; /* A dark, off-black color */
        color: #FFFFFF;             /* White text for readability */
        border: 1px solid #30363d;   /* A subtle border */
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
QUERY_ENDPOINT = f"{API_BASE_URL}/process-input/"  # ✅ UPDATED TO NEW UNIFIED ENDPOINT
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
            
            # Show available endpoints from stats
            endpoints = stats_data.get('endpoints', [])
            if endpoints:
                st.write("🔗 Available Endpoints:")
                for endpoint in endpoints:
                    st.write(f"  • {endpoint}")
    except:
        st.write("📊 Stats unavailable")
    
    st.header("ℹ️ About")
    st.info(
        "This UI demonstrates the 'DevOps Sentinel', an AI agent for a TiDB Hackathon project. "
        "It uses a RAG pipeline with TiDB Cloud for vector search and Google's Gemini for answer generation."
    )
    
    st.header("🛠️ Tech Stack")
    st.markdown(
        """
        - **UI:** Streamlit
        - **Backend:** FastAPI (Unified Endpoint)
        - **Database:** TiDB Cloud (Vector Search)
        - **LLM:** Google Gemini Flash
        - **Embeddings:** Sentence-Transformers
        - **Notifications:** Slack Integration
        - **Alert Processing:** Grafana Webhooks
        """
    )

# --- Main Interface ---
# Create columns for better layout
col1, col2 = st.columns([2, 1])

with col1:
    # --- User Input ---
    st.subheader("💬 Ask Your Question")
    
    # Predefined questions for quick testing
    quick_questions = [
        "What should I do about database connection timeouts?",
        "How do I troubleshoot high CPU usage on the database?",
        "What are the steps to resolve memory issues?",
        "How do I handle database lock timeouts?",
        "How do I resolve disk space issues?",
        "What should I do when the application is not responding?",
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

with col2:
    st.subheader("🚀 Quick Actions")
    
    # Add some example scenarios
    if st.button("🔄 Test Connection"):
        with st.spinner("Testing connection..."):
            try:
                response = requests.get(HEALTH_ENDPOINT, timeout=5)
                if response.status_code == 200:
                    st.success("✅ Connection successful!")
                else:
                    st.error("❌ Connection failed!")
            except:
                st.error("❌ Cannot reach backend!")
    
    if st.button("📊 Refresh Stats"):
        st.rerun()
    
    # Add a test alert button for demonstration
    if st.button("🚨 Test Alert Processing"):
        with st.spinner("Testing alert processing..."):
            try:
                test_alert = {
                    "status": "firing",
                    "alerts": [
                        {
                            "labels": {
                                "alertname": "HighCPUUsage",
                                "service": "database-server",
                                "instance": "db-prod-01"
                            },
                            "annotations": {
                                "summary": "CPU usage is above 90% for 5 minutes"
                            }
                        }
                    ]
                }
                
                response = requests.post(QUERY_ENDPOINT, json=test_alert, timeout=10)
                if response.status_code == 200:
                    st.success("✅ Alert processing test successful!")
                    result = response.json()
                    if "status" in result:
                        st.info(f"Result: {result['status']}")
                else:
                    st.error("❌ Alert processing test failed!")
            except Exception as e:
                st.error(f"❌ Test failed: {str(e)}")

# --- Main Query Section ---
st.subheader("🔍 Ask the Sentinel")

# --- Button to Trigger the Agent ---
if st.button("🤖 Ask the Sentinel", type="primary", use_container_width=True):
    if user_question and user_question.strip():
        # Show a spinner while the agent is "thinking"
        with st.spinner("🧠 The Sentinel is consulting its knowledge base..."):
            try:
                # Prepare the request payload for the unified endpoint
                payload = {"question": user_question.strip()}
                
                # Add timeout and better error handling
                response = requests.post(
                    QUERY_ENDPOINT, 
                    json=payload, 
                    timeout=60,  # Increase timeout to 60 seconds
                    headers={"Content-Type": "application/json"}
                )
                
                # Check if the request was successful
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check if the query was successful
                    if data.get("success", False):
                        st.success("✅ Answer Found!")
                        
                        # Display the response
                        st.markdown("### 🤖 DevOps Sentinel Response:")
                        st.markdown(data.get("answer", "No answer provided"))
                        
                        # Show source context if available
                        source = data.get("source_context", "")
                        if source:
                            with st.expander("📚 Source Information"):
                                st.text(source)
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
                        
                        # Get the answer from the API response
                        llm_answer = data.get("answer", "No answer provided.")
                        
                        # --- Save the answer to the session state ---
                        st.session_state['last_answer'] = llm_answer
                        st.session_state['last_question'] = user_question.strip()
                        
                        # Display the formatted answer from the LLM
                        st.subheader("🎯 Recommended Solution:")
                        
                        # Display answer in a nice container
                        with st.container():
                            st.markdown(f"""
                            <div class="success-box">
                                {llm_answer}
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # Display source context in a more user-friendly way
                        with st.expander("📖 View Source Context", expanded=False):
                            source_context = data.get("source_context", "No context available.")
                            
                            # Check if it's a string that looks like it has structure
                            if isinstance(source_context, str):
                                # Split by newlines and format nicely
                                lines = source_context.split('\n')
                                for line in lines:
                                    if line.strip():
                                        if line.startswith('Source:'):
                                            st.markdown(f"**{line}**")
                                        else:
                                            st.markdown(line)
                            else:
                                st.json(source_context)
                        
                        # Add feedback section
                        st.subheader("📝 Feedback")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if st.button("👍 Helpful"):
                                st.success("Thank you for your feedback!")
                        with col2:
                            if st.button("👎 Not Helpful"):
                                st.info("We'll work on improving our responses!")
                        with col3:
                            if st.button("🔄 Try Again"):
                                st.rerun()
                    
                    else:
                        # Handle unsuccessful queries
                        st.warning("⚠️ Partial Result")
                        st.subheader("📋 Available Information:")
                        answer_text = data.get("answer", "No information found.")
                        st.markdown(answer_text)
                        
                        # --- Save partial answers too ---
                        st.session_state['last_answer'] = answer_text
                        st.session_state['last_question'] = user_question.strip()
                        
                        if "source_context" in data:
                            with st.expander("📖 View Context"):
                                st.text(data["source_context"])
                
                elif response.status_code == 500:
                    st.error("🚫 Internal Server Error")
                    try:
                        error_data = response.json()
                        st.error(f"Error: {error_data.get('detail', 'Unknown server error')}")
                    except:
                        st.error("The server encountered an error processing your request.")
                
                else:
                    # Show an error message if the API call failed
                    st.error(f"❌ Error: Could not get an answer from the agent. Status code: {response.status_code}")
                    try:
                        error_data = response.json()
                        st.json(error_data)
                    except:
                        st.text(response.text)

            except requests.exceptions.Timeout:
                st.error("⏱️ Request timed out. The server might be busy. Please try again.")
            
            except requests.exceptions.ConnectionError:
                st.error("🔌 Connection Error: Could not connect to the Sentinel API.")
                st.info("Please ensure the backend is running at http://127.0.0.1:8000")
                
                # Provide troubleshooting steps
                with st.expander("🛠️ Troubleshooting Steps"):
                    st.markdown("""
                    1. Make sure your FastAPI server is running:
                       ```bash
                       uvicorn main:app --reload
                       ```
                    2. Check if the server is accessible at http://127.0.0.1:8000
                    3. Verify your environment variables are set correctly
                    4. Check the server logs for any errors
                    5. Try the new unified endpoint: /process-input/
                    """)
            
            except requests.exceptions.RequestException as e:
                st.error(f"🚫 Request Error: {str(e)}")
                
            except Exception as e:
                st.error(f"🚫 Unexpected Error: {str(e)}")
    else:
        st.warning("⚠️ Please enter a question.")

# --- Slack Integration Section ---
# Check if there is an answer in the session state to send
if 'last_answer' in st.session_state and st.session_state['last_answer']:
    st.markdown("---")
    st.subheader("📢 Share Results")
    
    # Show a preview of what will be sent
    with st.expander("📋 Preview Slack Message", expanded=False):
        question = st.session_state.get('last_question', 'Question not available')
        answer = st.session_state.get('last_answer', 'Answer not available')
        
        preview_message = f"""🤖 DevOps Sentinel Alert:

**Question:** {question}

**Solution:** {answer}"""
        
        st.markdown(preview_message)
    
    # Create columns for different sharing options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Main Slack button
        if st.button("💬 Send to Slack", type="secondary", use_container_width=True):
            with st.spinner("Sending notification to Slack..."):
                try:
                    # Format the message for Slack
                    question = st.session_state.get('last_question', 'Question not available')
                    answer = st.session_state.get('last_answer', 'Answer not available')
                    
                    slack_message = f"""**Question:** {question}

**DevOps Solution:** {answer}

Generated by DevOps Sentinel AI Assistant"""
                    
                    slack_payload = {"message": slack_message}
                    slack_response = requests.post(SLACK_ENDPOINT, json=slack_payload, timeout=10)
                    
                    if slack_response.status_code == 200:
                        st.toast("✅ Successfully sent to Slack!", icon="💬")
                        st.success("Message sent to your Slack channel!")
                    else:
                        error_msg = "Failed to send message to Slack"
                        try:
                            error_data = slack_response.json()
                            error_msg = error_data.get('detail', error_msg)
                        except:
                            pass
                        st.toast(f"❌ {error_msg}", icon="🚨")
                        st.error(f"Failed to send to Slack: {error_msg}")
                        
                except requests.exceptions.Timeout:
                    st.error("⏱️ Timeout: Slack notification took too long to send.")
                    
                except requests.exceptions.ConnectionError:
                    st.error("🔌 Connection Error: Could not reach the backend for Slack integration.")
                    
                except Exception as e:
                    st.error(f"🚫 Unexpected error sending to Slack: {str(e)}")
    
    with col2:
        # Copy to clipboard button
        copy_text = f"{st.session_state.get('last_question', '')}\n\n{st.session_state.get('last_answer', '')}"
        if st.button("📋 Copy Answer", use_container_width=True):
            st.toast("📋 Answer copied to clipboard!", icon="📋")
    
    with col3:
        # Clear session button
        if st.button("🗑️ Clear Session", use_container_width=True):
            if 'last_answer' in st.session_state:
                del st.session_state['last_answer']
            if 'last_question' in st.session_state:
                del st.session_state['last_question']
            st.toast("🗑️ Session cleared!", icon="🗑️")
            st.rerun()

# --- Footer ---
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("*Built for TiDB Hackathon 2025 🚀*")
with col2:
    if 'last_answer' in st.session_state:
        st.markdown("💡 *Ready to share your solution!*")
with col3:
    st.markdown("*Powered by Gemini AI & TiDB Vector Search*")