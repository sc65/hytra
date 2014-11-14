import optparse
import numpy as np
import h5py
import os
import sys
import scipy.misc

def getoutLabelImage(labelfile,t):
    try:
        return np.array(labelfile["exported_data_T"][t,...]).squeeze().astype(np.int)        
    except:
        return np.transpose(np.array(labelfile["exported_data"][t,...]).squeeze().astype(np.int))

def generate_groundtruth(options):
    # read image

    # read ground truth file
    with h5py.File(options.input_file, 'r') as inputfile:

        if(options.end == -1):
            options.end = int(inputfile["tracking"].keys()[-1])


        inId_to_outId_dics = {}
        outId_to_inId_dics = {}
        inId_to_outId_funct = {}

        splitdict = {}
        movedict = {}


        for t in xrange(options.start,options.end+1,1):

            # #just for fun :)
            sys.stdout.write('\r')
            # the exact output you're looking for:
            sys.stdout.write("[%-20s] %d%%" % ('='*(20*t/options.end), (100*t/options.end)))
            sys.stdout.flush()

            outputFileName = options.output_dir.rstrip('/')+ "/%04d.h5" % t
            #create output file
            if os.path.exists(outputFileName):
                os.remove(outputFileName)

            with h5py.File(outputFileName, 'w') as out_h5:

                trackingdata = out_h5.create_group('tracking')
                meta = out_h5.create_group('objects/meta')

                with h5py.File(options.label_image, 'r') as labelfile:

                    outLabelImage = getoutLabelImage(labelfile,t)
                    inputLabelImage   = np.array(inputfile["label_image"][t,...]).squeeze().astype(np.int)

                    inputIds  =  np.unique(inputLabelImage).flatten()
                    outputIds =  np.unique(outLabelImage).flatten()

                    #remove background
                    inputIds = np.delete(inputIds,np.where(inputIds == 0))
                    outputIds = np.delete(outputIds,np.where(outputIds == 0))

                    meta.create_dataset("id", data=outputIds, dtype='u2')
                    meta.create_dataset("valid", data=np.ones(outputIds.shape[0]), dtype='u2')

                    #create id translation dictionary 

                    inId_to_outId_dics[t] = {}
                    outId_to_inId_dics[t] = {}

                    applist = []
                    dislist = []
                    movlist = []
                    spllist = []
                    merlist = []

                    for outId in outputIds:
                        if( outId > 0 ):
                            outId_to_inId_dics[t][outId] = np.unique(inputLabelImage[outLabelImage==outId]).tolist()
                            if(0 in outId_to_inId_dics[t][outId]):
                                outId_to_inId_dics[t][outId].remove(0)

                            if(len(outId_to_inId_dics[t][outId]) == 0):
                                del outId_to_inId_dics[t][outId]
                            elif(len(outId_to_inId_dics[t][outId]) == 1):
                                outId_to_inId_dics[t][outId] = outId_to_inId_dics[t][outId][0]
                            else:
                                merlist.append([outId,len(outId_to_inId_dics[t][outId])])
                                outId_to_inId_dics[t][outId] = outId_to_inId_dics[t][outId][0]

                    for inId in inputIds:
                        if( inId > 0 ):
                            inId_to_outId_dics[t][inId] = np.unique(outLabelImage[inputLabelImage==inId]).tolist()
                            
                            if(0 in inId_to_outId_dics[t][inId]):
                                inId_to_outId_dics[t][inId].remove(0)

                            if(len(inId_to_outId_dics[t][inId]) == 0):
                                inId_to_outId_dics[t][inId] = -1
                            elif(len(inId_to_outId_dics[t][inId]) == 1):
                                inId_to_outId_dics[t][inId] = inId_to_outId_dics[t][inId][0]
                            else:
                                inId_to_outId_dics[t][inId] = inId_to_outId_dics[t][inId][0]#just use one of the ids


                    inId_to_outId_funct[t] = np.vectorize(inId_to_outId_dics[t].get)

                    applist = []
                    disapplist = []
                    movelist = []
                    splitlist= []

                    if(len(merlist) > 0):
                        #TODO: THIS IS WRONG NEED TO ADD NUMBER OF MERGERS AND OUT ID
                        trackingdata.create_dataset("Mergers", data=np.asarray(merlist), dtype='u2') 

                    if(len(inId_to_outId_funct) > 1):
                        if("Moves" in inputfile["tracking"][options.format.format(t)].keys()):
                            moves = np.array(inputfile["tracking"][options.format.format(t)]["Moves"]).squeeze().astype(np.int)
                            moves = np.reshape(moves, (-1,2))
                            remlist = []

                            if(np.any(moves == 0)):
                                print "ERROR ::: 0 in moves found"
                                exit()

                            # for i,mov_row in  enumerate(moves):
                            #     # print i,mov_row
                            #     if mov_row[0] == 0 or mov_row[1] == 0:
                            #         remlist.append(i)

                            # moves = np.delete(moves,remlist,axis=0)
                            # print inId_to_outId_dics
                            # print "moves",moves[:,0]

                            # print "inputIds",inputIds
                            # for m in moves[:,0]:
                            #     print m
                            #     if(not m in inId_to_outId_dics[t-1]):
                            #         print m, " not in inId_to_outId_dics","at t=",t-1
                            #         try:
                            #             print inId_to_outId_dics[t][m]," at t=",t
                            #             inId_to_outId_dics[t-1][m] = inId_to_outId_dics[t][m]
                            #             inId_to_outId_funct[t] = np.vectorize(inId_to_outId_dics[t].get)
                            #             print "but found in next label image"
                            #         except:
                            #             print "and not even found in the next label image"

                            # print inId_to_outId_funct[t-1](moves[:,0])
                            # print inId_to_outId_funct[t](moves[:,1])
                            moves[:,0] = inId_to_outId_funct[t-1](moves[:,0])
                            moves[:,1] = inId_to_outId_funct[t](moves[:,1])


                            #make moves without match
                            # print moves to disapp and app
                            movelist = moves.tolist()
                            for mov in movelist:
                                if (-1 in mov):
                                    print "\nresolving ", mov, "at ",t
                                    if(mov[0] == -1 and mov[1] > 0):#appearance
                                        applist.append(mov[1])
                                    if(mov[1] == -1 and mov[0] > 0):#disappearance
                                        # print mov[0]
                                        disapplist.append(mov[0])

                            movelist = [mov for mov in movelist if (not -1 in mov)]

                            trackingdata.create_dataset("Moves", data=moves, dtype='u2')
                            movedict[t] = moves

                        if("Splits" in inputfile["tracking"][options.format.format(t)].keys()):
                            splits = np.array(inputfile["tracking"][options.format.format(t)]["Splits"]).squeeze().astype(np.int)
                            splits = np.reshape(splits,(-1,3))
                            splits[:,0] = inId_to_outId_funct[t-1](splits[:,0])
                            splits[:,1:] = inId_to_outId_funct[t](splits[:,1:])

                            # splitlist = splits.tolist()
                            # for spl in splits:
                            #     if (-1 in spl):
                            #         print "error can not resolve split"
                            #         exit()

                            splitlist = splits.tolist()
                            for spl in splitlist:
                                if (-1 in spl):
                                    print "\nresolving ", spl, "at ",
                                    if(spl[0] == -1):
                                        if spl[1] > 0:
                                            applist.append(spl[1])
                                        if spl[2] > 0:
                                            applist.append(spl[2])
                                    else:
                                        disapplist.append(spl[0])
                                        if spl[1] > 0:
                                            movelist.append([spl[0],spl[1]])
                                        if spl[2] > 0:
                                            movelist.append([spl[0],spl[2]])

                            splitlist = [spl for spl in splitlist if (not -1 in spl)]


                        for i in inId_to_outId_dics[t]:
                            outid = inId_to_outId_dics[t][i]
                            if outid > 0:
                                if((t in movedict and not np.any(movedict[t][:,1]==outid)) and 
                                   (t in splitdict and not np.any(splitdict[t][:,1:]==outid))):
                                    applist.append(outid)


                        for i in inId_to_outId_dics[t-1]:
                            outid = inId_to_outId_dics[t-1][i]
                            if outid > 0:
                                if((t in movedict and not np.any(movedict[t][:,0]==outid)) and 
                                   (t in splitdict and not np.any(splitdict[t][:,0]==outid))):
                                    disapplist.append(outid)

                        if(len(movelist) > 0):
                            moves = np.array(movelist)

                            if(np.any(moves == -1)):
                                print "-1 in moves !!! at timestep",t
                                print "#####################################"
                                print np.array(inputfile["tracking"][options.format.format(t)]["Moves"]).squeeze().astype(np.int)
                                print movelist
                                print moves
                                exit()




                        if(len(splitlist) > 0):
                            splits = np.array(splitlist)
                            trackingdata.create_dataset("Splits", data=splits, dtype='u2') 
                            splitdict[t] = splits

                            if(np.any(splits == -1)):
                                print "-1 in splits !!! at timestep",t
                                print "#####################################"
                                print splits
                                exit()


                        if(len(applist) > 0):
                            trackingdata.create_dataset("Appearances", data=np.reshape(np.asarray(applist),(-1,1)), dtype='u2')
                        if(len(disapplist) > 0):
                            trackingdata.create_dataset("Disappearances", data=np.reshape(np.asarray(disapplist),(-1,1)), dtype='u2') 








if __name__ == "__main__":
    parser = optparse.OptionParser(description='Compute TRA loss of a new labeling compared to ground truth')

    # file paths
    parser.add_option('--output-dir', type=str, dest='output_dir', default=".",
                        help='Folder where the groundTruthfiles are created')
    parser.add_option('--input-file', type=str, dest='input_file',
                        help='Filename for the resulting HDF5 file.')

    parser.add_option('--input_format', type=str, dest='format',
                        help='added 0 to number string, default="{0:03d}", produces 004 from 4',default="{0:03d}")

    parser.add_option('--start', type=int, dest='start',
                        help='first timestep',default=0)
    parser.add_option('--end', type=int, dest='end',
                        help='last timestep',default=-1)
    parser.add_option('--label-image', type=str, dest='label_image',
                        help='file to label image with ids corresponding to opengm ids. ')

    # parse command line
    opt , args = parser.parse_args()

    generate_groundtruth(opt)