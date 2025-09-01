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

# --- Autonomous Agent Controls ---
def render_agent_controls():
    """Render autonomous agent controls in sidebar"""
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🤖 Autonomous Agent")
    
    # Get agent status
    try:
        agent_status = requests.get(f"{API_BASE_URL}/agent/status", timeout=10).json()
        
        if agent_status.get("monitoring_active"):
            st.sidebar.success("🟢 Agent: ACTIVE")
            
            if st.sidebar.button("🛑 Stop Agent"):
                try:
                    stop_response = requests.post(f"{API_BASE_URL}/agent/stop-monitoring/", timeout=10)
                    if stop_response.status_code == 200:
                        st.sidebar.success("✅ Agent stopped!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.sidebar.error(f"❌ Failed to stop agent: {stop_response.status_code}")
                except Exception as e:
                    st.sidebar.error(f"❌ Failed to stop agent: {str(e)}")
        else:
            st.sidebar.error("🔴 Agent: OFFLINE")
            
            if st.sidebar.button("🚀 Start Agent"):
                try:
                    start_response = requests.post(f"{API_BASE_URL}/agent/start-monitoring/", timeout=10)
                    if start_response.status_code == 200:
                        st.sidebar.success("✅ Agent started!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.sidebar.error(f"❌ Failed to start agent: {start_response.status_code}")
                except Exception as e:
                    st.sidebar.error(f"❌ Failed to start agent: {str(e)}")
        
        # Show agent stats
        st.sidebar.metric("Autonomous Actions", agent_status.get("total_autonomous_actions", 0))
        st.sidebar.metric("Patterns Learned", agent_status.get("learned_patterns_count", 0))
        st.sidebar.metric("Memory Usage", agent_status.get("memory_usage_mb", "Unknown"))
        
        # Show recent agent actions
        if st.sidebar.button("📊 View Agent Actions"):
            st.session_state.show_agent_actions = True
            st.rerun()
            
    except requests.exceptions.RequestException as e:
        st.sidebar.warning("⚠️ Agent endpoints not available")
        st.sidebar.text("Agent may not be deployed")
        
        # Show manual test button
        if st.sidebar.button("🧪 Test Agent Endpoints"):
            st.session_state.test_agent = True
            st.rerun()
    except Exception as e:
        st.sidebar.error(f"❌ Agent error: {str(e)}")

def get_agent_status():
    """Get agent status safely"""
    try:
        response = requests.get(f"{API_BASE_URL}/agent/status", timeout=5)
        return response.status_code == 200 and response.json().get("monitoring_active", False)
    except:
        return False

def render_agent_dashboard():
    """Render agent dashboard page"""
    
    st.title("🤖 DevOps Sentinel - Autonomous Agent Dashboard")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Agent Status", "🟢 ACTIVE" if get_agent_status() else "🔴 OFFLINE")
    
    with col2:
        agent_data = requests.get(f"{API_BASE_URL}/agent/actions").json()
        st.metric("Actions Taken", len(agent_data.get("recent_actions", [])))
    
    with col3:
        st.metric("Patterns Learned", len(agent_data.get("learned_patterns", {})))
    
    # Recent autonomous actions
    st.subheader("🔄 Recent Autonomous Actions")
    
    for action in agent_data.get("recent_actions", []):
        with st.expander(f"🤖 {action['issue_type']} - {action['timestamp'][:19]}"):
            st.json(action)
    
    # Learned patterns
    st.subheader("🧠 Learned Patterns")
    
    for pattern, data in agent_data.get("learned_patterns", {}).items():
        success_rate = data["success_count"] / data["total_attempts"] if data["total_attempts"] > 0 else 0
        
        st.write(f"**{pattern}**")
        st.progress(success_rate)
        st.write(f"Success Rate: {success_rate:.1%} ({data['success_count']}/{data['total_attempts']})")
        st.write(f"Best Action: {data.get('best_action', 'None learned yet')}")
        st.write("---")

# Add to your main UI function:
# In your main UI, add this to the sidebar:
render_agent_controls()

# Tech Stack Section - placed after autonomous agent controls
with st.sidebar:
    st.header("🛠️ Tech Stack")
    st.markdown("""
    **Backend:**
    - 🚀 **FastAPI** - REST API framework
    - 🗄️ **TiDB Cloud** - Vector database
    - 🤖 **Google Gemini** - LLM for responses
    - 🔍 **SentenceTransformers** - Embeddings
    - 📊 **SQLAlchemy** - Database ORM
    
    **Frontend:**
    - 🎨 **Streamlit** - Interactive UI
    - 💬 **Slack Integration** - Notifications
    
    **Deployment:**
    - ☁️ **Railway.app** - Backend hosting
    - 🌐 **Streamlit Cloud** - Frontend hosting
    - 🐳 **Docker** - Containerization
    
    **Agent Features:**
    - 🤖 **Autonomous Monitoring**
    - 🧠 **Pattern Learning**
    - 📈 **Predictive Analysis**
    - ⚡ **Auto-remediation**
    """)

# Add agent testing section
if st.session_state.get('test_agent'):
    st.sidebar.markdown("### 🧪 Agent Endpoint Testing")
    
    endpoints = [
        "/agent/status",
        "/agent/start-monitoring/",
        "/agent/actions"
    ]
    
    for endpoint in endpoints:
        try:
            if endpoint.endswith("/"):
                response = requests.post(f"{API_BASE_URL}{endpoint}", timeout=5)
            else:
                response = requests.get(f"{API_BASE_URL}{endpoint}", timeout=5)
            
            if response.status_code == 200:
                st.sidebar.success(f"✅ {endpoint}")
            else:
                st.sidebar.error(f"❌ {endpoint} ({response.status_code})")
        except:
            st.sidebar.error(f"❌ {endpoint} (failed)")
    
    if st.sidebar.button("🔄 Clear Test"):
        st.session_state.test_agent = False
        st.rerun()

# Add agent dashboard option
if st.session_state.get('show_agent_actions'):
    render_agent_dashboard()

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
    