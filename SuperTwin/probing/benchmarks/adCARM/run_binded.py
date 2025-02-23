import argparse
import os
import subprocess
#import matplotlib as mpl
#mpl.use('Agg')
#import matplotlib.pyplot as plt
import numpy as np
import datetime

#Mapping between ISA and memory transfer size
mem_inst_size = {"avx512": {"sp": 64, "dp": 64}, "avx": {"sp": 32, "dp": 32}, "avx2": {"sp": 32, "dp": 32}, "sse": {"sp": 16, "dp": 16}, "scalar": {"sp": 4, "dp": 8}}
ops_fp = {"avx512": {"sp": 16, "dp": 8}, "avx": {"sp": 8, "dp": 4}, "avx2": {"sp": 8, "dp": 4}, "sse": {"sp": 4, "dp": 2}, "scalar": {"sp": 1, "dp": 1}}

#Read system configuration file
def read_config(config_file):
    f = open(config_file, "r")
    name = ''
    l1_size = 0
    l2_size = 0
    l3_size = 0

    for line in f:
        l = line.split('=')
        if(l[0] == 'name'):
            name = l[1].rstrip()

        if(l[0] == 'l1_cache'):
            l1_size = l[1].rstrip()

        if(l[0] == 'l2_cache'):
            l2_size = l[1].rstrip()
        
        if(l[0] == 'l3_cache'):
            l3_size = l[1].rstrip()

    return name, l1_size, l2_size, l3_size


def round_power_of_2(number):
    if number > 1:
        for i in range(1, int(number)):
            if (2 ** i >= number):
                return 2 ** i
    else:
        return 1

def carm_eq(ai, bw, fp):
    return np.minimum(ai*bw, fp)


def plot_roofline(name, data, ct):

    fig, ax = plt.subplots(figsize=(7.1875*1.5,3.75*1.5))
    plt.xlim(0.015625, 256)
    plt.ylim(0.25, round_power_of_2(int(data['FP'])))
    ai = np.linspace(0.00390625, 256, num=200000)

    #Ploting Lines
    plt.plot(ai, carm_eq(ai, data['L1'], data['FP']), 'k', lw = 3, label='L1')
    plt.plot(ai, carm_eq(ai, data['L2'], data['FP']), 'grey', lw = 3, label='L2')
    plt.plot(ai, carm_eq(ai, data['L3'], data['FP']), 'k', linestyle='dashed', lw = 3, label='L3')
    plt.plot(ai, carm_eq(ai, data['DRAM'], data['FP']), 'k', linestyle='dotted', lw = 3, label='DRAM')

    #Customization
    #Turn off top and right axis
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)

    plt.ylabel('Performance [GFLOPS/s]', fontsize=18)
    plt.xlabel('Arithmetic Intensity [flops/bytes]', fontsize=18)
    plt.setp(ax.get_xticklabels(), fontsize=18)
    plt.setp(ax.get_yticklabels(), fontsize=18)
    plt.yscale('log', base=2)
    plt.xscale('log', base=2)
    plt.legend(fontsize=18, loc='lower right')
    new_rc_params = {'text.usetex': False,"svg.fonttype": 'none'}
    plt.rcParams.update(new_rc_params)
    plt.tight_layout()
    plt.savefig('Results/' + name + '_roofline_' + str(ct.time()) + '_' + str(ct.date()) + '.svg')

