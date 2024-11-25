from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import Enum,func, extract
import pytz
import csv
import os
import io
from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField, PasswordField, SelectField
from wtforms.validators import DataRequired, Email
import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import date


app = Flask(__name__)
app.config['SECRET_KEY'] = '122qkwkkskdvmvVHJVvkhhjBH2Y87OLwe2skslDKD'
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True}
#app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///project.db"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get('DATABASE_URL')
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
app.app_context().push()


# database
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=True)
    pin = db.Column(db.String(4), nullable=True)
    role = db.Column(db.String(25), nullable=False)
    category = db.Column(Enum('M', 'C', 'S', name='category_types'), nullable=False)

    def __repr__(self):
        return f"User('{self.username}', '{self.name}', '{self.email}', '{self.role}')"


class LoginDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    login_time = db.Column(db.DateTime, nullable=False,
                           default=datetime.datetime.now())


class Student(db.Model):
    student_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_name = db.Column(db.String(100))
    roll_no = db.Column(db.String(20))
    room_number = db.Column(db.String(10))
    category = db.Column(Enum('V', 'NV', name='cat_types'), nullable=False)
    active = db.Column(db.Boolean, default=True)  # New boolean parameter
    days = db.Column(db.Integer, default=0)  # New number of days parameter

    def __repr__(self):
        return f'<Student(student_id={self.student_id}, student_name={self.student_name}>'


class HolidayInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    description = db.Column(db.String(255))
    student_id = db.Column(db.Integer, db.ForeignKey(
        'student.student_id'), nullable=False)

    def __repr__(self):
        return f'<HolidayInfo(id={self.id}, student_id={self.student_id}, start_date={self.start_date}, end_date={self.end_date}>'


class FoodConsumption(db.Model):
    record_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey(
        'student.student_id'), nullable=False)
    breakfast_amt = db.Column(db.Integer, default=0)
    lunch_amt = db.Column(db.Integer, default=0)
    snack_amt = db.Column(db.Integer, default=0)
    dinner_amt = db.Column(db.Integer, default=0)
    consumption_date = db.Column(db.Date)

    def __repr__(self):
        student = Student.query.get(self.student_id)
        return f'<FoodConsumption(record_id={self.record_id}, student_id={self.student_id},student_name={student.student_name}>'

# ----------------------------------------------------------------


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and user.password == password:
            #print(user.category)
            session['username'] = username
            session['category'] = user.category
            session['id'] = user.id
            login_user(user)
            login_detail = LoginDetail(user_id=user.id)
            db.session.add(login_detail)
            db.session.commit()
            if user.category == 'S':
                return redirect(url_for('index1'))
            else:
                return redirect(url_for('home'))

        flash('Invalid username or password.', 'error')

    return render_template('login.html')

# ----------------------------------------------------------------


scheduler = BackgroundScheduler()
scheduler.start()
def update_student_status():
    today = date.today()
    holiday_infos = HolidayInfo.query.filter_by(end_date=today).all()
    for holiday_info in holiday_infos:
        student = Student.query.get(holiday_info.student_id)
        if student:
            student.active = True
            db.session.commit()

# Schedule the update function to run daily
scheduler.add_job(update_student_status, 'interval', days=1)


class ClearLoginHistoryForm(FlaskForm):
    submit = SubmitField('Clear Login History')


class SignupForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[Email()])
    role = StringField('Role', validators=[DataRequired()])
    category = SelectField('Category', choices=[(
        'M', 'Master'), ('C', 'Client'), ('S', 'Servent')], validators=[DataRequired()])
    submit = SubmitField('Sign Up')


@app.route('/add_user', methods=['POST'])
@login_required
def add_user():
    form = SignupForm()
    email = request.form['email']
    #print(email)
    new_user = User(
        username=form.username.data,
        password=form.password.data,
        name=form.name.data,
        email=form.email.data if form.email.data else None,
        role=form.role.data,
        category=form.category.data
    )
    #print(new_user)
    db.session.add(new_user)
    db.session.commit()
    flash('User created successfully!', 'success')
    return redirect(url_for('setting'))


