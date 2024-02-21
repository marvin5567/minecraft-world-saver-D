# operating system imports
import os
import time
import json
import shutil
import hashlib
import tempfile
import threading
from threading import Thread
from colorama import init, Fore

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
from kivy.properties import StringProperty, NumericProperty

from tkinter import Tk
from tkinter import filedialog


TOKEN = 'mongodb+srv://karimabouelnour2006:Dwad2O3dnTWp9KaZ@minecraftworldsaver.wefidgi.mongodb.net/?retryWrites=true&w=majority'

# load KV file
Builder.load_file("worldsaver.kv")

def printf(output_type, source, message):
    """
    easy print function
    
    args:
        output_type (str): type of output (e.g., INFO, ERROR).
        source (str): source of the output.
        message (str): message to be printed.
    """
    output_color = {
        "INFO": Fore.GREEN,
        "ERROR": Fore.RED,
        "WARNING": Fore.YELLOW,
    }.get(output_type, Fore.RESET)  # default color is RESET if output_type is not recognized

    formatted_output = f"[{output_color}{output_type}{Fore.RESET}] [{source}] {message}"
    print(formatted_output)

class HomePage(BoxLayout):
    def __init__(self, **kwargs):
        super(HomePage, self).__init__(**kwargs)
        self.defaultDir = r"C:\Users\Owner\AppData\Roaming\.minecraft\saves"
        self.currentUserId = self.readUserID()  # to be set after login
        self.upload_queue = Queue()
        self.upload_thread = Thread(target=self.process_upload_queue)
        self.upload_thread.daemon = True
        self.upload_thread.start()

    def readUserID(self):
            try:
                with open("currentUserId.txt", "r") as file:
                    return file.read().strip()
            except FileNotFoundError:
                return None

    def selectDirectory(self):
        root = Tk()
        root.withdraw()

        directory = filedialog.askdirectory(initialdir=self.defaultDir, title="Select Minecraft Worlds Directory")
        root.destroy()

        if directory:
            printf("INFO","HomePage.selectDirectory",f"Selected directory: {directory}")
            self.defaultDir = directory
            self.displayWorlds()
        else:
            printf("WARNING","HomePage.selectDirectory","No directory selected")

    def logoutUser(self):
        # delete user ID file when logging out
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
                # if queue is empty, wait for some time before checking again
                time.sleep(1)

    def displayWorlds(self):
        # accessing the worldLayout from the kv file
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
        printf("INFO","HomePage.uploadWorld",f"Uploading world: '{worldName}'")
        printf("INFO","HomePage.uploadWorld",f"Size: {len(worldData) * 0.000001} MB")

        try:
            # create a GridFS object
            fs = GridFS(app.db, collection='worlds_fs')

            # upload the world data to GridFS
            file_id = fs.put(worldData, filename=worldName)

            # store metadata in the worlds collection
            app.db.worlds.insert_one({'name': worldName, 'file_id': file_id, 'user_id': currentUserId})
            
            printf("INFO","HomePage.uploadWorld",f"World '{worldName}' uploaded successfully.")
            
            popup = Popup(title='World', content=Label(text='World Uploaded Succesfully!'),
                              size_hint=(None, None), size=(400, 400))
            popup.open()

        except Exception as e:
            printf("ERROR","HomePage.uploadWorld",f"Error uploading world to GridFS: {e}")
            
        self.displayWorlds()

    def uploadWorldButton(self, worldName):
        worldPath = os.path.join(self.defaultDir, worldName)

        print("Enqueuing world:", worldName)
        self.upload_queue.enqueue((worldName, worldPath))  # enqueue world information

        print("packing sqeuence initiated")
        try:
            # make a temp directory
            tempDir = tempfile.mkdtemp()
            printf("INFO","HomePage.uploadWorld","packing p1 done")

            # create a zip archive of the world directory
            tempZipPath = os.path.join(tempDir, worldName + '.zip')
            printf("INFO","HomePage.uploadWorld","packing p2 done")

            shutil.make_archive(tempZipPath[:-4], 'zip', worldPath)
            printf("INFO","HomePage.uploadWorld","packing p3 done")

            # read the zip file as binary data
            with open(tempZipPath, 'rb') as zip_file:
                zipData = zip_file.read()
            printf("INFO","HomePage.uploadWorld","packing p4 done")

            printf("INFO","HomePage.uploadWorld","Initiating upload sequence")
            self.uploadWorld(worldName, zipData, self.currentUserId)
        except FileNotFoundError:
            printf("ERROR","HomePage.uploadWorld",f"World file not found at '{worldPath}'")
        except PermissionError:
            printf("ERROR","HomePage.uploadWorld",f"Permission denied reading world file '{worldPath}'")
        except Exception as e:
            printf("ERROR","HomePage.uploadWorld",f"Error reading/world file: {e}")
        finally:
            # remove the temporary directory
            shutil.rmtree(tempDir, ignore_errors=True)

    def loadUploadedWorld(self, worldName):
        try:
            # retrieve the uploaded world data from MongoDB
            worldData = app.db.worlds.find_one({'name': worldName, 'user_id': self.currentUserId})

            if worldData:
                world_details_screen = WorldDetailsScreen(worldName=worldName)  # pass worldName argument
                world_details_screen.worldData = worldData  # set worldData as an attribute

                # clear existing widgets and add the new world details screen
                app.root.clear_widgets()
                app.root.add_widget(world_details_screen)
            else:
                printf("ERROR","HomePage.loadUploadedWorld",f"Uploaded world data not found for '{worldName}'")
        except Exception as e:
            printf("ERROR","Homepage.loadUploadedWorld",f"Error loading uploaded world: {e}")

    def switchToSettings(self):
        App.get_running_app().root.clear_widgets()
        App.get_running_app().root.add_widget(SettingsScreen())

