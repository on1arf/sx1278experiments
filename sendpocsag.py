# sx1278/RFM95 pocsag transmitter


# this is proof-of-concept code to show the ability of the sx1276 (AKA RFM95, AKA LORA32) to transmit POCSAG paging messages
# Datasheet: https://www.semtech.com/products/wireless-rf/lora-core/sx1276#download-resources

# This program uses code from the "RadioHead" project, converted from c++ to python
# https://github.com/hallard/RadioHead/blob/master/RH_RF95.cpp
# https://github.com/hallard/RadioHead/blob/master/RH_RF95.h

# The original code of the RadioHead library was developed by Mike McCauley
# http://www.airspayce.com/mikem/arduino/RadioHead/


# this code was tested on a TTGO T-beam, which uses a ESP32 and a "LORA32" radiochip.
# https://github.com/LilyGO/TTGO-T-Beam
# the LORA32 is identical to the semtech sx1278, operating on 439.9875 
# Note that transmitting on 439.9875 MHz is only allowed if you have a amateur-radio license
# check the local laws on the amateur-radio regulation in your particular country


# this code is tested on micropython 3.4.0 on a ESP32
# more info here:
# https://micropython.org/download/esp32spiram/


##### imports

from machine import SPI
from machine import Pin
import array
import time



#### configuration
XMITFREQ=439.9875 		# frequency used for ham-radio paging in Europe


##### lora32 specific information
spi = SPI(2, baudrate=100000, polarity=0, bits=8, phase=0, sck=Pin(5), mosi=Pin(27), miso=Pin(19))
nss = Pin(18, Pin.OUT) # GPIO5 = D5 = 5 = VSPI_CS0
resetpin = Pin(23, Pin.OUT) # GPIO22 = D22 = 22 = resetpin


##### constants

# 'FSK/OOK' registers of the sx1278
RH_RF95_REG_00_FIFO = const(0x00)	# RegFifo
RH_RF95_REG_01_OP_MODE = const(0x01)	# RegOpMode
RH_RF95_REG_02_BRT_MSB = const(0x02)	# RegBitrateMsb
RH_RF95_REG_03_BRT_LSB = const(0x03)	# RegBitrateLsb
RH_RF95_REG_04_FDV_MSB = const(0x04)	# RegFdevMsb
RH_RF95_REG_05_FDV_LSB = const(0x05)	# RegFdevLsb
RH_RF95_REG_06_FRF_MSB = const(0x06)	# RegFrfMsb
RH_RF95_REG_07_FRF_MID = const(0x07)	# RegFrfMid
RH_RF95_REG_08_FRF_LSB = const(0x08)	# RegFrfLsb
RH_RF95_REG_09_PA_CONFIG = const(0x09) # RegPaConfig

RH_RF95_REG_25_PRA_MSB	= const(0x25)	# RegPreambleMsb
RH_RF95_REG_25_PRA_LSB	= const(0x26)	# RegPreambleLsb

RH_RF95_REG_27_SYN_CFG = const(0x27)	# RegSyncConfig
RH_RF95_REG_30_PKT_CF1	= const(0x30)	# RegPacketConfig1
RH_RF95_REG_31_PKT_CF2	= const(0x31)	# RegPacketConfig2
RH_RF95_REG_32_PAY_LEN	= const(0x32)	# RegPayloadLength
RH_RF95_REG_35_FIF_THR	= const(0x35)	# RegFifoThresh
RH_RF95_REG_3F_IRQ_FL2 = const(0x3f)	# RegIrqFlags2

RH_RF95_REG_4D_PA_DAC	= const(0x4d)	# RegPaDac



# Mode of operations
RH_RF95_MODE_SLEEP = const(0x00)
RH_RF95_MODE_STDBY = const(0x01)
RH_RF95_MODE_TX = const(0x03)


# some other stuff
RH_RF95_FXOSC = 32000000.0
RH_RF95_FSTEP = (RH_RF95_FXOSC / 524288)

RH_SPI_WRITE_MASK = const(0x80)

RH_RF95_PA_DAC_DISABLE = const(0x04)
RH_RF95_PA_DAC_ENABLE = const(0x07)
RH_RF95_PA_SELECT = const(0x80)




#### Support functions