@app.route('/setting', methods=['GET', 'POST'])
@login_required
def setting():
    if 'username' in session and session["category"] == 'M':
        #if current_user.category == 'M':
        form = SignupForm()
        login_history = LoginDetail.query.join(User).add_columns(
            User.name, LoginDetail.login_time, User.role, User.category).order_by(LoginDetail.login_time.desc()).limit(20).all()
        form2 = ClearLoginHistoryForm()
        c_s_users = User.query.filter(User.category.in_(['C', 'S'])).all()
        #print(c_s_users)
        if form2.validate_on_submit():
            LoginDetail.query.filter_by(user_id=session["id"]).delete()
            db.session.commit()
            flash('Login history has been cleared.', 'success')
            return redirect(url_for('setting'))
        return render_template('setting.html', login_history=login_history, form=form, form2=form2, c_s_users=c_s_users, navbard=getnavbar())
    else:
        logout_user()  # Make sure you have imported and set up the logout_user function
        return redirect(url_for('login'))


@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.category in ['C', 'S']:
        db.session.delete(user)
        db.session.commit()
        flash(f'User {user.username} has been deleted.', 'success')
    else:
        flash(f'Cannot delete user {user.username}.', 'error')

    return redirect(url_for('setting'))


@app.route('/logout')
@login_required
def logout():
    #logout_user()
    session.pop('username', None)
    session.pop('category', None)
    session.pop('id', None)
    return redirect(url_for('login'))

# ----------------------------------------------------------------


def getnavbar():
    role = "S"
    if 'username' in session:
        role = session["category"]
        print(role)
    navigation_data = []
    if role == 'M':
        data = {'message': 'Hello Master from Flask!'}
        navigation_data = [
            {'url': '/home', 'label': 'Home'},
            {'url': '/users', 'label': 'Student Page'},
            {'url': '/consumption', 'label': 'Consumption Page'},
            {'url': '/personal', 'label': 'Personal Page'},
            {'url': '/setting', 'label': 'Settings'},
            {'url': '/studententry', 'label': 'Student Entry'},
            {'url': '/logout', 'label': 'Logout'},
        ]
    elif role == 'C':
        navigation_data = [
            {'url': '/home', 'label': 'Home'},
            {'url': '/consumption', 'label': 'Consumption Page'},
            {'url': '/personal', 'label': 'Personal Page'},
            {'url': '/logout', 'label': 'Logout'},
        ]
    elif role == 'S':
        navigation_data = [{'url': '/logout', 'label': 'Logout'}]
    return navigation_data


@app.route('/users')
@login_required
def list_users():
    if 'username' in session and session["category"] == 'M':
        #if current_user.category == 'M':
        users = Student.query.all()
        return render_template('users.html', users=users, navbard=getnavbar())
    else:
        logout_user() 
        return redirect(url_for('login'))


@app.route('/add_student', methods=['POST'])
@login_required
def add_student():
    studentname = request.form['name']
    roll_no = request.form['roll_no']
    room_number = request.form['room_number']
    category = request.form['category']
    new_user = Student(student_name=studentname, roll_no=roll_no,
                       room_number=room_number, category=category)
    db.session.add(new_user)
    db.session.commit()
    return redirect(url_for('list_users'))


@app.route('/delete_student/<int:user_id>', methods=['POST'])
@login_required
def delete_student(user_id):
    food_consumptions = FoodConsumption.query.filter_by(student_id=user_id).all()
    for food_consumption in food_consumptions:
        db.session.delete(food_consumption)
    holiday_infos = HolidayInfo.query.filter_by(student_id=user_id).all()
    for holiday_info in holiday_infos:
        db.session.delete(holiday_info)
    student = Student.query.get_or_404(user_id)
    db.session.delete(student)
    db.session.commit()
    return redirect(url_for('list_users'))