class WorldDetailsScreen(BoxLayout):
    worldName = StringProperty("")  # add worldName attribute

    def __init__(self, **kwargs):
        super(WorldDetailsScreen, self).__init__(**kwargs)
        self.worldName = kwargs.get('worldName', '')  # set worldName if provided
        self.currentUserId = self.readUserID()

    def readUserID(self):
        try:
            with open("currentUserId.txt", "r") as file:
                return file.read().strip()
        except FileNotFoundError:
            return None

    def downloadWorld(self, worldData, worldName):
        try:
            # create a temporary directory
            tempDir = tempfile.mkdtemp()

            # retrieve the file_id from the MongoDB document
            file_id = worldData['file_id']

            # use GridFS to retrieve the file data by its ObjectId
            fs = GridFS(app.db, collection='worlds_fs')
            file_data = fs.get(ObjectId(file_id)).read()

            # create a zip file with the world data
            tempZipPath = os.path.join(tempDir, f"{worldName}.zip")
            with open(tempZipPath, 'wb') as zip_file:
                zip_file.write(file_data)

            # specify the target directory for downloading (adjust as needed)
            downloadDir = SettingsScreen.loadDownladDir()

            # copy the zip file to the target directory
            shutil.copy(tempZipPath, os.path.join(downloadDir, f"{worldName}.zip"))

            printf("INFO","WorldDetailsScreen.downloadWorld",f"World '{worldName}' downloaded successfully to {downloadDir}")
            popup = Popup(title='World', content=Label(text='World Downloaded Succesfully!'),
                              size_hint=(None, None), size=(400, 400))
            popup.open()

            App.get_running_app().root.clear_widgets()
            App.get_running_app().root.add_widget(HomePage())

        except Exception as e:
            printf("ERROR","WorldDetailsScreen.downloadWorld",f"Error downloading world: {e}")

        finally:
            # remove the temporary directory
            shutil.rmtree(tempDir, ignore_errors=True)

    def deleteWorld(self, worldName):
        printf("INFO","WorldDetailsScreen.deleteWorld",f"Deleting world '{self.worldName}'...")
        try:
            # retrieve the world document from MongoDB
            worldData = app.db.worlds.find_one({'name': worldName, 'user_id': self.currentUserId})

            if worldData:
                # retrieve the file_id from the world document
                file_id = worldData['file_id']

                # create a GridFS object
                fs = GridFS(app.db, collection='worlds_fs')

                # delete the chunks and file document associated with the file_id
                fs.delete(ObjectId(file_id))

                # delete the world from MongoDB
                app.db.worlds.delete_one({'name': worldName, 'user_id': self.currentUserId})

                printf("INFO","WorldDetailsScreen.deleteWorld",f"World '{worldName}' deleted successfully")
                self.show_popup(f"World '{worldName}' deleted successfully!")

                popup = Popup(title='World', content=Label(text='World Succesfully Deleted'),
                              size_hint=(None, None), size=(400, 400))
                popup.open()
                # refresh the UI after deleting the world
                app.root.clear_widgets()
                app.root.add_widget(HomePage(currentUserId=self.currentUserId))

            else:
                printf("ERROR","WorldDetailsScreen.deleteWorld",f"World data not found for '{worldName}'")

        except Exception as e:
            printf("ERROR","WorldDetailsScreen.deleteWorld",f"Error deleting world: {e}")

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

        # hash the password
        hashedPassword = hashlib.sha256(password.encode()).hexdigest()

        # check if the user exists in the database using the hashed password
        userExists = app.db.users.find_one({'username': user, 'password': hashedPassword})

        if userExists:

            # save user ID to a file
            with open("currentUserId.txt", "w") as file:
                file.write(str(userExists['_id']))

            # switch pages
            App.get_running_app().root.clear_widgets()
            App.get_running_app().root.add_widget(HomePage())

        else:
            # if it doesn't exist, display an error message
            popup = Popup(title='Invalid Login', content=Label(text='Invalid username or password'),
                          size_hint=(None, None), size=(400, 400))
            popup.open()

    def switchToSignupScreen(self):
        App.get_running_app().root.clear_widgets()
        App.get_running_app().root.add_widget(SignUpScreen())
        
