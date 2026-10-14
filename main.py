import random
import datetime
import re
from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
from kivy.core.window import Window
from kivy.uix.slider import Slider
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.checkbox import CheckBox
from kivy.properties import ObjectProperty
from kivy.uix.dropdown import DropDown
from kivy.uix.scrollview import ScrollView
from kivy.animation import Animation
from kivy.uix.popup import Popup
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.graphics import Rectangle
from kivy.core.image import Image as CoreImage
import sqlite3


class NavigationMenu(Popup): # menu pour naviguer d'un écran à l'autre
    def __init__(self, sm, **kwargs):
        super().__init__(**kwargs)
        self.title= 'Menu'
        self.sm = sm

        self.P = FloatLayout()
        self.P.orientation = 'vertical'  # Menu vertical
        self.P.size_hint = (0.4, 1)
        self.P.x = -self.width  # Position initiale (hors de l'écran à gauche)
        
        # Bouton pour retourner sur l'écran où on tire les mots
        self.P.HomeButton = Button(text="Tirer un mot", font_size=40, size_hint=(0.8,0.15), pos_hint={'x': 0.1, 'top':0.8})
        self.P.HomeButton.name="home"
        self.P.HomeButton.bind(on_release=self.on_option_select)
        self.P.add_widget(self.P.HomeButton)

        # Bouton pour retourner sur l'écran du menu des listes
        self.P.DictMenuButton = Button(text="Menu des listes", size_hint=(0.8,0.15), pos_hint={'x': 0.1, 'top':0.6})
        self.P.DictMenuButton.name="dictMenu"
        self.P.DictMenuButton.bind(on_release=self.on_option_select)
        self.P.add_widget(self.P.DictMenuButton)

        # Bouton pour retourner sur l'écran du menu des listes
        self.P.JournalButton = Button(text="Journal", size_hint=(0.8,0.15), pos_hint={'x': 0.1, 'top':0.4})
        self.P.JournalButton.name="journal"
        self.P.JournalButton.bind(on_release=self.on_option_select)
        self.P.add_widget(self.P.JournalButton)
        
        self.content= self.P
        self.size_hint= (0.4,1)
        self.pos_hint= {"x":0}

    def on_option_select(self, button):
        if self.sm.current != button.name :
            if button.name in ["home", "journal"] :
                self.sm.get_screen(button.name).before_enter()
            self.sm.current = button.name
            self.close_Menu()
        else :
            self.close_Menu()

    def show_Menu(self, instance) :
        self.open()
        Clock.schedule_once(self.update_position, 0)

    def update_position(self, dt):
        self.pos_hint = {"x": 0}
        self.x = 0
        

    def close_Menu(self) :
        self.dismiss()






class ImageButton(Button):
    def __init__(self, image_source, **kwargs):
        super().__init__(**kwargs)
        self.image_source = image_source
        self.background_color = (0.35, 0.35, 0.35, 1) 
        self.background_normal = '' 
        self.img = None
        self.aspect_ratio = None
        self.rect = None
        self.linked = False

        # Charger l'image
        if image_source :
            self.img = CoreImage(image_source)

            if not self.img.texture:
                raise ValueError(f"Erreur de chargement de l'image : {image_source}")

            self.aspect_ratio = self.img.width / self.img.height
            self.rect = None

            # Mise à jour au démarrage et sur redimensionnement
            self.background_color = (0, 0, 0, 0) 
            self.bind(size=self.update_background, pos=self.update_background)
            self.linked = True
            self.update_background()

    def change_image(self, new_image_source) :
        if not self.linked :
            self.background_color = (0, 0, 0, 0) 
            self.bind(size=self.update_background, pos=self.update_background)
            self.linked = True
        self.img = CoreImage(new_image_source)
        self.aspect_ratio = self.img.width / self.img.height
        self.update_background()

    def update_background(self, *args):
        if self.width == 0 or self.height == 0:
            return

        # Calculer la taille ajustée de l'image
        button_width, button_height = self.size
        if button_width  > button_height :
            new_img_height = 0.95*button_height
            new_img_width = new_img_height * self.aspect_ratio
        else:
            new_img_width = 0.95*button_width
            new_img_height = new_img_width / self.aspect_ratio

        # Calculer la position centrée
        x_pos = self.x + (button_width - new_img_width) / 2
        y_pos = self.y + (button_height - new_img_height) / 2

        # Dessiner l'image dans le Canvas
        with self.canvas.after:
            self.canvas.after.clear()  # Effacer l'ancienne image
            self.rect = Rectangle(texture=self.img.texture, pos=(x_pos, y_pos), size=(new_img_width, new_img_height))

        self.canvas.ask_update()  # Forcer l'affichage





class HomeScreen(Screen) :
    def __init__(self, sm, conn1, conn2, **kw):
        super().__init__(**kw)
        self.conn1 = conn1
        self.conn2 = conn2
        self.menu = NavigationMenu(sm=sm) # c'est le menu pour naviguer d'un écran à l'autre
        # Window.bind(on_resize=self.menu.update_menu_position)
        self.words = [] # stocke les mots de la liste sélectionnée
        self.gender_bool = "" # détermine si oui ou non le dictionnaire sélectionné a la caractéristique "genre"
        self.genders = [] # stocke (s'il y a) les genres de la liste sélectionnée
        self.proportions = [] #stocke les proportions de la liste séléctionnée
        self.dictNames = self.conn1.execute_select_all("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name ASC") # stocke les noms des listes pour ne pas charger plusieurs fois leur nom dans le dropdown dictList

        self.layout = FloatLayout()
        self.layout.add_widget(Label(text="Choix de la liste", font_size=40, size_hint=(0.9,0.15), pos_hint={'x': 0.05, 'top':1}))
        dictButtonBox = BoxLayout(orientation='vertical', size_hint=(1,0.1), pos_hint={'top':0.85})
        
        self.dictButton = Button(text='', size_hint=(0.8,0.1), pos_hint={'x': 0.1, 'top':1})
        dictButtonBox.add_widget(self.dictButton)
        
        self.dictList = DropDown()
        self.dictButton.bind(on_release=self.dictList.open)
        self.dictList.bind(on_select=self.pick_dictionary)
        
        MenuButton = ImageButton("images\menu-deroulant.png", size_hint=(0.1,0.1), pos_hint={'top':1})
        MenuButton.bind(on_release=self.menu.show_Menu)

        self.showWord = Label(text="", font_size=80, size_hint=(0.9,0.5), pos_hint={'x': 0.05, 'top':0.75})
        self.refresh_dictList(self.dictNames)
        
        pickingButton = Button(text='Tirer au hasard', font_size=40, size_hint=(0.8,0.15), pos_hint={'x': 0.1, 'top':0.25})
        pickingButton.bind(on_release=self.pick_random_word)

        self.layout.add_widget(dictButtonBox)
        self.layout.add_widget(MenuButton)
        self.layout.add_widget(self.showWord)
        self.layout.add_widget(pickingButton)
        self.add_widget(self.layout)


    def before_enter(self):
        # On réintilise le menu déroulant et les variables qui permettent de sélectionner
        self.words = []
        self.genders = [] 
        self.proportions = [] 
        self.dictButton.text = ""

        currentDictNames = self.conn1.execute_select_all("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name ASC")
        newDictNames = [name for name in currentDictNames if name not in self.dictNames]
        deletedDictNames = [clear_string(str(name)) for name in self.dictNames if name not in currentDictNames]

        self.dictNames = currentDictNames
        self.refresh_dictList(newDictNames)

        if deletedDictNames:
            buttonsToDelete = [child for child in self.dictList.children[0].children if child.text in deletedDictNames]
            for button in buttonsToDelete :
                self.dictList.remove_widget(button)
            del buttonsToDelete

    def refresh_dictList(self, names):
        if names != [] :
            for name in names :
                btn = Button(text=clear_string(str(name)), font_size=30, size_hint_y=None, height=40)
                btn.bind(on_release=lambda btn: self.dictList.select(btn.text))
                self.dictList.add_widget(btn)

        if self.dictNames:
            if self.words == [] :
                self.showWord.text = "Il n'y a pas de mot dans la liste"
            else:
                self.showWord.text = ""
        else:
            self.showWord.text = "Il n'y a pas encore de liste"

    def pick_random_word(self, instance):
        if self.words != [] and self.proportions != [] :
            index = random.choices(range(len(self.words)), weights=self.proportions, k=1)[0] # On choisit un indice aléatoire (pour pouvoir tirer le bon genre ensuite)
            text = self.words[index]
            text ="".join(text) # on le transforme en une string
            add_modified_words(self.dictButton.text, text)
            self.showWord.text = text

            increase_occurence = f'''
                UPDATE {self.dictButton.text}
                SET occurence = occurence + 1
                WHERE name =?;
            '''
            self.conn1.execute_modify(increase_occurence, (text,))
            date = datetime.datetime.now().strftime("%Y-%m-%d")
            query = f"SELECT name FROM {self.dictButton.text} WHERE name=? AND date=?"
            result = self.conn2.execute_select_one(query, (text,date))
            
            if result:
                increase_occurence = f'''
                    UPDATE {self.dictButton.text}
                    SET occurence = occurence + 1
                    WHERE name =? AND date=?;
                '''
                self.conn2.execute_modify(increase_occurence, (text,date))
            else:
                if self.gender_bool :
                    gender = self.genders[index]
                    create_word = f'''
                        INSERT INTO {self.dictButton.text} (name, gender, date, occurence)
                        VALUES (?, ?, ?, 1)
                        '''
                    self.conn2.execute_modify(create_word, (text,gender,date))
                else : 
                    create_word = f'''
                        INSERT INTO {self.dictButton.text} (name, date, occurence)
                        VALUES (?, ?, 1)
                        '''
                    self.conn2.execute_modify(create_word, (text,date))
        else : 
            self.showWord.text = "Aucun mot n'a pu être tiré"

    def pick_dictionary(self, instance, name):
        self.words = []
        self.genders = [] 
        self.proportions = [] 
        self.dictButton.text = name

        columns = self.conn1.execute_select_all(f"PRAGMA table_info({name});")
        column_names = [column[1] for column in columns] 
        if 'gender' in column_names:
            self.gender_bool = True
        else:
            self.gender_bool = False

        query = f'SELECT * FROM {name}'
        words_info = self.conn1.execute_select_all(query)

        if words_info :
            if self.gender_bool :
                for word_info in words_info :
                    self.words.append(word_info[0])
                    self.genders.append(word_info[1])
                    self.proportions.append(word_info[2])
            else :
                for word_info in words_info :
                    self.words.append(word_info[0])
                    self.proportions.append(word_info[1])
            self.showWord.text = ""
        else : 
            self.showWord.text = "Il n'y a pas de mot dans la liste"

            




