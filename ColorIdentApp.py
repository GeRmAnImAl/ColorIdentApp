import tkinter as tk
from tkinter import *
from tkinter import ttk
from tkinter import messagebox
import sqlite3
from PIL import ImageTk, Image
import random
from playsound import playsound
from gpiozero import LED
from time import sleep

root = tk.Tk()
root.title("Color Identification Assessment")
root.eval("tk::PlaceWindow . center")

#Set application default theme
#Theme optimized for Raspberry Pi OS
style = ttk.Style()
style.configure('TFrame', background = '#e1d8b9')
style.configure('TLabel', background = '#e1d8b9', font = ('Arial', 11))
style.configure('TButton', background = '#28393a', foreground = 'White')
style.configure('Header.TLabel', font = ('Arial', 18, 'bold'))
style.configure('Header2.TLabel', font = ('Arial', 14, 'bold'))

#User class to store data to before updating DB
class User:
     def __init__(self, userID, highestLevel, totalCorrect, totalIncorrect, staff):
          self.userID = userID
          self.highestLevel = highestLevel
          self.totalCorrect = totalCorrect
          self. totalIncorrect = totalIncorrect
          self.staff = staff

#Global variables for usage throughout the application
global userOBJ

#Creates a User object to be used throughout the application
def createUserOBJ(data):
    global userOBJ
    userOBJ = User(data[0][0], data[0][1], data[0][2], data[0][3], data[0][4])

#Creates the local database and users table if they do not already exist.
def createDB():
        db = sqlite3.connect('ColorIdentUsers.db')
        db.row_factory = sqlite3.Row
        cur = db.cursor()
        res = cur.execute('SELECT name FROM sqlite_master WHERE name = "users"')

        if res.fetchone() is None:
            cur.execute('CREATE TABLE users (id, highest_level, total_correct, total_incorrect, staff)')

#Checks if the user ID exists in the database, if it does the instructions screen, or teacher UI loads, otherwise throws an error.
def login(entry):
        user = entry.get()
        if user:
            db = sqlite3.connect('ColorIdentUsers.db')
            db.row_factory = sqlite3.Row
            cur = db.cursor()
            res = cur.execute('SELECT id FROM users WHERE id = ?', (user,))

            if res.fetchone() is None:
                messagebox.showerror(title = 'User Not Found', message = 'That user does not exist.')
            else:
                result = cur.execute('SELECT * FROM users where id = ?', (user,))
                createUserOBJ(result.fetchall())
                db.close()
                if userOBJ.staff == "True":
                    loadTeacherUI()
                else:
                    loadInstructionsUI()
        else:
            messagebox.showerror(title = 'Blank User ID', message = 'You must enter a user ID to login.')

#Creates a new user, checks if the chosen ID already exists and throws an error if true. Proceeds to load instructions screen or teacher UI.
def createUser(entry, flag):
    user = entry.get()
    staff = False
    if flag.get() is True:
        staff = True

    if user:
        db = sqlite3.connect('ColorIdentUsers.db')
        db.row_factory = sqlite3.Row
        cur = db.cursor()
        res = cur.execute('SELECT id FROM users WHERE id = ?', (user,))

        if res.fetchone() is not None:
            messagebox.showerror(title = 'Can Not Create User', message = 'A user with that ID already exists!')
        else:
            cur.execute('INSERT INTO users VALUES (?, ?, ?, ?, ?)', (user, 1, 0, 0, str(staff)))
            db.commit()
            messagebox.showinfo(title = 'Success!', message = 'User created successfully!')
            result = cur.execute('SELECT * FROM users where id = ?', (user,))
            createUserOBJ(result.fetchall())
            db.close()
            if userOBJ.staff == "True":
                loadTeacherUI()
            else:
                loadInstructionsUI()
    else:
        messagebox.showerror(title = 'Blank User ID', message = 'You must enter a User ID for the new User.')

#Updates user data after a user session.
def updateUser(correct, incorrect, level):
    userOBJ.totalCorrect += correct
    userOBJ.totalIncorrect += incorrect
    db = sqlite3.connect('ColorIdentUsers.db')
    db.row_factory = sqlite3.Row
    cur = db.cursor()
    res = cur.execute('SELECT highest_level FROM users WHERE id = ?', (userOBJ.userID,))
    highestLevel = res.fetchone()[0]

    cur.execute('UPDATE users SET total_correct = ? WHERE id = ?', (userOBJ.totalCorrect, userOBJ.userID,))
    cur.execute('UPDATE users SET total_incorrect = ? WHERE id = ?', (userOBJ.totalIncorrect, userOBJ.userID,))
    if level > int(highestLevel):
        userOBJ.highestLevel = level
        cur.execute('UPDATE users SET highest_level = ? WHERE id = ?', (userOBJ.highestLevel, userOBJ.userID,))

    db.commit()
    db.close()
    quit()

