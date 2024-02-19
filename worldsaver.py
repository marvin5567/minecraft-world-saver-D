# operating system imports
import os
import time
import shutil
import hashlib
import tempfile
import threading
from threading import Thread

# database related imports
from gridfs import GridFS
from bson import ObjectId
from pymongo import MongoClient

# kivy imports
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty
from kivy.graphics import Color, Rectangle
from kivy.uix.gridlayout import GridLayout


from tkinter import Tk
from tkinter import filedialog


TOKEN = 'mongodb+srv://karimabouelnour2006:Dwad2O3dnTWp9KaZ@minecraftworldsaver.wefidgi.mongodb.net/?retryWrites=true&w=majority'
image_data = ''
defImgPath = './resc/images/defaultPFP.jpg'

# Load the KV file
Builder.load_file("worldsaver.kv")

class HomePage(BoxLayout):
    def __init__(self, **kwargs):
        super(HomePage, self).__init__(**kwargs)
        self.defaultDir = r"C:\Users\Owner\AppData\Roaming\.minecraft\saves"
        self.currentUserId = self.readUserID()  # To be set after login
        self.upload_queue = Queue()
        self.upload_thread = Thread(target=self.process_upload_queue)
        self.upload_thread.daemon = True
        self.flask_thread = None  # Initialize the Flask thread
        self.upload_thread.start()

    def readUserID(self):
            try:
                with open("currentUserId.txt", "r") as file:
                    return file.read().strip()
            except FileNotFoundError:
                return None

    def selectDirectory(self):
        # Perform actions when the "Select Directory" button is pressed
        root = Tk()
        root.withdraw()

        directory = filedialog.askdirectory(initialdir=self.defaultDir, title="Select Minecraft Worlds Directory")
        root.destroy()

        if directory:
            print(f"Selected directory: {directory}")
            self.defaultDir = directory
            self.displayWorlds()
        else:
            print("No directory selected")

    def logoutUser(self):
        # Delete user ID file when logging out
        try:
            os.remove("currentUserId.txt")
        except FileNotFoundError:
            pass

        self.clear_widgets()
        self.add_widget(LoginScreen())

    def process_upload_queue(self):
        while True:
            if not self.upload_queue.is_empty():
                worldName, worldPath = self.upload_queue.dequeue()  # Dequeue item from the queue
                try:
                    print(f"Processing upload queue: '{worldName}' from {worldPath}...")
                    # Simulate upload process
                    time.sleep(2)
                    print(f"World '{worldName}' uploaded successfully.")
                except Exception as e:
                    print(f"Error uploading world '{worldName}': {e}")
            else:
                # If queue is empty, wait for some time before checking again
                time.sleep(1)

    def displayWorlds(self):
        # Accessing the worldLayout from the kv file
        world_layout = self.ids.worldLayout
        world_layout.clear_widgets()

        # create layouts for local and uploaded worlds
        local_worlds_layout = GridLayout(cols=1, size_hint_y=None)
        local_worlds_layout.bind(minimum_height=local_worlds_layout.setter('height'))

        uploaded_worlds_layout = GridLayout(cols=1, size_hint_y=None)
        uploaded_worlds_layout.bind(minimum_height=uploaded_worlds_layout.setter('height'))

        # display local worlds in the directory
        local_worlds_label = Label(text="Local Worlds", size_hint_y=None, height=40, font_size='20sp')
        local_worlds_layout.add_widget(local_worlds_label)

        local_worlds = [world for world in os.listdir(self.defaultDir) if os.path.isdir(os.path.join(self.defaultDir, world))]
        local_worlds_buttons = [Button(text=world, size_hint_y=None, height=60, font_size='15sp') for world in local_worlds]

        # use the bubbleSortWorlds function to sort local worlds
        local_worlds_buttons = self.bubbleSortWorlds(local_worlds_buttons)

        for button in local_worlds_buttons:
            button.bind(on_press=lambda instance: self.uploadWorldButton(instance.text))

        local_world_layout = self.createGridLayout(local_worlds_buttons, 3, spacing=10)
        local_worlds_layout.add_widget(local_world_layout)

        # display uploaded worlds
        uploaded_worlds_label = Label(text="Uploaded Worlds", size_hint_y=None, height=40, font_size='20sp')
        uploaded_worlds_layout.add_widget(uploaded_worlds_label)

        user_uploaded_worlds = app.db.worlds.find({'user_id': self.currentUserId})
        uploaded_worlds_buttons = [Button(text=world['name'], size_hint_y=None, height=60, font_size='15sp') for world in user_uploaded_worlds]

        # use the bubbleSortWorlds function to sort uploaded worlds
        uploaded_worlds_buttons = self.bubbleSortWorlds(uploaded_worlds_buttons)

        for button in uploaded_worlds_buttons:
            button.bind(on_press=lambda instance, w=button.text: self.loadUploadedWorld(w))

        uploaded_world_layout = self.createGridLayout(uploaded_worlds_buttons, 3, spacing=10)
        uploaded_worlds_layout.add_widget(uploaded_world_layout)

        # add local and uploaded worlds layouts to the main layout
        world_layout.add_widget(local_worlds_layout)
        world_layout.add_widget(uploaded_worlds_layout)

    def bubbleSortWorlds(self, worlds):
        n = len(worlds)

        for i in range(n - 1):
            for j in range(0, n - i - 1):
                # assuming worlds is a list of dictionaries with 'text' attribute
                if worlds[j].text > worlds[j + 1].text:
                    worlds[j], worlds[j + 1] = worlds[j + 1], worlds[j]

        return worlds
    
    def createGridLayout(self, buttons, cols, spacing=0):
        grid_layout = GridLayout(cols=cols, size_hint_y=None, spacing=spacing)
        grid_layout.bind(minimum_height=grid_layout.setter('height'))

        for button in buttons:
            grid_layout.add_widget(button)

        return grid_layout
    
    def uploadWorld(self, worldName, worldData, currentUserId):
        print(f"Uploading world '{worldName}' with size {len(worldData)} bytes")

        try:
            # Create a GridFS object
            fs = GridFS(app.db, collection='worlds_fs')

            # Upload the world data to GridFS
            file_id = fs.put(worldData, filename=worldName)

            # Store metadata in the worlds collection
            app.db.worlds.insert_one({'name': worldName, 'file_id': file_id, 'user_id': currentUserId})
            
            print(f"World '{worldName}' uploaded successfully.")

        except Exception as e:
            print(f"Error uploading world to GridFS: {e}")
            
        self.displayWorlds()

    def uploadWorldButton(self, worldName):
        worldPath = os.path.join(self.defaultDir, worldName)

        print("Enqueuing world:", worldName)  # Print when enqueuing
        self.upload_queue.enqueue((worldName, worldPath))  # Enqueue world information

        print("packing sqeuence initiated")
        try:
            # make a temp directory
            tempDir = tempfile.mkdtemp()
            print("packing p1 done")
            # create a zip archive of the world directory
            tempZipPath = os.path.join(tempDir, worldName + '.zip')
            print("packing p2 done")
            shutil.make_archive(tempZipPath[:-4], 'zip', worldPath)
            print("packing p3 done")
            # read the zip file as binary data
            with open(tempZipPath, 'rb') as zip_file:
                zipData = zip_file.read()
            print("packing p4 done")

            # Await the uploadWorld method
            self.uploadWorld(worldName, zipData, self.currentUserId)
            print(f"World '{worldName}' uploaded successfully.")
        except FileNotFoundError:
            print(f"Error: World file not found at '{worldPath}'")
        except PermissionError:
            print(f"Error: Permission denied reading world file '{worldPath}'")
        except Exception as e:
            print(f"Error reading/world file: {e}")
        finally:
            # remove the temporary directory
            shutil.rmtree(tempDir, ignore_errors=True)

    def loadUploadedWorld(self, worldName):
        try:
            # retrieve the uploaded world data from MongoDB
            worldData = app.db.worlds.find_one({'name': worldName, 'user_id': self.currentUserId})

            if worldData:
                world_details_screen = WorldDetailsScreen(worldName=worldName)  # Pass worldName argument
                world_details_screen.worldData = worldData  # Set worldData as an attribute

                # clear existing widgets and add the new world details screen
                app.root.clear_widgets()
                app.root.add_widget(world_details_screen)
            else:
                print(f"Error: Uploaded world data not found for '{worldName}'")
        except Exception as e:
            print(f"Error loading uploaded world: {e}")

    def switchToUserDashboard(self):
        user_dashboard = UserDashboard()
        self.clear_widgets()
        self.add_widget(user_dashboard)