class DictionariesMenu(Screen) :
    def __init__(self, sm, conn1, conn2,**kw):
        super().__init__(**kw)
        self.conn1 = conn1
        self.conn2 = conn2
        self.sorting_type = "Trier A-Z"

        # Layout de la fenêtre
        self.layout = FloatLayout()

        # Popup création d'une nouvelle liste
        self.errorPopup = Popup(title = "Erreur", content=Label(text=f"Ce nom est déjà pris"), size_hint=(0.4,0.3), pos_hint={'x':0.3, 'top':0.65})
        P = FloatLayout()
        P.add_widget(Label(text="Entrez le nom de la nouvelle liste : ", size_hint=(0.8, 0.1), pos_hint={"x":0.1, "top":0.9}))
        self.input = TextInput(size_hint=(0.8, 0.25), pos_hint={"x":0.1, "top":0.70}, multiline=False)
        P.add_widget(self.input)
        P.add_widget(Label(text="Genre", size_hint=(0.3, 0.15), pos_hint={"x":0.1, "top":0.325}))
        self.gender_checkbox = CheckBox(active = True, size_hint=(0.15, 0.15), pos_hint={"x":0.35, "top":0.325})
        P.add_widget(self.gender_checkbox)
        validate = Button(text="Valider", size_hint=(0.3,0.2), pos_hint={'x':0.60, 'top':0.325})
        validate.bind(on_release=self.newDictionary)
        P.add_widget(validate)
        self.createPopup = Popup(title = "Créer une nouvelle liste", content=P, size_hint=(0.4,0.3), pos_hint={'x':0.3, 'top':0.65})

        # Bouton du menu
        self.menu = NavigationMenu(sm=sm)
        MenuButton = ImageButton("images\menu-deroulant.png", size_hint=(0.1,0.1), pos_hint={'top':1})
        MenuButton.bind(on_release=self.menu.show_Menu)

        CreateDict = Button(text="Ajouter une liste", font_size=40, size_hint=(0.8,0.1), pos_hint={'x':0.1,'top':1})
        CreateDict.bind(on_release=self.showCreatePopup)

        # Bouton unique pour alterner entre tri A-Z et Z-A
        self.sort_button = ImageButton("images\ordre alphabetique.png", size_hint=(0.1,0.1), pos_hint={'x':0.9,'top':1})
        self.sort_button.background_color = (0.35, 0.35, 0.35, 1) 
        self.sort_button.bind(on_release=self.toggle_sort)
        
        self.layout.add_widget(self.sort_button)
        self.layout.add_widget(CreateDict)
        self.layout.add_widget(MenuButton)

        # Layout de la liste des listes
        self.dictNames = self.conn1.execute_select_all("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name ASC")
        self.dictListLayout = GridLayout(cols=1, size_hint_y=None, padding=[0, 10])
        self.dictListLayout.pos_hint = {'top': 0.9}  # Ancrer le GridLayout en haut de la fenêtre

        self.button_height = Window.height * 0.1  # 1/10 de la hauteur de la fenêtre
        self.button_width = Window.width * 0.9   # 90% de la largeur de la fenêtre

        # Créer un ScrollView pour permettre le défilement si besoin
        self.scroll_view = ScrollView(size_hint=(1, None), size=(Window.width, Window.height), pos_hint={'top':0.9})
        
        if self.dictNames != [] :
            for name in self.dictNames:  
                name = name[0]
                # name = clear_string(str(name))
                self.addDictionaryButton(name)
        
        # Redimensionner le scrollview et la dictList pour que ça puisse scroll.
        self.scroll_view.add_widget(self.dictListLayout)

        # Connecter le redimensionnement de la fenêtre pour ajuster les tailles
        Window.bind(on_resize=self.on_resize)
        self.layout.add_widget(self.scroll_view)
        self.add_widget(self.layout)

    def on_enter(self):
        Clock.schedule_once(lambda dt: self.on_resize(Window, Window.width, Window.height), 0)

    def remove_buttons(self, name) :
        self.dictListLayout.remove_widget(find_layout_by_button_text(self.dictListLayout, str(name)))

        # On le supprime de la base de données
        delete_table = f"DROP TABLE IF EXISTS {name}"
        self.conn1.execute_modify(delete_table)
        self.conn2.execute_modify(delete_table)

        Clock.schedule_once(lambda dt: self.on_resize(Window, Window.width, Window.height), 0)

    def toggle_sort(self, instance):
        """Alterner entre tri A-Z et Z-A sans supprimer les widgets"""
        reverse = self.sorting_type == "Trier Z-A"
        self.sorting_type = "Trier A-Z" if reverse else "Trier Z-A"
        self.sort_button.change_image("images\ordre alphabetique.png") if reverse else self.sort_button.change_image("images\ordre anti alphabetique.png")
        self.sort_button.background_color = (0.35, 0.35, 0.35, 1) 

        # Réorganiser les enfants dans GridLayout
        self.dictListLayout.children[:] = sorted(self.dictListLayout.children,  key=lambda btns: btns.children[0].text, reverse=reverse)

    def on_resize(self, window, width=Window.width, height=Window.height):
        """Met à jour la taille des boutons et du GridLayout lors du redimensionnement de la fenêtre."""
        self.button_height = height * 0.1  # Recalcule la hauteur de chaque bouton (1/10 de la hauteur de la fenêtre)
        self.button_width = width    # Recalcule la largeur de chaque bouton 

        # Recalcule la taille des boutons et les redimensionne
        for button in self.dictListLayout.children:
            button.size = (self.button_width, self.button_height)

            for child in button.children:  # Parcours les widgets à l'intérieur des GridLayout
                if isinstance(child, Button):
                    child.size = (self.button_width * 0.9, self.button_height)  # Bouton principal (90% de la largeur)
                elif isinstance(child, ImageButton):
                    child.size = (self.button_width * 0.1, self.button_height)  # Image bouton (10% de la largeur)


        # Recalcule la hauteur totale du GridLayout pour qu'il occupe toute la fenêtre verticalement
        self.dictListLayout.height = len(self.dictListLayout.children) * self.button_height

        # Mettre à jour le ScrollView pour qu'il s'ajuste à la nouvelle taille
        self.scroll_view.height = height *0.9

    def showCreatePopup(self, instance):
        self.createPopup.open()
        
    def addDictionaryButton(self, name) :
        btns = GridLayout(cols=2, size=(Window.width, self.button_height))
        dict = Button(text=str(name), size_hint=(0.9, 1), pos_hint={'x':0.1})
        dict.bind(on_release=lambda x: self.go_to_modifier(name=name))
        deleteButton = ImageButton("images\supprimer.png", size_hint=(0.1, 1), pos_hint={'x':0.01, 'top':1})
        deleteButton.bind(on_release=lambda x: self.remove_buttons(name=name))
        btns.add_widget(deleteButton)
        btns.add_widget(dict)
        self.dictListLayout.add_widget(btns)

    def newDictionary(self, instance) :
        if self.input.text != "" :
            # Requête pour vérifier si la table existe dans sqlite_master
            query=f"SELECT name FROM sqlite_master WHERE type='table' AND name=?"
            
            # Récupérer les résultats
            result = self.conn1.execute_select_one(query, (self.input.text,))
            
            # Vérifier si la table existe
            if result:
                self.errorPopup.open()
            else : 
                if self.gender_checkbox.active :
                    create_table = f'''
                        CREATE TABLE IF NOT EXISTS {self.input.text} (
                            name TEXT,
                            gender TEXT,
                            proportion INTEGER,
                            occurence INTEGER
                        )
                        '''
                    self.conn1.execute_modify(create_table)
                    create_table = f'''
                        CREATE TABLE IF NOT EXISTS {self.input.text} (
                            name TEXT,
                            gender TEXT,
                            date TEXT,
                            occurence INTEGER
                        )
                        '''
                    self.conn2.execute_modify(create_table)
                    self.addDictionaryButton(self.input.text)
                else:
                    create_table = f'''
                        CREATE TABLE IF NOT EXISTS {self.input.text} (
                            name TEXT,
                            proportion INTEGER,
                            occurence INTEGER
                        )
                        '''
                    self.conn1.execute_modify(create_table)
                    create_table = f'''
                        CREATE TABLE IF NOT EXISTS {self.input.text} (
                            name TEXT,
                            date TEXT,
                            occurence INTEGER
                        )
                        '''
                    self.conn2.execute_modify(create_table)
                    self.addDictionaryButton(self.input.text)
                
                Clock.schedule_once(lambda dt: self.on_resize(Window, Window.width, Window.height), 0)
                # Reranger dans l'ordre alphabétique
                if self.sorting_type == "Trier A-Z" :
                    self.dictListLayout.children[:] = sorted(self.dictListLayout.children, key=lambda btns: btns.children[0].text, reverse=True)
                else : 
                    self.dictListLayout.children[:] = sorted(self.dictListLayout.children, key=lambda btns: btns.children[0].text, reverse=False)
            self.createPopup.dismiss()
            self.input.text = ""
    
    def go_to_modifier(self, name):
        modifier = self.manager.get_screen('modifier')
        modifier.namee = name
        columns = self.conn1.execute_select_all(f"PRAGMA table_info({name});")
        column_names = [column[1] for column in columns] 
        if 'gender' in column_names:
            modifier.gender = True
        else:
            modifier.gender = False
        modifier.before_enter()
        self.manager.current = 'modifier'








