import os, sys

# functions used for parsing strip measurement file and outputting a pandas dataframe

def cleanFile(filename, to_drop=[], remove_leaky=False):

    print('Parsing file:', filename)
    nameForSave = filename.strip('.txt') + '_clean.txt'
    file = open(filename, 'r').read().splitlines()
    # Find out how large the header is
    headerEnd = 0
    for i, line in enumerate(file):
        if line.startswith('Strip') or line.startswith('Bias'):
            headEnd = i
            break
            
    header = file[:i]
    file = file[i:]

    #Get Measurements
    meas = []
    numruns = 0
    for line in file:
        if line.startswith('Strip'):
            if numruns == 0:
                meas = line.split('\t')
            else:
                for ms in line.split('\t'):
                    if ms not in meas:
                        meas.append(ms)
            numruns += 1
    print ("Number of Different Runs: ", numruns)
    print ("Measurements: ", meas)

    strips = []
    stripdata = []
    for line in file:
        if len(line) == 0: continue
        elif line.startswith('Strip'):
            currmeas = line.split('\t')
        elif not line.startswith('#') and not line.startswith('Strip') and not line.startswith('Bias'):
            dt = line.split('\t')
            strip = dt[0]
            #print (strip), strip in strips
            data = []
            if strip not in strips:
                if len(currmeas) == len(dt):
                    strips.append(strip)
                    data.append([currmeas,dt])
                    stripdata.append(data)
            else:
                #print ("Overwrite Data")
                data = stripdata[strips.index(strip)][0]
                #print ("Old: ", data)
                for ms in currmeas:
                    if ms in data[0]:
                        #print (ms, data[0].index(ms), currmeas.index(ms), len(data[0]), len(data[1]), len(dt))
                        data[1][data[0].index(ms)] = dt[currmeas.index(ms)]
                    else:
                        #print ("DATA: ", data)
                        #print (ms, currmeas.index(ms), len(dt))
                        data[0].append(ms)
                        data[1].append(dt[currmeas.index(ms)])
                stripdata[strips.index(strip)][0] = data
                #print ("New: ", data)
                #data[strips.index(strip)] = line

    print ("Writing clean file ", nameForSave)
    f = open(nameForSave, "w")
    for line in header: 
        f.write(line)
        f.write('\n')
    for ms in meas:
        f.write(ms)
        f.write('\t')
    f.write('\n')
    for dt in stripdata:
        #print (dt)
        f.write(dt[0][1][0])
        for ms in meas: 
            if "Strip" not in ms:
                f.write('\t')
                f.write(dt[0][1][dt[0][0].index(ms)])
        f.write('\n')
    return 


if __name__ == '__main__':
    cleanFile(sys.argv[1])
