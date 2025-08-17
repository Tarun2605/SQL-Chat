import streamlit as st
from pathlib import Path
from langchain.agents import create_sql_agent
from langchain.sql_database import SQLDatabase
from langchain.agents.agent_types import AgentType
from langchain.callbacks import StreamlitCallbackHandler
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from sqlalchemy import create_engine, text
import sqlite3
from langchain_groq import ChatGroq
import psycopg2
import os
import tempfile
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import time
from datetime import datetime
import re
import io
import base64
from urllib.parse import urlparse

# Page configuration
st.set_page_config(
    page_title="Advanced SQL Database Chat Assistant", 
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.main-header {
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    padding: 1rem;
    border-radius: 10px;
    color: white;
    text-align: center;
    margin-bottom: 2rem;
}
.metric-card {
    background: #f0f2f6;
    padding: 1rem;
    border-radius: 8px;
    border-left: 4px solid #667eea;
}
.query-history {
    max-height: 300px;
    overflow-y: auto;
    background: #f8f9fa;
    padding: 1rem;
    border-radius: 8px;
}
.success-message {
    background: #d4edda;
    color: #155724;
    padding: 0.75rem;
    border-radius: 8px;
    border: 1px solid #c3e6cb;
}
.connection-url-input {
    background: #f8f9fa;
    border: 2px solid #e9ecef;
    border-radius: 8px;
    padding: 0.75rem;
    margin: 0.5rem 0;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>🚀 Advanced SQL Database Chat Assistant</h1>
    <p>AI-powered database analysis with visualizations, exports, and intelligent insights</p>
    <p><strong>✨ Now with Neon PostgreSQL Support!</strong></p>
</div>
""", unsafe_allow_html=True)

# Database connection constants
POSTGRES = "POSTGRES"
POSTGRES_URL = "POSTGRES_URL"
LOCALDB = "USE_LOCALDB"
MYSQL = "USE_MYSQL"
SQLITE_FILE = "SQLITE_FILE"

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "query_history" not in st.session_state:
    st.session_state.query_history = []
if "db_stats" not in st.session_state:
    st.session_state.db_stats = {}
if "favorite_queries" not in st.session_state:
    st.session_state.favorite_queries = []
if "export_data" not in st.session_state:
    st.session_state.export_data = []

# Sidebar configuration
with st.sidebar:
    st.header("🔧 Database Configuration")
    
    db_options = [
        "SQLite Sample Database",
        "Upload SQLite File",
        "Connect to MySQL",
        "Connect to PostgreSQL (Individual Parameters)",
        "Connect to PostgreSQL (Connection URL) - Neon Compatible"
    ]
    
    selected_opt = st.selectbox("Choose Database Type", db_options)
    
    if "MySQL" in selected_opt:
        db_uri = MYSQL
        st.subheader("MySQL Configuration")
        mysql_host = st.text_input("Host", "localhost", help="MySQL server hostname")
        mysql_port = st.number_input("Port", 3306, help="MySQL server port")
        mysql_user = st.text_input("Username", "root")
        mysql_password = st.text_input("Password", type="password")
        mysql_db = st.text_input("Database Name", help="Name of the MySQL database")
        postgres_url = None
        
    elif "Individual Parameters" in selected_opt:
        db_uri = POSTGRES
        st.subheader("PostgreSQL Configuration")
        mysql_host = st.text_input("Host", "localhost", help="PostgreSQL server hostname")
        mysql_port = st.number_input("Port", 5432, help="PostgreSQL server port")
        mysql_user = st.text_input("Username", "postgres")
        mysql_password = st.text_input("Password", type="password")
        mysql_db = st.text_input("Database Name", help="Name of the PostgreSQL database")
        postgres_url = None
        
    elif "Connection URL" in selected_opt:
        db_uri = POSTGRES_URL
        st.subheader("🎯 PostgreSQL URL Connection")
        st.info("Perfect for Neon, Supabase, Railway, and other cloud PostgreSQL providers!")
        
        postgres_url = st.text_area(
            "Database Connection URL",
            placeholder="postgresql://username:password@host:port/database?sslmode=require",
            help="Enter your complete PostgreSQL connection URL. Example for Neon: postgresql://neondb_owner:npg_YQ0xTfoFALz6@ep-morning-recipe-aevzeb7i-pooler.c-2.us-east-2.aws.neon.tech/neondb?sslmode=require",
            height=100
        )
        
        if postgres_url:
            try:
                parsed_url = urlparse(postgres_url)
                st.success(f"✅ URL parsed successfully!")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Host:** {parsed_url.hostname}")
                    st.write(f"**Port:** {parsed_url.port}")
                with col2:
                    st.write(f"**Database:** {parsed_url.path[1:] if parsed_url.path else 'N/A'}")
                    st.write(f"**SSL:** {'Yes' if 'sslmode=require' in postgres_url else 'No'}")
            except Exception as e:
                st.error(f"❌ Invalid URL format: {str(e)}")
        
        mysql_host = mysql_user = mysql_password = mysql_db = mysql_port = None
        
    elif "Upload SQLite" in selected_opt:
        db_uri = SQLITE_FILE
        uploaded_file = st.file_uploader("Upload SQLite Database", type=['db', 'sqlite', 'sqlite3'])
        mysql_host = mysql_user = mysql_password = mysql_db = mysql_port = None
        postgres_url = None
        
    else:  # Sample SQLite
        db_uri = LOCALDB
        mysql_host = mysql_user = mysql_password = mysql_db = mysql_port = None
        postgres_url = None
    
    st.divider()
    
    # Connection examples
    if db_uri == POSTGRES_URL:
        with st.expander("📚 Connection URL Examples"):
            st.markdown("""
            **Neon PostgreSQL:**
            ```
            postgresql://neondb_owner:password@ep-xxx-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require
            ```
            
            **Supabase:**
            ```
            postgresql://postgres:password@db.xxx.supabase.co:5432/postgres
            ```
            
            **Railway:**
            ```
            postgresql://postgres:password@containers-us-west-xxx.railway.app:5432/railway
            ```
            
            **Heroku:**
            ```
            postgres://user:password@host:5432/database
            ```
            """)
    
    st.subheader("🤖 AI Configuration")
    api_key = st.text_input("Groq API Key", type="password", help="Get your API key from https://console.groq.com/")
    
    model_options = ["llama3-8b-8192", "llama3-70b-8192", "mixtral-8x7b-32768"]
    selected_model = st.selectbox("Select Model", model_options)
    
    temperature = st.slider("Response Creativity", 0.0, 1.0, 0.1, 0.1, help="Higher values make responses more creative")
    
    st.divider()
    
    st.subheader("🎯 Features")
    auto_visualize = st.checkbox("Auto-generate Charts", True, help="Automatically create visualizations for numeric data")
    show_sql = st.checkbox("Show Generated SQL", False, help="Display the SQL queries generated by AI")
    enable_exports = st.checkbox("Enable Data Export", True, help="Allow exporting query results")
    
    st.subheader("📝 Quick Templates")
    templates = {
        "Data Overview": "Give me an overview of all tables and their record counts",
        "Top Records": "Show me the top 10 records from the largest table",
        "Data Quality": "Check for missing values and data quality issues",
        "Relationships": "Show me the relationships between tables",
        "Summary Stats": "Provide summary statistics for numeric columns"
    }
    
    selected_template = st.selectbox("Choose Template", ["Custom Query"] + list(templates.keys()))

# Validation checks
if not api_key:
    st.warning("⚠️ Please enter your Groq API key to continue")
    st.stop()

if db_uri in [MYSQL, POSTGRES]:
    if not all([mysql_host, mysql_user, mysql_password, mysql_db]):
        st.warning("⚠️ Please fill in all database connection fields")
        st.stop()

if db_uri == POSTGRES_URL:
    if not postgres_url:
        st.warning("⚠️ Please enter your PostgreSQL connection URL")
        st.stop()

if db_uri == SQLITE_FILE and not uploaded_file:
    st.warning("⚠️ Please upload a SQLite database file")
    st.stop()

def create_enhanced_sample_db():
    """Create a comprehensive sample database with multiple tables and realistic data"""
    db_path = Path(tempfile.gettempdir()) / "enhanced_sample.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Students table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            student_id INTEGER PRIMARY KEY,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE,
            phone TEXT,
            date_of_birth DATE,
            enrollment_date DATE,
            gpa REAL,
            major TEXT,
            year_level INTEGER,
            status TEXT DEFAULT 'Active',
            address TEXT,
            city TEXT,
            state TEXT,
            zip_code TEXT
        )
    ''')
    
    # Courses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            course_id INTEGER PRIMARY KEY,
            course_code TEXT UNIQUE NOT NULL,
            course_name TEXT NOT NULL,
            department TEXT,
            credits INTEGER,
            instructor_id INTEGER,
            semester TEXT,
            year INTEGER,
            capacity INTEGER,
            enrolled_count INTEGER DEFAULT 0,
            course_fee REAL
        )
    ''')
    
    # Instructors table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS instructors (
            instructor_id INTEGER PRIMARY KEY,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE,
            department TEXT,
            hire_date DATE,
            salary REAL,
            office_location TEXT
        )
    ''')
    
    # Enrollments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS enrollments (
            enrollment_id INTEGER PRIMARY KEY,
            student_id INTEGER,
            course_id INTEGER,
            enrollment_date DATE,
            grade TEXT,
            points REAL,
            status TEXT DEFAULT 'Enrolled',
            FOREIGN KEY (student_id) REFERENCES students (student_id),
            FOREIGN KEY (course_id) REFERENCES courses (course_id)
        )
    ''')
    
    # Payments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            payment_id INTEGER PRIMARY KEY,
            student_id INTEGER,
            amount REAL,
            payment_date DATE,
            payment_method TEXT,
            semester TEXT,
            year INTEGER,
            status TEXT DEFAULT 'Completed',
            FOREIGN KEY (student_id) REFERENCES students (student_id)
        )
    ''')
    
    import random
    from datetime import date, timedelta
    
    # Insert sample data
    instructors_data = [
        ('Dr. Sarah', 'Johnson', 'sarah.johnson@university.edu', 'Computer Science', '2018-08-15', 75000, 'CS-201'),
        ('Prof. Michael', 'Brown', 'michael.brown@university.edu', 'Mathematics', '2015-01-10', 68000, 'MATH-105'),
        ('Dr. Emily', 'Davis', 'emily.davis@university.edu', 'Physics', '2019-09-01', 72000, 'PHYS-301'),
        ('Prof. James', 'Wilson', 'james.wilson@university.edu', 'Chemistry', '2016-03-20', 70000, 'CHEM-202'),
        ('Dr. Lisa', 'Anderson', 'lisa.anderson@university.edu', 'English', '2017-08-25', 65000, 'ENG-101')
    ]
    cursor.executemany('INSERT OR REPLACE INTO instructors (first_name, last_name, email, department, hire_date, salary, office_location) VALUES (?, ?, ?, ?, ?, ?, ?)', instructors_data)
    
    majors = ['Computer Science', 'Mathematics', 'Physics', 'Chemistry', 'English', 'Biology', 'Economics', 'Psychology']
    states = ['CA', 'NY', 'TX', 'FL', 'IL', 'PA', 'OH', 'GA', 'NC', 'MI']
    
    students_data = []
    for i in range(1, 51):
        first_names = ['Alice', 'Bob', 'Carol', 'David', 'Eve', 'Frank', 'Grace', 'Henry', 'Iris', 'Jack']
        last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez']
        
        first_name = random.choice(first_names) + str(i)
        last_name = random.choice(last_names)
        email = f"{first_name.lower()}.{last_name.lower()}@student.edu"
        phone = f"555-{random.randint(100, 999)}-{random.randint(1000, 9999)}"
        birth_date = date(2000 + random.randint(-2, 2), random.randint(1, 12), random.randint(1, 28))
        enrollment_date = date(2020 + random.randint(0, 4), random.choice([1, 8]), random.randint(15, 30))
        gpa = round(random.uniform(2.0, 4.0), 2)
        major = random.choice(majors)
        year_level = random.randint(1, 4)
        address = f"{random.randint(100, 9999)} {random.choice(['Main', 'Oak', 'Pine', 'Elm'])} St"
        city = random.choice(['Springfield', 'Riverside', 'Franklin', 'Georgetown', 'Madison'])
        state = random.choice(states)
        zip_code = f"{random.randint(10000, 99999)}"
        
        students_data.append((i, first_name, last_name, email, phone, birth_date, enrollment_date, 
                           gpa, major, year_level, 'Active', address, city, state, zip_code))
    
    cursor.executemany('INSERT OR REPLACE INTO students VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', students_data)
    
    courses_data = [
        (1, 'CS101', 'Introduction to Programming', 'Computer Science', 3, 1, 'Fall', 2024, 30, 25, 1200),
        (2, 'MATH201', 'Calculus II', 'Mathematics', 4, 2, 'Fall', 2024, 25, 20, 800),
        (3, 'PHYS301', 'Quantum Physics', 'Physics', 3, 3, 'Spring', 2024, 20, 15, 1000),
        (4, 'CHEM202', 'Organic Chemistry', 'Chemistry', 4, 4, 'Fall', 2024, 28, 22, 1100),
        (5, 'ENG101', 'English Composition', 'English', 3, 5, 'Fall', 2024, 35, 30, 600),
        (6, 'CS301', 'Data Structures', 'Computer Science', 3, 1, 'Spring', 2024, 25, 18, 1200),
        (7, 'MATH301', 'Linear Algebra', 'Mathematics', 3, 2, 'Spring', 2024, 20, 16, 800),
        (8, 'PHYS201', 'Classical Mechanics', 'Physics', 4, 3, 'Fall', 2024, 22, 19, 1000)
    ]
    cursor.executemany('INSERT OR REPLACE INTO courses VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', courses_data)
    
    # Generate enrollments and payments data
    enrollments_data = []
    grades = ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D']
    grade_points = {'A': 4.0, 'A-': 3.7, 'B+': 3.3, 'B': 3.0, 'B-': 2.7, 'C+': 2.3, 'C': 2.0, 'C-': 1.7, 'D+': 1.3, 'D': 1.0}
    
    enrollment_id = 1
    for student_id in range(1, 51):
        num_courses = random.randint(3, 5)
        enrolled_courses = random.sample(range(1, 9), num_courses)
        
        for course_id in enrolled_courses:
            enrollment_date = date(2024, random.choice([1, 8]), random.randint(10, 20))
            grade = random.choice(grades)
            points = grade_points[grade]
            
            enrollments_data.append((enrollment_id, student_id, course_id, enrollment_date, grade, points, 'Completed'))
            enrollment_id += 1
    
    cursor.executemany('INSERT OR REPLACE INTO enrollments VALUES (?, ?, ?, ?, ?, ?, ?)', enrollments_data)
    
    payments_data = []
    payment_methods = ['Credit Card', 'Bank Transfer', 'Cash', 'Check', 'Financial Aid']
    
    for i, student_id in enumerate(range(1, 51)):
        num_payments = random.randint(2, 4)
        for j in range(num_payments):
            payment_id = i * 4 + j + 1
            amount = random.uniform(500, 2000)
            payment_date = date(2024, random.randint(1, 12), random.randint(1, 28))
            method = random.choice(payment_methods)
            semester = random.choice(['Fall', 'Spring', 'Summer'])
            year = 2024
            
            payments_data.append((payment_id, student_id, amount, payment_date, method, semester, year, 'Completed'))
    
    cursor.executemany('INSERT OR REPLACE INTO payments VALUES (?, ?, ?, ?, ?, ?, ?, ?)', payments_data)
    
    conn.commit()
    conn.close()
    return db_path

def validate_postgres_url(url):
    """Validate PostgreSQL connection URL format"""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ['postgresql', 'postgres']:
            return False, "URL must start with 'postgresql://' or 'postgres://'"
        if not parsed.hostname:
            return False, "Missing hostname in URL"
        if not parsed.username:
            return False, "Missing username in URL"
        if not parsed.password:
            return False, "Missing password in URL"
        return True, "Valid PostgreSQL URL"
    except Exception as e:
        return False, f"Invalid URL format: {str(e)}"

def configure_database(db_uri, **kwargs):
    """Enhanced database configuration with better error handling and URL support"""
    try:
        if db_uri == LOCALDB:
            dbfilepath = create_enhanced_sample_db()
            creator = lambda: sqlite3.connect(f"file:{dbfilepath}?mode=rw", uri=True)
            return SQLDatabase(create_engine("sqlite:///", creator=creator))
        
        elif db_uri == SQLITE_FILE:
            uploaded_file = kwargs.get('uploaded_file')
            if uploaded_file:
                temp_path = Path(tempfile.gettempdir()) / f"uploaded_{uploaded_file.name}"
                with open(temp_path, 'wb') as f:
                    f.write(uploaded_file.read())
                
                creator = lambda: sqlite3.connect(f"file:{temp_path}?mode=rw", uri=True)
                return SQLDatabase(create_engine("sqlite:///", creator=creator))
        
        elif db_uri == MYSQL:
            connection_string = f"mysql+pymysql://{kwargs['mysql_user']}:{kwargs['mysql_password']}@{kwargs['mysql_host']}:{kwargs.get('mysql_port', 3306)}/{kwargs['mysql_db']}"
            return SQLDatabase(create_engine(connection_string))
        
        elif db_uri == POSTGRES:
            connection_string = f"postgresql+psycopg2://{kwargs['mysql_user']}:{kwargs['mysql_password']}@{kwargs['mysql_host']}:{kwargs.get('mysql_port', 5432)}/{kwargs['mysql_db']}"
            return SQLDatabase(create_engine(connection_string))
        
        elif db_uri == POSTGRES_URL:
            postgres_url = kwargs.get('postgres_url')
            if not postgres_url:
                raise Exception("PostgreSQL URL is required")
            
            # Validate URL format
            is_valid, message = validate_postgres_url(postgres_url)
            if not is_valid:
                raise Exception(message)
            
            # Handle both 'postgres://' and 'postgresql://' schemes
            if postgres_url.startswith('postgres://'):
                postgres_url = postgres_url.replace('postgres://', 'postgresql://', 1)
            
            # Use psycopg2 driver
            if '+psycopg2' not in postgres_url:
                postgres_url = postgres_url.replace('postgresql://', 'postgresql+psycopg2://', 1)
            
            return SQLDatabase(create_engine(postgres_url))
            
    except Exception as e:
        st.error(f"Database connection error: {str(e)}")
        return None

def get_database_statistics(db):
    """Get comprehensive database statistics"""
    try:
        stats = {}
        table_names = db.get_usable_table_names()
        stats['table_count'] = len(table_names)
        stats['tables'] = {}
        
        for table in table_names:
            try:
                result = db.run(f"SELECT COUNT(*) FROM {table}")
                if result:
                    lines = result.strip().split('\n')
                    row_count = 0
                    for line in lines:
                        import re
                        numbers = re.findall(r'\d+', line)
                        if numbers:
                            row_count = int(numbers[0])
                            break
                else:
                    row_count = 0
                
                try:
                    if 'sqlite' in str(db._engine.url):
                        columns_result = db.run(f"PRAGMA table_info({table})")
                    else:
                        columns_result = db.run(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}'")
                    
                    if columns_result:
                        column_count = len([line for line in columns_result.split('\n') if line.strip() and ('|' in line or column_count == 0)])
                        column_count = max(0, column_count - 1 if column_count > 0 else 0)
                    else:
                        column_count = 0
                except:
                    column_count = 0
                
                stats['tables'][table] = {
                    'row_count': max(0, row_count),
                    'columns': max(0, column_count)
                }
            except Exception as e:
                print(f"Error getting stats for table {table}: {e}")
                stats['tables'][table] = {'row_count': 0, 'columns': 0}
        
        return stats
    except Exception as e:
        print(f"Error getting database statistics: {e}")
        return {'table_count': 0, 'tables': {}}

def create_visualization(query_result, query_text):
    """Create intelligent visualizations based on query results"""
    if not query_result or not auto_visualize:
        return None
    
    try:
        lines = query_result.strip().split('\n')
        if len(lines) < 3:
            return None
            
        rows = []
        headers = None
        
        for line in lines[1:]:
            if line.strip() and '|' in line:
                row = [cell.strip() for cell in line.split('|') if cell.strip()]
                if headers is None:
                    headers = row
                else:
                    rows.append(row)
        
        if not headers or not rows or len(rows) == 0:
            return None
            
        df = pd.DataFrame(rows, columns=headers)
        
        # Convert numeric columns
        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col])
            except:
                pass
        
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
        
        fig = None
        
        if len(numeric_cols) >= 1 and len(categorical_cols) >= 1:
            fig = px.bar(df, x=categorical_cols[0], y=numeric_cols[0], 
                        title=f"{numeric_cols[0]} by {categorical_cols[0]}")
            fig.update_layout(
                height=400, 
                showlegend=True,
                xaxis_tickangle=45 if len(df) > 5 else 0
            )
        elif len(numeric_cols) >= 2:
            fig = px.scatter(df, x=numeric_cols[0], y=numeric_cols[1],
                           title=f"{numeric_cols[1]} vs {numeric_cols[0]}")
            fig.update_layout(height=400, showlegend=True)
        elif len(numeric_cols) == 1:
            fig = px.histogram(df, x=numeric_cols[0], title=f"Distribution of {numeric_cols[0]}")
            fig.update_layout(height=400, showlegend=True)
        else:
            if categorical_cols and len(categorical_cols) > 0:
                value_counts = df[categorical_cols[0]].value_counts()
                if len(value_counts) > 0:
                    fig = px.bar(x=value_counts.index, y=value_counts.values,
                               title=f"Count of {categorical_cols[0]}")
                    fig.update_layout(
                        height=400, 
                        showlegend=True,
                        xaxis_tickangle=45 if len(value_counts) > 5 else 0,
                        xaxis_title=categorical_cols[0],
                        yaxis_title="Count"
                    )
        
        return fig
        
    except Exception as e:
        return None

def export_to_csv(data, filename):
    """Export data to CSV format"""
    try:
        df = pd.read_csv(io.StringIO(data))
        csv = df.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">📥 Download CSV</a>'
        return href
    except:
        return None

def save_query_to_history(query, response, execution_time):
    """Save query to history with metadata"""
    history_item = {
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'query': query,
        'response': response[:500] + "..." if len(response) > 500 else response,
        'execution_time': execution_time,
        'favorited': False
    }
    st.session_state.query_history.append(history_item)
    
    if len(st.session_state.query_history) > 50:
        st.session_state.query_history.pop(0)

# Database connection setup
with st.spinner("🔄 Connecting to database..."):
    db_kwargs = {}
    if db_uri in [MYSQL, POSTGRES]:
        db_kwargs.update({
            'mysql_host': mysql_host,
            'mysql_user': mysql_user,
            'mysql_password': mysql_password,
            'mysql_db': mysql_db,
            'mysql_port': locals().get('mysql_port')
        })
    elif db_uri == POSTGRES_URL:
        db_kwargs['postgres_url'] = postgres_url
    elif db_uri == SQLITE_FILE:
        db_kwargs['uploaded_file'] = uploaded_file
    
    db = configure_database(db_uri, **db_kwargs)

if not db:
    st.error("❌ Failed to connect to database")
    st.stop()

# Initialize AI agent
try:
    llm = ChatGroq(
        groq_api_key=api_key,
        model_name=selected_model,
        streaming=True,
        temperature=temperature
    )
    
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    agent = create_sql_agent(
        llm=llm,
        toolkit=toolkit,
        verbose=True,
        agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        handle_parsing_errors=True
    )
    
    with st.spinner("📊 Analyzing database structure..."):
        st.session_state.db_stats = get_database_statistics(db)
    
    st.success("✅ Successfully connected and ready!")
    
except Exception as e:
    st.error(f"❌ Error initializing AI agent: {str(e)}")
    st.stop()

# Main interface
col1, col2 = st.columns([2, 1])

with col1:
    with st.expander("📊 Database Overview", expanded=True):
        stats = st.session_state.db_stats
        
        metric_cols = st.columns(4)
        with metric_cols[0]:
            st.metric("Total Tables", stats.get('table_count', 0))
        with metric_cols[1]:
            total_rows = sum(table_info.get('row_count', 0) for table_info in stats.get('tables', {}).values())
            st.metric("Total Records", f"{total_rows:,}")
        with metric_cols[2]:
            avg_rows = total_rows // max(stats.get('table_count', 1), 1)
            st.metric("Avg Records/Table", f"{avg_rows:,}")
        with metric_cols[3]:
            connection_status = "🟢 Neon" if db_uri == POSTGRES_URL else "🟢 Active"
            st.metric("Connection Status", connection_status)
        
        if stats.get('tables'):
            st.subheader("📋 Table Details")
            table_df = pd.DataFrame([
                {
                    'Table': table,
                    'Records': f"{info.get('row_count', 0):,}",
                    'Columns': info.get('columns', 0)
                }
                for table, info in stats['tables'].items()
            ])
            st.dataframe(table_df, use_container_width=True)

with col2:
    st.subheader("⚡ Quick Actions")
    
    if st.button("🔍 Explore Schema", use_container_width=True):
        schema_query = "Show me the schema and structure of all tables"
        st.session_state.messages.append({"role": "user", "content": schema_query})
        st.rerun()
    
    if st.button("📈 Generate Summary Report", use_container_width=True):
        summary_query = "Generate a comprehensive summary report of the database including key statistics and insights"
        st.session_state.messages.append({"role": "user", "content": summary_query})
        st.rerun()
    
    if st.button("🔎 Data Quality Check", use_container_width=True):
        quality_query = "Check for data quality issues like missing values, duplicates, and inconsistencies"
        st.session_state.messages.append({"role": "user", "content": quality_query})
        st.rerun()

st.divider()
st.subheader("💬 Chat with your Database")

# Initialize chat messages
if not st.session_state.messages:
    welcome_message = f"Hello! I'm your AI database assistant. I can help you analyze your database with {st.session_state.db_stats.get('table_count', 0)} tables."
    if db_uri == POSTGRES_URL:
        welcome_message += " 🎉 Great choice using Neon PostgreSQL!"
    welcome_message += " What would you like to explore?"
    
    st.session_state.messages = [
        {
            "role": "assistant", 
            "content": welcome_message
        }
    ]

# Display chat messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        
        if "visualization" in msg:
            st.plotly_chart(msg["visualization"], use_container_width=True)
        
        if "export_data" in msg and enable_exports:
            st.markdown(msg["export_data"], unsafe_allow_html=True)

# Handle user input
user_query = st.chat_input("Ask anything about your database...")

if selected_template != "Custom Query" and selected_template in templates:
    user_query = templates[selected_template]
    selected_template = "Custom Query"  # Reset selection

if user_query:
    st.session_state.messages.append({"role": "user", "content": user_query})
    
    with st.chat_message("user"):
        st.write(user_query)
    
    with st.chat_message("assistant"):
        try:
            start_time = time.time()
            
            with st.spinner("🤖 AI is analyzing your query..."):
                response_container = st.empty()
                streamlit_callback = StreamlitCallbackHandler(st.container())
                
                response = agent.run(user_query, callbacks=[streamlit_callback])
            
            execution_time = time.time() - start_time
            
            st.write("**Answer:**")
            st.write(response)
            
            if show_sql:
                sql_match = re.search(r'```sql\n(.*?)\n```', response, re.DOTALL)
                if sql_match:
                    st.code(sql_match.group(1), language='sql')
            
            # Create visualization
            viz = create_visualization(response, user_query)
            message_data = {"role": "assistant", "content": response}
            
            if viz:
                st.subheader("📊 Data Visualization")
                st.plotly_chart(viz, use_container_width=True)
                message_data["visualization"] = viz
            
            # Export option
            if enable_exports and len(response.split('\n')) > 5:  # If response looks like tabular data
                export_link = export_to_csv(response, f"query_result_{int(time.time())}.csv")
                if export_link:
                    st.markdown("**📥 Export Options:**")
                    st.markdown(export_link, unsafe_allow_html=True)
                    message_data["export_data"] = export_link
            
            save_query_to_history(user_query, response, execution_time)
            st.info(f"⏱️ Query executed in {execution_time:.2f} seconds")
            
            st.session_state.messages.append(message_data)
            
        except Exception as e:
            error_message = f"❌ Error processing query: {str(e)}"
            st.error(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message})

st.divider()

# Tabs for additional features
tab1, tab2, tab3, tab4 = st.tabs(["📚 Query History", "⭐ Favorites", "📊 Analytics", "⚙️ Advanced"])

with tab1:
    st.subheader("Recent Queries")
    if st.session_state.query_history:
        for i, item in enumerate(reversed(st.session_state.query_history[-10:])):  # Show last 10
            with st.expander(f"🕐 {item['timestamp']} - {item['query'][:50]}..."):
                st.write("**Query:**", item['query'])
                st.write("**Response:**", item['response'])
                st.write("**Execution Time:**", f"{item['execution_time']:.2f}s")
                
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("🔄 Run Again", key=f"rerun_{i}"):
                        st.session_state.messages.append({"role": "user", "content": item['query']})
                        st.rerun()
                with col2:
                    if st.button("⭐ Add to Favorites", key=f"fav_{i}"):
                        if item not in st.session_state.favorite_queries:
                            st.session_state.favorite_queries.append(item)
                            st.success("Added to favorites!")
    else:
        st.info("No query history yet. Start asking questions about your database!")

with tab2:
    st.subheader("Favorite Queries")
    if st.session_state.favorite_queries:
        for i, item in enumerate(st.session_state.favorite_queries):
            with st.expander(f"⭐ {item['query'][:60]}..."):
                st.write("**Query:**", item['query'])
                st.write("**Last Used:**", item['timestamp'])
                
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("🔄 Run Query", key=f"fav_run_{i}"):
                        st.session_state.messages.append({"role": "user", "content": item['query']})
                        st.rerun()
                with col2:
                    if st.button("🗑️ Remove", key=f"fav_remove_{i}"):
                        st.session_state.favorite_queries.pop(i)
                        st.rerun()
    else:
        st.info("No favorite queries yet. Add queries from your history!")

with tab3:
    st.subheader("Database Analytics")
    
    if st.session_state.db_stats.get('tables'):
        # Table size distribution
        table_data = []
        for table, info in st.session_state.db_stats['tables'].items():
            table_data.append({
                'Table': table,
                'Records': info.get('row_count', 0),
                'Columns': info.get('columns', 0)
            })
        
        df = pd.DataFrame(table_data)
        
        st.subheader("📊 Records by Table")
        if not df.empty and len(df) > 0:
            try:
                fig = px.bar(df, x='Table', y='Records', title="Record Count by Table")
                fig.update_layout(
                    xaxis_tickangle=45,
                    height=400,
                    showlegend=False
                )
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error creating bar chart: {str(e)}")
                try:
                    st.bar_chart(df.set_index('Table')['Records'])
                except:
                    st.write("Data:", df)
        else:
            st.info("No data available for visualization")
        
        # Query performance analytics
        if st.session_state.query_history:
            st.subheader("⚡ Query Performance")
            perf_data = [
                {
                    'Query': item['query'][:30] + "...",
                    'Execution Time': item['execution_time'],
                    'Timestamp': item['timestamp']
                }
                for item in st.session_state.query_history[-20:]  # Last 20 queries
            ]
            
            perf_df = pd.DataFrame(perf_data)
            if not perf_df.empty and len(perf_df) > 0:
                try:
                    fig = px.scatter(perf_df, x='Timestamp', y='Execution Time', 
                                   hover_data=['Query'], title="Query Execution Times")
                    fig.update_layout(
                        xaxis_tickangle=45,
                        height=400,
                        xaxis_title="Query Time",
                        yaxis_title="Execution Time (seconds)"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Error creating performance chart: {str(e)}")
                    try:
                        chart_data = pd.DataFrame({
                            'Execution Time': [item['execution_time'] for item in st.session_state.query_history[-20:]]
                        })
                        st.line_chart(chart_data)
                    except:
                        st.write("Performance data:", perf_df)
            else:
                st.info("No query performance data available")

with tab4:
    st.subheader("Advanced Features")
    
    st.write("**🔄 Batch Query Execution**")
    batch_queries = st.text_area(
        "Enter multiple queries (one per line):",
        placeholder="SELECT COUNT(*) FROM students;\nSELECT * FROM courses LIMIT 5;\nSELECT AVG(gpa) FROM students;"
    )
    
    if st.button("▶️ Execute Batch Queries"):
        if batch_queries:
            queries = [q.strip() for q in batch_queries.split('\n') if q.strip()]
            for query in queries:
                st.session_state.messages.append({"role": "user", "content": query})
            st.rerun()
    
    st.divider()
    
    st.write("**💾 Database Export**")
    if st.button("📤 Export Database Schema"):
        schema_query = "Show me the complete database schema with all table structures, relationships, and constraints"
        st.session_state.messages.append({"role": "user", "content": schema_query})
        st.rerun()
    
    st.divider()
    
    st.write("**⚡ Query Optimization**")
    optimization_query = st.text_input("Enter a query to optimize:", placeholder="SELECT * FROM students WHERE...")
    
    if st.button("🔧 Get Optimization Suggestions") and optimization_query:
        opt_query = f"Analyze this query for optimization opportunities and suggest improvements: {optimization_query}"
        st.session_state.messages.append({"role": "user", "content": opt_query})
        st.rerun()
    
    st.divider()
    st.write("**⚙️ Direct SQL Execution**")
    custom_sql = st.text_area("Execute custom SQL:", placeholder="SELECT * FROM table_name LIMIT 10;")
    
    if st.button("🔄 Execute SQL") and custom_sql:
        sql_query = f"Execute this SQL query and show results: {custom_sql}"
        st.session_state.messages.append({"role": "user", "content": sql_query})
        st.rerun()

st.divider()

# Footer actions
footer_col1, footer_col2, footer_col3 = st.columns([1, 1, 1])

with footer_col1:
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = [
            {
                "role": "assistant", 
                "content": "Chat history cleared! How can I help you with your database?"
            }
        ]
        st.rerun()

with footer_col2:
    if st.button("📊 Refresh Database Stats", use_container_width=True):
        with st.spinner("Refreshing database statistics..."):
            st.session_state.db_stats = get_database_statistics(db)
        st.success("Database statistics refreshed!")
        st.rerun()

with footer_col3:
    if st.button("💡 Get Query Suggestions", use_container_width=True):
        suggestion_query = "Suggest 5 interesting and useful queries I can run on this database based on its structure and data"
        st.session_state.messages.append({"role": "user", "content": suggestion_query})
        st.rerun()

# Enhanced sidebar information
with st.sidebar:
    st.divider()
    st.markdown("### 📈 Session Statistics")
    st.metric("Queries Executed", len(st.session_state.query_history))
    st.metric("Favorites Saved", len(st.session_state.favorite_queries))
    
    if st.session_state.query_history:
        avg_time = sum(q['execution_time'] for q in st.session_state.query_history) / len(st.session_state.query_history)
        st.metric("Avg Query Time", f"{avg_time:.2f}s")
    
    st.divider()
    st.markdown("### 🌐 Connection Info")
    if db_uri == POSTGRES_URL:
        st.success("🎯 Connected via URL")
        if postgres_url:
            parsed = urlparse(postgres_url)
            st.write(f"**Host:** {parsed.hostname}")
            st.write(f"**Database:** {parsed.path[1:] if parsed.path else 'default'}")
            st.write(f"**SSL:** {'Enabled' if 'sslmode=require' in postgres_url else 'Disabled'}")
    elif db_uri == POSTGRES:
        st.info("🐘 PostgreSQL Connection")
    elif db_uri == MYSQL:
        st.info("🐬 MySQL Connection")
    else:
        st.info("📁 SQLite Connection")
    
    st.divider()
    st.markdown("### 🔧 Troubleshooting")
    
    with st.expander("Neon PostgreSQL Tips"):
        st.markdown("""
        **Connection URL Format:**
        ```
        postgresql://username:password@host:port/database?sslmode=require
        ```
        
        **Common Issues:**
        - Ensure SSL mode is included for Neon
        - Check if your IP is whitelisted
        - Verify credentials are correct
        - Try removing query parameters if having issues
        
        **Neon Specific:**
        - Use the pooler connection string for better performance
        - SSL is required for Neon connections
        - Database automatically sleeps after inactivity
        """)
    
    with st.expander("Common Issues"):
        st.markdown("""
        **Database Connection Issues:**
        - Check your credentials
        - Ensure database server is running
        - Verify network connectivity
        - For cloud databases, check IP whitelisting
        
        **Query Errors:**
        - Check table and column names
        - Verify SQL syntax
        - Ensure proper permissions
        
        **Performance Issues:**
        - Use LIMIT for large datasets
        - Index frequently queried columns
        - Avoid SELECT * in production
        """)
    
    with st.expander("Sample Queries"):
        st.markdown("""
        **Basic Queries:**
        ```sql
        -- Count records
        SELECT COUNT(*) FROM table_name;
        
        -- Get recent data
        SELECT * FROM table_name 
        ORDER BY date_column DESC LIMIT 10;
        
        -- Group by analysis
        SELECT category, COUNT(*) 
        FROM table_name GROUP BY category;
        
        -- Join tables
        SELECT a.*, b.column_name
        FROM table_a a
        JOIN table_b b ON a.id = b.foreign_id;
        ```
        """)
    
    st.markdown("---")
    st.markdown("*Built with Streamlit & LangChain*")
    st.markdown("*Powered by Groq AI*")
    st.markdown("*🌟 Enhanced for Neon PostgreSQL*")