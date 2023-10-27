from xml.etree.ElementTree import Element, SubElement, Comment, tostring
import sys
import os
import itertools
import rhapi_mod as rhapi
from xml.etree import ElementTree
from xml.dom import minidom
from datetime import datetime

def getrunnum():
    cli = rhapi.CLIClient()
    cli.parser.url = "http://dbloader-tracker:8113"
    cli.parser.format = "csv"
    cli.parser.QUERY = "select r.run_number from trker_cmsr.trk_ot_test_nextrun_v r"
    #cli.parser.parser_args() =  "--url=http://dbloader-tracker:8113 -f csv \"select r.run_number from trker_cmsr.trk_ot_test_nextrun_v r\""
    #print ("Parser Args", cli.parser.parser_args())
    #sys.exit(cli.run())
    return(cli.run())

def getradinfo():
    f = open("RadInfoTable.csv","r")
    header = f.readline().split(',')
    fileline = f.readline()
    data = []
    while fileline:
        data.append(fileline.split(','))
        fileline = f.readline()
    return header, list(map(list, zip(*data)))

def prettify(elem):
    """Return a pretty-printed XML string for the Element.
    """
    rough_string = ElementTree.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


def list_files(dir):
   files = []
   for obj in os.listdir(dir):
      if os.path.isfile(obj):
         files.append(obj)
   return files


def add_branch(tree, branchname, data=""):

	child = SubElement(tree, branchname)
	child.text = data
	return child


test = True
if len(sys.argv) > 1:
    if sys.argv[1] == "-d":
        test = False
        sys.argv = ["test.py"] 
    else:
        print ("Producing test xmls, to produce db ready xmls use python xml_writer_strips -d flag")
else:
    print ("Producing test xmls, to produce db ready xmls use python xml_writer_strips -d flag")

radheader,raddata = getradinfo()
print (raddata[0])