class WorldDetailsScreen(BoxLayout):
    worldName = StringProperty("")  # Add worldName attribute

    def __init__(self, **kwargs):
        super(WorldDetailsScreen, self).__init__(**kwargs)
        self.worldName = kwargs.get('worldName', '')  # Set worldName if provided
        self.currentUserId = self.readUserID()

    def readUserID(self):
        try:
            with open("currentUserId.txt", "r") as file:
                return file.read().strip()
        except FileNotFoundError:
            return None

    def downloadWorld(self, worldData, worldName):
        try:
            # Create a temporary directory
            tempDir = tempfile.mkdtemp()

            # Retrieve the file_id from the MongoDB document
            file_id = worldData['file_id']

            # Use GridFS to retrieve the file data by its ObjectId
            fs = GridFS(app.db, collection='worlds_fs')
            file_data = fs.get(ObjectId(file_id)).read()

            # Create a zip file with the world data
            tempZipPath = os.path.join(tempDir, f"{worldName}.zip")
            with open(tempZipPath, 'wb') as zip_file:
                zip_file.write(file_data)

            # Specify the target directory for downloading (adjust as needed)
            downloadDir = r"C:\Users\Owner\Downloads"

            # Copy the zip file to the target directory
            shutil.copy(tempZipPath, os.path.join(downloadDir, f"{worldName}.zip"))

            print(f"World '{worldName}' downloaded successfully to {downloadDir}")
            self.show_popup(f"World '{worldName}' downloaded successfully!")

        except Exception as e:
            print(f"Error downloading world: {e}")

        finally:
            # Remove the temporary directory
            shutil.rmtree(tempDir, ignore_errors=True)

    def deleteWorld(self, worldName):
        print(f"Deleting world '{self.worldName}'...")
        try:
            # Retrieve the world document from MongoDB
            worldData = app.db.worlds.find_one({'name': worldName, 'user_id': self.currentUserId})

            if worldData:
                # Retrieve the file_id from the world document
                file_id = worldData['file_id']

                # Create a GridFS object
                fs = GridFS(app.db, collection='worlds_fs')

                # Delete the chunks and file document associated with the file_id
                fs.delete(ObjectId(file_id))

                # Delete the world from MongoDB
                app.db.worlds.delete_one({'name': worldName, 'user_id': self.currentUserId})

                print(f"World '{worldName}' deleted successfully")
                self.show_popup(f"World '{worldName}' deleted successfully!")

                # Refresh the UI after deleting the world
                app.root.clear_widgets()
                app.root.add_widget(HomePage(currentUserId=self.currentUserId))

            else:
                print(f"Error: World data not found for '{worldName}'")

        except Exception as e:
            print(f"Error deleting world: {e}")

    def goBack(self):
        App.get_running_app().root.clear_widgets()
        App.get_running_app().root.add_widget(HomePage())

