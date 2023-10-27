from xml.etree.ElementTree import Element, SubElement, Comment, tostring
import sys
import os
import rhapi_mod as rhapi
from xml.etree import ElementTree
from xml.dom import minidom
from datetime import datetime, timedelta
from strip_parser import *

def xml_writer(DataFile,option,test):

    if ".txt" in DataFile:
        print ("Analyzing: ", DataFile)
        nameForSave = DataFile.strip('.txt')
        print ("Getting Run Number")
        if test:
            RunNum = 1
        else:
            RunNum = getrunnum()

        print ("Run #: ", RunNum)

        SensorName, SensorType, User, TimeStamp, pdata, notes = parseFile(DataFile)
        if (option == 'RS'):
            notes = "RPoly Measurement done at 1V. " + notes

        datetime_obj = datetime.strptime(TimeStamp, '%m/%d/%Y %I:%M:%S %p')
        print("Header Info: ", datetime_obj, SensorName, User)

            # Filling out xml header
        top = Element('ROOT')
        header = add_branch(top, "HEADER")
        type = add_branch(header, "TYPE")
        exttable = add_branch(type, "EXTENSION_TABLE_NAME", "TEST_SENSOR_SMMRY")
        name = add_branch(type, "NAME", "Tracker Strip-Sensor Summary Data")
        run = add_branch(header, "RUN")
        runtype = add_branch(run, "RUN_TYPE", "SQC")
        runnumtag = add_branch(run, "RUN_NUMBER", str(RunNum))
        location = add_branch(run, "LOCATION", "Brown")
        username = add_branch(run, "INITIATED_BY_USER", User)
        runbegin = add_branch(run, "RUN_BEGIN_TIMESTAMP", str(datetime_obj))
        comment = add_branch(run, "COMMENT_DESCRIPTION", notes)
        dataset = add_branch(top, "DATA_SET")
        comment2 = add_branch(dataset, "COMMENT_DESCRIPTION", notes)
        version = add_branch(dataset, "VERSION", "1.0")
        part = add_branch(dataset, "PART")
        kindpart = add_branch(part, "KIND_OF_PART", SensorType)
        barcode = add_branch(part, "BARCODE", SensorName)

        global_curr = []
        leakage_curr = []
        cap = []
        #cv10kHz = []
        #bv = []
        temp = []
        secs = []
        stripnum = []
        res = []
        rh = []
        pincurr = []

        if 'interstrip' in DataFile or 'Interstrip' in DataFile:
         res = [1e-9*float(val) for val in pdata['Interstrip Resistance']]   
         cap = [1e12*float(val) for val in pdata['Interstrip C']]
            
        else:
            res = [1e-9*float(val) for val in pdata['Poly Resistance LowV']]
            cap = [1e12*float(val) for val in pdata['Coupling Cap']]
            pincurr = [1e9*float(val) for val in pdata['Pinhole']]
            leakage_curr = [1e9*float(val) for val in pdata['Istrip_Median']]
        
        global_curr = [1e9*float(val) for val in pdata['Global Current']]
        temp = [float(val) for val in pdata['ChuckT']]
        rh = [float(val) for val in pdata['RH']]
        secs = [int(val) for val in pdata['Time']]
        stripnum = [int(val) for val in pdata['Strip']]

        #calculate the time
        deltasecs = [val - secs[0] for val in secs]
        time = [datetime_obj + timedelta(seconds=val - secs[0]) for val in secs]

        AvTemp = str(sum(temp)/len(temp))
        if sum(rh) > 0:
            AvRH = str(sum(rh)/len(rh))
        else:
            AvRH = "4.0"

        envdata = add_branch(dataset, "DATA")
        avgtemp = add_branch(envdata, "AV_TEMP_DEGC", AvTemp)
        avgrh = add_branch(envdata, "AV_RH_PRCNT", AvRH)
        if option == 'CIS': freq = add_branch(envdata, "FREQ_HZ", "1000000.0")
        if option == 'CS': freq = add_branch(envdata, "FREQ_HZ", "1000.0")
        child_DS = add_branch(dataset, "CHILD_DATA_SET")
        header2 = add_branch(child_DS, "HEADER")
        type2 = add_branch(header2, "TYPE")
        exttable2 = add_branch(type2, "EXTENSION_TABLE_NAME", "TEST_SENSOR_"+str(option))
        name2 = add_branch(type2, "NAME", "Tracker Strip-Sensor "+str(option)+" Test")
        dataset2 = add_branch(child_DS, "DATA_SET")
        comment3 = add_branch(dataset2, "COMMENT_DESCRIPTION", notes)
        version2 = add_branch(dataset2, "VERSION", "1.0")
        part2 = add_branch(dataset2, "PART")
        kindpart2 = add_branch(part2, "KIND_OF_PART", SensorType)
        barcode2 = add_branch(part2, "BARCODE", SensorName)

        if option == 'CIS':
            for i in range(len(pdata['Strip'])):
                cvivdata = add_branch(dataset2, "DATA")
                stripcouplenum = add_branch(cvivdata, "STRIPCOUPLE", str(stripnum[i]))
                capdata = add_branch(cvivdata, "CAPCTNC_PFRD", str(cap[i]))
                tempdata = add_branch(cvivdata, "TEMP_DEGC", str(temp[i]))
                if rh[i] > 0:
                    rhdata = add_branch(cvivdata, "RH_PRCNT", str(rh[i]))
                biasdata = add_branch(cvivdata, "BIASCURRNT_NAMPR", str(global_curr[i]))
                timestamp = add_branch(cvivdata, "TIME", str(time[i]))

        if option == 'CS':
            for i in range(len(pdata['Strip'])):
                cvivdata = add_branch(dataset2, "DATA")
                strip = add_branch(cvivdata, "STRIP", str(stripnum[i]))
                capdata = add_branch(cvivdata, "CAPCTNC_PFRD", str(cap[i]))
                tempdata = add_branch(cvivdata, "TEMP_DEGC", str(temp[i]))
                if rh[i] > 0:
                    rhdata = add_branch(cvivdata, "RH_PRCNT", str(rh[i]))
                biasdata = add_branch(cvivdata, "BIASCURRNT_NAMPR", str(global_curr[i]))
                timestamp = add_branch(cvivdata, "TIME", str(time[i]))

        if option == 'IS':
             for i in range(len(pdata['Strip'])):
                cvivdata = add_branch(dataset2, "DATA")
                strip = add_branch(cvivdata, "STRIP", str(stripnum[i]))
                currdata = add_branch(cvivdata, "CURRNT_NAMPR", str(leakage_curr[i]))
                tempdata = add_branch(cvivdata, "TEMP_DEGC", str(temp[i]))
                if rh[i] > 0:
                    rhdata = add_branch(cvivdata, "RH_PRCNT", str(rh[i]))
                biasdata = add_branch(cvivdata, "BIASCURRNT_NAMPR", str(global_curr[i]))
                timestamp = add_branch(cvivdata, "TIME", str(time[i]))

        if option == 'RIS':
            for i in range(len(pdata['Strip'])):
                cvivdata = add_branch(dataset2, "DATA")
                stripcouplenum = add_branch(cvivdata, "STRIPCOUPLE", str(stripnum[i]))
                resdata = add_branch(cvivdata, "RESSTNC_GOHM", str(res[i]))
                tempdata = add_branch(cvivdata, "TEMP_DEGC", str(temp[i]))
                if rh[i] > 0:
                    rhdata = add_branch(cvivdata, "RH_PRCNT", str(rh[i]))
                biasdata = add_branch(cvivdata, "BIASCURRNT_NAMPR", str(global_curr[i]))
                timestamp = add_branch(cvivdata, "TIME", str(time[i]))

        if option == 'RS':
            for i in range(len(pdata['Strip'])):
     
                cvivdata = add_branch(dataset2, "DATA")
                strip = add_branch(cvivdata, "STRIP", str(stripnum[i]))
                resdata = add_branch(cvivdata, "RESSTNC_MOHM", str(res[i]*1e3))
                tempdata = add_branch(cvivdata, "TEMP_DEGC", str(temp[i]))
                if rh[i] > 0:
                    rhdata = add_branch(cvivdata, "RH_PRCNT", str(rh[i]))
                biasdata = add_branch(cvivdata, "BIASCURRNT_NAMPR", str(global_curr[i]))
                timestamp = add_branch(cvivdata, "TIME", str(time[i]))


        if option == 'PHS':
            for i in range(len(pdata['Strip'])):
                cvivdata = add_branch(dataset2, "DATA")
                strip = add_branch(cvivdata, "STRIP", str(stripnum[i]))
                currdata = add_branch(cvivdata, "CURRNTPH_NAMP", str(pincurr[i]))
                tempdata = add_branch(cvivdata, "TEMP_DEGC", str(temp[i]))
                if rh[i] > 0:
                    rhdata = add_branch(cvivdata, "RH_PRCNT", str(rh[i]))
                biasdata = add_branch(cvivdata, "BIASCURRNT_NAMPR", str(global_curr[i]))
                timestamp = add_branch(cvivdata, "TIME", str(time[i]))

        #Write xml to file
        #print (tostring(top))
        #print (prettify(top))
        print(nameForSave+'_'+option+".xml")
        f = open(nameForSave+'_'+option+".xml","w")
        f.write(str(prettify(top)))
        f.close()


