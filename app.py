from flask import Flask, request, render_template, redirect, session
import mysql.connector
from langchain_google_genai.chat_models import ChatGoogleGenerativeAI
from langchain_community.document_loaders import PyPDFLoader
from langchain.chains.summarize import load_summarize_chain
import logging
import os

app = Flask(__name__)
app.secret_key = 'secret_key'

log_file = "activity.log"
if not os.path.exists(log_file):
    with open(log_file, 'w') as f:
        pass
logging.basicConfig(filename='activity.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
 
uploads_folder = "uploads"
if not os.path.exists(uploads_folder):
    os.makedirs(uploads_folder)

llm = ChatGoogleGenerativeAI(model = "gemini-pro")  


def summarize_pdf (file):
    current_directory = os.getcwd()
    current_directory=current_directory+r"/uploads"
    file_path = os.path.join(current_directory, file.filename)
    loader = PyPDFLoader(file_path)
    docs = loader.load_and_split()
    chain = load_summarize_chain(llm, chain_type="map_reduce")
    summary = chain.run(docs)
    logging.info(f'Summarized {file.filename}.')
    return summary

@app.route('/summarized', methods=['POST'])
def upload_file_handler():
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'
    if file:
        file.save('uploads/' + file.filename)
        logging.info(f'{file.filename} uploaded.')
        summarized_version = summarize_pdf (file)
        return render_template('summarizedFile.html', summarized_version=summarized_version )

def connect_to_database():
    try:
        mydb = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="mysql2002", 
            database="registrations",
            auth_plugin='mysql_native_password'
        )
        return mydb
    except mysql.connector.Error as error:
        print("Error connecting to MySQL:", error)
        return None

def insert_row(mydb, name, email, password):
    try:
        mycursor = mydb.cursor()
        sql = "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)"
        val = (name, email, password)
        mycursor.execute(sql, val)
        mydb.commit()
        print("Row inserted successfully!")
        mycursor.close()
    except mysql.connector.Error as error:
        print("Error inserting row:", error)

def is_user_valid(email, password):
    mydb = connect_to_database()
    if not mydb:
        return False
    mycursor = mydb.cursor()
    sql = "SELECT * FROM users WHERE email = %s AND password = %s"
    val = (email, password)
    mycursor.execute(sql, val)
    user = mycursor.fetchone()
    mydb.close()
    if user:
        return user
    else:
        return False

def email_exists_in_database(email):
    mydb = connect_to_database()
    cursor = mydb.cursor()
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    result = cursor.fetchone()
    mydb.close()
    if result:
        return True
    else:
        return False


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        mydb = connect_to_database()
        if not mydb:
            return "Error connecting to database"

        if email_exists_in_database(email):
            return render_template('register.html', error="Email already exists")

        insert_row(mydb, name, email, password)
        mydb.close()

        return redirect('/login')  

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if is_user_valid(email, password):
            session['email'] = email
            return redirect('/dashboard')
        else:
            return render_template('login.html', error="Invalid email or password")

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'email' in session:
        email = session['email']
        print(email)
        
        mydb = connect_to_database()
        if not mydb:
            return "Error connecting to database"

        mycursor = mydb.cursor()
        sql = "SELECT * FROM users WHERE email = %s"
        val = (email,) 
        mycursor.execute(sql, val)
        user = mycursor.fetchone()
        print(user)
        mydb.close()
        print("User retrieved from database:", user) 

        if user:
            return render_template('dashboard.html', user=user)
        else:
            return "User not found"
    else:
        return redirect('/login')

@app.route('/logout')
def logout():
    session.pop('email', None)
    return redirect('/login')


if __name__ == '__main__':
    app.run(debug=True)