class LoginScreen(BoxLayout):
    def __init__(self, **kwargs):
        super(LoginScreen, self).__init__(**kwargs)

    def validateUser(self):
        global user
        user = self.ids.username.text
        password = self.ids.password.text

        # Hash the password
        hashedPassword = hashlib.sha256(password.encode()).hexdigest()

        # Check if the user exists in the database using the hashed password
        userExists = app.db.users.find_one({'username': user, 'password': hashedPassword})

        if userExists:
            # Save user ID to a file
            with open("currentUserId.txt", "w") as file:
                file.write(str(userExists['_id']))

            # Switch pages
            App.get_running_app().root.clear_widgets()
            App.get_running_app().root.add_widget(HomePage())

        else:
            # If it doesn't exist, display an error message
            popup = Popup(title='Invalid Login', content=Label(text='Invalid username or password'),
                          size_hint=(None, None), size=(400, 400))
            popup.open()

    def switchToSignupScreen(self):
        App.get_running_app().root.clear_widgets()
        App.get_running_app().root.add_widget(SignUpScreen())
        
class SignUpScreen(BoxLayout):
    def __init__(self, **kwargs):
        super(SignUpScreen, self).__init__(**kwargs)
        self.fs = GridFS(app.db, collection='profile_pictures')

    def add_user(self):
        user = self.ids.username.text
        password = self.ids.password.text
        confirmPassword = self.ids.confirmPassword.text

        if user and password and confirmPassword:
            # Check if the username is already taken
            existing_user = app.db.users.find_one({'username': user})
            if existing_user:
                popup = Popup(title='Sign Up Error', content=Label(text='Username already taken'),
                              size_hint=(None, None), size=(400, 400))
                popup.open()
                return

            if password == confirmPassword:
                # Hash the password
                hashedPassword = hashlib.sha256(password.encode()).hexdigest()

                # Add the new user to the database
                app.db.users.insert_one({'username': user, 'password': hashedPassword, 'age':'', 'name':''})
                session = app.db.users.find_one({'username': user, 'password': hashedPassword})

                with open("currentUserId.txt", "w") as file:
                    file.write(str(session['_id']))

                print("User added")
                App.get_running_app().root.clear_widgets()
                App.get_running_app().root.add_widget(AdditionalInfoScreen())
            else:
                popup = Popup(title='Sign Up Error', content=Label(text='Passwords do not match'),
                              size_hint=(None, None), size=(400, 400))
                popup.open()
        else:
            popup = Popup(title='Sign Up Error', content=Label(text='Please fill in all fields'),
                          size_hint=(None, None), size=(400, 400))
            popup.open()

    def go_back(self):
        App.get_running_app().root.clear_widgets()
        App.get_running_app().root.add_widget(LoginScreen())