# Do Reset
def DoReset():
	resetpin.off()
	time.sleep_ms(100)
	resetpin.on()

#end doreset


# SPI write (with different datatypes)
def spi_write(register,data, nodrop=False):
	def d2bytes(d):
		if type(d) == int: return bytes([d])
		elif type(d) == str: return bytes([ord(c) for c in d])
		elif type(d) == bytes: return d
		elif type(d) == list: return [d2bytes(c) for c in d]
		else:
			print("unknown datatype in spi_write"+str(type(d)))
		
	#end def
	
	nss.off()
	spi.write(d2bytes(register | RH_SPI_WRITE_MASK))

	towrite=d2bytes(data)
	
	if (type(towrite) == bytes):
		spi.write(towrite)
	elif (type(towrite) == list):
		for c in towrite:
			spi.write(c)
	else:
		print("unknown datatype in spi_write"+str(type(data)))
		print(type(data))

	if nodrop == False:
		nss.on()

# end "spi_write"

# SPI read
# spi_read returns bytes!
def spi_read(register):
	data=array.array('H')

	nss.off()
	spi.write(bytes([register & ~RH_SPI_WRITE_MASK]))
	data=spi.read(1)
	nss.on()
	return(data)

# end "spi_read"


# Set Frequency
def setFrequency(centre):
	frf = (centre * 1000000.0) / RH_RF95_FSTEP
	spi_write(RH_RF95_REG_06_FRF_MSB, (int(frf) >> 16) & 0xff)
	spi_write(RH_RF95_REG_07_FRF_MID, (int(frf) >> 8) & 0xff)
	spi_write(RH_RF95_REG_08_FRF_LSB, int(frf) & 0xff)
	_usingHFport = (centre >= 779.0)

# end "setFrequency"




def setTxPower(power):
	if (power > 23):
		power = 23
	if (power < 5):
		power = 5

	if (power > 20):
		spi_write(RH_RF95_REG_4D_PA_DAC, RH_RF95_PA_DAC_ENABLE)
		power -= 3
	else:
		spi_write(RH_RF95_REG_4D_PA_DAC, RH_RF95_PA_DAC_DISABLE)

	spi_write(RH_RF95_REG_09_PA_CONFIG, RH_RF95_PA_SELECT | (power-5))

# end "setTxPower"


def setModeIdle():
	spi_write(RH_RF95_REG_01_OP_MODE, RH_RF95_MODE_STDBY)
	

def setModeTx():
	spi_write(RH_RF95_REG_01_OP_MODE, RH_RF95_MODE_TX)
#end setmodetx




def initchip():
	DoReset()
	time.sleep(1)


	# set chip in FSK/OOK and SLEEP mode
	spi_write(RH_RF95_REG_01_OP_MODE, RH_RF95_MODE_SLEEP) 

	#set bitrate
	# 1200 baud: 0x68,0x2B
	# see table 19, page 47 (PDF) of the sx1278 dataheet
	spi_write(RH_RF95_REG_02_BRT_MSB, 0x68) 
	spi_write(RH_RF95_REG_03_BRT_LSB, 0x2B) 


	# set frequency
	setFrequency(XMITFREQ) # should be 439.9875 

	# set tx power
	setTxPower(2)

	# go to mode idle
	spi_write(RH_RF95_REG_01_OP_MODE,RH_RF95_MODE_STDBY)


	# set length of preamble to 180
	# (minimum is 576 bits = 72 octets), then multiplied by 1200/512
	# according the https://www.sigidwiki.com/wiki/POCSAG, the preamble seems to be the same length (in time) for 512 and 1200 baud 
	spi_write(RH_RF95_REG_25_PRA_MSB, 0x00)
	spi_write(RH_RF95_REG_25_PRA_LSB, 180)	


	# setting up packet mode
	# ## note: the FSK polarity of POCSAG is inverted compaired to the sx1276 -> so we need to invert everything
	spi_write(RH_RF95_REG_27_SYN_CFG, 0x20) # preample is inverted, no sync word
	spi_write(RH_RF95_REG_30_PKT_CF1, 0x00) # fixed length, no DC-free encoding, no crc, no addr filter)
	spi_write(RH_RF95_REG_31_PKT_CF2, 0x40) # packet mode, no io-homecontrol compat. mode

	# set FIFO threshhold to 30
	# allows to upload 30 octets to the FIFO per transaction
	spi_write(RH_RF95_REG_35_FIF_THR, 0x9e) # set length to 30 (0x1e) + 0x80 for the TxStartCondition