@app.route('/student_active/<int:student_id>', methods=['POST'])
@login_required
def student_active(student_id):
    if request.method == 'POST':
        student = Student.query.get(student_id)
        if student:
            if student.active:
                # If student is active, set active to False and add holiday info
                start_date = datetime.datetime.strptime(
                    request.form['start_date'], '%Y-%m-%d')
                end_date = datetime.datetime.strptime(
                    request.form['end_date'], '%Y-%m-%d')
                description = request.form['description']
                new_holiday = HolidayInfo(
                    start_date=start_date, end_date=end_date, description=description, student_id=student_id)
                student.active = False
                db.session.add(new_holiday)
                flash(
                    f'Student {student.student_name} is now off. Holiday information added.', 'success')
            else:
                # If student is not active, set active to True and update end_date to today
                student.active = True
                today_date = datetime.datetime.now().date()
                most_recent_holiday = HolidayInfo.query.filter_by(student_id=student.student_id).order_by(HolidayInfo.start_date.desc()).first()
                if most_recent_holiday:
                    start_date = most_recent_holiday.start_date
                    days_difference = (today_date - start_date).days
                    student.days = days_difference + student.days
                    most_recent_holiday.end_date = today_date
                else:
                    # Handle case where there are no holidays recorded
                    student.days += 1
                flash(
                    f'Student {student.student_name} is now active.', 'success')
            db.session.commit()
        else:
            flash('Student not found.', 'error')
    return redirect(url_for('list_users'))


@app.route('/upload_csv', methods=['POST'])
@login_required
def upload():
    if request.method == 'POST':
        csv_file = request.files['csv_file'] 

        if not csv_file:
            return "No file provided."
        csv_data = csv_file.read().decode('utf-8')
        csvreader = csv.DictReader(io.StringIO(csv_data))
        
        for row in csvreader:
            roll_no = row['roll_no']
            existing_student = Student.query.filter_by(roll_no=roll_no).first()
            if existing_student:
                existing_student.student_name = row['\ufeffname']
                existing_student.room_number = row['room_number']
                existing_student.category = row['category']
            else:
                # If no student with the same roll number exists, create a new entry
                new_student = Student(
                    student_name=row['\ufeffname'],
                    roll_no=roll_no,
                    room_number=row['room_number'],
                    category=row['category']
                )
                db.session.add(new_student)

        db.session.commit()
        
    return redirect(url_for('list_users'))

# ----------------------------------------------------------------


@app.route('/studententry')
@login_required
def index():
    if 'username' in session and session["category"] == 'M':
        #if current_user.category == 'M':
        return render_template('submitstu.html', navbard=getnavbar())
    else:
        logout_user()  # Make sure you have imported and set up the logout_user function
        return redirect(url_for('login'))


@app.route('/studententry1')
@login_required
def index1():
    senddata = {
        'todaydate': datetime.datetime.now().date().strftime('%d-%m-%Y'),
        'todaydate2': datetime.datetime.now().date(),
        'meal': get_meal_from_time(),
    }
    return render_template('studententry2.html', navbard=getnavbar(), data=senddata)


@app.route('/process_text', methods=['POST'])
@login_required
def process_text():
    user_input = request.form.get('userInput')
    date_input = request.form.get('dateInput')
    meal_select = request.form.get('mealSelect')
    # Process the received data as needed
    # For example, you can save it to a database or perform other operations
    # print(f"User Input: {user_input}")
    # print(f"Date Input: {date_input}")
    # print(f"Meal Select: {meal_select}")
    student = Student.query.filter_by(roll_no=user_input).first()
    date_input = datetime.datetime.strptime(date_input, '%Y-%m-%d').date()
    # print(student)
    if student:
        if student.active:
            # Found the student with the given roll_no
            existing_record = FoodConsumption.query.filter_by(
                student_id=student.student_id, consumption_date=date_input).first()
            if existing_record:
            #Update the meal value based on the selected option
                if meal_select == 'breakfast':
                    if existing_record.breakfast_amt == 1:
                        return jsonify({'error': 'Student already done'})
                    else:
                        existing_record.breakfast_amt = 1
                elif meal_select == 'lunch':
                    if existing_record.lunch_amt == 1:
                        return jsonify({'error': 'Student already done'})
                    else:
                        existing_record.lunch_amt = 1
                elif meal_select == 'snacks':
                    if existing_record.snack_amt == 1:
                        return jsonify({'error': 'Student already done'})
                    else:
                        existing_record.snack_amt = 1
                elif meal_select == 'dinner':
                    if existing_record.dinner_amt == 1:
                        return jsonify({'error': 'Student already done'})
                    else:
                        existing_record.dinner_amt = 1
                
            else:
                # Create a new record for the student and date
                new_record = FoodConsumption(
                    student_id=student.student_id,
                    consumption_date=date_input
                )
                # Set the meal value based on the selected option
                if meal_select == 'breakfast':
                    new_record.breakfast_amt = 1
                elif meal_select == 'lunch':
                    new_record.lunch_amt = 1
                elif meal_select == 'snacks':
                    new_record.snack_amt = 1
                elif meal_select == 'dinner':
                    new_record.dinner_amt = 1

                db.session.add(new_record)

            db.session.commit()
            student_details = {
                'id': student.student_id,
                'name': student.student_name,
                'roll_no': student.roll_no,
                'room_number': student.room_number,
                'category': student.category
            }
            return jsonify(student_details)
        else:
            return jsonify({'error': 'Student on holiday'})
    else:
        return jsonify({'error': 'Student not found'})


