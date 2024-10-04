from flask import Flask, render_template, redirect, url_for, request, flash, session
import sqlite3
from flask_bcrypt import Bcrypt
from threading import Lock
import json
import os
from dotenv import load_dotenv

print(os.getcwd())

load_dotenv()
app = Flask(__name__, static_folder='static')
# bcrypt
bcrypt = Bcrypt(app)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback_secret_key')  

conn = sqlite3.connect('databases/myers.db', check_same_thread=False)
cursor = conn.cursor()
thread_lock = Lock()

# Laad de vragen
with open('actiontype_statements.json') as json_file:
    questions_data = json.load(json_file)

# Functie voor de volgende vraag
def get_next_question(current_question):
    global questions_data
    next_question_id = current_question + 1
    if next_question_id <= len(questions_data):
        return questions_data[next_question_id - 1]  
    else:
        return None

# connecten met database
with open('students.json') as json_file:
    data = json.load(json_file)


for entry in data:
    studentnummer = entry['student_number']
    studentnaam = entry['student_name']
    studentklas = entry['student_class']


    cursor.execute("SELECT * FROM Studenten WHERE studentnummer=?", (studentnummer,))
    existing_student = cursor.fetchone()
    
    if not existing_student:
        cursor.execute("INSERT INTO Studenten (studentnummer, studentnaam, studentklas) VALUES (?, ?, ?)", (studentnummer, studentnaam, studentklas))
    else:
        print(f"Studentnummer {studentnummer} bestaat al in de database. Overslaan...")


conn.commit()
# connecten met database

# Login route voor studenten en docenten
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if 'studentNum' in request.form and 'studentName' in request.form:
            input_student_num = request.form.get('studentNum')
            input_student_name = request.form.get('studentName')

            cursor.execute("SELECT studentnummer FROM Studenten WHERE studentnaam = ? AND studentnummer = ?", (input_student_name, input_student_num))
            result = cursor.fetchone()

            if result:
                session['studentName'] = input_student_name
                session['current_question'] = 1
                session['selected_choices'] = []  
                flash('Student login successful!', 'success')
                return redirect(url_for('homepage'))
            else:
                flash('Incorrect student number or name. Please try again.', 'error')

        elif 'docentName' in request.form and 'password' in request.form:
            input_docent_name = request.form.get('docentName')
            input_password = request.form.get('password')
            
            print("name = " + input_docent_name)
            #Check if password is correct
            cursor.execute("SELECT Wachtwoord FROM Docenten WHERE Docentnaam = ?", (input_docent_name,))
            result = cursor.fetchone()
            check_password = bcrypt.check_password_hash(result[0].encode(), input_password)

            if check_password is True:
                session['docentName'] = input_docent_name
                flash('Teacher login successful!', 'success')
                return redirect(url_for('homepagedocent'))
            
            else:
                flash('Incorrect teacher name or password. Please try again.', 'error')

    return render_template('index.html')


# Homepage voor studenten
@app.route('/homepage')
def homepage():
    if 'studentName' in session:
        return render_template('homepage.html')
    else:
        flash('You must be logged in to access this page.', 'error')
        return redirect(url_for('login'))
    
# Homepage voor docenten
@app.route('/homepagedocent')
def homepagedocent():
    if 'docentName' in session:
        cursor.execute("SELECT studentnummer, studentnaam, studentklas, resultaat FROM Studenten")
        student_data = cursor.fetchall()  

        if student_data:
            student_data_dicts = [{'student_number': row[0], 'student_name': row[1], 'student_class': row[2], 'resultaat': row[3]} for row in student_data]
            return render_template('homepagedocent.html', student_data=student_data_dicts)
        else:
            flash('No student data found.', 'error')
            return render_template('homepagedocent.html', student_data=[])
    else:
        flash('You must be logged in as a teacher to access this page.', 'error')
        return redirect(url_for('login'))