class AdditionalInfoScreen(Screen):
    def __init__(self, **kwargs):
        super(AdditionalInfoScreen, self).__init__(**kwargs)
        self.fs = GridFS(app.db, collection='profile_pictures')

    def readUserID(self):
            try:
                with open("currentUserId.txt", "r") as file:
                    return file.read().strip()
            except FileNotFoundError:
                return None

    def uploadProfilePicture(self):
        root = Tk()
        root.withdraw()

        global picFilePath
        picFilePath = filedialog.askopenfilename(initialdir=".", title="Select Profile Picture",
                                               filetypes=(("Image files", "*.jpg;*.png;*.jpeg"), ("All files", "*.*")))

        root.destroy()

        if picFilePath:
            print(f"Selected file: {picFilePath}")

            try:
                with open(picFilePath, 'rb') as f:
                    image_data = f.read()
                    print("Data accessed successfully!")
                

            except Exception as e:
                print(f"Error uploading profile picture: {e}")
        else:
            print("No file selected")

    def submitAdditionalInfo(self):
        # Retrieve additional information from input fields
        name = self.ids.name_input.text
        global age
        age = self.ids.age_input.text

        # Assuming you have a MongoDB collection called 'users'
        # Update the user's document with the additional information
        try:
            if name == '':
                app.db.users.update({'_id': self.readUserID()}, {'name': ''})
                print(f'Now entering age: none')
            else:
                app.db.users.update({'_id': self.readUserID()}, {'name': name})
                print(f'Now entering age: {str(name)}')

            if age == '':
                app.db.users.update({'_id': self.readUserID()}, {'age': ''})
                print(f'Now entering age: none')
            else:
                app.db.users.update({'_id': self.readUserID()}, {'age': age})
                print(f'Now entering age: {str(age)}')


            if image_data == '':
             
                with open(defImgPath, 'rb') as f:
                    def_image_data = f.read()
                    print("Data accessed successfully!")


                file_id = self.fs.put(def_image_data, filename=os.path.basename(defImgPath))
                print(f"Profile picture data uploaded successfully. File ID: {file_id}")

                app.db.pfps.insert_one({'user_id': self.readUserID(), 'file_id': file_id})
                print(f"Profile picture meta data uploaded succesfully. File ID: {file_id}")

            else:
                file_id = self.fs.put(image_data, filename=os.path.basename(picFilePath))
                print(f"Profile picture data uploaded successfully. File ID: {file_id}")

                app.db.pfps.insert_one({'user_id': self.readUserID(), 'file_id': file_id})
                print(f"Profile picture meta data uploaded succesfully. File ID: {file_id}")

            # app.db.users.update({'_id': self.readUserID()}, {'$set': {'name': name, 'age': age}})
            print("All Additional information submitted successfully!")

            App.get_running_app().root.clear_widgets()
            App.get_running_app().root.add_widget(HomePage())

        except Exception as e:
            print(f"Error submitting additional information: {e}")