#end init chip


### POCSAG related functions
# original source here: https://github.com/on1arf/gr-pocsag

def CalculateCRCandParity(datatype,data):
	cw=data<<11 

	# make leftmost bit "1" for datatype 1 (text)
	if datatype == 1:
		cw |= 0x80000000
	#end if

	local_cw=cw

	for i in range(21):
		if (cw & 0x80000000) > 0:
			cw ^= 0xED200000
		#end if
		cw <<= 1
	#end for

	local_cw |= (cw >> 21)


	parity=0
	cw=local_cw
	for i in range(32):
		if (cw & 0x80000000) > 0:
			parity += 1
		#end if
		cw <<= 1
	#end for

	# make even parity
	local_cw += (parity % 2)

	return(local_cw)
# end Calculate CRC and Parity



def createpocsagmsg(address, source, txt):

	# checking input
	if not (0 < address <= 0x1fffff):
		errmsg="Invalid address "+str(address)
		raise ValueError(errmsg)
	#end if

	if not (0 <= source <= 3):
		errmsg="Invalid source "+str(source)
		raise ValueError(errmsg)
	#nd if


	if len(txt) == 0:
		raise ValueError("No text")
	#end if


	if len(txt) >= 40:
		txt=txt[:39]
		print("Warning, text truncated to 39 characters: {txt}".format(txt=txt))
	

	# init pocsag message
	# init data
	# 2 batches
	# 1 batch = sync codeword + 8 frames
	# 1 frame = 1 codeword

	syncpattern = 0xAAAAAAAA 
	synccodeword = 0x7cd215d8
	idlepattern  = 0x7ac9c197 


	# init all codewords with idle pattern: 2 batches = 16 frames = 32 codewords
	codeword = [idlepattern for _ in range(32)]


	# part 1: address + source 

	# parse address and source
	addressline=address>>3

	# add address-source
	addressline<<=2
	addressline += source


	# the message starts at the frame address determined by the last 3 bits of the address
	cwnum = ((address % 8) << 1) # codeword number

	codeword[cwnum]=CalculateCRCandParity(datatype = 0, data = addressline)


	# part 2: text

	# 2.1 convert text into int, also add EOT char
	ts=[ord(c) for c in txt] + [0x04] 

	## 2.2 make sure all characers are 7 bit
	#ts=list(map(lambda x: x%128, ts))

	# 2.3 create one big list of bits
	textbits=[]

	bitw=(0x01,0x02,0x04,0x08,0x10,0x20,0x40)
	for c in ts:
		# convert character to 7-character bit-string)
		# note, for transmission, the bit-order must be reversed, so start with LSB
		charbits=[1 if (c & bitw[i]) else 0  for i in range(7) ]

		# add to total string
		textbits += charbits
	#end for


	# 2.4 make the list of bits  a multiple of 20 bits

	# add '1010...' or '0101...' depending on the last bit of the list
	if textbits[-1] == 1:
		textbits += [0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1]
	else:
		# last bit is a 0
		textbits += [1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0]
	#end

	ncw = len(textbits)//20 # number of codewords
	textbits=textbits[:(ncw*20)] # truncate to a multiple of 20



	# 2.5 for every block of 20 bits, calculate crc and partity, and add to codeword

	startbit=0
	stopbit=20 # (actually, the 19th bit)
	for i in range(ncw):
		thiscw=textbits[startbit:stopbit]
		thiscw_i=0
		for i in range(20):
			thiscw_i<<=1 # multiply by 2
			thiscw_i+=thiscw[i]
		#end for 
			
		#move up all pointers
		startbit=stopbit # stopbit is startbit + 20
		stopbit += 20

		#codeword pointer
		cwnum += 1

		# calculate CRC for a text block (datatype = 1)
		codeword[cwnum]=CalculateCRCandParity(datatype = 1, data = thiscw_i)
	#end for


	# 3. now create complete pocsag message
	# sync codeword at beginning of the 1st batch
	ret=[synccodeword]

	# add frames 0 to 7 (i.e. codewords 0 to 15)
	ret += [codeword[n] for n in range(16)]



	# create add 2nd batch if the text has spilled into the 2nd batch
	if cwnum >=  16:
		# long message, 2 batches
		nbatch=2

		# add sync codeword
		ret.append(synccodeword)

		# and add frames 8 to 15 (i.e. codewords 16 to 31)
		ret += [codeword[n] for n in range(16,32)]
	else:
		# short message, 1 batch
		nbatch=1
	#end else - if


	return((nbatch,ret))

