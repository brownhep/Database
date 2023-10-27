from xml.etree.ElementTree import Element, SubElement, Comment, tostring
import sys
import os
import itertools
import rhapi_mod as rhapi
import pandas as pd
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

def readexcel(DataFile):
    sheets_dict = pd.read_excel(DataFile,engine='openpyxl', sheet_name=None, header=0, nrows=5)

    all_sheets = []
    SensorNames = []
    for name, sheet in sheets_dict.items():
        sheet['sheet'] = name
        print(name)
        if not "Unirrad" in name and not "Chart" in name:
            SensorName = name.split("_")[1] + "_" + name.split("_")[2] + "_"
            if "2S" in name:
                SensorName += "2-S"
            elif "PSS" in name:
                SensorName += "PSS"
            all_sheets.append(sheet)
            print(name)
            SensorNames.append(SensorName)

    full_table = pd.concat(all_sheets)
    full_table.reset_index(inplace=True, drop=True)

    print(full_table["sheet"])
    return(SensorNames, full_table)

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

filelist = ["test600.xlsx", "test800.xlsx"]
for DataFile in filelist:
    print ("Analyzing: ", DataFile)
    voltage = DataFile[4:7]
    SensorNames, AliData = readexcel(DataFile)
    for i, SensorName in enumerate(SensorNames):
        nameForSave = SensorName + "_" + voltage
        structure = "BABYSENSOR"
        radrun_idx = len(tuple(itertools.takewhile(lambda x: SensorName[0:8] not in x, raddata[0])))
        print ("Sensor:", SensorName, radrun_idx)

        print ("Getting Run Number")
        if test:
            RunNum = 1
        else:
            RunNum = getrunnum()
        print ("Run #: ", RunNum, DataFile)

        if "2-S" in SensorName:
            flavor = "2S Halfmoon S"
            SensorName += "_SS"
        if "PSS" in SensorName:
            flavor = "PS-s Halfmoon SW"
            SensorName += "_SW"

        TimeStamp = "8/16/2022 4:33:55 PM"
        datetime_obj = datetime.strptime(TimeStamp, '%m/%d/%Y %I:%M:%S %p')
        User = "Eric Spencer"
        Notes = ""
        AvTemp = "-15.0"
        AvRH = "10.0"

        print("Header Info: ", datetime_obj, SensorName, flavor, User, Notes)
#                idx = [i for i, line in enumerate(txtLines) if "BiasVoltage" in line][0]
#                headers = txtLines[idx].split('\t')

        radfac = raddata[radheader.index("Facility")][radrun_idx]
        if (radfac == "RINSC"):
           radtype = "n"
        elif (radfac == "FNAL"):
           radtype = "p"
        tgtfluence = raddata[radheader.index("Target Fluence")][radrun_idx]
        measfluence = raddata[radheader.index("PIN Fluence")][radrun_idx]
        raddate = raddata[radheader.index("Date")][radrun_idx]

        #seedmpv = full_table["Seed MPV"]
        #clustmpv = full_table["Clust MPV"])

        for j in range(5):
            idx = 5*i + j
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


            #Writing xml
            envdata = add_branch(dataset, "DATA")
            struct = add_branch(envdata, "KIND_OF_HM_STRUCT_ID", structure)
            radtypetag = add_branch(envdata, "RADIATION_TYP", radtype)
            radfactag = add_branch(envdata, "RADIATION_FCLTY", radfac)
            tgtfluencetag = add_branch(envdata, "TARGET_FLUENCE", tgtfluence)
            measfluencetag = add_branch(envdata, "MEASURED_FLUENCE", measfluence)
            anntimetag = add_branch(envdata, "ANN_TIME_H_21C", str(AliData["Ann (days@21C)"][idx]*24))
            raddatetag = add_branch(envdata, "RADIATION_DATE", raddate)
            avgtemp = add_branch(envdata, "AV_TEMP_DEGC", AvTemp)
            avgrh = add_branch(envdata, "AV_RH_PRCNT", AvRH)
            child_DS = add_branch(dataset, "CHILD_DATA_SET")
            header2 = add_branch(child_DS, "HEADER")
            type2 = add_branch(header2, "TYPE")
            exttable2 = add_branch(type2, "EXTENSION_TABLE_NAME", "TEST_SENSOR_ALIBAVA")
            name2 = add_branch(type2, "NAME", "Tracker Halfmoon Alibava Test")
            dataset2 = add_branch(child_DS, "DATA_SET")
            comment3 = add_branch(dataset2, "COMMENT_DESCRIPTION", Notes)
            version2 = add_branch(dataset2, "VERSION", "1.0")
            part2 = add_branch(dataset2, "PART")
            kindpart2 = add_branch(part2, "KIND_OF_PART", flavor)
            barcode2 = add_branch(part2, "NAME_LABEL", SensorName)
            cvivdata = add_branch(dataset2, "DATA")
            voltdata = add_branch(cvivdata, "VOLTAGE_V", voltage)
            #capdata = add_branch(cvivdata, "CAPCTNC_PFRD", str(cv1kHz[i]))
            #tempdata = add_branch(cvivdata, "TEMP_DEGC", str(temp[i]))
            #rhdata = add_branch(cvivdata, "RH_PRCNT", str(rh[i]))

            print(nameForSave+".xml")
            f = open(nameForSave+".xml","w")
            f.write(str(prettify(top)))
            f.close()