def getrunnum():
    cli = rhapi.CLIClient()
    cli.parser.url = "http://dbloader-tracker:8113"
    cli.parser.format = "csv"
    cli.parser.QUERY = "select r.run_number from trker_cmsr.trk_ot_test_nextrun_v r"
    #cli.parser.parser_args() =  "--url=http://dbloader-tracker:8113 -f csv \"select r.run_number from trker_cmsr.trk_ot_test_nextrun_v r\""
    #print ("Parser Args", cli.parser.parser_args())
    #sys.exit(cli.run())
    return(cli.run())

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



if __name__ == '__main__':
    test = True
    if len(sys.argv) > 1:
        if sys.argv[1] == "-d":
            test = False
            sys.argv[1] = ""
        else:
            print ("Producing test xmls, to produce db ready xmls use python xml_writer_strips -d flag")
    else:
        print ("Producing test xmls, to produce db ready xmls use python xml_writer_strips -d flag")
    drop = ['Time', '_0', '_1', '_2', '_3', '_Mean', '_V']
    filelist = list_files(".")
    for filename in filelist:
        if ".txt" in filename:
            if "interstrip" in filename or 'Interstrip' in filename:
                xml_writer(filename, 'CIS', test)
                xml_writer(filename, 'RIS', test)
            else:
                xml_writer(filename, 'PHS', test)
                xml_writer(filename, 'RS', test)
                xml_writer(filename, 'CS', test)
                xml_writer(filename, 'IS', test)