def clear_string(string) :
    return string[2:-3]

def find_layout_by_button_text(parent_widget, button_text):
        # Parcours tous les enfants du parent
        for child in parent_widget.children:
            if isinstance(child, GridLayout):  # On suppose ici que ce sont des GridLayouts enfants
                # Parcours les enfants du layout
                for grandchild in child.children:
                    if isinstance(grandchild, Button) and grandchild.text == button_text:
                        return child  # Retourne le layout (BoxLayout) contenant le bouton
        return None




class DictionaryModifier(Screen) :
    def __init__(self, sm, conn1, conn2,**kw):
        super().__init__(**kw)
        self.namee = "" #Nom de la liste dans laquelle on est
        self.gender = False
        self.gender_previous = self.gender
        self.previous_namee = ""
        self.conn1 = conn1
        self.conn2 = conn2
        self.sorting_type = "ordre alphabetique"

        # Layout de la fenêtre
        self.layout = FloatLayout()


        # Popup d'erreur
        self.errorPopup = Popup(title = "Erreur", content=Label(text=f"Ce mot est déjà dans la liste"), size_hint=(0.4,0.3), pos_hint={'x':0.3, 'top':0.65})
        # Ajouter un nouveau mot
        self.P = FloatLayout()
        self.P.add_widget(Label(text="Entrez le nouveau mot de la liste : ", size_hint=(0.8, 0.1), pos_hint={"x":0.1, "top":0.9}))
        self.input = TextInput(size_hint=(0.8, 0.20), pos_hint={"x":0.1, "top":0.70}, multiline=False)
        self.P.add_widget(self.input)

        # Checkbox genre que l'on insère ou non en fonction de self.gender 
        self.gender_layout = BoxLayout(orientation='horizontal', spacing=10, padding=10, size_hint=(0.8, 0.2), pos_hint={"x":0.1, "top":0.45})
        self.male_checkbox = CheckBox(active = False, group='gender')
        self.female_checkbox = CheckBox(active = True, group='gender')
        self.gender_layout.add_widget(Label(text='H'))
        self.gender_layout.add_widget(self.male_checkbox)
        self.gender_layout.add_widget(Label(text='F'))
        self.gender_layout.add_widget(self.female_checkbox)

        validate = Button(text="Valider", size_hint=(0.8,0.15), pos_hint={'x':0.1, 'top':0.2})
        validate.bind(on_release=self.new_word)
        self.P.add_widget(validate)
        self.createPopup = Popup(title = "Ajouter un nouveau mot", content=self.P, size_hint=(0.7,0.7), pos_hint={'x':0.15, 'top':0.85})

        addButton = Button(text="Ajouter un mot", size_hint=(0.8,0.1), pos_hint={'x':0.1, 'top':1})
        addButton.bind(on_release=self.createPopup.open)
        self.layout.add_widget(addButton)

        # Bouton du menu
        self.menu = NavigationMenu(sm=sm)
        MenuButton = ImageButton("images\menu-deroulant.png", size_hint=(0.1,0.1), pos_hint={'top':1})
        MenuButton.bind(on_release=self.menu.show_Menu)
        self.layout.add_widget(MenuButton)

        # Trier
        sort_button_box = BoxLayout(orientation='vertical', size_hint=(0.1,0.1), pos_hint={'x':0.9, 'top':1})
        
        self.sort_button = ImageButton(None, text="Trier", size_hint=(1,1))
        sort_button_box.add_widget(self.sort_button)
        self.layout.add_widget(sort_button_box)

        self.sortingList = DropDown()
        self.sort_button.bind(on_release=self.sortingList.open)

        self.alphabetical_button = ImageButton("images\ordre alphabetique.png", size_hint_y=None, height=Window.height*0.08)
        self.alphabetical_button.background_color = (0.35, 0.35, 0.35, 1) 
        self.anti_alphabetical_button = ImageButton("images\ordre anti alphabetique.png", size_hint_y=None, height=Window.height*0.08)
        self.anti_alphabetical_button.background_color = (0.35, 0.35, 0.35, 1) 
        self.desc_occurences_button = ImageButton("images\occurence decroissant.png", size_hint_y=None, height=Window.height*0.08)
        self.desc_occurences_button.background_color = (0.35, 0.35, 0.35, 1) 
        self.asc_occurences_button = ImageButton("images\occurence croissant.png", size_hint_y=None, height=Window.height*0.08)
        self.asc_occurences_button.background_color = (0.35, 0.35, 0.35, 1) 
    
        self.sortingList.add_widget(self.alphabetical_button)
        self.sortingList.add_widget(self.anti_alphabetical_button)
        self.sortingList.add_widget(self.desc_occurences_button)
        self.sortingList.add_widget(self.asc_occurences_button)
        self.sortingList.bind(on_select=self.change_sorting_type)

        self.alphabetical_button.bind(on_release=lambda btn: self.sortingList.select(["ordre alphabetique", btn.img]))
        self.anti_alphabetical_button.bind(on_release=lambda btn: self.sortingList.select(["ordre anti alphabetique", btn.img]))
        self.desc_occurences_button.bind(on_release=lambda btn: self.sortingList.select(["occurences decroissantes", btn.img]))
        self.asc_occurences_button.bind(on_release=lambda btn: self.sortingList.select(["occurences croissantes", btn.img]))

        # Label pour savoir qu'est-ce que quoi 
        self.layout.add_widget(Label(text="proportion", size_hint={0.5,0.05}, pos_hint={'x':0.5, 'top':0.9}))
        self.layout.add_widget(Label(text="occurences", size_hint={0.2,0.05}, pos_hint={'x':0.35, 'top':0.9}))

        # Layout qui sera dans le scroll view
        self.words = []
        self.wordsLayout = GridLayout(cols=1, size_hint_y=None, padding=[0, 10])
        self.wordsLayout.pos_hint = {'top': 1}  # Ancrer le GridLayout en haut de la fenêtre


        # Créer un ScrollView pour permettre le défilement si besoin
        self.scroll_view = ScrollView(size_hint=(1, None), size=(Window.width, Window.height), pos_hint={'top':0.85})

        # Ajouts des widgets
        self.scroll_view.add_widget(self.wordsLayout)
        Window.bind(on_resize=self.on_resize)
        self.layout.add_widget(self.scroll_view)
        self.add_widget(self.layout)

    def change_sorting_type(self, instance, infos) :
        name = infos[0]
        image = infos[1]
        self.sort_button.text=""
        self.sort_button.change_image(image)
        self.sort_button.background_color = (0.35, 0.35, 0.35, 1) 
        self.sortingList.clear_widgets()
        self.sorting_type = name
        match name :
            case "ordre alphabetique" :
                self.sortingList.add_widget(self.anti_alphabetical_button)
                self.sortingList.add_widget(self.asc_occurences_button)
                self.sortingList.add_widget(self.desc_occurences_button)
            case "ordre anti alphabetique" :
                self.sortingList.add_widget(self.alphabetical_button)
                self.sortingList.add_widget(self.asc_occurences_button)
                self.sortingList.add_widget(self.desc_occurences_button)
            case "occurences croissantes" :
                self.sortingList.add_widget(self.alphabetical_button)
                self.sortingList.add_widget(self.anti_alphabetical_button)
                self.sortingList.add_widget(self.desc_occurences_button)
            case "occurences decroissantes" :
                self.sortingList.add_widget(self.alphabetical_button)
                self.sortingList.add_widget(self.anti_alphabetical_button)
                self.sortingList.add_widget(self.asc_occurences_button) 
        self.sort()

    def sort(self) :
        match self.sorting_type :
            case "ordre alphabetique" :
                self.wordsLayout.children[:] = sorted(self.wordsLayout.children, key=lambda btns: btns.children[2].text, reverse=True)
            case "ordre anti alphabetique" :
                self.wordsLayout.children[:] = sorted(self.wordsLayout.children, key=lambda btns: btns.children[2].text, reverse=False)
            case "occurences croissantes" :
                self.wordsLayout.children[:] = sorted(self.wordsLayout.children, key=lambda btns: int(btns.children[1].text), reverse=True)
            case "occurences decroissantes" :
                self.wordsLayout.children[:] = sorted(self.wordsLayout.children, key=lambda btns: int(btns.children[1].text), reverse=False)

    def before_enter(self):
        if self.namee != self.previous_namee :
            self.words = self.fetch_words()
            self.wordsLayout.clear_widgets()
            
            self.button_height = Window.height * 0.1  # 1/10 de la hauteur de la fenêtre
            self.button_width = Window.width * 0.9   # 90% de la largeur de la fenêtre

            if self.words != [] :
                for word in self.words: 
                    word = clear_string(str(word))
                    self.add_word(word)
            
            # Redimensionner le scrollview et la words(list) pour que ça puisse scroll.
            self.change_sorting_type(instance=None, infos=["ordre alphabetique", "images\ordre alphabetique.png"])
        else : # On actualise les occurences
            for i in range(len(self.wordsLayout.children)) :
                self.wordsLayout.children[i].children[1].text = str(self.conn1.execute_select_one(f"SELECT occurence FROM {self.namee} WHERE name=?", (self.wordsLayout.children[i].children[2].text,))[0])

        self.previous_namee = self.namee

        if self.gender == True and self.gender_previous == False:
            self.female_checkbox.active = True
            self.P.add_widget(self.gender_layout)
        elif self.gender == False and self.gender_previous == True:
            if self.gender_layout in self.P.children :
                self.P.remove_widget(self.gender_layout)
        self.gender_previous = self.gender

    def on_enter(self):
        Clock.schedule_once(lambda dt: self.on_resize(Window, Window.width, Window.height), 0)

    def remove_buttons(self, name) :
        add_deleted_words(self.namee, name)
        self.wordsLayout.remove_widget(find_layout_by_button_text(self.wordsLayout, str(name)))

        # On le supprime de la base de données
        delete_word = f"DELETE FROM {self.namee} WHERE name=?"
        self.conn1.execute_modify(delete_word, (name,))
        self.conn2.execute_modify(delete_word, (name,))

        Clock.schedule_once(lambda dt: self.on_resize(Window, Window.width, Window.height), 0)

    def on_resize(self, window, width=Window.width, height=Window.height):
        """Met à jour la taille des boutons et du GridLayout lors du redimensionnement de la fenêtre."""
        self.button_height = height * 0.1  # Recalcule la hauteur de chaque bouton (1/10 de la hauteur de la fenêtre)
        self.button_width = width    # Recalcule la largeur de chaque bouton (90% de la largeur de la fenêtre)

        # Recalcule la taille des boutons et les redimensionne
        for button in self.wordsLayout.children:
            button.size = (self.button_width, self.button_height)

            for child in button.children:  # Parcours les widgets à l'intérieur des GridLayout
                if isinstance(child, Button):
                    child.size = (self.button_width * 0.3, self.button_height) 
                elif isinstance(child, ImageButton):
                    child.size = (self.button_width * 0.1, self.button_height)  
                elif isinstance(child, Slider):
                    child.size = (self.button_width * 0.5, self.button_height * 0.5) 
                elif isinstance(child, Label) :
                    child.size = (self.button_width * 0.1, self.button_height)

        # Recalcule la hauteur totale du GridLayout pour qu'il occupe toute la fenêtre verticalement
        self.wordsLayout.height = len(self.wordsLayout.children) * self.button_height

        # Mettre à jour le ScrollView pour qu'il s'ajuste à la nouvelle taille
        self.scroll_view.height = height *0.85

    def add_word(self, word) :
        btns = GridLayout(cols=4, size=(Window.width, self.button_height))
        wordButton = Button(text=str(word), size_hint=(0.3, 1), pos_hint={'x':0.1})
        deleteButton = ImageButton("images\supprimer.png", size_hint=(0.1, 1), pos_hint={'top':1})
        deleteButton.bind(on_release=lambda x: self.remove_buttons(name=word))

        # Label qui indique le nombre d'occurences du mot
        occurence = self.conn1.execute_select_one(f"SELECT occurence FROM {self.namee} WHERE name=?", (str(word),))
        occurence_label = Label(text=str(occurence[0]), size_hint=(0.1, 1), pos_hint={'x':0.4})

        # Création d'un curseur allant de 0 à 5
        # Requête pour vérifier si la table existe dans sqlite_master
        proportion_query = f"SELECT proportion FROM {self.namee} WHERE name=?"
        proportion = self.conn1.execute_select_one(proportion_query, (str(word),))
        slider = Slider(min=0, max=5, value=int(proportion[0]), step=1, size_hint=(0.5, 0.5), pos_hint={'x':0.5, 'top':0.75})
        slider.bind(value=self.on_slider_value_change)

        # Ajout des éléments au layout
        btns.add_widget(deleteButton)
        btns.add_widget(wordButton)
        btns.add_widget(occurence_label)
        btns.add_widget(slider)
        self.wordsLayout.add_widget(btns)

    def on_slider_value_change(self, instance, value):
        # Trouver le bouton associé au slider
        name = instance.parent.children[2].text

        # Requête SQL pour mettre à jour la proportion
        update_query = f'''
                        UPDATE {self.namee}
                        SET proportion = ?
                        WHERE name = ?
                        '''
        self.conn1.execute_modify(update_query, (int(value), name))

    def fetch_words(self) :
        query = f"SELECT name FROM {self.namee}"
        return self.conn1.execute_select_all(query)

    def new_word(self, instance) :
        if self.input.text != "" :
        # Requête pour vérifier si la table existe dans sqlite_master
            query = f"SELECT name FROM {self.namee} WHERE name=?"
            result = self.conn1.execute_select_one(query, (self.input.text,))
            
            # Vérifier si la table existe
            if result:
                self.errorPopup.open()
            else:
                if self.gender == True :
                    word_gender = ""
                    if self.male_checkbox.active :
                        word_gender = "garçon"
                    else : 
                        word_gender = "fille"
                    create_word = f'''
                        INSERT INTO {self.namee} (name, gender, proportion, occurence)
                        VALUES (?, ?, 1, 0)
                        '''
                    self.conn1.execute_modify(create_word, (self.input.text, word_gender))
                else :
                    create_word = f'''
                        INSERT INTO {self.namee} (name, proportion, occurence)
                        VALUES (?, 1, 0)
                        '''
                    self.conn1.execute_modify(create_word, (self.input.text,))
                self.add_word(self.input.text)
                self.on_resize(window=Window)
                add_new_words(self.namee, self.input.text)
                Clock.schedule_once(lambda dt: self.on_resize(Window, Window.width, Window.height), 0)

                match self.sorting_type :
                    case "ordre alphabetique" :
                        self.wordsLayout.children[:] = sorted(self.wordsLayout.children, key=lambda btns: btns.children[2].text, reverse=True)
                    case "ordre anti alphabetique" :
                        self.wordsLayout.children[:] = sorted(self.wordsLayout.children, key=lambda btns: btns.children[2].text, reverse=False)
                    case "occurences croissantes" :
                        self.wordsLayout.children[:] = sorted(self.wordsLayout.children, key=lambda btns: int(btns.children[1].text), reverse=True)
                    case "occurences decroissantes" :
                        self.wordsLayout.children[:] = sorted(self.wordsLayout.children, key=lambda btns: int(btns.children[1].text), reverse=False)
            self.input.text = ""
            self.createPopup.dismiss()







