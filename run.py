import os
import sys
import json
import re
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

# Load local .env if present (for local testing)
load_dotenv()

# --- PREDEFINED CURRICULUM ---
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
    sub_clean = str(subject).strip().lower()

    matched_subject = None
    for key in CURRICULUM_DATA:
        if key in sub_clean or sub_clean in key:
            matched_subject = key
            break

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
        fallback_topics = [
            f"{subject} Fundamentals & Core Syntax",
            f"{subject} Intermediate Structures & Workflows",
            f"{subject} Advanced Concepts & Best Practices",
            f"{subject} Real-world Application & Problem Solving",
            f"{subject} Comprehensive Review & Practice"
        ]
        return {
            "status": "success",
            "subject": str(subject).title(),
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

    revision_hours = round(total_hours * 0.20, 1)
    learning_hours = total_hours - revision_hours

    if isinstance(weak_topics, str):
        weak_clean = [w.strip().lower() for w in re.split(r'[\r\n,;]+', weak_topics) if w.strip()]
    elif isinstance(weak_topics, list):
        weak_clean = [str(w).strip().lower() for w in weak_topics if str(w).strip()]
    else:
        weak_clean = []

    topic_entries = []
    total_weight = 0.0

    for t in topics:
        is_weak = any(w in str(t).lower() or str(t).lower() in w for w in weak_clean)
        weight = 1.75 if is_weak else 1.0
        total_weight += weight
        topic_entries.append({
            "topic": t,
            "is_weak": is_weak,
            "weight": weight
        })

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


TOOL_MAP = {
    "get_subject_topics": get_subject_topics,
    "calculate_available_time": calculate_available_time,
    "create_study_schedule": create_study_schedule
}

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

# --- UTILITIES ---

def sanitize_error(err_msg: str, api_key: str = "") -> str:
    """Ensure API keys and credentials are never exposed in logs or outputs."""
    cleaned = str(err_msg)
    if api_key and len(api_key) > 4:
        cleaned = cleaned.replace(api_key, "[REDACTED_API_KEY]")
    cleaned = re.sub(r'gsk_[A-Za-z0-9_]{16,}', '[REDACTED_API_KEY]', cleaned)
    return cleaned


def parse_weak_topics(raw) -> list:
    """Normalize weak topics from list or delimited textarea string into a list of strings."""
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    if isinstance(raw, str):
        parts = re.split(r'[\r\n,;]+', raw)
        return [p.strip() for p in parts if p.strip()]
    return [str(raw).strip()]


def read_aikart_input() -> dict:
    """
    Read aiKart input with priority:
    1. /aikart/input.json
    2. AIKART_INPUT environment variable (inline JSON string or file path)
    3. Local aikart/input.json or input.json (convenience for development)
    """
    # 1. Primary path in aiKart runtime
    primary_input = Path("/aikart/input.json")
    if primary_input.is_file():
        try:
            with open(primary_input, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to parse /aikart/input.json: {e}", file=sys.stderr)

    # 2. AIKART_INPUT environment variable
    env_input = os.environ.get("AIKART_INPUT")
    if env_input:
        env_input = env_input.strip()
        # Direct JSON string
        if (env_input.startswith("{") and env_input.endswith("}")) or (env_input.startswith("[") and env_input.endswith("]")):
            try:
                return json.loads(env_input)
            except Exception as e:
                print(f"Warning: Failed to parse AIKART_INPUT as JSON: {e}", file=sys.stderr)
        # File path in environment variable
        env_path = Path(env_input)
        if env_path.is_file():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Failed to read file from AIKART_INPUT ({env_path}): {e}", file=sys.stderr)
        # Fallback generic JSON parse
        try:
            return json.loads(env_input)
        except Exception:
            pass

    # 3. Local workspace fallback for testing
    for local_path in [Path("aikart/input.json"), Path("input.json")]:
        if local_path.is_file():
            try:
                with open(local_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Failed to read local input {local_path}: {e}", file=sys.stderr)

    raise ValueError("Input data not found. Provide /aikart/input.json or set the AIKART_INPUT environment variable.")


def write_aikart_output(response_markdown: str):
    """Write output conforming to the aiKart output contract."""
    output_payload = {
        "format": "markdown",
        "response": response_markdown
    }

    primary_path = Path("/aikart/output.json")
    try:
        primary_path.parent.mkdir(parents=True, exist_ok=True)
        with open(primary_path, "w", encoding="utf-8") as f:
            json.dump(output_payload, f, indent=2)
        print(f"Output successfully written to {primary_path}")
    except OSError as e:
        print(f"Notice: /aikart/output.json not directly accessible ({e}).", file=sys.stderr)

    # Also mirror to local workspace aikart/output.json for local visibility and testing
    try:
        local_path = Path("aikart/output.json")
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with open(local_path, "w", encoding="utf-8") as f:
            json.dump(output_payload, f, indent=2)
        print(f"Output mirrored to local workspace: {local_path}")
    except OSError:
        pass


# --- AGENT RUNNER ---

def run_agentic_study_planner(
    subject: str,
    days: float,
    hours_per_day: float,
    weak_topics: list,
    api_key: str
) -> str:
    """
    Executes an autonomous agent loop where Groq selects and calls tools
    dynamically, synthesizes observations, and creates an actionable Markdown study plan.
    """
    client = Groq(api_key=api_key)

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

    weak_str = ", ".join(weak_topics) if weak_topics else "None"
    user_prompt = (
        f"Please create a comprehensive study plan for me with the following constraints:\n"
        f"- Subject: {subject}\n"
        f"- Days Available: {days}\n"
        f"- Study Hours Per Day: {hours_per_day}\n"
        f"- Weak Topics: {weak_str}\n\n"
        f"Invoke your planning tools to retrieve the curriculum, calculate time availability, "
        f"and create a weighted schedule that prioritizes my weak topics and includes revision buffers. "
        f"Then generate the final study plan formatted in Markdown."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    primary_model = "openai/gpt-oss-120b"
    fallback_model = "openai/gpt-oss-20b"
    active_model = primary_model

    max_turns = 8
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
                max_tokens=2000
            )
        except Exception as e:
            err_str = str(e).lower()
            if active_model == primary_model and ("rate" in err_str or "unavailable" in err_str or "overloaded" in err_str):
                print(f"Primary model {primary_model} rate-limited/unavailable. Switching to fallback {fallback_model}...", file=sys.stderr)
                active_model = fallback_model
                response = client.chat.completions.create(
                    model=active_model,
                    messages=messages,
                    tools=AGENT_TOOLS,
                    tool_choice="auto",
                    temperature=0.2,
                    max_tokens=2000
                )
            else:
                raise e

        msg = response.choices[0].message
        tool_calls = msg.tool_calls

        if not tool_calls:
            return msg.content or "No study plan content generated."

        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": tool_calls
        })

        for tc in tool_calls:
            fn_name = tc.function.name
            try:
                fn_args = json.loads(tc.function.arguments) if tc.function.arguments else {}
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


# --- ENTRY POINT ---

def main():
    print("Starting StudyPilot aiKart agent runner...")
    api_key = os.environ.get("GROQ_API_KEY", "").strip()

    try:
        # 1. Read input
        raw_data = read_aikart_input()

        # Handle potential nesting under "inputs" or "input"
        if isinstance(raw_data, dict):
            if "inputs" in raw_data and isinstance(raw_data["inputs"], dict):
                raw_data = raw_data["inputs"]
            elif "input" in raw_data and isinstance(raw_data["input"], dict):
                raw_data = raw_data["input"]
        else:
            raise ValueError("Input data must be a JSON object.")

        # 2. Extract and validate fields
        subject = raw_data.get("subject")
        if not subject or not str(subject).strip():
            raise ValueError("Missing required input field: 'subject'")
        subject = str(subject).strip()

        days_raw = raw_data.get("days")
        if days_raw is None:
            raise ValueError("Missing required input field: 'days'")
        try:
            days = float(days_raw)
        except (ValueError, TypeError):
            raise ValueError("Field 'days' must be a valid number")
        if days <= 0:
            raise ValueError("Field 'days' must be greater than 0")

        hours_raw = raw_data.get("hours_per_day")
        if hours_raw is None:
            raise ValueError("Missing required input field: 'hours_per_day'")
        try:
            hours_per_day = float(hours_raw)
        except (ValueError, TypeError):
            raise ValueError("Field 'hours_per_day' must be a valid number")
        if hours_per_day <= 0:
            raise ValueError("Field 'hours_per_day' must be greater than 0")

        weak_topics_raw = raw_data.get("weak_topics")
        weak_topics = parse_weak_topics(weak_topics_raw)

        print(f"Loaded input: subject='{subject}', days={days}, hours_per_day={hours_per_day}, weak_topics={weak_topics}")

        # 3. Check GROQ API key
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set. Please provide GROQ_API_KEY in the environment.")

        # 4. Run autonomous agent loop
        print("Executing agent loop with Groq tool calling (model: openai/gpt-oss-120b)...")
        study_plan = run_agentic_study_planner(
            subject=subject,
            days=days,
            hours_per_day=hours_per_day,
            weak_topics=weak_topics,
            api_key=api_key
        )

        # 5. Write output
        write_aikart_output(study_plan)
        print("StudyPilot agent completed successfully.")
        sys.exit(0)

    except Exception as err:
        safe_err = sanitize_error(str(err), api_key)
        print(f"StudyPilot encountered an error: {safe_err}", file=sys.stderr)
        error_markdown = f"## StudyPilot Planning Notice\n\nUnable to generate study plan: {safe_err}"
        write_aikart_output(error_markdown)
        sys.exit(0)


if __name__ == "__main__":
    main()