# Route voor de vragen
@app.route('/question', methods=['GET', 'POST'])
def question():
    if 'studentName' in session:
        if 'current_question' not in session:
            session['current_question'] = 1
        
        current_question_id = session['current_question']
        
        if 1 <= current_question_id <= len(questions_data):
            current_question_data = questions_data[current_question_id - 1]

            if request.method == 'POST':
                selected_choice = request.form.get('choice')
                session['selected_choices'].append(selected_choice)

            if request.method == 'POST' and selected_choice is not None:
                next_question_id = current_question_id + 1
                if next_question_id <= len(questions_data):
                    session['current_question'] = next_question_id
                    return redirect(url_for('question'))
                else:
                    personality_type = calculate_personality_type(session['selected_choices'])
                    student_name = session['studentName']
                    print("Student Name:", student_name)  
                    cursor.execute("UPDATE Studenten SET resultaat=? WHERE studentnaam=?", (personality_type, student_name))
                    conn.commit()

                    return render_template('result.html', personality_type=personality_type)

            return render_template('question.html', question_data=current_question_data, total_questions=len(questions_data), current_question=session['current_question'])

        else:
            flash('Invalid current question index.', 'error')
            return redirect(url_for('login'))
    else:
        flash('You must be logged in to access this page.', 'error')
        return redirect(url_for('login'))


# Berekening van personality type
def calculate_personality_type(selected_choices):
    result_dict = {
        "E": 0,
        "I": 0,
        "S": 0,
        "N": 0,
        "T": 0,
        "F": 0,
        "J": 0,
        "P": 0
    }

    for choice in selected_choices:
        if choice is not None and choice in result_dict:
            result_dict[choice] += 1
        else:
            print("Invalid choice:", choice)

    personality_type = ""
    personality_type += "E" if result_dict["E"] > result_dict["I"] else "I"
    personality_type += "S" if result_dict["S"] > result_dict["N"] else "N"
    personality_type += "T" if result_dict["T"] > result_dict["F"] else "F"
    personality_type += "J" if result_dict["J"] > result_dict["P"] else "P"

    print("Personality Type:", personality_type)
    
    return personality_type

def some_function():

    selected_choices = [
        "E", "I", "S", "N", "T", "F", "J", "P", "E", "I",
        "S", "N", "T", "F", "J", "P", "E", "I", "S", "N"
    ]

    personality_type = calculate_personality_type(selected_choices)
    return personality_type

# resultaat zien
@app.route('/resultaat_bekijken')
def resultaat_bekijken():
    if 'studentName' in session:  
        student_name = session['studentName']


        cursor.execute("SELECT resultaat FROM Studenten WHERE studentnaam = ?", (student_name,))
        resultaat = cursor.fetchone()

        if resultaat:
            return render_template('resultaat_bekijken.html', resultaat=resultaat[0])
        else:
            return "Geen resultaat gevonden voor deze gebruiker."

    else:
        flash('Je moet ingelogd zijn om deze pagina te bekijken.', 'error')
        return redirect(url_for('login'))

# docenttoevoegen route
@app.route('/docenttoevoegen', methods=['GET', 'POST'])
def docent_toevoegen():
    if request.method == 'POST':
        if 'add_user' in request.form:
            username = request.form['add_username']
            password = request.form['add_password']
            is_admin_value = 1 if 'is_admin' in request.form else 0  


            cursor.execute("SELECT Docentnaam FROM Docenten WHERE Docentnaam = ?", (username,))
            existing_user = cursor.fetchone()

            if existing_user:
                error_message = 'Gebruiker met deze naam bestaat al. Kies een andere gebruikersnaam.'
                return render_template('docenttoevoegen.html', error_message=error_message)

            hashed_password = bcrypt.generate_password_hash(password).decode('utf8')
            cursor.execute("INSERT INTO Docenten (Docentnaam, Wachtwoord, is_admin) VALUES (?, ?, ?)", (username, hashed_password, is_admin_value))
            conn.commit()

            success_message = 'Gebruiker succesvol toegevoegd!'
            return render_template('docenttoevoegen.html', success_message=success_message)

        elif 'delete_user' in request.form:
            username_to_delete = request.form['delete_username']


            cursor.execute("DELETE FROM Docenten WHERE Docentnaam = ?", (username_to_delete,))
            conn.commit()

            success_message = 'Gebruiker succesvol verwijderd!'
            return render_template('docenttoevoegen.html', success_message=success_message)

    return render_template('docenttoevoegen.html')


if __name__ == '__main__':
    app.run(debug=False)
