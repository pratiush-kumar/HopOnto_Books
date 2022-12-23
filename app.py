from pymongo import MongoClient
from flask import *
from flask_session import Session
from datetime import datetime, timedelta
import bcrypt
import os
import pytz

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

client = MongoClient('mongodb://localhost:27017')
Credentials = client['LibrO']['credentials']
Books = client['LibrO']['book_list']
Subscribers = client['LibrO']['subscribers']

@app.route("/")
def login():
    if 'username' in session:
        return redirect('/home')
    return render_template('preLogin/login.html')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static/images'),'favicon.ico')

@app.route("/logout")
def logout():
    session.pop('username',None)
    flash("Logout Successful")
    return redirect("/")

@app.route("/login_verification", methods=['POST'])
def login_verification():
    username = request.form.get("username")
    password = request.form.get("password")
    username_found = Credentials.find_one({"username": username})
    if username_found:
        passwordCheck = username_found['password']
        if bcrypt.checkpw(password.encode('utf-8'), passwordCheck):
            session["username"] = username
            flash("Welcome to HopOnto Lending Library - Admin Web Portal.")
            return redirect("/home")
        else:
            flash("Please enter valid credentials")
            return redirect('/')
    else:
        flash("Please enter valid credentials")
        return redirect('/')

@app.route("/home")
def home():
    if not session.get("username"):
        flash("Please Login to continue")
        return redirect("/")
    book_list = Books.find().sort("BookID")
    books=[]
    for book in book_list:
        status = book["IssuedTo"]
        book["daysLeft"] = (book["IssueDate"]-datetime.strptime(str(datetime.now(tz=pytz.timezone('Asia/Calcutta')).date()),"%Y-%m-%d")).days
        if status==-1:
            book["colour"] = "bg-success"
        elif book["daysLeft"]<=0:
            book["colour"] = "bg-danger"
        else:
            book["colour"] = "bg-warning"
        books.append(book)
    subscriber_list = Subscribers.find().sort("CardNo")
    subscribers=[]
    for subscriber in subscriber_list:
        status = subscriber["DueDate"]-datetime.strptime(str(datetime.now(tz=pytz.timezone('Asia/Calcutta')).date()),"%Y-%m-%d")
        subscriber["daysLeft"] = status.days
        if status.days<=0:
            subscriber["colour"] = "bg-danger"
        elif status.days<=3:
            subscriber["colour"] = "bg-warning"
        else:
            subscriber["colour"] = "bg-success"
        subscribers.append(subscriber)
    return render_template('postLogin/home.html', book_list=books, subscriber_list=subscribers)

@app.route("/registration")
def registration():
    return render_template('preLogin/registration.html')

@app.route("/registration_verification", methods=['POST'])
def registration_verification():
    username = request.form.get("username")
    email = request.form.get("email")
    contact = request.form.get("contact")
    contact='+91'+contact
    password1 = request.form.get("password1")
    password2 = request.form.get("password2")
    username_found = Credentials.find_one({"username": username})
    if username_found:
        flash("Username already exists")
        return redirect("/")
    elif password1 != password2:
        flash("Re-entered password does not match")
        return redirect('/registration')
    password_hash = bcrypt.hashpw(password2.encode('utf-8'), bcrypt.gensalt())
    Credentials.insert_one({ "username":username, "password":password_hash, "email":email, "contact":contact })
    flash("Registration successful")
    return redirect('/home')

@app.route("/add_book")
def add_book():
    if not session.get("username"):
        flash("Please Login to continue")
        return redirect("/")
    return render_template("postLogin/newBook.html")

@app.route("/add_new_book",methods=['POST'])
def add_new_book():
    if not session.get("username"):
        flash("Please Login to continue")
        return redirect("/")
    title = request.form.get("title")
    author1 = request.form.get("author1")
    author2 = request.form.get("author2")
    bookID = request.form.get('id')
    authors = []
    if author1!="":
        authors.append(request.form.get("author1"))
    if author2!="":
        authors.append(request.form.get("author2"))
    if bookID!="":
        BookID=int(bookID)
        elem = Books.find_one({"BookID":BookID})
        if elem:
            flash("Book with ID already exists")
            return redirect("/add_book")
    else:
        if Books.count_documents({})==0:
            BookID=1
        else:
            elem = Books.find().sort("BookID",-1).limit(1)[0]
            BookID = elem['BookID']+1
    Books.insert_one({ "Title":title, "Authors":authors, "IssuedTo":-1, "BookID": BookID, "IssueDate":datetime.strptime(str(datetime.now(tz=pytz.timezone('Asia/Calcutta')).date()),"%Y-%m-%d") })
    flash("Successfully added new Book")
    return redirect('/book/'+str(BookID))

@app.route("/add_subscriber")
def add_subscriber():
    if not session.get("username"):
        flash("Please Login to continue")
        return redirect("/")
    return render_template("/postLogin/newSubscriber.html")