def toggle_checkbox(instance, checkbox) :
    checkbox.active = not checkbox.active  # Change l'état de la checkbox

class StatsOptionsMenu(Popup) :
    def __init__(self, sm, conn1, conn2, **kwargs):
        super().__init__(**kwargs)
        self.conn1 = conn1
        self.conn2 = conn2
        self.title= 'Options'
        self.sm = sm
        self.has_refreshed = False # permet de ne pas activer on_enter la première fois.
        # Pop-up options d'affichages
        self.P = FloatLayout(pos_hint={'top':1})
        
        self.button_width = Window.width * 0.8   # 90% de la largeur de la fenêtre
        self.button_height = Window.height * 0.1  # 1/10 de la hauteur de la fenêtre

        self.dictNames = self.conn1.execute_select_all("SELECT name FROM sqlite_master WHERE type='table'")
        self.dictListLayout = GridLayout(cols=1, size_hint=(1,None), padding=[0, 10])
        self.dictListLayout.pos_hint = {'top': 1}  # Ancrer le GridLayout en haut de la fenêtre
        for name in self.dictNames :
            button_layout = FloatLayout(size=(self.button_width, self.button_height), pos_hint={'x':0.1, 'top':1})
            btn = Button(text=clear_string(str(name)), font_size=30, size_hint=(1, 1), pos_hint={'top':1})
            checkbox = CheckBox(active = True, size_hint=(0.1, 1), pos_hint={'top':1})

            # Relier l'événement de clic du bouton à la checkbox
            btn.bind(on_press=lambda instance, cb=checkbox: toggle_checkbox(instance, cb))

            button_layout.add_widget(btn)
            button_layout.add_widget(checkbox)
            self.dictListLayout.add_widget(button_layout)


        # Créer un ScrollView pour permettre le défilement si besoin + on crée toutes les liaisons
        self.scroll_view = ScrollView(size_hint=(1, None), size=(Window.width, Window.height*0.8), pos_hint={'x':0, 'top':0.9})
        self.scroll_view.add_widget(self.dictListLayout)
        self.P.add_widget(self.scroll_view)
        self.P.add_widget(Label(text="Listes à afficher :", size_hint=(1,0.1), pos_hint={'x':0, 'top':1}))
        self.content= self.P
        self.size_hint= (0.6,1)
        self.pos_hint= {"x":0.4}

    def refresh_dictList(self) :
        currentDictNames = self.conn1.execute_select_all("SELECT name FROM sqlite_master WHERE type='table'")
        newDictNames = [name for name in currentDictNames if name not in self.dictNames]
        deletedDictNames = [clear_string(str(name)) for name in self.dictNames if name not in currentDictNames]

        self.dictNames = currentDictNames
        if newDictNames != [] :
            for name in newDictNames :
                button_layout = FloatLayout(size=(self.button_width, self.button_height), pos_hint={'x':0.1, 'top':1})
                btn = Button(text=clear_string(str(name)), font_size=30, size_hint=(1, 1), pos_hint={'top':1})
                checkbox = CheckBox(active = True, size_hint=(0.1, 1), pos_hint={'top':1})

                # Relier l'événement de clic du bouton à la checkbox
                btn.bind(on_press=lambda instance, cb=checkbox: toggle_checkbox(instance, cb))

                button_layout.add_widget(btn)
                button_layout.add_widget(checkbox)
                self.dictListLayout.add_widget(button_layout)


        if deletedDictNames:
            buttonsToDelete = [child for child in self.dictListLayout.children if child.children[1].text in deletedDictNames]
            for button in buttonsToDelete :
                self.dictListLayout.remove_widget(button)
            del buttonsToDelete

        self.dictListLayout.height = len(self.dictListLayout.children) * self.button_height
        
    def show_Menu(self, instance) :
        self.open()
        Clock.schedule_once(self.update_position, 0)

    def update_position(self, dt):
        self.pos_hint = {"x": 0.4}  # Repositionner à l'endroit voulu
        self.x = Window.width * 0.4