def get_meal_from_time():
    india_tz = pytz.timezone('Asia/Kolkata')
    time = datetime.datetime.now(india_tz).time()
    #print(time)
    if time >= datetime.time(6, 30) and time <= datetime.time(10, 30):
        return 'breakfast'
    elif time >= datetime.time(11, 30) and time <= datetime.time(14, 30):
        return 'lunch'
    elif time >= datetime.time(15, 50) and time <= datetime.time(18, 15):
        return 'snacks'
    elif time >= datetime.time(18, 30) and time <= datetime.time(23, 00):
        return 'dinner'
    else:
        return 'Unknown'


# ----------------------------------------------------------------


@app.route("/consumption", methods=["GET"])
@login_required
def consumption():
    return render_template("consumption.html", navbard=getnavbar())


@app.route("/consumption_data", methods=["GET"])
@login_required
def consumption_data():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    # Run the SQL query using SQLAlchemy and group the results by student, weekday
    results = (
        db.session.query(
            FoodConsumption.student_id,
            Student.student_name,
            Student.roll_no,
            extract('dow', FoodConsumption.consumption_date).label(
                "weekday"),  # Extract the weekday from the date
            func.sum(FoodConsumption.breakfast_amt + FoodConsumption.lunch_amt + \
                     FoodConsumption.snack_amt + FoodConsumption.dinner_amt).label("total_food_amt"),
            func.sum(FoodConsumption.breakfast_amt).label("breakfast_amt"),
            func.sum(FoodConsumption.lunch_amt).label("lunch_amt"),
            func.sum(FoodConsumption.snack_amt).label("snack_amt"),
            func.sum(FoodConsumption.dinner_amt).label("dinner_amt"),
        )
        .join(Student, FoodConsumption.student_id == Student.student_id)
        # Filter data based on start_date and end_date
        .filter(FoodConsumption.consumption_date.between(start_date, end_date))
        # Group by student, weekday
        .group_by(FoodConsumption.student_id, Student.student_name, Student.roll_no, "weekday")
        .all()
    )

    # Convert the query results to a list of dictionaries
    rows = []
    for result in results:
        rows.append({
            "student_id": result.student_id,
            "student_name": result.student_name,
            "roll_number": result.roll_no,
            "weekday": result.weekday,
            "total": result.total_food_amt,
            "amount1": result.breakfast_amt,
            "amount2": result.lunch_amt,
            "amount3": result.snack_amt,
            "amount4": result.dinner_amt,
        })

    return jsonify(rows=rows)


# ----------------------------------------------------------------


@app.route("/personal")
@login_required
def personal():
    student_id = request.args.get("id")
    student = Student.query.get(student_id)
    return render_template("personal.html", stu=student, navbard=getnavbar())

# Route to fetch data based on start_date and end_date


@app.route("/get_data", methods=["GET"])
@login_required
def get_data1():
    # Get the start_date and end_date from the query parameters
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    id = request.args.get("id")
    if not id:
        id = 0
    try:
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Please use YYYY-MM-DD format."})
    # Query the consumption table to filter data based on the date range and student_id
    filtered_data = FoodConsumption.query.filter(
        FoodConsumption.student_id == id,
        FoodConsumption.consumption_date.between(start_date, end_date)
    ).all()
    # Convert the filtered data into a list of dictionaries
    rows = []
    for record in filtered_data:
        rows.append({
            "date": record.consumption_date.strftime("%Y-%m-%d"),
            "breakfast": record.breakfast_amt,
            "lunch": record.lunch_amt,
            "snacks": record.snack_amt,
            "dinner": record.dinner_amt,
        })

    return jsonify(rows=rows)


