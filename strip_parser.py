import os, sys
import pandas as pd
import numpy as np

# functions used for parsing strip measurement file and outputting a pandas dataframe

def parseFile(filename, to_drop=[], remove_leaky=False):

    print('Parsing file:', filename)
    file = open(filename, 'r').read().splitlines()
    # Find out how large the header is
    headerEnd = 0
    for i, line in enumerate(file):
        if line.startswith('Strip') or line.startswith('Bias'):
            headEnd = i
            break
            
    header = file[:i+1]
    file = file[i+1:]
    
    name, type, openCC, openIC, user, time, notes = parseHeader(header)
    meas_list = measOrder(header[-1])
    # create dictionary that holds measurement info
    data = {}
    for meas in meas_list:
        data[meas] = []
    
    for line in file:
        if len(line) == 0: continue
        elif line.startswith('#'):
            if '1000Hz' in line:
                try:
                    openCC = float(line.split(':')[-1])
                except:
                    pass
            elif '100000Hz' in line or '1000000Hz' in line:
                try:
                    openIC = float(line.split(':')[-1])
                except:
                    pass
            continue
        if line.startswith('Strip') or line.startswith('Bias'): 
            continue
            #meas_list = measOrder(line)
            #continue
        vals = line.strip().split('\t')
        vals = [val.strip() for val in vals]
        for i, val in enumerate(vals):
            key = meas_list[i]
            if key == 'Strip':
                data[key].append(int(val))
            else:
                data[key].append(float(val))

    if __name__ == '__main__':
        for key in data.keys():
            print(key, len(data[key]))
    # Turn dictionary of measurements into a pandas dataframe
    pdata = pd.DataFrame.from_dict(data=data)

    # now perform some extra processing to remove cap offsets
    if 'Coupling Cap' in meas_list:
        pdata['Coupling Cap'] = pdata['Coupling Cap'] - openCC
        pdata['Coupling Cap'][pdata['Coupling Cap'] < 0.] = 0.
    if 'Interstrip C' in meas_list:
        pdata['Interstrip C'] = pdata['Interstrip C'] - openIC
        pdata['Interstrip C'][pdata['Interstrip C'] < 0.] = np.NaN

    # now calculate resistance values
    #if any(['I_RBias_V' in m for m in meas_list]):
    #    v_step, i_cols = rPreProcesses(meas_list, 'I_RBias_V')
    #    i_mat = pdata[i_cols].to_numpy(copy=True)
    #    i_mat = np.transpose(i_mat)
    #    pdata['Poly Resistance'] = np.polyfit(v_step, i_mat, 1)[0]**-1
    if any(['I_RBias_V-5.0' in m for m in meas_list]):
        v_step, i_cols = rPreProcesses(meas_list, 'I_RBias_V-5.0')
        i_mat = pdata[i_cols].to_numpy(copy=True)
        i_mat = np.transpose(i_mat)
        pdata['Poly Resistance'] = np.polyfit(v_step, i_mat, 1)[0]**-1
    if any(['I_RBias_V-1.0' in m for m in meas_list]):
        v_step, i_cols = rPreProcesses(meas_list, 'I_RBias_V-1.0')
        i_mat = pdata[i_cols].to_numpy(copy=True)
        i_mat = np.transpose(i_mat)
        pdata['Poly Resistance LowV'] = np.polyfit(v_step, i_mat, 1)[0]**-1
    if any(['I_RBias Nbr_V' in m for m in meas_list]):
        v_step, i_cols = rPreProcesses(meas_list, 'I_RBias Nbr_V')
        i_mat = pdata[i_cols].to_numpy(copy=True)
        i_mat = np.transpose(i_mat)
        pdata['Poly Resistance Neighbor'] = np.polyfit(v_step, i_mat,1)[0]**-1
    if any(['I_InterstripR_V' in m for m in meas_list]):
        v_step, i_cols = rPreProcesses(meas_list, 'I_InterstripR_V')
        i_mat = pdata[i_cols].to_numpy(copy=True)
        i_mat = np.transpose(i_mat)
        pdata['Interstrip Resistance'] = np.polyfit(v_step, i_mat,1)[0]**-1
        # Get rid of entrees where we dont measure interR
        pdata['Interstrip Resistance'][np.abs(pdata['Interstrip Resistance']) > 1e20] = np.NaN

    print('Created a pandas dataframe with the following axes:', pdata.axes)
    print('Will drop unneeded branches based on following substrins:', to_drop)

    for col in pdata.columns:
        if any([ss for ss in to_drop if ss in col]):
            del pdata[col]
    # rename the Strip column if there is an extra space in the name
    if 'Strip ' in pdata.columns:
        pdata.rename(columns={'Strip ':'Strip'}, inplace=True)
    if remove_leaky:
        if 'Istrip_Median' in pdata.columns:
            pdata['Istrip No Leaky'] = pdata['Istrip_Median']
            pdata['Istrip No Leaky'][abs(pdata['Istrip No Leaky']) > 1e-9] = np.NaN

    print('Dataframe for sensor', name, 'now has the following axes:', pdata.axes)

    if __name__ == '__main__':
        print('Will print 5 measurements:')
        print(pdata.iloc[0])
        print(pdata.iloc[1])
        print(pdata.iloc[2])
        print(pdata.iloc[3])
        print(pdata.iloc[4])

    return name, type, user, time, pdata, notes

def rPreProcesses(meas_list, rtype):
    #if rtype == 'I_RBias_V':
    if 'I_RBias_V' in rtype:
        itype = 'Istrip_Median'
    elif rtype == 'I_RBias Nbr_V':
        itype = 'IstripNbr_Median'
    else:
        itype = 'iMpOsSiBle StRiNg'
    
    i_cols = [m for m in meas_list if rtype in m]
    v_steps = [float(m.split('V')[-1]) for m in i_cols]

    if itype in meas_list:
        i_cols.insert(0, itype)
        v_steps.insert(0, 0.)

    return v_steps, i_cols
    

def parseHeader(lines):

    sensor = ''
    openCC = 0.
    openIC = 0.
    notes = ''

    for line in lines:
        if '1000Hz' in line:
            try:
                openCC = float(line.split(':')[-1])
                print('Found open coupling capacitance measurement:', openCC)
            except:
                print('Open coupling capacitance not measured')
        if '100000Hz' in line or '1000000Hz' in line:
            try:
                openIC = float(line.split(':')[-1])
                print('Found open inter capacitance measurement:', openIC)
            except:
                print('Open interstrip capacitance not measured')
        if "Date/Time" in line:
            TimeStamp = line.split(': ')[-1]
            print("Time Stamp")
            print(TimeStamp)
        if "Tester" in line:
            User = line.split(': ')[-1]
            print("User")
            print(User)

        if 'Sensor Name' in line:
            sensor = line.split()[-1]
            print('*******Found sensor name:', sensor)
            if "2-S" in sensor:
                type = "2S Sensor"
            if "PSS" in sensor:
                type = "PS-s Sensor"
        if 'Notes' in line:
            notes = line.split(':')[1]

    if sensor == '':
        print('****** WARNING ******')
        print('Unable to find sensor name in file header, check file and try re-running code')
        sys.exit()
    return sensor, type, openCC, openIC, User, TimeStamp, notes

def measOrder(line):
    measurements = line.strip().split('\t')
    print('Measurements are:', measurements)
    return measurements

if __name__ == '__main__':
    drop = ['Time', '_0', '_1', '_2', '_3', '_Mean', '_V']
    parseFile(sys.argv[1], drop)