for cviv in ["IV","CV"]:
 #for state in ["Preirrad", "Postirrad"]:
 # statedir = os.path.join(".",state)
 # for struct in os.listdir(statedir):
 #   structdir = os.path.join(statedir,struct)
 #   filelist = list_files(structdir)
    filelist = list_files(".")
    for cvivDataFile in filelist:
        if ".txt" in cvivDataFile and cviv in cvivDataFile:
            print ("Analyzing: ", cvivDataFile)
            if "20min" in cvivDataFile:
                anntime = 71.19
            elif "1100min" in cvivDataFile:
                anntime = 3915.6
            elif ("80m" in cvivDataFile) or ("Irrad" in cvivDataFile):
                anntime = 284.76
            else:
                anntime = 0
            nameForSave = cvivDataFile.strip('.txt')

            grconnected = "F"
            if "DIODEQUARTER" in cvivDataFile:
                structure = "DIODE_QUARTER"
            elif "DIODEHALFPSTOP" in cvivDataFile:
                structure = "DIODE_HALF_PSTOP"
                if "GR" in cvivDataFile: grconnected = "T"
            elif "DIODEHALF" in cvivDataFile:
                structure = "DIODE_HALF"
            elif "DIODE" in cvivDataFile:
                structure = "DIODE"
            elif "SENSOR" in cvivDataFile:
                structure = "BABYSENSOR"

            SensorName = cvivDataFile[3:20]
            radrun_idx = len(tuple(itertools.takewhile(lambda x: SensorName[0:8] not in x, raddata[0])))
            print ("Sensor:", SensorName, radrun_idx)

            print ("Getting Run Number")
            if test:
                RunNum = 1
            else:
                RunNum = getrunnum()
            print ("Run #: ", RunNum, cvivDataFile)

            with open(cvivDataFile, "r") as df:
                #Reading Text File Header
                txtLines = [line for line in df]
                Notes = ""
                for line in txtLines:
                    if "Date/Time" in line:
                        TimeStamp = line[11:-1]
                        print (TimeStamp)
                        datetime_obj = datetime.strptime(TimeStamp, '%m/%d/%Y %I:%M:%S %p')
                        print (datetime_obj)
                    #elif "Sensor Name" in line:
                    #    SensorName = line[13:30]
                    #    radrun_idx = len(tuple(itertools.takewhile(lambda x: SensorName[0:8] not in x, raddata[0])))
                    #    print ("Sensor:", line, SensorName, radrun_idx)
                    elif "Tester" in line:
                        User = line[8:-1]
                    elif "Notes" in line:
                        Notes = line[7:-1]
                if "2-S" in SensorName:
                    flavor = "2S Halfmoon S"
                    SensorName += "SS"
                if "PSS" in SensorName:
                    flavor = "PS-s Halfmoon SW"
                    SensorName += "SW"

                print("Header Info: ", datetime_obj, SensorName, flavor, User, Notes)
                idx = [i for i, line in enumerate(txtLines) if "BiasVoltage" in line][0]
                headers = txtLines[idx].split('\t')

                radfac = raddata[radheader.index("Facility")][radrun_idx]
                if (radfac == "RINSC"):
                    radtype = "n"
                elif (radfac == "FNAL"):
                    radtype = "p"
                tgtfluence = raddata[radheader.index("Target Fluence")][radrun_idx]
                measfluence = "0"
                raddate = raddata[radheader.index("Date")][radrun_idx]

                # Filling out xml header
                top = Element('ROOT')
                header = add_branch(top, "HEADER")
                type = add_branch(header, "TYPE")
                exttable = add_branch(type, "EXTENSION_TABLE_NAME", "TEST_ITSENSOR_SMMRY")
                name = add_branch(type, "NAME", "Tracker Halfmoon IT Summary Data")
                run = add_branch(header, "RUN")
                runtype = add_branch(run, "RUN_TYPE", "IT")
                runnumtag = add_branch(run, "RUN_NUMBER", str(RunNum))
                location = add_branch(run, "LOCATION", "Brown")
                username = add_branch(run, "INITIATED_BY_USER", User)
                runbegin = add_branch(run, "RUN_BEGIN_TIMESTAMP", str(datetime_obj))
                comment = add_branch(run, "COMMENT_DESCRIPTION", Notes)
                dataset = add_branch(top, "DATA_SET")
                comment2 = add_branch(dataset, "COMMENT_DESCRIPTION", Notes)
                version = add_branch(dataset, "VERSION", "1.0")
                part = add_branch(dataset, "PART")
                kindpart = add_branch(part, "KIND_OF_PART", flavor)
                barcode = add_branch(part, "NAME_LABEL", SensorName)

                if "CV" in cvivDataFile:
                    if "LCR_Cp_freq1000.0" in headers:
                        cv1kHz_idx = headers.index("LCR_Cp_freq1000.0")
                    elif "LCR_Cp_freq1" in headers:
                        cv1kHz_idx = headers.index("LCR_Cp_freq1")
                    #cv10kHz_idx = headers.index("LCR_Cp_freq10000.0")
                    temp_idx = headers.index("Temperature")
                    rh_idx = headers.index("Humidity")

                    cv1kHz = []
                    #cv10kHz = []
                    bv = []
                    temp = []
                    rh = []

                    data = txtLines[idx+1:]
                    for line in data:
                        words = line.split()
                        bv.append(float(words[0]))
                        cv1kHz.append(float(words[cv1kHz_idx])*1e12)
                        #cv10kHz.append(words[cv10kHz_idx])
                        temp.append(float(words[temp_idx]))
                        rh.append(float(words[rh_idx]))

                    for i in range(len(bv)):
                        bv[i] = bv[i]
                        if temp[i] == 25.0:  temp[i] = 18.0
                        if temp[i] == 0.0:  temp[i] = 22.0
                        #if rh[i] < 0: rh[i] = 4.0

                    AvTemp = str(sum(temp)/len(temp))
                    if sum(rh) < 0:
                        AvRH = "4.0"
                    else:
                        AvRH = str(sum(rh)/len(rh))


                    #Writing xml
                    envdata = add_branch(dataset, "DATA")
                    struct = add_branch(envdata, "KIND_OF_HM_STRUCT_ID", structure)
                    radtypetag = add_branch(envdata, "RADIATION_TYP", radtype)
                    radfactag = add_branch(envdata, "RADIATION_FCLTY", radfac)
                    tgtfluencetag = add_branch(envdata, "TARGET_FLUENCE", tgtfluence)
                    measfluencetag = add_branch(envdata, "MEASURED_FLUENCE", measfluence)
                    anntimetag = add_branch(envdata, "ANN_TIME_H_21C", str(anntime))
                    raddatetag = add_branch(envdata, "RADIATION_DATE", raddate)
                    grtag = add_branch(envdata, "GR_CONNECTED", grconnected)
                    avgtemp = add_branch(envdata, "AV_TEMP_DEGC", AvTemp)
                    avgrh = add_branch(envdata, "AV_RH_PRCNT", AvRH)
                    freq = add_branch(envdata, "FREQ_HZ", "1000.0")
                    child_DS = add_branch(dataset, "CHILD_DATA_SET")
                    header2 = add_branch(child_DS, "HEADER")
                    type2 = add_branch(header2, "TYPE")
                    exttable2 = add_branch(type2, "EXTENSION_TABLE_NAME", "TEST_SENSOR_CV")
                    name2 = add_branch(type2, "NAME", "Tracker Halfmoon CV Test")
                    dataset2 = add_branch(child_DS, "DATA_SET")
                    comment3 = add_branch(dataset2, "COMMENT_DESCRIPTION", Notes)
                    version2 = add_branch(dataset2, "VERSION", "1.0")
                    part2 = add_branch(dataset2, "PART")
                    kindpart2 = add_branch(part2, "KIND_OF_PART", flavor)
                    barcode2 = add_branch(part2, "NAME_LABEL", SensorName)
                    for i in range(len(bv)):
                        cvivdata = add_branch(dataset2, "DATA")
                        voltdata = add_branch(cvivdata, "VOLTS", str(bv[i]))
                        capdata = add_branch(cvivdata, "CAPCTNC_PFRD", str(cv1kHz[i]))
                        tempdata = add_branch(cvivdata, "TEMP_DEGC", str(temp[i]))
                        if rh[i] > 0:
                            rhdata = add_branch(cvivdata, "RH_PRCNT", str(rh[i]))

                elif "IV" in cvivDataFile:
                    iv_idx = headers.index("Bias Current_Avg")
                    temp_idx = headers.index("Temperature")
                    rh_idx = headers.index("Humidity")

                    iv = []
                    bv = []
                    temp = []
                    rh = []

                    data = txtLines[idx+1:]
                    for line in data:
                        words = line.split()
                        bv.append(float(words[0]))
                        iv.append(float(words[iv_idx]))
                        temp.append(float(words[temp_idx]))
                        rh.append(float(words[rh_idx]))

                    for i in range(len(bv)):
                        bv[i] = bv[i]
                        iv[i] = iv[i]*1e9
                        if temp[i] == 25.0:  temp[i] = 18.0
                        if temp[i] == 0.0:  temp[i] = 22.0
                        #if rh[i] < 0: rh[i] = 4.0

                    AvTemp = str(sum(temp)/len(temp))
                    if sum(rh) < 0:
                        AvRH = "4.0"
                    else:
                        AvRH = str(sum(rh)/len(rh))

                    #Writing xml
                    envdata = add_branch(dataset, "DATA")
                    struct = add_branch(envdata, "KIND_OF_HM_STRUCT_ID", structure)
                    radtypetag = add_branch(envdata, "RADIATION_TYP", radtype)
                    radfactag = add_branch(envdata, "RADIATION_FCLTY", radfac)
                    tgtfluencetag = add_branch(envdata, "TARGET_FLUENCE", tgtfluence)
                    measfluencetag = add_branch(envdata, "MEASURED_FLUENCE", measfluence)
                    anntimetag = add_branch(envdata, "ANN_TIME_H_21C", str(anntime))
                    raddatetag = add_branch(envdata, "RADIATION_DATE", raddate)
                    grtag = add_branch(envdata, "GR_CONNECTED", grconnected)
                    avgtemp = add_branch(envdata, "AV_TEMP_DEGC", AvTemp)
                    avgrh = add_branch(envdata, "AV_RH_PRCNT", AvRH)
                    child_DS = add_branch(dataset, "CHILD_DATA_SET")
                    header2 = add_branch(child_DS, "HEADER")
                    type2 = add_branch(header2, "TYPE")
                    exttable2 = add_branch(type2, "EXTENSION_TABLE_NAME", "TEST_SENSOR_IV")
                    name2 = add_branch(type2, "NAME", "Tracker Halfmoon IV Test")
                    dataset2 = add_branch(child_DS, "DATA_SET")
                    comment3 = add_branch(dataset2, "COMMENT_DESCRIPTION", Notes)
                    version2 = add_branch(dataset2, "VERSION", "1.0")
                    part2 = add_branch(dataset2, "PART")
                    kindpart2 = add_branch(part2, "KIND_OF_PART", flavor)
                    barcode2 = add_branch(part2, "BARCODE", SensorName)
                    for i in range(len(bv)):
                        cvivdata = add_branch(dataset2, "DATA")
                        voltdata = add_branch(cvivdata, "VOLTS", str(bv[i]))
                        currdata = add_branch(cvivdata, "CURRNT_NAMP", str(iv[i]))
                        tempdata = add_branch(cvivdata, "TEMP_DEGC", str(temp[i]))
                        if rh[i] > 0:
                            rhdata = add_branch(cvivdata, "RH_PRCNT", str(rh[i]))

                #Write xml to file
                #print (tostring(top))
                #print (prettify(top))
                print(nameForSave+".xml")
                f = open(nameForSave+".xml","w")
                f.write(str(prettify(top)))
                f.close()