class StatsScreensTop(FloatLayout) :
    def __init__(self, sm, conn1, conn2, title, modes, **kw):
        super().__init__(**kw)
        self.gender = ""
        self.conn1 = conn1
        self.conn2 = conn2
        self.modes = modes

        # On affiche le mode d'affichage "Par genres" que s'il y a au moins une table genrée dans la db
        for name in self.conn1.execute_select_all("SELECT name FROM sqlite_master WHERE type='table'") :
            name = clear_string(str(name))
            columns = self.conn1.execute_select_all(f"PRAGMA table_info({name});")
            column_names = [column[1] for column in columns] 
            if 'gender' in column_names:
                self.gender = True
                break
            else:
                self.gender = False

        # Barre du haut
        # Bouton du menu
        self.menu = NavigationMenu(sm=sm)
        MenuButton = ImageButton("images\menu-deroulant.png", size_hint=(0.1,1),pos_hint={'top':1})
        MenuButton.bind(on_release=self.menu.show_Menu)
        self.add_widget(MenuButton)

        # Bouton des options
        self.options_menu = StatsOptionsMenu(sm=sm, conn1=self.conn1, conn2=self.conn2)

        if modes :
            self.options_menu.scroll_view.height = Window.height*0.5

            display_modes = GridLayout(cols=2, size_hint=(1,0.25), padding=[10,0], pos_hint={'x':0, 'top':0.25})

            part_mode = BoxLayout(orientation='vertical', spacing=10, padding=10)
            self.journal_checkbox = CheckBox(active = True, group='part')
            self.total_checkbox = CheckBox(active = False, group='part')
            journal = BoxLayout(orientation='horizontal', spacing=10, padding=10)
            journal.add_widget(Label(text='Journal'))
            journal .add_widget(self.journal_checkbox)
            total = BoxLayout(orientation='horizontal', spacing=10, padding=10)
            total.add_widget(Label(text='Totaux'))
            total.add_widget(self.total_checkbox)
            part_mode.add_widget(journal)
            part_mode.add_widget(total)

            self.gender_mode = BoxLayout(orientation='vertical', spacing=10, padding=10)
            self.classic_checkbox = CheckBox(active = True, group='gender')
            self.per_gender_checkbox = CheckBox(active = False, group='gender')
            classic = BoxLayout(orientation='horizontal', spacing=10, padding=10)
            classic.add_widget(Label(text='Classique'))
            classic.add_widget(self.classic_checkbox)
            self.options_menu_gender = BoxLayout(orientation='horizontal', spacing=10, padding=10)
            self.options_menu_gender.add_widget(Label(text='Par genres'))
            self.options_menu_gender.add_widget(self.per_gender_checkbox)
            self.gender_mode.add_widget(classic)
            if self.gender == True :
                self.gender_mode.add_widget(self.options_menu_gender)

            display_modes.add_widget(part_mode)
            display_modes.add_widget(self.gender_mode)

            self.options_menu.P.add_widget(Label(text="Modes d'affichages :", size_hint=(1,0.1), pos_hint={'x':0, 'top':0.3}))
            self.options_menu.P.add_widget(display_modes)

        OptionsMenuButton = ImageButton("images\options3.png", size_hint=(0.1,1), pos_hint={'x':0.9, 'top':1})
        OptionsMenuButton.bind(on_release=self.options_menu.show_Menu)
        self.add_widget(OptionsMenuButton)

        # "Titre" de la fenêtre
        self.add_widget(Label(text=title, size_hint=(0.8,1), pos_hint={'x':0.1, 'top':1}))


    def on_enter(self, *args):
        self.options_menu.refresh_dictList()
        # On affiche le mode d'affichage "Par genres" que s'il y a au moins une table genrée dans la db
        if self.modes :
            for name in self.conn1.execute_select_all("SELECT name FROM sqlite_master WHERE type='table'") :
                name = clear_string(str(name))
                columns = self.conn1.execute_select_all(f"PRAGMA table_info({name});")
                column_names = [column[1] for column in columns] 
                if 'gender' in column_names:
                    self.gender = True
                    break
                else:
                    self.gender = False

            if self.gender == True and len(self.gender_mode.children) == 1 :
                self.gender_mode.add_widget(self.options_menu_gender)
            elif self.gender == False and len(self.gender_mode.children) == 2 :
                self.gender_mode.remove_widget(self.options_menu_gender)