#Loads the UI for gameplay
def loadGamePlayUI():
    clearWidgets(instructionsFrame)
    gamePlayFrame.tkraise()
    gamePlayFrame.pack_propagate(False)
    ttk.Label(gamePlayFrame, text = 'Lets Play!', style = 'Header.TLabel').grid(row = 0, column = 1, columnspan= 2)

    color_image = tk.Label(gamePlayFrame, width= 10, height=5)
    color_image.grid(row=2, column =1, columnspan=2)

    color_label = ttk.Label(gamePlayFrame, text = "Color", style = "Header2.TLabel")
    color_label.grid(row = 3, column = 1, columnspan= 2, padx= 5, pady= 5)

    tk.Button(gamePlayFrame, text = 'RED', background='dark red', foreground='pink', width= 10, command= lambda: checkAnswer('Red')).grid(row = 4, column = 0, padx=5, pady=5)
    tk.Button(gamePlayFrame, text = 'Yellow', background='#CDCD33', foreground='#FFFF14', width= 10, command= lambda: checkAnswer('Yellow')).grid(row = 4, column = 1, padx=5, pady=5)
    tk.Button(gamePlayFrame, text = 'Green', background= 'green', foreground='lime green', width= 10, command= lambda: checkAnswer('Green')).grid(row = 4, column = 2, padx=5, pady=5)
    tk.Button(gamePlayFrame, text = 'Blue', background='blue', foreground='cyan', width= 10, command= lambda: checkAnswer('Blue')).grid(row = 4, column = 3, padx=5, pady=5)

    ttk.Button(gamePlayFrame, text = 'Quit', command= lambda:updateUser(correct, incorrect, level)).grid(row = 0, column = 3, padx=5, pady=5)

    colorList = ['Red', 'Yellow', 'Green', 'Blue']
    randomColor = ''
    counter = 1
    masteryCount = 0
    correct = 0
    incorrect = 0
    level = 1
    
    #Assign variables to corosponding LEDs
    redLed = LED(13)
    yellowLed = LED(19)
    greenLed = LED(26)
    blueLed = LED(12)

    #Game logic for level one
    def generateLevelOne():
        nonlocal randomColor
        randomColor = random.choice(colorList)
        color_image.config(bg= randomColor)
        color_label.config(text = randomColor, foreground= randomColor)
        lightLED(randomColor)
    
    #Game logic for level two
    def generateLevelTwo():
        nonlocal randomColor
        randomColor = random.choice(colorList)
        color_image.config(bg= randomColor)
        color_label.config(text = randomColor, foreground= 'Black')
        lightLED(randomColor)

    #Game logic for level three
    def generateLevelThree():
        nonlocal randomColor
        randomColor = random.choice(colorList)
        color_image.config(bg= '#e1d8b9')
        color_label.config(text = randomColor, foreground= randomColor)
        lightLED(randomColor)
    
    #Game logic for level four
    def generateLevelFour():
        nonlocal randomColor
        randomColor = random.choice(colorList)
        color_image.config(bg= '#e1d8b9')
        color_label.config(text = randomColor, foreground= 'Black')
    
    #Game logic for level five
    def generateLevelFive():
        nonlocal randomColor
        randomColor = random.choice(colorList)
        color_image.config(bg= '#e1d8b9')
        color_label.config(text = randomColor, foreground= random.choice(colorList))
        
    #Logic to determine which LED to turn on
    def lightLED(lightColor):        
        if lightColor == 'Red':
            redLed.on()
        elif lightColor == 'Yellow':
            yellowLed.on()
        elif lightColor == 'Green':
            greenLed.on()
        elif lightColor == 'Blue':
            blueLed.on()
            
    #Game logic to determine correct/incorrect answer's as well as determine mastery and level advancement
    def checkAnswer(guess):
        nonlocal counter
        nonlocal correct
        nonlocal incorrect
        nonlocal randomColor
        nonlocal masteryCount
        nonlocal level
        
        if guess == randomColor:
            correct += 1
            masteryCount += 1
        else:
            incorrect += 1

        if counter == 5:
            if masteryCount >= 4:
                level += 1
            masteryCount = 0
            counter = 1
        else:
            counter += 1
        
        #Turn off any LED which is lit by forcing them all off.
        redLed.off()
        yellowLed.off()
        greenLed.off()
        blueLed.off()

        #This block of code only works with Python 3.10 or later
        #match level:
        #   case 1:
        #      generateLevelOne()
        # case 2:
        #    generateLevelTwo()
        #case 3:
        #   generateLevelThree()
        #case 4:
        #   messagebox.showinfo(title = 'CONGRATULATIONS!', message= 'You have reached the max level of this game!')
        
        #This block of code is used for Python versions earlier than 3.10
        if level == 1:
            generateLevelOne()
        elif level == 2:
            generateLevelTwo()
        elif level == 3:
            generateLevelThree()
        elif level == 4:
            generateLevelFour()
        elif level == 5:
            generateLevelFive()
        elif level == 6:
            messagebox.showinfo(title = 'CONGRATULATIONS!', message= 'You have reached the max level of this game!')
            loadLoginUI()


    generateLevelOne()

