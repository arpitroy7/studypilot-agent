import os
import json
import streamlit as st
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="StudyPilot — Agentic Study Planner",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom Styling for polished, minimal UI
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #10b981;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #94a3b8;
        margin-bottom: 1.5rem;
    }
    .activity-card {
        background-color: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 1rem;
        font-family: monospace;
        font-size: 0.92rem;
        color: #e2e8f0;
        margin-bottom: 1rem;
    }
    .activity-line {
        padding: 4px 0;
        border-bottom: 1px solid #1e293b;
    }
    .activity-line:last-child {
        border-bottom: none;
    }
</style>
""", unsafe_allow_html=True)

# Predefined curriculum for core subjects
CURRICULUM_DATA = {
    "python": [
        "Python Syntax, Types & Control Flow",
        "Data Structures (Lists, Tuples, Sets, Dictionaries)",
        "Functions, Scope, Recursion & Lambdas",
        "Object-Oriented Programming (OOP: Classes, Inheritance, Polymorphism)",
        "File Handling, Serialization & Exception Handling",
        "Standard Modules & Practical Problem Solving"
    ],
    "c programming": [
        "C Data Types, Operators & Control Flow",
        "Functions, Parameter Passing & Storage Classes",
        "Arrays, Strings & 2D Arrays",
        "Pointers, Pointer Arithmetic & Dynamic Memory (malloc/free)",
        "Structures, Unions & Typedef",
        "File Operations (fopen, fread, fwrite, fclose)"
    ],
    "data structures": [
        "Arrays, Strings & Complexity Analysis (Big-O)",
        "Linked Lists (Singly, Doubly, Circular)",
        "Stacks, Queues & Applications",
        "Trees, Binary Search Trees (BST) & Balanced Trees",
        "Graphs, BFS, DFS & Shortest Path Basics",
        "Sorting, Searching & Basic Dynamic Programming"
    ],
    "java": [
        "Java Syntax, Data Types & Flow Control",
        "Core OOP Concepts (Encapsulation, Inheritance, Polymorphism)",
        "Interfaces, Abstract Classes & Packages",
        "Java Collections Framework (List, Set, Map)",
        "Exception Handling & Multithreading Fundamentals",
        "File I/O, Streams & Lambda Expressions"
    ],
    "computer organization and architecture": [
        "Digital Logic Gates, Boolean Algebra & Combinational Circuits",
        "Instruction Set Architecture (ISA) & Addressing Modes",
        "ALU, Data Path & Control Unit Design",
        "Memory Hierarchy, Cache Mapping & Virtual Memory",
        "Pipelining, Hazards & Branch Prediction",
        "Input/Output Organization, Direct Memory Access (DMA) & Interrupts"
    ],
    "dbms": [
        "Database Architecture & Entity-Relationship (ER) Modeling",
        "Relational Model, Relational Algebra & Constraints",
        "SQL (DDL, DML, Joins, Subqueries, Aggregations)",
        "Normalization Theory (1NF, 2NF, 3NF, BCNF)",
        "Transactions, ACID Properties & Serializability",
        "Concurrency Control, Locking & Indexing (B/B+ Trees)"
    ]
}

# --- TOOL IMPLEMENTATIONS ---

def get_subject_topics(subject: str) -> dict:
    """Return a predefined structured set of topics for common subjects."""
    sub_clean = subject.strip().lower()
    
    # Exact or substring match
    matched_subject = None
    for key in CURRICULUM_DATA:
        if key in sub_clean or sub_clean in key:
            matched_subject = key
            break
            
    # Default fallbacks for common acronyms
    if not matched_subject:
        if "coa" in sub_clean or "architecture" in sub_clean or "organization" in sub_clean:
            matched_subject = "computer organization and architecture"
        elif "dsa" in sub_clean or "data structure" in sub_clean:
            matched_subject = "data structures"
        elif "database" in sub_clean or "sql" in sub_clean:
            matched_subject = "dbms"

    if matched_subject:
        topics = CURRICULUM_DATA[matched_subject]
        return {
            "status": "success",
            "subject": matched_subject.title(),
            "topic_count": len(topics),
            "topics": topics
        }
    else:
        # Generic fallback if subject is outside the standard 6
        fallback_topics = [
            f"{subject} Fundamentals & Core Syntax",
            f"{subject} Intermediate Structures & Workflows",
            f"{subject} Advanced Concepts & Best Practices",
            f"{subject} Real-world Application & Problem Solving",
            f"{subject} Comprehensive Review & Practice"
        ]
        return {
            "status": "success",
            "subject": subject.title(),
            "topic_count": len(fallback_topics),
            "topics": fallback_topics
        }

def calculate_available_time(days: float, hours_per_day: float) -> dict:
    """Calculate total available study hours."""
    days_val = float(days)
    hours_val = float(hours_per_day)
    total_hours = round(days_val * hours_val, 2)
    return {
        "status": "success",
        "days": days_val,
        "hours_per_day": hours_val,
        "total_available_hours": total_hours
    }

def create_study_schedule(topics: list, total_hours: float, weak_topics: list) -> dict:
    """
    Allocate available study time across topics with higher priority/weight
    given to weak topics, including dedicated buffer for revision and testing.
    """
    if not topics:
        return {"status": "error", "message": "No topics provided"}

    total_hours = float(total_hours)
    
    # Reserve 20% of total hours for final revision & mock testing
    revision_hours = round(total_hours * 0.20, 1)
    learning_hours = total_hours - revision_hours
    
    # Normalize weak topics for matching
    weak_clean = [w.strip().lower() for w in (weak_topics or [])]
    
    # Calculate weights: weak topics get 1.75x weight
    topic_entries = []
    total_weight = 0.0
    
    for t in topics:
        is_weak = any(w in t.lower() or t.lower() in w for w in weak_clean)
        weight = 1.75 if is_weak else 1.0
        total_weight += weight
        topic_entries.append({
            "topic": t,
            "is_weak": is_weak,
            "weight": weight
        })
        
    # Allocate hours based on weight
    allocated_schedule = []
    for item in topic_entries:
        topic_hrs = round((item["weight"] / total_weight) * learning_hours, 1)
        allocated_schedule.append({
            "topic": item["topic"],
            "allocated_hours": max(0.5, topic_hrs),
            "priority": "HIGH (Weak Topic Focus)" if item["is_weak"] else "STANDARD"
        })
        
    return {
        "status": "success",
        "total_available_hours": total_hours,
        "learning_hours": learning_hours,
        "revision_and_testing_hours": revision_hours,
        "schedule": allocated_schedule
    }

# Mapping tool functions
TOOL_MAP = {
    "get_subject_topics": get_subject_topics,
    "calculate_available_time": calculate_available_time,
    "create_study_schedule": create_study_schedule
}

# Tool schemas for Groq Tool Calling
AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_subject_topics",
            "description": "Retrieve the official list of core syllabus topics for common computer science and programming subjects (e.g. Python, C Programming, Data Structures, Java, Computer Organization and Architecture, DBMS).",
            "parameters": {
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "string",
                        "description": "The academic subject name, e.g. 'Python', 'DBMS', 'Data Structures'."
                    }
                },
                "required": ["subject"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_available_time",
            "description": "Calculate total available study hours given the number of days until the exam and daily study hours.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "number",
                        "description": "Number of days available before the exam."
                    },
                    "hours_per_day": {
                        "type": "number",
                        "description": "Hours of study available per day."
                    }
                },
                "required": ["days", "hours_per_day"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_study_schedule",
            "description": "Calculate structured time allocations for topics based on total study hours, prioritizing weak topics with higher weight and reserving revision/testing time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of topics to cover."
                    },
                    "total_hours": {
                        "type": "number",
                        "description": "Total available study hours."
                    },
                    "weak_topics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of student-identified weak topics that require extra attention."
                    }
                },
                "required": ["topics", "total_hours", "weak_topics"]
            }
        }
    }
]

# --- AGENT RUNNER ---

def run_agentic_study_planner(user_query: str, groq_api_key: str, activity_container):
    """
    Executes an autonomous agent loop where the LLM dynamically decides
    which tools to invoke, processes tool responses, and produces an actionable plan.
    """
    client = Groq(api_key=groq_api_key)
    
    system_prompt = (
        "You are StudyPilot, an autonomous agentic study planning assistant. "
        "Your task is to turn a student's study request and constraints into an optimal, realistic study plan.\n\n"
        "Guidelines:\n"
        "1. Analyze the student's request for subject, time constraints (days and hours per day), and weak areas.\n"
        "2. You have access to tools. Autonomously invoke the required tools in the necessary sequence:\n"
        "   - Use 'get_subject_topics' to get the standard curriculum.\n"
        "   - Use 'calculate_available_time' to calculate total study hours.\n"
        "   - Use 'create_study_schedule' to distribute time prioritizing weak topics with revision buffer.\n"
        "3. Once you receive the tool results, formulate a comprehensive, beautifully structured study plan containing:\n"
        "   - Overview & Total Available Hours\n"
        "   - Weak Topic Priority Breakdown\n"
        "   - Day-by-Day Detailed Schedule\n"
        "   - Topic Time Allocation\n"
        "   - Dedicated Revision & Practice Testing Time\n"
        "   - Short Practical Recommendation\n"
        "Do not expose internal hidden thoughts. Deliver an encouraging, actionable, and structured markdown plan."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_query}
    ]

    action_logs = []
    
    def log_action(icon_text: str):
        action_logs.append(icon_text)
        with activity_container:
            lines_html = "".join([f'<div class="activity-line">{log}</div>' for log in action_logs])
            st.markdown(f'<div class="activity-card">{lines_html}</div>', unsafe_allow_html=True)

    log_action("🧠 Analyzing study request")

    # Primary model with fallback support
    primary_model = "openai/gpt-oss-120b"
    fallback_model = "openai/gpt-oss-20b"
    active_model = primary_model

    max_turns = 6
    turn = 0
    
    while turn < max_turns:
        turn += 1
        try:
            response = client.chat.completions.create(
                model=active_model,
                messages=messages,
                tools=AGENT_TOOLS,
                tool_choice="auto",
                temperature=0.2,
                max_tokens=1500
            )
        except Exception as e:
            # If 120b fails, attempt fallback
            if active_model == primary_model and "rate" in str(e).lower():
                active_model = fallback_model
                response = client.chat.completions.create(
                    model=active_model,
                    messages=messages,
                    tools=AGENT_TOOLS,
                    tool_choice="auto",
                    temperature=0.2,
                    max_tokens=1500
                )
            else:
                raise e

        msg = response.choices[0].message
        tool_calls = msg.tool_calls

        if not tool_calls:
            # Agent concluded and produced final answer
            log_action("✅ Processing tool results")
            log_action("✅ Study plan generated")
            return msg.content

        # Handle tool calls dynamically chosen by the agent
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": tool_calls
        })

        for tc in tool_calls:
            fn_name = tc.function.name
            log_action(f"🔧 Calling {fn_name}")
            
            try:
                fn_args = json.loads(tc.function.arguments)
            except Exception:
                fn_args = {}

            if fn_name in TOOL_MAP:
                try:
                    tool_res = TOOL_MAP[fn_name](**fn_args)
                except Exception as ex:
                    tool_res = {"status": "error", "error": str(ex)}
            else:
                tool_res = {"status": "error", "error": f"Unknown tool '{fn_name}'"}

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "name": fn_name,
                "content": json.dumps(tool_res)
            })

    return "The agent reached the maximum number of tool iterations without generating a final response. Please try again."


# --- UI LAYOUT ---

st.markdown('<div class="main-title">🌱 StudyPilot — Agentic Study Planner</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Your AI agent for turning study constraints into an actionable plan.</div>', unsafe_allow_html=True)

# Check API Key
api_key = os.getenv("GROQ_API_KEY")

if not api_key or not api_key.strip():
    st.error("⚠️ GROQ_API_KEY is missing. Please add your GROQ_API_KEY to the .env file in the project folder to proceed.")
    st.stop()

# Example Queries
st.markdown("**💡 Quick Examples (Click to Load):**")
col1, col2, col3 = st.columns(3)

if "user_input" not in st.session_state:
    st.session_state["user_input"] = ""

with col1:
    if st.button("🐍 Python Exam (5 Days)"):
        st.session_state["user_input"] = "I have a Python exam in 5 days. I can study 3 hours per day. I am weak in OOP and file handling. Make me a study plan."
with col2:
    if st.button("🌳 Data Structures (7 Days)"):
        st.session_state["user_input"] = "I have a Data Structures exam in 7 days. I can study 4 hours per day. I am weak in Trees and Dynamic Programming. Make me a study plan."
with col3:
    if st.button("💾 DBMS Exam (4 Days)"):
        st.session_state["user_input"] = "I have a DBMS exam in 4 days. I can study 3.5 hours per day. I am weak in Normalization and Concurrency Control. Make me a study plan."

# Query Input
user_query = st.text_area(
    "Enter your study request:",
    value=st.session_state["user_input"],
    height=120,
    placeholder="e.g., I have a Python exam in 5 days. I can study 3 hours per day. I am weak in OOP and file handling. Make me a study plan."
)

plan_button = st.button("🚀 Plan My Study", type="primary", use_container_width=True)

if plan_button:
    if not user_query.strip():
        st.warning("Please enter your study requirements above.")
    else:
        st.markdown("---")
        st.subheader("🤖 Agent Activity")
        activity_placeholder = st.empty()
        
        with st.spinner("Agent is working..."):
            try:
                final_plan = run_agentic_study_planner(user_query, api_key, activity_placeholder)
                
                st.markdown("---")
                st.subheader("📋 Final Study Plan")
                st.markdown(final_plan)
                st.success("Study plan successfully crafted by StudyPilot Agent!")
            except Exception as e:
                st.error(f"Error during agent execution: {str(e)}")