# end create createpocsagmsg


# ### some more support functions
# convert long to 4 octets (MSB first), also do inversion!
def long4octets(l):
	return (((l>>24)&0xff)^0xff,((l>>16)&0xff)^0xff,((l>>8)&0xff)^0xff,(l&0xff)^0xff)


###### start demo 

def transmitmsg(address,source,txt):
	initchip()

	(nbatch,ret) = createpocsagmsg(address, source, txt)


	pocsag8b=[]
	for elem in ret:
		pocsag8b += long4octets(elem)
	#end for


	# 1 batch = 17 cz = 17 * 2 * 2 octets = 68 octets
	d1=pocsag8b[:60] # 60 octets
	d2=pocsag8b[60:] # 8 octets

	# set packet length
	spi_write(RH_RF95_REG_32_PAY_LEN, 68)

	# write 1st block of 60 octets
	spi_write(RH_RF95_REG_00_FIFO,d1)

	# start TX
	setModeTx()

	# wait until Fifo Threadhold empty
	while (spi_read(RH_RF95_REG_3F_IRQ_FL2)[0] & 0x20): pass

	# write 2nd block (8 octets)
	spi_write(RH_RF95_REG_00_FIFO,d2)

	# wait until packet done
	while not (spi_read(RH_RF95_REG_3F_IRQ_FL2)[0] & 0x08): pass
	time.sleep_ms(100) # wait a little bit before shutting down
	setModeIdle()



	if (nbatch == 1):
		# 1 batch = 17 cz = 17 * 2 * 2 octets = 68 octets
		d1=pocsag8b[:60] # 60 octets
		d2=pocsag8b[60:] # 8 octets

		# set packet length
		spi_write(RH_RF95_REG_32_PAY_LEN, 68)

		# write 1st block of 60 octets
		spi_write(RH_RF95_REG_00_FIFO,d1)
		
		# start TX
		setModeTx()

		# wait until Fifo Threadhold empty
		while (spi_read(RH_RF95_REG_3F_IRQ_FL2)[0] & 0x20): pass

		# write 2nd block (8 octets)
		spi_write(RH_RF95_REG_00_FIFO,d2)

		# wait until packet done
		while not (spi_read(RH_RF95_REG_3F_IRQ_FL2)[0] & 0x08): pass
		time.sleep_ms(100) # wait a little bit before shutting down
		setModeIdle()

	else:
		# 2 batches = 34 cz = 34 * 2 * 2 octets = 136 octets
		d1=pocsag8b[:60] # 60 octets
		d2=pocsag8b[60:120] # 60 octets
		d3=pocsag8b[120:] # 16 octets

		# set packet length
		spi_write(RH_RF95_REG_32_PAY_LEN, 136)

		# write 1st block of 60 octets
		spi_write(RH_RF95_REG_00_FIFO,d1)
		
		# start TX
		setModeTx()

		# wait until Fifo Threadhold empty
		while (spi_read(RH_RF95_REG_3F_IRQ_FL2)[0] & 0x20): pass

		# write 2nd block (60 octets)
		spi_write(RH_RF95_REG_00_FIFO,d2)

		# wait until Fifo Threadhold empty
		while (spi_read(RH_RF95_REG_3F_IRQ_FL2)[0] & 0x20): pass

		# write 3th block (16 octets)
		spi_write(RH_RF95_REG_00_FIFO,d3)

		# wait until packet done
		while not (spi_read(RH_RF95_REG_3F_IRQ_FL2)[0] & 0x08): pass
		time.sleep_ms(100) # wait a little bit before shutting down
		setModeIdle()

	# end if
	
#end transmitmsg