#Exits the application
def quit():
    root.destroy()

#Clears the widgets from a frame
def clearWidgets(frame):
    for widget in frame.winfo_children():
        widget.destroy()

#Loads the UI for the user login
def loadLoginUI():
    clearWidgets(teacherUIFrame)
    loginFrame.tkraise()
    loginFrame.pack_propagate(False)
    ttk.Label(loginFrame, text= "Welcome to Color Picker!", style = 'Header.TLabel').grid(row=0, column=0, columnspan = 3)
    ttk.Label(loginFrame, text = 'User Name:').grid(row= 1, column= 0, padx = 5, pady= 5, sticky = 'e')
    entry_userID = ttk.Entry(loginFrame, width = 12, font = ('Arial', 10))
    entry_userID.grid(row = 1, column=1, padx = 5, sticky = 'w', columnspan= 3)
    ttk.Button(loginFrame, text = 'Login', command = lambda: login(entry_userID)).grid(row = 2, column = 0, padx=5, pady= 5, columnspan = 3)
    ttk.Button(loginFrame, text = 'Create User', command = lambda: createUser(entry_userID, staffFlag)).grid(row = 3, column = 0, padx= 5, pady= 5, columnspan = 3)
    staffFlag = tk.BooleanVar()
    staff = ttk.Checkbutton(loginFrame, text = "Staff", variable = staffFlag, onvalue=True, offvalue= False).grid(row = 3, column = 2, sticky = 'w')
    
    ttk.Button(loginFrame, text = '1', command = lambda: entry_userID.insert(END, '1')).grid(row = 5, column = 0, padx = 5, pady = 5)
    ttk.Button(loginFrame, text = '2', command = lambda: entry_userID.insert(END, '2')).grid(row = 5, column = 1, padx = 5, pady = 5)
    ttk.Button(loginFrame, text = '3', command = lambda: entry_userID.insert(END, '3')).grid(row = 5, column = 2, padx = 5, pady = 5)
    ttk.Button(loginFrame, text = '4', command = lambda: entry_userID.insert(END, '4')).grid(row = 6, column = 0, padx = 5, pady = 5)
    ttk.Button(loginFrame, text = '5', command = lambda: entry_userID.insert(END, '5')).grid(row = 6, column = 1, padx = 5, pady = 5)
    ttk.Button(loginFrame, text = '6', command = lambda: entry_userID.insert(END, '6')).grid(row = 6, column = 2, padx = 5, pady = 5)
    ttk.Button(loginFrame, text = '7', command = lambda: entry_userID.insert(END, '7')).grid(row = 7, column = 0, padx = 5, pady = 5)
    ttk.Button(loginFrame, text = '8', command = lambda: entry_userID.insert(END, '8')).grid(row = 7, column = 1, padx = 5, pady = 5)
    ttk.Button(loginFrame, text = '9', command = lambda: entry_userID.insert(END, '9')).grid(row = 7, column = 2, padx = 5, pady = 5)
    ttk.Button(loginFrame, text = '0', command = lambda: entry_userID.insert(END, '0')).grid(row = 8, column = 0, padx = 5, pady = 5, columnspan = 3)
    ttk.Button(loginFrame, text = 'Clear', command = lambda: entry_userID.delete(0, END)).grid(row = 9, column = 2, padx = 5, pady =5)