class SignUpScreen(BoxLayout):
    def __init__(self, **kwargs):
        super(SignUpScreen, self).__init__(**kwargs)

    def add_user(self):
        user = self.ids.username.text
        password = self.ids.password.text
        confirmPassword = self.ids.confirmPassword.text

        if user and password and confirmPassword:
            # check if the username is already taken
            existing_user = app.db.users.find_one({'username': user})
            if existing_user:
                popup = Popup(title='Sign Up Error', content=Label(text='Username already taken'),
                              size_hint=(None, None), size=(400, 400))
                popup.open()
                return

            if password == confirmPassword:
                # hash password
                hashedPassword = hashlib.sha256(password.encode()).hexdigest()

                # add new user to the database
                app.db.users.insert_one({'username': user, 'password': hashedPassword, 'age':'', 'name':''})
                session = app.db.users.find_one({'username': user, 'password': hashedPassword})

                with open("currentUserId.txt", "w") as file:
                    file.write(str(session['_id']))

                printf("INFO","SignUp.addUser","Account Creation Successful")
                App.get_running_app().root.clear_widgets()
                App.get_running_app().root.add_widget(HomePage())
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

class SettingsScreen(Screen):
    themeColor = StringProperty()
    defaultDownloadDir = ''

    def selectDirectory(self):
        root = Tk()
        root.withdraw()
        directory = filedialog.askdirectory(initialdir=self.defaultDownloadDir, title="Select Download Directory")
        root.destroy()

        if directory:
            printf("INFO","HomePage.selectDirectory",f"Selected directory: {directory}")
            self.defaultDownloadDir = directory
        else:
            printf("WARNING","HomePage.selectDirectory","No directory selected")

    def saveChanges(self):
        # write data to JSON file
        if self.ids.theme_color_input.text != '':

            if not isinstance(self.ids.theme_color_input.text, str) or len(self.ids.theme_color_input.text) != 7 or not all(c in '0123456789abcdefABCDEF' for c in self.ids.theme_color_input.text[1:]):
                popup = Popup(title='Parsing Error', content=Label(text='Invalid hex code format'),
                              size_hint=(None, None), size=(400, 400))
                popup.open()
            
            else:
                with open("settings.json", "r") as f:
                    settings_data = json.load(f)

                settings_data["themeColor"] = self.ids.theme_color_input.text

                with open("settings.json", "w") as f:
                    json.dump(settings_data, f, indent=4)
        else:
            pass

        if self.defaultDownloadDir != '':
            with open("settings.json", "r") as f:
                settings_data = json.load(f)

            settings_data["defaultDownloadsDirectory"] = self.defaultDownloadDir

            with open("settings.json", "w") as f:
                json.dump(settings_data, f, indent=4)
        else:
            pass

        popup = Popup(title='Settings', content=Label(text='Changes succesfully changed!'),
                              size_hint=(None, None), size=(400, 400))
        popup.open()
        App.get_running_app().root.clear_widgets()
        App.get_running_app().root.add_widget(HomePage())

    def loadThemeColor(*self):

        with open('settings.json', 'r') as file:
            data = json.load(file)
            printf("INFO","Settings.loadThemeColor",data['themeColor'])
        return data['themeColor']
    
    def loadDownladDir(*self):
        with open('settings.json', 'r') as file:
            data = json.load(file)
            printf("INFO","Settings.loadDownladDir",data['defaultDownloadsDirectory'])
        return data['defaultDownloadsDirectory']
    
    def goBack(self):
        App.get_running_app().root.clear_widgets()
        App.get_running_app().root.add_widget(HomePage())

    def on_enter(self, *args):
        self.loadSettings()

