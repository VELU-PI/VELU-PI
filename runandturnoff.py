#!/usr/bin/python3

import os
import logging
from time import sleep
from pijuice import PiJuice

logging.basicConfig(
	filename = '/home/pi/pistatus.log',
	level = logging.DEBUG,
	format = '%(asctime)s %(message)s',
	datefmt = '%d/%m/%Y %H:%M:%S')

pj = PiJuice(1,0x14)

pjOK = False
while pjOK == False:
   stat = pj.status.GetStatus()
   if stat['error'] == 'NO_ERROR':
      pjOK = True
   else:
      sleep(0.1)

# Indien op batterij, schakel uit na 8 uur
data = stat['data']
if data['powerInput'] == "NOT_PRESENT" and data['powerInput5vIo'] == 'NOT_PRESENT':

	# Schrijf een statement naar de log
	logging.info('Raspberry Pi op batterij. Schakelt uit na 8 uur')

   # Houdt de Raspberry Pi draaiende gedurende 8 uur.
   # Aanpassen van deze tijd (in seconden) zorgt voor een ander moment van afsluiten.
   sleep(28800)

   # Zorg dat wakeup_enabled and wakeup_on_charge de juiste waardes hebben
   pj.rtcAlarm.SetWakeupEnabled(True)
   pj.power.SetWakeUpOnCharge(0)

   # Geen stroom meer naar de Raspberry Pi om de batterij niet te draineren
   pj.power.SetSystemPowerSwitch(0)
   pj.power.SetPowerOff(30)

   # Schakel het systeem uit
   os.system("sudo shutdown -h now")

else:

	# Schrijf een statement naar de log
	logging.info('Raspberry Pi aangesloten op stroom, zal niet automatisch uitschakelen')