class UserDashboard(BoxLayout):
    def goToAccountDetails(self):
        print("Navigating to Account Details")
        # App.get_running_app().root.clear_widgets()
        # App.get_running_app().root.add_widget(AccountDetails())
        
    def goToSettings(self):
        print("Navigating to Settings")
        # Placeholder for navigation logic
    
    def goBack(self):
        App.get_running_app().root.clear_widgets()
        App.get_running_app().root.add_widget(HomePage())

# class AccountDetails(BoxLayout):
#     def __init__(self, user_data=None, **kwargs):
#         super(AccountDetails, self).__init__(**kwargs)
#         if user_data:
#             self.ids.username_label.text = f"Username: {user_data.get('username', '')}"
#             self.ids.age_label.text = f"Age: {user_data.get('age', '')}"
#             # Load profile picture if available
#             self.load_profile_picture(user_data.get('profile_picture', ''))

#     def load_profile_picture(self, file_id):
#         if file_id:
#             # Load profile picture based on file_id
#             try:
#                 fs = GridFS(app.db, collection='profile_pictures')
#                 profile_picture_data = fs.get(ObjectId(file_id)).read()
#                 # Display profile picture
#                 self.ids.profile_image.texture = CoreImage(BytesIO(profile_picture_data), ext="png").texture
#             except Exception as e:
#                 print(f"Error loading profile picture: {e}")

#     def goBack(self):
#         App.get_running_app().root.clear_widgets()
#         App.get_running_app().root.add_widget(UserDashboard())

    
#     def readUserID(self):
#             try:
#                 with open("currentUserId.txt", "r") as file:
#                     return file.read().strip()
#             except FileNotFoundError:
#                 return None
        
#     def changeAdditionalDetails(self):
#         print("Changing additional account details")
#         # Placeholder for changing additional details logic

#     def deleteAccount(self):
#         print("Deleting account")
#         # Placeholder for deleting account logic

#     def deleteAllData(self):
#         print("Deleting all data")
#         # Placeholder for deleting all data logic

#     def goBack(self):
#         App.get_running_app().root.clear_widgets()
#         App.get_running_app().root.add_widget(UserDashboard())

class ColoredBoxLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0.561, 0.8, 0.361, 1)  # set the color to green
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_rect, pos=self._update_rect)

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

class Queue:
    def __init__(self):
        self.items = []
        
    def is_empty(self):
        if self.items:
            print("is empty active")
            print("Queue length:", len(self.items))  # Print queue length for debugging
            print("Thread ID:", threading.get_ident())  # Print thread ID for debugging
        return len(self.items) == 0
    
    def enqueue(self, item):
        print("enqueue")
        self.items.append(item)

    def dequeue(self):
        print("dequeue")
        if self.items:
            item = self.items.pop(0)
            print("Queue length:", len(self.items))  # Print queue length for debugging
            print("Thread ID:", threading.get_ident())  # Print thread ID for debugging
            return item

    def peek(self):
        print("peek")
        if not self.is_empty():
            return self.items[0]

    def size(self):
        print("size")
        return len(self.items)

class MainApp(App):
    def build(self):
        self.client = MongoClient(TOKEN)
        self.db = self.client['minecraft_worlds']
        self.users = self.db.users
        return LoginScreen()

if __name__ == '__main__':
    app = MainApp()
    app.run()
