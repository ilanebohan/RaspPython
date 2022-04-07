from tkinter import *
import sqlite3,urllib.request
from tkinter import messagebox
import json
import RPi.GPIO as GPIO #Importe la bibliothèque pour contrôler les GPIOs
from rfid import RFID
import numpy as np
import cv2
import os
from src import microbit
import time



redCross = microbit.Image("90009:09090:00900:09090:90009")
checkMark = microbit.Image("00000:00009:00090:90900:09000")





(im_width, im_height) =(112,92)
face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
video_capture = cv2.VideoCapture(0)

(images,labels,names,id) = ([],[],{},0)

def predict_image():
    size = 2
    global model,name
    continuer = True
    compteur = 0;
    compteurinconnu = 0;
    start_time = time.time()
    while continuer:
        if not video_capture.isOpened():
            print('Unable to load camera.')
            break
    
        
    # Capture frame-by-frame
        ret, frame = video_capture.read()
        frame = cv2.flip(frame, 1, 0)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)      #gray color
        faces = face_cascade.detectMultiScale(gray,
                                          scaleFactor=1.2,
                                          minNeighbors=5,
                                          minSize=(80, 80)) #face detection in gray image

    # Draw a rectangle around the faces 
        for (x, y, w, h) in faces:
            #if (np.count_nonzero(faces) > 1):
                #continuer = False
            if (compteurinconnu >= 10):
                continuer = False
                video_capture.release()
                connectionKO();
                InsererBDD('3','0','Reco facile refusée, utilisateur inconnu')
            if (compteur >= 5):
                if (names[prediction[0]] == text_box.get()):
                    video_capture.release()
                    microbit.display.show(checkMark)
                    messagebox.showinfo('Bravo ! ','Félicitation, vous êtes connecté !')
                if (names[prediction[0]] != text_box.get()):
                    video_capture.release()
                    connectionKO();
                    InsererBDD('3','0','Reco faciale refusée, mauvais utilisateur')
                
            face = gray[y:y + h, x:x + w]
            
            face_resize = cv2.resize(face, (im_width, im_height))
        
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
            prediction = model.predict(face_resize)
            if (prediction[1]<85):
                compteur = compteur +1;
                cv2.putText(frame,'%s - %.0f' % (names[prediction[0]],prediction[1]), (x-10,y-10), cv2.FONT_HERSHEY_PLAIN,1,(0,0,255))
            else:
                compteurinconnu = compteurinconnu +1
                cv2.putText(frame,'Inconnu', (x-10,y-10), cv2.FONT_HERSHEY_PLAIN,1,(0,0,255))
        
        
        if ((time.time() - start_time)>20):
            continuer = False
        cv2.imshow('Video', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break


fn_dir = 'Photos'




for (subdirs,dirs,files) in os.walk(fn_dir):
    for subdir in dirs:
        names[id] = subdir
        subjectpath = os.path.join(fn_dir, subdir)
        
        for filename in os.listdir(subjectpath):
            f_name, f_extension = os.path.splitext(filename) 
            path = subjectpath + '/' + filename
            label = id
            images.append(cv2.imread(path,0))
            labels.append(int(label))
        id += 1
        
        
(images, labels) = [np.array(liste) for liste in [images,labels]]
        

model = cv2.face.createLBPHFaceRecognizer()
model.train(images,labels)










def lectureBadge():
    GPIO.setmode(GPIO.BOARD) #Définit le mode de numérotation (Board)
    GPIO.setwarnings(False) #On désactive les messages d'alerte

    rc522 = RFID() #On instancie la lib

    print('En attente d\'un badge (pour quitter, Ctrl + c): ') #On affiche un message demandant à l'utilisateur de passer son badge

    continuer = True
    while continuer :
        continuer = rc522.wait_for_tag() #On attnd qu'une puce RFID passe à portée
        #wait_tag()
        
        (error, tag_type) = rc522.request() 

        if not error : #Si on a pas d'erreur
            (error, uid) = rc522.anticoll() 

        if not error : #Si on a réussi à nettoyer
            idbadge = str(uid[0])+str(uid[1])+str(uid[2])+str(uid[3])+str(uid[4])
            print(idbadge)
            time.sleep(1) 
            return idbadge



def webServiceBadge(login,id):
    if (id != None):
        #Si le badge est présenté dans les 30 secondes
        print(login)
        print(id)
        url = "https://btssio-carcouet.fr/ppe4/public/badge/" + login + "/" + id
        result = urllib.request.urlopen(url).read()
        testResult = json.loads(result)
        if (testResult["status"] == "false"):
            #Si la réponse est négative
            InsererBDD('2','0','Connection badge refusée')
            connectionKO();
        else:
            #Si la réponse est positive
            print("Connection badge OK")
            messagebox.showwarning('Attente de reconnaissance faciale', 'En attente de reconnaissance faciale');
            predict_image()
            #InsererBDD('1','1','Connection réussie')
    else:
        #Si aucun badge n'est présenté dans les 30 secondes
        InsererBDD('2','0','Connection badge refusée')
        connectionKO();

    

    



def webServiceFormulaire(login, passwd):
    #print(login)
    #print(passwd)
    url = "https://btssio-carcouet.fr/ppe4/public/connect2/" + login + "/" + passwd + "/infirmiere"
    result = urllib.request.urlopen(url).read()
    testResult = json.loads(result)
    if ("status" in testResult):
        #Si la réponse est négative
        InsererBDD('1','0','Mauvais mot de passe')
        connectionKO();
    else:
        #Si la réponse est positive
        print("Connection formulaire OK")
        messagebox.showwarning('Attente de badge', 'En attente d un badge');
        webServiceBadge(login,lectureBadge())
        #InsererBDD('1','1','Connection réussie')
    
def onClick():
    login = text_box.get()
    passwd = text_box2.get()
    webServiceFormulaire(login,passwd)
   

     
def InsererBDD(numEtape,statut,commentaire):
    conn = sqlite3.connect('/home/pi/ppe4.db')
    cursor = conn.cursor()
    print ("DB OK")
    cursor.execute("INSERT INTO user (identifiant,numEtape,etat,commentaire) VALUES ('"+ text_box.get() +"',"+numEtape+","+statut+",'"+commentaire+"')")
    conn.commit()
    cursor.close()
    print ("INSERT OK")
    
def connectionKO():
    microbit.display.show(redCross)
    messagebox.showerror('Erreur', 'Connexion refusée');
    
    
    



    

ws = Tk()
ws.title('Connection')
ws.geometry('300x300')
ws.config(bg='black')
loginLbl = Label(ws,text="Login").pack()
text_box = Entry(ws)
text_box.pack(expand=False)
    
passwdLbl = Label(ws,text="Password").pack()
text_box2 = Entry(ws)
text_box2.pack(expand=False)
    

    
bouton=Button(ws, text="Connexion", command=onClick)
bouton.pack()