#Loads the UI for gameplay instructions
def loadInstructionsUI():
    clearWidgets(loginFrame)
    instructionsFrame.tkraise()
    instructionsFrame.pack_propagate(False)
    ttk.Label(instructionsFrame, text = "Game Instructions", style = 'Header.TLabel').grid(row = 0, column = 0, columnspan = 2, padx=5, pady=5)
    
    pic = Image.open('Assets/Look.png')
    resizePic = pic.resize((100, 100), Image.LANCZOS)
    eyes = ImageTk.PhotoImage(resizePic)
    eyes_label = ttk.Label(instructionsFrame, image = eyes)
    eyes_label.image = eyes
    eyes_label.grid(row = 1, column = 0, padx=5, pady=5)
    ttk.Label(instructionsFrame, text = 'Look!', style = 'TLabel').grid(row = 1, column=1, padx=5, pady=5)

    pic = Image.open('Assets/Listen.png')
    resizePic = pic.resize((100, 100), Image.LANCZOS)
    ear = ImageTk.PhotoImage(resizePic)
    ear_label = ttk.Label(instructionsFrame, image = ear)
    ear_label.image = ear
    ear_label.grid(row = 2, column = 1, padx=5, pady=5)
    ttk.Label(instructionsFrame, text = 'Listen!', style = 'TLabel').grid(row = 2, column=0, padx=5, pady=5)

    pic = Image.open('Assets/Press.png')
    resizePic = pic.resize((100, 100), Image.LANCZOS)
    press = ImageTk.PhotoImage(resizePic)
    press_label = ttk.Label(instructionsFrame, image = press)
    press_label.image = press
    press_label.grid(row = 3, column = 0, padx=5, pady=5)
    ttk.Label(instructionsFrame, text = 'Choose!', style = 'TLabel').grid(row = 3, column=1, padx=5, pady=5)

    ttk.Button(instructionsFrame, text = "Start", command = lambda: loadGamePlayUI()).grid(row = 4, column = 0, padx= 5, pady= 5)
    ttk.Button(instructionsFrame, text = 'Quit', command = lambda: quit()).grid(row = 4, column = 1, padx= 5, pady= 5)
    
    #Assign variables to corosponding LEDs
    redLed = LED(13)
    yellowLed = LED(19)
    greenLed = LED(26)
    blueLed = LED(12)
    
    #Used to flash the leds in sequence, one at a time.
    def flashLights():
        redLed.on()
        sleep(0.25)
        redLed.off()
        sleep(0.25)
        yellowLed.on()
        sleep(0.25)
        yellowLed.off()
        sleep(0.25)
        greenLed.on()
        sleep(0.25)
        greenLed.off()
        sleep(0.25)
        blueLed.on()
        sleep(0.25)
        blueLed.off()
        sleep(0.25)
    
    flashLights()

#Loads the UI for staff to view user data
def loadTeacherUI():
    clearWidgets(loginFrame)
    teacherUIFrame.tkraise()
    teacherUIFrame.pack_propagate(False)
    ttk.Label(teacherUIFrame, text = 'User Data', style = 'Header.TLabel').grid(row = 0, column = 0, columnspan = 5)
    ttk.Label(teacherUIFrame, text = 'ID', style = 'Header2.TLabel').grid(row = 1, column = 0, padx = 5)
    ttk.Label(teacherUIFrame, text = 'Highest Level', style = 'Header2.TLabel').grid(row = 1, column = 1, padx = 5)
    ttk.Label(teacherUIFrame, text = 'Total Correct', style = 'Header2.TLabel').grid(row = 1, column = 2, padx = 5)
    ttk.Label(teacherUIFrame, text = 'Total Incorrect', style = 'Header2.TLabel').grid(row = 1, column = 3, padx = 5)
    ttk.Label(teacherUIFrame, text = 'Staff', style = 'Header2.TLabel').grid(row = 1, column = 4, padx = 5)
    db = sqlite3.connect('ColorIdentUsers.db')
    db.row_factory = sqlite3.Row
    cur = db.cursor()
    res = cur.execute('SELECT * FROM users WHERE staff = "False"')
    i = 2
    for user in res:
        for j in range(len(user)):
            ttk.Label(teacherUIFrame, width = 10, anchor = 'center', text = user[j]).grid(row = i, column = j, padx = 5)
        i += 1

    ttk.Button(teacherUIFrame, text = 'Back', command = lambda: loadLoginUI()).grid(row = i, column = 0, columnspan= 5, padx= 5, pady= 5)

#Frame assets used in the application
loginFrame = ttk.Frame(root)
instructionsFrame = ttk.Frame(root)
teacherUIFrame = ttk.Frame(root)
gamePlayFrame= ttk.Frame(root)

for frame in (loginFrame, instructionsFrame, teacherUIFrame, gamePlayFrame):
    frame.grid(row = 0, column = 0, sticky = 'nesw')

#Create the database if one does not exist
createDB()
#Load the user login UI
loadLoginUI()

root.mainloop()