#Run roofline tests
def run_roofline(name, freq, l1_size, l2_size, l3_size, inst, isa, precision, num_ld, num_st, threads, interleaved, num_ops, dram_bytes, test_type, verbose, set_freq, measure_freq, args):
    
    data = {}
    freq_aux = 0

    #Compile benchmark generator
    os.system("make clean && make isa=" + isa)
    if (test_type == 'L1' or test_type == 'roofline'):
        #Run L1 Test 
        num_reps = int(int(l1_size)*1024/(2*mem_inst_size[isa][precision]*(num_ld+num_st)))

        ##binding
        bind = args.binding.split("|")
        
        os.system("./Bench/Bench -test MEM -num_LD " + str(num_ld) + " -num_ST " + str(num_st) + " -precision " + precision + " -num_rep " + str(num_reps))
        
        if(interleaved):
            result = subprocess.run([bind[0], bind[1], bind[2], bind[3], "./bin/test", "-threads", str(threads), "-freq", str(freq), "-measure_freq", str(measure_freq), "--interleaved"], stdout=subprocess.PIPE)
        else:
            result = subprocess.run([bind[0], bind[1], bind[2], bind[3], "./bin/test", "-threads", str(threads), "-freq", str(freq), "-measure_freq", str(measure_freq)], stdout=subprocess.PIPE)
    
        out = result.stdout.decode('utf-8').split(',')

        freq_aux = float(out[2])
        freq = float(out[3])
        data['L1'] = float(((threads*num_reps*(num_ld+num_st)*mem_inst_size[isa][precision]*float(freq_aux))*float(out[1]))/(float(out[0])*float(freq_aux/freq)))
        
        if (verbose > 1):
            print ("---------L1 RESULTS-----------")
            print ("Total Cycles:", out[0],"Total Inner Loop Reps:", out[1], "Number of threads:", threads, "Number of reps:", num_reps,"Number of loads:", num_ld,"Number of stores:", num_st, "Memory instruction size:", mem_inst_size[isa][precision], "Frequency:", freq)
            
            #print ("EXTRA MODIFIERS:", float(threads*num_reps*(num_ld+num_st)*mem_inst_size[isa][precision]*float(freq)))
            
            print ("CYCLES PER INNER LOOP:", (float(out[0])*(freq_aux/freq))/float(out[1]))
        
            print ("ISTRUCTION PER CYCLE:", threads*num_reps*(num_ld+num_st)*float(out[1])/(float(out[0])*float(freq_aux/freq)))
            print ("BYTES PER CYCLE:", threads*num_reps*(num_ld+num_st)*mem_inst_size[isa][precision]*float(out[1])/(float(out[0])*float(freq_aux/freq)))
            print ("BANDWIDTH (Gbps):", data['L1'])
            print ("Max Recorded Frequency (GHz):", freq_aux)
            print ("Nominal Frequency (GHz):", freq)
            print ("Actual Frequency to Nominal Frequency Ratio:", float(freq_aux/freq))
            print ("------------------------------")
        
    if (test_type == 'L2' or test_type == 'roofline'):
        #Run L2 Test
        num_reps = int(1024*(int(l1_size) + (int(l2_size) - int(l1_size))/2)/(mem_inst_size[isa][precision]*(num_ld+num_st)))
    
        os.system("./Bench/Bench -test MEM -num_LD " + str(num_ld) + " -num_ST " + str(num_st) + " -precision " + precision + " -num_rep " + str(num_reps))
        
        if(interleaved):
            result = subprocess.run([bind[0], bind[1], bind[2], bind[3], "./bin/test", "-threads", str(threads), "-freq", str(freq), "-measure_freq", str(measure_freq),  "--interleaved"], stdout=subprocess.PIPE)
        else:
            result = subprocess.run([bind[0], bind[1], bind[2], bind[3], "./bin/test", "-threads", str(threads), "-freq", str(freq), "-measure_freq", str(measure_freq)], stdout=subprocess.PIPE)
        
        out = result.stdout.decode('utf-8').split(',')

        freq_aux = float(out[2])
        freq = float(out[3])
        data['L2'] = float((threads*num_reps*(num_ld+num_st)*mem_inst_size[isa][precision]*float(freq_aux)*float(out[1]))/(float(out[0])*float(freq_aux/freq)))
        if (verbose > 1):
            print ("---------L2 RESULTS-----------")
            print ("Total Cycles:", out[0],"Total Inner Loop Reps:", out[1], "Number of threads:", threads, "Number of reps:", num_reps,"Number of loads:", num_ld,"Number of stores:", num_st, "Memory instruction size:", mem_inst_size[isa][precision], "Frequency:", freq)
            
            #print ("EXTRA MODIFIERS:", float(threads*num_reps*(num_ld+num_st)*mem_inst_size[isa][precision]*float(freq)))
            
            print ("CYCLES PER INNER LOOP:", (float(out[0])*(freq_aux/freq))/float(out[1]))
        
            print ("ISTRUCTION PER CYCLE:", threads*num_reps*(num_ld+num_st)*float(out[1])/(float(out[0])*float(freq_aux/freq)))
            print ("BYTES PER CYCLE:", threads*num_reps*(num_ld+num_st)*mem_inst_size[isa][precision]*float(out[1])/(float(out[0])*float(freq_aux/freq)))
            print ("BANDWIDTH (Gbps):", data['L2'])
            print ("Max Recorded Frequency (GHz):", freq_aux)
            print ("Nominal Frequency (GHz):", freq)
            print ("Actual Frequency to Nominal Frequency Ratio:", float(freq_aux/freq))
            print ("------------------------------")
        
    if (test_type == 'L3' or test_type == 'roofline'):
        #Run L3 Test 
        num_reps = int(1024*(int(l2_size)*threads + (int(l3_size) - int(l2_size)*threads)/2)/(threads*mem_inst_size[isa][precision]*(num_ld+num_st)))
    
        os.system("./Bench/Bench -test MEM -num_LD " + str(num_ld) + " -num_ST " + str(num_st) + " -precision " + precision + " -num_rep " + str(num_reps))
        
        if(interleaved):
            result = subprocess.run([bind[0], bind[1], bind[2], bind[3], "./bin/test", "-threads", str(threads), "-freq", str(freq), "-measure_freq", str(measure_freq), "--interleaved"], stdout=subprocess.PIPE)
        else:
            result = subprocess.run([bind[0], bind[1], bind[2], bind[3], "./bin/test", "-threads", str(threads), "-freq", str(freq), "-measure_freq", str(measure_freq)], stdout=subprocess.PIPE)
       
        out = result.stdout.decode('utf-8').split(',')

        freq_aux = float(out[2])
        freq = float(out[3])
        data['L3'] = float(threads*num_reps*(num_ld+num_st)*mem_inst_size[isa][precision]*float(freq_aux)*float(out[1]))/(float(out[0])*float(freq_aux/freq))
        if (verbose > 1):
            print ("---------L3 RESULTS-----------")
            print ("Total Cycles:", out[0],"Total Inner Loop Reps:", out[1], "Number of threads:", threads, "Number of reps:", num_reps,"Number of loads:", num_ld,"Number of stores:", num_st, "Memory instruction size:", mem_inst_size[isa][precision], "Frequency:", freq)
            
            #print ("EXTRA MODIFIERS:", float(threads*num_reps*(num_ld+num_st)*mem_inst_size[isa][precision]*float(freq)))
            
            print ("CYCLES PER INNER LOOP:", (float(out[0])*(freq_aux/freq))/float(out[1]))
        
            print ("ISTRUCTION PER CYCLE:", threads*num_reps*(num_ld+num_st)*float(out[1])/(float(out[0])*float(freq_aux/freq)))
            print ("BYTES PER CYCLE:", (threads*num_reps*(num_ld+num_st)*mem_inst_size[isa][precision]*float(out[1]))/(float(out[0])*float(freq_aux/freq)))
            print ("BANDWIDTH (Gbps):", data['L3'])
            print ("Max Recorded Frequency (GHz):", freq_aux)
            print ("Nominal Frequency (GHz):", freq)
            print ("Actual Frequency to Nominal Frequency Ratio:", float(freq_aux/freq))
            print ("------------------------------")
        
    if (test_type == 'DRAM' or test_type == 'roofline'):
        #Run DRAM Test
        num_reps = int(dram_bytes*1024/(threads*2*mem_inst_size[isa][precision]*(num_ld+num_st)))
    
        os.system("./Bench/Bench -test MEM -num_LD " + str(num_ld) + " -num_ST " + str(num_st) + " -precision " + precision + " -num_rep " + str(num_reps))
        
        if(interleaved):
            result = subprocess.run([bind[0], bind[1], bind[2], bind[3], "./bin/test", "-threads", str(threads), "-freq", str(freq), "-measure_freq", str(measure_freq), "--interleaved"], stdout=subprocess.PIPE)
        else:
            result = subprocess.run([bind[0], bind[1], bind[2], bind[3], "./bin/test", "-threads", str(threads), "-freq", str(freq), "-measure_freq", str(measure_freq)], stdout=subprocess.PIPE)
        
        out = result.stdout.decode('utf-8').split(',')

        freq_aux = float(out[2])
        freq = float(out[3])
        data['DRAM'] = float(threads*num_reps*(num_ld+num_st)*mem_inst_size[isa][precision]*float(freq_aux)*float(out[1]))/(float(out[0])*float(freq_aux/freq))
        if (verbose > 1):
            print ("---------DRAM RESULTS-----------")
            print ("Total Cycles:", out[0],"Total Inner Loop Reps:", out[1], "Number of threads:", threads, "Number of reps:", num_reps,"Number of loads:", num_ld,"Number of stores:", num_st, "Memory instruction size:", mem_inst_size[isa][precision], "Frequency:", freq)
            
            #print ("EXTRA MODIFIERS:", float(threads*num_reps*(num_ld+num_st)*mem_inst_size[isa][precision]*float(freq)))
            
            print ("CYCLES PER INNER LOOP:", (float(out[0])*(freq_aux/freq))/float(out[1]))
        
            print ("ISTRUCTION PER CYCLE:", threads*num_reps*(num_ld+num_st)*float(out[1])/(float(out[0])*float(freq_aux/freq)))
            print ("BYTES PER CYCLE:", (threads*num_reps*(num_ld+num_st)*mem_inst_size[isa][precision]*float(out[1]))/(float(out[0])*float(freq_aux/freq)))
            print ("BANDWIDTH (Gbps):", data['DRAM'])
            print ("Max Recorded Frequency (GHz):", freq_aux)
            print ("Nominal Frequency (GHz):", freq)
            print ("Actual Frequency to Nominal Frequency Ratio:", float(freq_aux/freq))
            print ("------------------------------")

    if (test_type == 'FP' or test_type == 'roofline'):
        #Run FP Test
        if(inst == 'fma'):
            factor = 2
        else:
            factor = 1
    
        num_fp = int(num_ops/(factor*ops_fp[isa][precision]))
    
        os.system("./Bench/Bench -test FLOPS -op " + inst + " -precision " + precision + " -fp " + str(num_fp))
        
        if(interleaved):
            result = subprocess.run([bind[0], bind[1], bind[2], bind[3], "./bin/test", "-threads", str(threads), "-freq", str(freq), "-measure_freq", str(measure_freq), "--interleaved"], stdout=subprocess.PIPE)
        else:
            result = subprocess.run([bind[0], bind[1], bind[2], bind[3], "./bin/test", "-threads", str(threads), "-freq", str(freq), "-measure_freq", str(measure_freq)], stdout=subprocess.PIPE)
        
        out = result.stdout.decode('utf-8').split(',')

        freq_aux = float(out[2])
        freq = float(out[3])
        data['FP'] = float(threads*num_fp*factor*ops_fp[isa][precision]*float(freq_aux)*float(out[1]))/(float(out[0])*float(freq_aux/freq))
        if (verbose > 1):
            print ("---------FP RESULTS-----------")
            print ("Total Cycles:", out[0],"| Total Inner Loop Reps:", out[1], "| Number of threads:", threads, "| Number of reps:", num_fp,"| Instruction:", inst, "| Floating point operations per instruction:", (factor*ops_fp[isa][precision]), "| Frequency:", freq)
            
            print ("CYCLES PER INNER LOOP:", (float(out[0])*float(freq_aux/freq))/float(out[1]))
            print ("ISTRUCTION PER CYCLE:", (threads*num_fp*float(out[1]))/(float(out[0])*float(freq_aux/freq)))
            print ("FlOPS PER CYCLE:", (threads*num_fp*factor*ops_fp[isa][precision]*float(out[1]))/(float(out[0])*float(freq_aux/freq)))
            print ("GFLOPS:", data['FP'])
            print ("Max Recorded Frequency (GHz):", freq_aux)
            print ("Nominal Frequency (GHz):", freq)
            print ("Actual Frequency to Nominal Frequency Ratio:", float(freq_aux/freq))
            print ("------------------------------")
        
    if (test_type == 'roofline'):

        if(os.path.isdir('Results') == False):
            os.mkdir('Results')
    
        ct = datetime.datetime.now()
        
        #Plot Roofline
        #plot_roofline(name, data, ct)
    
        #f = open('Results/' + name + '_data_roofline_' + str(ct.time()) + '_' + str(ct.date()) + '.out', 'w')

        #"__inst__isa__precision__ldst__only__ld__threads__interleaved__numops__drambytes__"
    
        fname = "inst_" + str(args.inst) + \
        "__isa_" + str(args.isa) + \
        "__precision_" + str(args.precision) + \
        "__ldstratio_" + str(args.ld_st_ratio) + \
        "__onlyld_" + str(args.only_ld) + \
        "__threads_" + str(args.threads) + \
        "__interleaved_" + str(args.interleaved) + \
        "__numops_" + str(args.num_ops) + \
        "__drambytes_" + str(args.dram_bytes) + \
        "__binding_" + str(args.binding)
    
        f = open('Results/' + name + '_data_roofline__' + fname + '.out', 'w')

        for d, v in data.items():
            f.write(str(d) + ": " + str(v) + '\n')
        f.close()