class IndentedLabel(Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None  # Permet de fixer la hauteur
        self.bind(texture_size=self.update_height)  # Adapter la hauteur automatiquement
        self.bind(size=self.update_text_size)  

    def update_text_size(self, *args):
        self.text_size = (self.width, None)  # Permet le retour à la ligne

    def update_height(self, *args):
        self.height = self.texture_size[1] + 5

def compare_dicts(old_data, new_data):
    # Nouveaux dictionnaires (clés dans new_data mais pas dans old_data)
    new_dates_entries = {key: new_data[key] for key in new_data if key not in old_data}

    # Dictionnaires supprimés (clés dans old_data mais pas dans new_data)
    deleted_dates_entries = {key: old_data[key] for key in old_data if key not in new_data}

    # Dictionnaires modifiés (seules les valeurs modifiées sont conservées)
    modified_entries_modified = {}
    modified_entries_new_list = {}
    modified_entries_deleted_list = {}

    for key in new_data:
        if key in old_data:  # Présent dans les deux
            for sub_key in new_data[key] :
                if sub_key in old_data[key] and old_data[key][sub_key] != new_data[key][sub_key] :
                    if key not in modified_entries_modified :
                        modified_entries_modified[key] = {}
                    if sub_key not in modified_entries_modified[key] :
                        modified_entries_modified[key][sub_key] = []
                    modified_entries_modified[key][sub_key] = new_data[key][sub_key]
                elif sub_key not in old_data[key] :
                    if key not in modified_entries_new_list :
                        modified_entries_new_list[key] = {}
                    if sub_key not in modified_entries_new_list[key] :
                        modified_entries_new_list[key][sub_key] = []
                    modified_entries_new_list[key][sub_key] = new_data[key][sub_key]
            for sub_key in old_data[key] :
                if sub_key not in new_data[key] :
                    if key not in modified_entries_deleted_list :
                        modified_entries_deleted_list[key] = {}
                    if sub_key not in modified_entries_deleted_list[key] :
                        modified_entries_deleted_list[key][sub_key] = []
                    modified_entries_deleted_list[key][sub_key] = new_data[key][sub_key]

    return new_dates_entries, deleted_dates_entries, modified_entries_modified, modified_entries_new_list, modified_entries_deleted_list

class Journal(Screen):
    def __init__(self, sm, conn1, conn2, **kw):
        super().__init__(**kw)
        self.gender = ""
        self.conn1 = conn1
        self.conn2 = conn2

        self.ScreensTop = StatsScreensTop(sm=sm, conn1=conn1, conn2=conn2, title="Journal", modes=True, size_hint=(1,0.1), pos_hint={'x':0, 'top':1})
        self.add_widget(self.ScreensTop)

        # Afficher les occurences par date et par occurence décroissantes
        self.dictNames = [] # On récupère les noms des listes qui sont cochées dans le menu des options d'affichage
        for button_layout in self.ScreensTop.options_menu.dictListLayout.children :
            button_layout.children[0].bind(active=self.on_checkbox_active)
            if button_layout.children[0].active :
                self.dictNames.append(button_layout.children[1].text)

        # On récupère toutes les infos à afficher, dans le bon ordre
        dict_infos = None 
        if self.dictNames :
            query_parts = [f"SELECT '{dictName}' AS table_name, name, date, occurence FROM {dictName}" for dictName in self.dictNames]
            query = " UNION ALL ".join(query_parts) + " ORDER BY date DESC, table_name ASC, occurence DESC, name ASC;"
            dict_infos = self.conn2.execute_select_all(query)

        # TTTT :  Il faudra aussi ajouter un buffer, mais pour l'instant c'est pas grave
        self.grouped_data = {}
        if dict_infos :
            for dictName, name, date, occurence in dict_infos:
                if date not in self.grouped_data:
                    self.grouped_data[date] = {}
                
                if dictName not in self.grouped_data[date]:
                    self.grouped_data[date][dictName] = []
                
                self.grouped_data[date][dictName].append(f"{name} a été tiré {occurence} fois")

        # Affichage formaté
        # TTTT : ajouter un on_resize pour que la taille des texts s'adapte et aussi celle des padding
        self.dates_layout = GridLayout(cols=1, size_hint_y=None , padding=[Window.width * 0.03, 0, Window.width * 0.02, 0])
        self.dates_layout.bind(minimum_height=self.dates_layout.setter('height'))
        self.scroll_view = ScrollView(size_hint=(1, None), size=(Window.width, Window.height), pos_hint={'top':0.9})
        if self.grouped_data :
            for date, tables in self.grouped_data.items():
                date_layout = GridLayout(cols=1, size_hint_y=None)
                date_layout.add_widget(IndentedLabel(text=f"{date}", size_hint=(1, None), halign="left"))
                date_layout.bind(minimum_height=date_layout.setter('height'))
                tables_layout =  GridLayout(cols=1, size_hint_y=None, padding=[Window.width * 0.03, 0, 0, 0])
                tables_layout.bind(minimum_height=tables_layout.setter('height'))
                for dictName, entries in tables.items():
                    table_layout = GridLayout(cols=1, size_hint_y=None)
                    table_layout.add_widget(IndentedLabel(text=f"{dictName}", size_hint=(1, None), halign="left"))
                    table_layout.bind(minimum_height=table_layout.setter('height'))
                    entry_layout =  GridLayout(cols=1, size_hint_y=None, padding=[Window.width * 0.03, 0, 0, 0])
                    entry_layout.bind(minimum_height=entry_layout.setter('height'))
                    for entry in entries:
                        entry_layout.add_widget(IndentedLabel(text=f"{entry}", size_hint=(1, None), halign="left"))
                    table_layout.add_widget(entry_layout)
                    tables_layout.add_widget(table_layout)
                date_layout.add_widget(tables_layout)
                self.dates_layout.add_widget(date_layout)
        self.scroll_view.add_widget(self.dates_layout)
        self.add_widget(self.scroll_view)
        self.scroll_view.height = Window.height *0.9


    def on_checkbox_active(self, checkbox, value) :
        dictName = checkbox.parent.children[1].text
        if value :
            dict_infos = self.conn2.execute_select_all(f"SELECT '{dictName}' AS table_name, name, date, occurence FROM {dictName} ORDER BY date DESC, table_name ASC, occurence DESC;")
            
            if dict_infos :
                dictNames, names, dates, occurences = zip(*dict_infos)
                for date in set(dates) :
                    if date in self.grouped_data :
                        self.grouped_data[date][dictName] = []
                        date_index = ""
                        for i in range(len(self.dates_layout.children)) :
                            if self.dates_layout.children[i].children[-1].text == date : 
                                date_index = i

                        table_layout = GridLayout(cols=1, size_hint_y=None)
                        table_layout.add_widget(IndentedLabel(text=f"{dictName}", size_hint=(1, None), halign="left"))
                        table_layout.bind(minimum_height=table_layout.setter('height'))
                        entry_layout =  GridLayout(cols=1, size_hint_y=None, padding=[Window.width * 0.03, 0, 0, 0])
                        entry_layout.bind(minimum_height=entry_layout.setter('height'))
                        for i in range(len(names)) :
                            if dates[i] == date :
                                name = names[i]
                                occurence = occurences[i]
                                self.grouped_data[date][dictName].append(f"{name} a été tiré {occurence} fois")
                                entry_layout.add_widget(IndentedLabel(text=f"{name} a été tiré {occurence} fois", size_hint=(1, None), halign="left"))
                        table_layout.add_widget(entry_layout)
                        self.dates_layout.children[date_index].children[0].add_widget(table_layout)
                        
                        # On réordonne les listes dans l'ordre croissant 
                        sorted_lists = sorted(self.dates_layout.children[date_index].children[0].children, key=lambda list: list.children[1].text, reverse=True)
                        self.dates_layout.children[date_index].children[0].children[:] = sorted_lists  # On réaffecte directement la liste sans tout recréer
                        del sorted_lists
                    else :
                        self.grouped_data[date] = {}
                        self.grouped_data[date][dictName] = []
                        date_layout = GridLayout(cols=1, size_hint_y=None)
                        date_layout.add_widget(IndentedLabel(text=f"{date}", size_hint=(1, None), halign="left"))
                        date_layout.bind(minimum_height=date_layout.setter('height'))
                        tables_layout =  GridLayout(cols=1, size_hint_y=None, padding=[Window.width * 0.03, 0, 0, 0])
                        tables_layout.bind(minimum_height=tables_layout.setter('height'))
                        table_layout = GridLayout(cols=1, size_hint_y=None)
                        table_layout.add_widget(IndentedLabel(text=f"{dictName}", size_hint=(1, None), halign="left"))
                        table_layout.bind(minimum_height=table_layout.setter('height'))
                        entry_layout =  GridLayout(cols=1, size_hint_y=None, padding=[Window.width * 0.03, 0, 0, 0])
                        entry_layout.bind(minimum_height=entry_layout.setter('height'))
                        for i in range(len(names)) :
                            if dates[i] == date :
                                name = names[i]
                                occurence = occurences[i]
                                self.grouped_data[date][dictName] = []
                                self.grouped_data[date][dictName].append(f"{name} a été tiré {occurence} fois")
                                entry_layout.add_widget(IndentedLabel(text=f"{name} a été tiré {occurence} fois", size_hint=(1, None), halign="left"))
                        table_layout.add_widget(entry_layout)
                        tables_layout.add_widget(table_layout)
                        date_layout.add_widget(tables_layout)
                        self.dates_layout.add_widget(date_layout)

                # On réordonne les dates dans l'ordre décroissant 
                sorted_dates = sorted(self.dates_layout.children, key=lambda date_layout: date_layout.children[1].text, reverse=True)
                # Réorganiser les enfants dans GridLayout
                self.dates_layout.children[:] = sorted_dates  # On réaffecte directement la liste sans tout recréer
                del sorted_dates

        else :
            for i in range(len(self.dates_layout.children)) :
                for j in range(len(self.dates_layout.children[i].children[0].children)) :
                    if self.dates_layout.children[i].children[0].children[j].children[1].text == dictName :
                        self.dates_layout.children[i].children[0].remove_widget(self.dates_layout.children[i].children[0].children[j]) # On supprime les table_layout dont le text du label est "dictName", comme il n'y en a qu'un, on peut faire comme ça !
                        break

            for date in self.grouped_data.keys() :
                self.grouped_data[date].pop(dictName, None)
            
            # On supprime les dates qui n'ont plus rien à afficher.
            date_to_delete = []
            for i in range(len(self.dates_layout.children)) :  
                if len(self.dates_layout.children[i].children[0].children) == 0:  # Vérifie si le layout est vide
                    date_to_delete.append(self.dates_layout.children[i])
            for widget in date_to_delete :
                self.grouped_data.pop(widget.children[1].text, None)
                self.dates_layout.remove_widget(widget)

    def before_enter(self) :
        self.ScreensTop.on_enter()
        # TTTT : y'a peut-être moyen de récupérer currentdictNames en utilisant self.dictNames non ? 
        currentdictNames = [] # On récupère les noms des listes qui sont cochées dans le menu des options d'affichage
        for button_layout in self.ScreensTop.options_menu.dictListLayout.children :
            button_layout.children[0].unbind(active=self.on_checkbox_active)
            button_layout.children[0].bind(active=self.on_checkbox_active)
            if button_layout.children[0].active :
                currentdictNames.append(button_layout.children[1].text)
        
        self.dictNames = currentdictNames

        # On récupère toutes les infos à afficher, dans le bon ordre
        dict_infos = None
        if currentdictNames :
            query_parts = [f"SELECT '{dictName}' AS table_name, name, date, occurence FROM {dictName}" for dictName in currentdictNames]
            query = " UNION ALL ".join(query_parts) + " ORDER BY date DESC, table_name ASC, occurence DESC, name ASC;"
            dict_infos = self.conn2.execute_select_all(query)

        # TTTT :  Il faudra aussi ajouter un buffer, mais pour l'instant c'est pas grave
        current_grouped_data = {}
        if dict_infos :
            for dictName, name, date, occurence in dict_infos:
                if date not in current_grouped_data:
                    current_grouped_data[date] = {}
                
                if dictName not in current_grouped_data[date]:
                    current_grouped_data[date][dictName] = []
                
                current_grouped_data[date][dictName].append(f"{name} a été tiré {occurence} fois")

        new_dates_entries, deleted_dates_entries, modified_entries_modified, modified_entries_new_list, modified_entries_deleted_list = compare_dicts(self.grouped_data, current_grouped_data)

        # print("modified_words : ",  modified_words)
        # print("new_words : ",  new_words)
        # print("deleted_word : ", deleted_words)
        # print("modified_entries_modified : ", modified_entries_modified)
        # print("modified_entries_new_list : ", modified_entries_new_list)
        # print("modified_entries_deleted_list : ", modified_entries_deleted_list)

        self.grouped_data = current_grouped_data 
        if current_grouped_data :
            del current_grouped_data

        if deleted_dates_entries :
            datesToDelete = [child for child in self.dates_layout.children if child.children[-1].text in deleted_dates_entries]
            for date in datesToDelete :
                self.dates_layout.remove_widget(date)
            del datesToDelete

        if new_dates_entries :
            for date, tables in new_dates_entries.items():
                date_layout = GridLayout(cols=1, size_hint_y=None)
                date_layout.add_widget(IndentedLabel(text=f"{date}", size_hint=(1, None), halign="left"))
                date_layout.bind(minimum_height=date_layout.setter('height'))
                tables_layout =  GridLayout(cols=1, size_hint_y=None, padding=[Window.width * 0.03, 0, 0, 0])
                tables_layout.bind(minimum_height=tables_layout.setter('height'))
                for dictName, entries in tables.items():
                    table_layout = GridLayout(cols=1, size_hint_y=None)
                    table_layout.add_widget(IndentedLabel(text=f"{dictName}", size_hint=(1, None), halign="left"))
                    table_layout.bind(minimum_height=table_layout.setter('height'))
                    entry_layout =  GridLayout(cols=1, size_hint_y=None, padding=[Window.width * 0.03, 0, 0, 0])
                    entry_layout.bind(minimum_height=entry_layout.setter('height'))
                    for entry in entries:
                        entry_layout.add_widget(IndentedLabel(text=f"{entry}", size_hint=(1, None), halign="left"))
                    table_layout.add_widget(entry_layout)
                    tables_layout.add_widget(table_layout)
                date_layout.add_widget(tables_layout)
                self.dates_layout.add_widget(date_layout)

        # TTTT : à vérifier un autre jour
        if deleted_dates_entries or new_dates_entries :
             # On réordonne les dates dans l'ordre décroissant 
            sorted_dates = sorted(self.dates_layout.children, key=lambda date_layout: date_layout.children[1].text, reverse=False)
            # Réorganiser les enfants dans GridLayout
            self.dates_layout.children[:] = sorted_dates  # On réaffecte directement la liste sans tout recréer
            del sorted_dates

        if modified_entries_new_list :
            for date, tables in modified_entries_new_list.items():
                date_index = ""
                for i in range(len(self.dates_layout.children)) :
                    if self.dates_layout.children[i].children[-1].text == date : 
                        date_index = i
                        break
                for dictName, entries in tables.items():
                    table_layout = GridLayout(cols=1, size_hint_y=None)
                    table_layout.add_widget(IndentedLabel(text=f"{dictName}", size_hint=(1, None), halign="left"))
                    table_layout.bind(minimum_height=table_layout.setter('height'))
                    entry_layout =  GridLayout(cols=1, size_hint_y=None, padding=[Window.width * 0.03, 0, 0, 0])
                    entry_layout.bind(minimum_height=entry_layout.setter('height'))
                    for entry in entries:
                        entry_layout.add_widget(IndentedLabel(text=f"{entry}", size_hint=(1, None), halign="left"))
                    table_layout.add_widget(entry_layout)
                    self.dates_layout.children[date_index].children[0].add_widget(table_layout)

        if modified_entries_deleted_list :
            for date, tables in modified_entries_deleted_list.items():
                date_index = ""
                for i in range(len(self.dates_layout.children)) :
                    if self.dates_layout.children[i].children[-1].text == date : 
                        date_index = i
                        break
                for dictName, entries in tables.items():
                    for j in range(len(self.dates_layout.children[date_index].children[0].children)) :
                        if self.dates_layout.children[date_index].children[0].children[j].children[1].text == dictName :
                            self.dates_layout.children[date_index].children[0].remove_widget(self.dates_layout.children[date_index].children[0].children[j]) # On supprime les table_layout dont le text du label est "dictName", comme il n'y en a qu'un, on peut faire comme ça !
                            break

        if modified_entries_deleted_list or modified_entries_new_list :
            for date in set(modified_entries_deleted_list.keys()) | set(modified_entries_new_list.keys()):
                for i in range(len(self.dates_layout.children)) :
                    if self.dates_layout.children[i].children[-1].text == date :
                        # On réordonne les listes dans l'ordre croissant 
                        self.dates_layout.children[i].children[0].children[:] = sorted(self.dates_layout.children[i].children[0].children, key=lambda list: list.children[1].text, reverse=True)
                        break

        if modified_entries_modified :
            pattern = r"(.+) a été tiré (\d+) fois"
            for date, tables in modified_entries_modified.items():
                date_index = ""
                for i in range(len(self.dates_layout.children)) :
                    if self.dates_layout.children[i].children[-1].text == date : 
                        date_index = i
                        break
                for dictName, entries in tables.items():
                    list_index = ""
                    for j in range(len(self.dates_layout.children[date_index].children[0].children)) :
                        if self.dates_layout.children[date_index].children[0].children[j].children[1].text == dictName :
                            list_index = j
                            break
                    for entry in entries:
                        # Recherche du nom dans la string
                        match = re.match(pattern, entry)
                        word = match.group(1)

                        if dictName in deleted_words :
                            if word in deleted_words[dictName] :
                                for k in range(len(self.dates_layout.children[date_index].children[0].children[list_index].children[0].children)) :
                                    match = re.match(pattern, self.dates_layout.children[date_index].children[0].children[list_index].children[0].children[k].text)
                                    name = match.group(1)
                                    if name == word :
                                        self.dates_layout.children[date_index].children[0].children[list_index].children[0].remove_widget(self.dates_layout.children[date_index].children[0].children[list_index].children[0].children[k])
                                        deleted_words[dictName].remove(word)
                                        break

                        if dictName in new_words :
                            if word in new_words[dictName] :    
                                self.dates_layout.children[date_index].children[0].children[list_index].children[0].add_widget(IndentedLabel(text=f"{entry}", size_hint=(1, None), halign="left")) 
                                new_words[dictName].remove(word)
                                if dictName in modified_words :
                                    if word in modified_words[dictName] :
                                        modified_words[dictName].remove(word)
                        
                        elif dictName in modified_words :
                            if word in modified_words[dictName] :
                                for k in range(len(self.dates_layout.children[date_index].children[0].children[list_index].children[0].children)) :
                                    match = re.match(pattern, self.dates_layout.children[date_index].children[0].children[list_index].children[0].children[k].text)
                                    name = match.group(1)
                                    if name == word :
                                        self.dates_layout.children[date_index].children[0].children[list_index].children[0].children[k].text = entry
                                        modified_words[dictName].remove(word)
                                        break

                    # On trie par occurence décroissante et par nom croissant
                    self.dates_layout.children[date_index].children[0].children[list_index].children[0].children[:] = sorted(self.dates_layout.children[date_index].children[0].children[list_index].children[0].children, 
                                                                                                                key=lambda entry: (-int(re.match(pattern, entry.text).group(2)), re.match(pattern, entry.text).group(1)), reverse=True)
                    

            self.scroll_view.height = Window.height *0.9

                                                                                                
                                            




class DBManager:
    def __init__(self):
        self.conn = None
        self.cursor = None
    
    def open_connection(self, db_name):
        """Ouvre une connexion à la base de données."""
        if self.conn is None:
            self.conn = sqlite3.connect(db_name)
            self.cursor = self.conn.cursor()
    
    def close_connection(self):
        """Ferme la connexion et le curseur."""
        if self.conn:
            self.conn.commit()  # S'assurer que toutes les modifications sont enregistrées
            self.conn.close()
            self.conn = None
            self.cursor = None

    def execute_select_one(self, query, params=None):
        """Exécute une requête SQL de type SELECT et retourne le résultat."""
        if self.cursor:
            if params is None:
                params = []
            self.cursor.execute(query, params)
            return self.cursor.fetchone()  # Récupère tous les résultats
        return None        

    def execute_select_all(self, query, params=None):
        """Exécute une requête SQL de type SELECT et retourne le résultat."""
        if self.cursor:
            if params is None:
                params = []
            self.cursor.execute(query, params)
            return self.cursor.fetchall()  # Récupère tous les résultats
        return None

    def execute_modify(self, query, params=None):
        """Exécute une requête SQL de type CREATE, INSERT, UPDATE ou DELETE et fait un commit."""
        if self.cursor:
            if params is None:
                params = []
            self.cursor.execute(query, params)  # Exécuter la requête
            self.conn.commit()  # Effectuer le commit pour enregistrer les changements





class ScreenTransition(ScreenManager) :
    def __init__(self, conn1, conn2,**kwargs):
        super().__init__(**kwargs)
        screens = [HomeScreen(sm=self,conn1=conn1, conn2=conn2,name="home"), DictionariesMenu(sm=self,conn1=conn1, conn2=conn2,name="dictMenu"),DictionaryModifier(sm=self,conn1=conn1, conn2=conn2,name="modifier"),Journal(sm=self,conn1=conn1, conn2=conn2,name="journal")]
        for screen in screens:
            self.add_widget(screen)
        self.current = "home"


# TTTT : il faudra adapter pour que ça soit transverse à tous les écrans de stats.
modified_words = {}
new_words = {}
deleted_words = {}
def add_new_words(dictName, word):
    if dictName not in new_words :
        new_words[dictName] = []
    if word not in new_words[dictName] :
        new_words[dictName].append(word)

def add_deleted_words(dictName, word):
    if dictName not in deleted_words :
        deleted_words[dictName] = []
    if word not in deleted_words[dictName] :
        deleted_words[dictName].append(word)

        if dictName in new_words :
            if word in new_words[dictName] :
                new_words[dictName].remove(word)
        elif dictName in modified_words :
            if word in modified_words[dictName] :
                modified_words[dictName].remove(word)

def add_modified_words(dictName, word):
    if dictName not in modified_words :
        modified_words[dictName] = []
    if word not in modified_words[dictName] :
        if dictName in new_words :
            if word not in new_words[dictName] :
                modified_words[dictName].append(word)
        else :
            modified_words[dictName].append(word)


class RandomPicker(App) :
    def build(self) :
        self.conn1 = DBManager()
        self.conn2 = DBManager()
        self.conn1.open_connection('list.db')
        self.conn2.open_connection('stats.db')
        self.sm = ScreenTransition(conn1=self.conn1, conn2=self.conn2)
        return self.sm
    
    def on_pause(self):
        self.conn1.close_connection() # Fermer la connexion à la DB
        self.conn2.close_connection()  
        return True  # Empêche Kivy de mettre l'application en pause (si nécessaire)

    def on_resume(self):
        self.conn1.open_connection('list.db')  # Rouvrir la connexion à la DB
        self.conn2.open_connection('stats.db') 

    def on_stop(self):
        self.conn1.close_connection() # Fermer la connexion à la DB
        self.conn2.close_connection()  

if __name__ == "__main__" :
    RandomPicker().run()