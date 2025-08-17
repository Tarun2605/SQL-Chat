# 🚀 SQL-Chat: Your AI-Powered Database Assistant

![SQL-Chat Demo](https://raw.githubusercontent.com/a-sh-dev/SQL-Chat/main/assets/app_demo.gif)

**Chat with your SQL databases in plain English!** SQL-Chat is an intuitive, powerful Streamlit application that leverages Large Language Models (LLMs) to translate natural language questions into SQL queries, execute them, and deliver answers in a human-friendly format. Analyze data, generate insights, and visualize results without writing a single line of SQL.

---

## ✨ Key Features

*   **Natural Language to SQL:** Ask complex questions about your data in everyday language.
*   **Multi-Database Support:** Connect to SQLite, PostgreSQL, or MySQL databases. You can even upload your own SQLite file!
*   **AI-Powered by Groq & LangChain:** Utilizes the speed of the Groq LPU™ Inference Engine and the power of LangChain for fast and accurate SQL generation.
*   **Interactive Chat Interface:** A familiar chat-based UI for a seamless user experience.
*   **Data Visualization:** Automatically generates charts and graphs from your query results.
*   **Query History & Favorites:** Keep track of your past queries and save your favorites for quick access.
*   **Advanced Analytics:** Get a quick overview of your database schema and statistics.
*   **Secure & Configurable:** Manage your API keys and database credentials securely through the UI.

## 🛠️ Tech Stack

*   **Framework:** [Streamlit](https://streamlit.io/)
*   **AI/LLM:** [Groq](https://groq.com/), [LangChain](https://www.langchain.com/)
*   **Data Handling:** [Pandas](https://pandas.pydata.org/)
*   **Database Drivers:** `psycopg2-binary`, `mysql-connector-python`
*   **Plotting:** [Plotly](https://plotly.com/)

## ⚙️ Getting Started

Follow these steps to get SQL-Chat running on your local machine.

### 1. Prerequisites

*   Python 3.9+
*   An account with [Groq](https://console.groq.com/keys) to get your free API key.

### 2. Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/a-sh-dev/SQL-Chat.git
    cd SQL-Chat
    ```

2.  **Create a virtual environment and activate it:**
    *Using `venv`:*
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```
    *Or using `uv` (a fast Python package installer):*
    ```bash
    uv venv
    source .venv/bin/activate
    ```

3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *Or using `uv`:*
    ```bash
    uv pip install -r requirements.txt
    ```

### 3. Configuration

No `.env` file needed! Simply run the application and configure everything from the sidebar UI:
*   Enter your Groq API Key.
*   Select your database type (Sample, Upload, MySQL, PostgreSQL).
*   Enter your database credentials if connecting to a remote database.

## ▶️ Running the Application

Once the installation is complete, run the Streamlit app:

```bash
streamlit run app.py
```

Open your web browser and navigate to `http://localhost:8501`.

## 📖 How to Use

1.  **Configure your Database:** Use the sidebar to connect to your desired database.
2.  **Set your API Key:** Enter your Groq API key in the sidebar.
3.  **Start Chatting:** Ask questions in the chat input box, like:
    *   "How many students are there?"
    *   "Show me the average GPA for each major."
    *   "List all courses in the Computer Science department."
4.  **Explore:** Use the tabs to view your query history, manage favorites, and see database analytics.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

## 📄 License

This project is licensed under the MIT License.

---

*This README was generated with the help of an AI assistant.*