def main():
    parser = argparse.ArgumentParser(description='Script to run micro-benchmarks to construct Cache-Aware Roofline Model')
    parser.add_argument('--test', default='roofline', nargs='?', choices=['FP', 'L1', 'L2', 'L3', 'DRAM', 'roofline'], help='Type of the test. Roofline test measures the bandwidth of the different memory levels and FP Performance (Default: roofline)')
    
    parser.add_argument('--no_freq_measure',  dest='measure_freq', action='store_const', const=1, default=0, help='Measure CPU frequency or not')

    parser.add_argument('--freq', default='2.0', nargs='?', type = float, help='Desired CPU frequency during test (if not using config file)')
    parser.add_argument('--set_freq',  dest='set_freq', action='store_const', const=1, default=0, help='Set Processor frequency to indicated one')
    parser.add_argument('--name', default='', nargs='?', type = str, help='Name for results file (if not using config file)')
    parser.add_argument('-v', '--verbose', default=0, nargs='?', type = int, choices=[0, 1, 2, 3], help='Level of terminal output (0 -> No Output 1 -> Only ISA Errors, 2 -> Intermediate Test Results, 3 -> Configuration Values Selected)')
    
    parser.add_argument('--inst', default='fma', nargs='?', choices=['fma', 'add', 'mul', 'div'], help='FP Instruction (Default: fma)')
    parser.add_argument('--isa', default='auto', nargs='?', choices=['avx512', 'avx', 'avx2', 'sse', 'scalar', 'auto'], help='ISA (Default: auto)')
    parser.add_argument('-p', '--precision', default='dp', nargs='?', choices=['dp', 'sp'], help='Data Precision (Default: dp)')
    parser.add_argument('-ldst', '--ld_st_ratio',  default=2, nargs='?', type = int, help='Load/Store Ratio (Default: 2)')
    parser.add_argument('--only_ld',  dest='only_ld', action='store_const', const=1, default=0, help='Run only loads in mem test (ld_st_ratio is ignored)')
    parser.add_argument('--only_st',  dest='only_st', action='store_const', const=1, default=0, help='Run only stores in mem test (ld_st_ratio is ignored)')
    #parser.add_argument('--curve',  dest='curve', action='store_const', const=1, default=0, help='To obtain full MEM and FP Curves')
    parser.add_argument('config', nargs='?', help='Path for the system configuration file')
    parser.add_argument('-t', '--threads', default=1, nargs='?', type = int, help='Number of threads for the micro-benchmarking (Default: 1)')
    parser.add_argument('-i', '--interleaved',  dest='interleaved', action='store_const', const=1, default=0, help='For thread binding when cores are interleaved between numa domains (Default: 0)')
    parser.add_argument('-ops', '--num_ops',  default=32768, nargs='?', type = int, help='Number of FP operations to be used in FP test (Default: 32768)')
    parser.add_argument('--dram_bytes',  default=524288, nargs='?', type = int, help='Size of the array for the DRAM test in KiB (Default: 524288 (512 MiB))')
    parser.add_argument('-b', '--binding', default='', nargs='?', type=str, help='Likwid-pin thread binding text, likwid-pin args should be separated by |')

    args = parser.parse_args()
    print(args)
    l1_size = 0
    l2_size = 0
    l3_size = 0
    freq = 0
    name = ''

    if (args.config != None):
        name, l1_size, l2_size, l3_size = read_config(args.config)
   

    #uses frequency from arguments if not present in config file
    if (freq == 0):
        freq = args.freq
    
    #uses name from arguments if not present in config file
    if (name == ''):
        name = args.name

    #print(name, freq, l1_size, l2_size, l3_size)

    if(args.only_ld == 1):
        num_ld = 1
        num_st = 0
    elif(args.only_st == 1):
        num_ld = 0
        num_st = 1
    else:
        num_ld = args.ld_st_ratio
        num_st = 1

    if args.test == 'fp':
        raise ValueError('Not implemented yet!')
        """  if(args.curve == 1):
            run_fp(name, freq, args.num_fp, args.inst, args.isa, args.precision)
        else:
            run_fp(name, freq, args.num_fp, args.inst, args.isa, args.precision) """
    elif args.test == 'mem':
        raise ValueError('Not implemented yet!')
        """ if(args.curve == 1):
            run_mem(name, freq, args.size, args.isa, args.precision, num_ld, num_st)
        else:
            run_mem(name, freq, args.size, args.isa, args.precision, num_ld, num_st) """
    else:
        run_roofline(name, freq, l1_size, l2_size, l3_size, args.inst, args.isa, args.precision, num_ld, num_st, args.threads, args.interleaved, args.num_ops, args.dram_bytes, args.test, args.verbose, args.set_freq, args.measure_freq, args)

if __name__ == "__main__":
    main()