class ColoredBoxLayout(BoxLayout):
    def loadThemeColor(self):
            with open('settings.json', 'r') as file:
                data = json.load(file)
        
            def hex_to_rgb(hex_color):
                if not isinstance(hex_color, str) or len(hex_color) != 7 or not all(c in '0123456789abcdefABCDEF' for c in hex_color[1:]):
                    raise ValueError(f"'{hex_color}' is not a valid hex color code")

                hex_color = hex_color.lstrip("#")
                return list(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
            
            color = hex_to_rgb(data['themeColor'])
            kivycolour = []
            
            for i in range(len(color)):
                kivycolour.append(color[i]/255)
            kivycolour.append('1')

            return kivycolour
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(self.loadThemeColor())
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
            printf("INFO","Queue.is_empty","is empty active")
            printf("INFO","Queue.is_empty",f'"Queue length:" {len(self.items)}')
            printf("INFO","Queue.is_empty",f'"Thread ID:" {threading.get_ident()}')
        return len(self.items) == 0
    
    def enqueue(self, item):
        printf("INFO","Queue.enqueue","enqueue")
        self.items.append(item)

    def dequeue(self):
        printf("INFO","Queue.dequeue","dequeue")
        if self.items:
            item = self.items.pop(0)
            printf("INFO","Queue.dequeue",f'"Queue length:" {len(self.items)}') 
            printf("INFO","Queue.dequeue",f'"Thread ID:" {threading.get_ident()}') 
            return item

    def peek(self):
        printf("INFO","Queue.peek","peek")
        if not self.is_empty():
            return self.items[0]

    def size(self):
        printf("INFO","size","size")
        return len(self.items)

class MainApp(App):

    def build(self):
        self.config = self.load_config()
        self.client = MongoClient(TOKEN)
        self.db = self.client['minecraft_worlds']
        self.users = self.db.users
        return LoginScreen()

if __name__ == '__main__':
    app = MainApp()
    app.run()