@app.route("/get_data2", methods=["GET"])
@login_required
def get_data2():
    # Get the start_date and end_date from the query parameters
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    id = request.args.get("id")
    if not id:
        id = 0
    try:
        # Convert the start_date and end_date strings to datetime objects
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Please use YYYY-MM-DD format."})
    # print(id)
    # Query the consumption table to filter data based on the date range and student_id
    filtered_data = HolidayInfo.query.filter(
        HolidayInfo.student_id == id,
        HolidayInfo.start_date.between(start_date, end_date)
    ).all()
    # Convert the filtered data into a list of dictionaries
    rows = []
    for record in filtered_data:
        rows.append({
            "startdate": record.start_date.strftime("%Y-%m-%d"),
            "enddate": record.end_date.strftime("%Y-%m-%d"),
            "description": record.description
        })
    return jsonify(rows=rows)


# ----------------------------------------------------------------


@app.route("/home", methods=["GET"])
@login_required
def home():
    # Calculate the aggregates from the FoodConsumption table
    breakfast_total = db.session.query(
        func.sum(FoodConsumption.breakfast_amt)).scalar() or 0
    lunch_total = db.session.query(
        func.sum(FoodConsumption.lunch_amt)).scalar() or 0
    snacks_total = db.session.query(
        func.sum(FoodConsumption.snack_amt)).scalar() or 0
    dinner_total = db.session.query(
        func.sum(FoodConsumption.dinner_amt)).scalar() or 0
    total_food_consumed = breakfast_total + \
        lunch_total + snacks_total + dinner_total
    total_students = db.session.query(func.count(Student.student_id)).scalar()

    # Prepare the data to be passed to the template
    data = {
        "breakfast_total": breakfast_total,
        "lunch_total": lunch_total,
        "snacks_total": snacks_total,
        "dinner_total": dinner_total,
        "total_food_consumed": total_food_consumed,
        "total_students": total_students
    }
    return render_template("homepage.html", data=data, navbard=getnavbar())


@app.route("/process_data", methods=["POST"])
@login_required
def process_data():
    start_date = request.form.get("start_date")
    end_date = request.form.get("end_date")
    weekday_totals = calculate_weekday_totals(start_date, end_date)
    return jsonify(weekday_totals=weekday_totals)


def calculate_weekday_totals(start_date, end_date):
    # Run the SQL query using SQLAlchemy to get the total food consumed for each weekday
    #print("working")
    results = (
    db.session.query(
        # 0 for Sunday, 1 for Monday, etc.
        func.extract('dow', FoodConsumption.consumption_date).label("weekday"),
        func.sum(FoodConsumption.breakfast_amt).label("breakfast_total"),
        func.sum(FoodConsumption.lunch_amt).label("lunch_total"),
        func.sum(FoodConsumption.snack_amt).label("snacks_total"),
        func.sum(FoodConsumption.dinner_amt).label("dinner_total"),
    )
    .filter(FoodConsumption.consumption_date.between(start_date, end_date))
    .group_by(func.extract('dow', FoodConsumption.consumption_date))
    .all()
    )

    # Convert the query results to a dictionary for each weekday
    weekday_totals = {}
    for result in results:
        weekday = int(result.weekday)
        weekday_name = get_day_of_week(weekday)
        weekday_totals[weekday_name] = {
            "breakfast_total": result.breakfast_total,
            "lunch_total": result.lunch_total,
            "snacks_total": result.snacks_total,
            "dinner_total": result.dinner_total,
        }

    return weekday_totals


def get_day_of_week(weekday):
    # Map weekday number to weekday name
    days_of_week = ["Sunday", "Monday", "Tuesday",
                    "Wednesday", "Thursday", "Friday", "Saturday"]
    return days_of_week[weekday]

# ----------------------------------------------------------------


if __name__ == '__main__':
    app.run()