@app.route("/add_new_subscriber", methods=['POST'])
def add_new_subscriber():
    if not session.get("username"):
        flash("Please Login to continue")
        return redirect("/")
    name = request.form.get("name")
    email = request.form.get("email")
    contact = request.form.get("contact")
    subscriptionDate = request.form.get("subscriptionDate")
    CardID = request.form.get("id")
    subscriptionType = int(request.form.get("subscriptionType"))
    subscriptionDuration = int(request.form.get("subscriptionDuration"))
    if subscriptionDate=="":
        DueDate = datetime.strptime(str(datetime.now(tz=pytz.timezone('Asia/Calcutta')).date()),"%Y-%m-%d")
    else:
        DueDate = datetime.strptime(subscriptionDate,"%Y-%m-%d")
    if CardID!="":
        CardID = int(CardID)
        elem = Subscribers.find_one({"CardNo":CardID})
        if elem:
            flash("Subscriber with Card Number already exists")
            return redirect("/add_subscriber")
    else:
        if Subscribers.count_documents({})==0:
            CardID=1
        else:
            elem = Subscribers.find().sort("CardNo",-1).limit(1)[0]
            CardID = (elem['CardNo'])+1
    Subscribers.insert_one({ "Name":name, "Email":email, "Contact":contact, "Books":[], "DueDate":DueDate+timedelta(days=31), "CardNo":CardID, "Type":subscriptionType, "Duration":DueDate+timedelta(days=subscriptionDuration*31), "TimePeriod":subscriptionDuration })
    flash("Successfully created new Subscriber")
    return redirect("/subscriber/"+str(CardID))

@app.route("/book/<book_id>")
def book(book_id):
    if not session.get("username"):
        flash("Please Login to continue")
        return redirect("/")
    book_id = int(book_id)
    book = Books.find_one({"BookID":book_id})
    daysLeft = (book["IssueDate"]-datetime.strptime(str(datetime.now(tz=pytz.timezone('Asia/Calcutta')).date()),"%Y-%m-%d")).days
    if daysLeft<=0:
        status = "text-danger"
    else:
        status = "text-success"
    return render_template("postLogin/book.html",book=book,status=status)

@app.route("/subscriber/<subscriber_id>")
def subscriber(subscriber_id):
    if not session.get("username"):
        flash("Please Login to continue")
        return redirect("/")
    subscriber_id = int(subscriber_id)
    subscriber = Subscribers.find_one({"CardNo":subscriber_id})
    status = subscriber['DueDate']-datetime.strptime(str(datetime.now(tz=pytz.timezone('Asia/Calcutta')).date()),"%Y-%m-%d")
    memberStatus = subscriber['Duration']-subscriber['DueDate']
    if status.days<=0:
        colour = "text-danger"
    elif status.days<=3:
        colour = "text-warning"
    else:
        colour = "text-success"
    if memberStatus.days<=0:
        memberColour = "text-success"
    else:
        memberColour = "text-danger"
    return render_template("postLogin/subscriber.html",subscriber=subscriber, status = colour, memberStatus=memberColour)

@app.route("/issue_book", methods=['POST'])
def issue_book():
    if not session.get("username"):
        flash("Please Login to continue")
        return redirect("/")
    bookID = int(request.form.get("bookID"))
    subscriberID = int(request.form.get("subscriberID"))
    returnDate = request.form.get('issueDate')
    subscriber = Subscribers.find_one({"CardNo":subscriberID})    
    if subscriber==None:
        flash("Issuer Card Number not found")
        return redirect("/book/"+str(bookID))
    if subscriber['Type']<=len(subscriber["Books"]):
        flash("Subscriber has issued maximum number of Books")
        return redirect("/book/"+str(bookID))
    if returnDate == "":
        returnDate = datetime.strptime(str(datetime.now(tz=pytz.timezone('Asia/Calcutta')).date()),"%Y-%m-%d")+timedelta(days=15)
    else:
        returnDate = datetime.strptime(returnDate,"%Y-%m-%d")
    subscriber['Books'].append(bookID)
    Subscribers.update_one({"CardNo":subscriberID},{"$set":{"Books":subscriber['Books']}})
    Books.update_one({"BookID":bookID},{"$set":{"IssuedTo":subscriberID, "IssueDate":returnDate }})
    flash("Book issued successfully")
    return redirect("/book/"+str(bookID))

@app.route("/return_book", methods=['POST'])
def return_book():
    if not session.get("username"):
        flash("Please Login to continue")
        return redirect("/")
    bookID = int(request.form.get('bookID'))
    subscriberID = int(request.form.get('subscriberID'))
    subscriber = Subscribers.find_one({"CardNo":subscriberID})    
    subscriber['Books'].remove(bookID)
    Subscribers.update_one({"CardNo":subscriberID},{"$set":{"Books":subscriber['Books']}})
    Books.update_one({"BookID":bookID},{"$set":{"IssuedTo":-1}})
    flash("Book returned successfully")
    return redirect("/book/"+str(bookID))

@app.route("/delete_book", methods=['POST'])
def delete_book():
    if not session.get("username"):
        flash("Please Login to continue")
        return redirect("/")
    bookID = int(request.form.get('bookID'))
    Books.delete_one({"BookID":bookID})
    flash("Book deleted successfully")
    return redirect("/")

@app.route("/delete_subscriber", methods=['POST'])
def delete_subscriber():
    if not session.get("username"):
        flash("Please Login to continue")
        return redirect("/")
    subscriberID = int(request.form.get('subscriberID'))
    Subscribers.delete_one({"CardNo":subscriberID})
    flash("Subscriber deleted successfully")
    return redirect("/")

@app.route("/renew_subscription", methods=['POST'])
def renew_subscription():
    if not session.get("username"):
        flash("Please Login to continue")
        return redirect("/")
    subscriberID = int(request.form.get('subscriberID'))
    subscriber = Subscribers.find_one({"CardNo":subscriberID})
    Subscribers.update_one({"CardNo":subscriberID},{'$set':{"DueDate":subscriber['DueDate']+timedelta(days=31)}})
    flash("Subscription renewal successful")
    return redirect("/subscriber/"+str(subscriberID))
