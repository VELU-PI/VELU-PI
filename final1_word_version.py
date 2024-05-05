import bme680
import os
import time
import datetime
import mysql.connector
import dropbox
import dropbox.files
import RPi.GPIO as GPIO
from ultralytics import YOLO
import glob
from picamera2 import Picamera2    
from picamera2.encoders import H264Encoder
from picamera2.outputs import FfmpegOutput

#Vooraf definiëren van beeldherkenningsmodel (aanwezig in zelfde map als dit script):
model = YOLO('best.pt')

print("Started script!")

# CONNECTIEGEGEVENS
host = 'localhost'
user = '…'	# Naam van de database user
password = '…'	# paswoord van de user
database = 'Sensordata'

# Verbinding maken met de database
mydb = mysql.connector.connect(
    host=host,
    user=user,
    password=password,
    database=database
)
cursor = mydb.cursor()

# Token voor Dropbox klaarzetten:
with open("dropbox_token.txt", "r") as f:
    TOKEN = f.read()
dbx = dropbox.Dropbox(TOKEN)

# bme680 instellen
try:
    sensor = bme680.BME680(bme680.I2C_ADDR_PRIMARY)
except IOError:
    sensor = bme680.BME680(bme680.I2C_ADDR_SECONDARY)

sensor.set_humidity_oversample(bme680.OS_2X)
sensor.set_pressure_oversample(bme680.OS_4X)
sensor.set_temperature_oversample(bme680.OS_8X)
sensor.set_filter(bme680.FILTER_SIZE_3)

# Motionsensor activeren
GPIO.setmode(GPIO.BOARD)
PIN = 18		# data pin van de bewegingssensor
GPIO.setup(PIN, GPIO.IN)
print("Start sensor...")
time.sleep(2)
print("Sensor geactiveerd...")


while True:
    if GPIO.input(PIN):	# Wanneer beweging gedetecteerd wordt
        # Tijdstempel genereren voor de afbeeldingsnaam
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        print("Beweging gedetecteerd! " + (time.strftime("%H:%M:%S")))
        time.sleep(5)	# Wacht 5 seconden om een foto van een bewegend insect te vermijden

        try:
            # Nieuwe afbeeldingsnaam met tijdstempel:
            image_name = f"/home/Autobeehive/Pictures/img_{timestamp}.jpg"  
            os.system(f"libcamera-still -n -o {image_name}")	# Foto maken
            print("Afbeelding gemaakt")
        except Exception as e:
            print("Fout bij het maken van de foto:", e)

        list_of_files = glob.glob('/home/Autobeehive/Pictures/*') # Namen van alle foto’s in de Pictures map
        latest_file = max(list_of_files, key=os.path.getctime)  # Naam van de laatste foto selecteren
        #  Beeldherkenningsmodel laten lopen op laatst getrokken foto
        results = model.predict(source=latest_file , show=False, conf=0.668, save=True) 
        for result in results: 
            if result.boxes:
                box = result.boxes[0]
                class_id = int(box.cls)
                #  Naam van de gedetecteerde klasse toekennen aan object name
                object_name = model.names[class_id] 
                print(object_name)

                # Als het een Aziatische hoornaar is wordt er een video gemaakt
                if object_name == 'Aziatische hoornaar': 
                    video_name = f"/home/Autobeehive/Videos/video_{timestamp}.mp4"
                    #Video maken:
                    picam2 = Picamera2()
                    video_config = picam2.create_video_configuration()
                    picam2.configure(video_config)

                    encoder = H264Encoder(10000000)	#Het aantal bits per seconde
                    output = FfmpegOutput(video_name)

                    picam2.start_recording(encoder, output)
                    time.sleep(10)  #duur van video
                    picam2.stop_recording()
                    picam2.close()

                    print('Het is een hoornaar, dus er werd een video gemaakt!')

                    #Afbeelding en video opslaan in databank en dropbox 
                    try:
                        # Afbeelding en video openen en lezen als binaire gegevens
                        with open(image_name, 'rb') as image_file, open(video_name, 'rb') as video_file:
                            image_binary = image_file.read()
                            video_binary = video_file.read()

                            # Uploaden van afbeelding en video naar Dropbox
                            dbx.files_upload(image_binary, f"/Raspi/Pictures/img_{timestamp}.jpg")
                            dbx.files_upload(video_binary, f"/Raspi/Videos/video_{timestamp}.mp4")

                            # INSERT-query uitvoeren om afbeelding en video op te slaan als een BLOB in de database
                            sql = "INSERT INTO image_video_bme680 (date, host, image, video, temperature, pressure, humidity) VALUES (%(date)s,%(host)s,%(image)s,%(video)s,%(temperature)s,%(pressure)s,%(humidity)s)"
                            image_data = {
                                'date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'host': host,
                                'image': image_binary,
                                'video': video_binary,
                                'temperature': '{0:.2f}'.format(sensor.data.temperature),
                                'pressure': '{0:.2f}'.format(sensor.data.pressure),
                                'humidity': '{0:.2f}'.format(sensor.data.humidity)}

                        cursor.execute(sql, image_data)
                        mydb.commit()
                        print("Afbeelding en video opgeslagen in de database")
                    except Exception as e:
                        print("Fout bij het uitvoeren van de query:", e)
                        mydb.rollback()
                    time.sleep(300) 		# Als een Aziatische hoornaar gedetecteerd is, wacht 5 minuten 
                else:                           		# Bij detectie van een wespachtige, maar geen Aziatische hoornaar:
                    time.sleep(60)             	# Wacht een minuut
                
            else:                               # Bij geen enkele detectie wordt de genomen afbeelding verwijderd
                os.remove(image_name)	
                print('Geen detectie: afbeelding verwijderd')
                time.sleep(30)                  # Bij geen detectie: wacht een halve minuut
mydb.close()
