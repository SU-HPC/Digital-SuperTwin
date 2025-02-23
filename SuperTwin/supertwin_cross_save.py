import sys
sys.path.append("probing")
sys.path.append("probing/benchmarks")
sys.path.append("observation")
sys.path.append("twin_description")
sys.path.append("sampling")
sys.path.append("dashboards")

import utils
import remote_probe
import detect_utils
import generate_dt
import sampling
import stream_benchmark
import hpcg_benchmark
import adcarm_benchmark
import observation
import influx_help
import observation_standard
import roofline_dashboard
import monitoring_dashboard
import monitoring_dashboard_modular as mdm

import static_data

import uuid

#from influxdb import InfluxDBClient
#import pymongo
#from pymongo import MongoClient

from bson.objectid import ObjectId
from bson.json_util import dumps
from bson.json_util import loads

import datetime
import json

#sys.path.append("quick_dashboard")
#import generate_plotly_panels_dd_go ##delete dis
#import unique
import observation_standard

##HPCG benchmark parameters are set to be separate from classes, so hpcg is repeatable and easily mutable
HPCG_PARAM = {}
HPCG_PARAM["nx"] = 104
HPCG_PARAM["ny"] = 104
HPCG_PARAM["nz"] = 104
HPCG_PARAM["time"] = 60
##HPCG benchmark parameters

ALWAYS_EXISTS_MONITOR = ["kernel.all.pressure.cpu.some.total",
                         "hinv.cpu.clock",
                         "lmsensors.coretemp_isa_0000.package_id_0",
                         "kernel.pernode.cpu.idle",
                         "kernel.percpu.cpu.idle",
                         "disk.dev.read",
                         "disk.dev.write",
                         "disk.dev.total",
                         "disk.dev.read_bytes",
                         "disk.dev.write_bytes",
                         "disk.dev.total_bytes",
                         "swap.pagesin",
                         "kernel.all.nusers",
                         "kernel.all.nprocs",
                         "network.all.in.bytes",
                         "network.all.out.bytes"]

ALWAYS_HAVE_MONITOR_NUMA = ALWAYS_EXISTS_MONITOR + ["lmsensors.coretemp_isa_0001.package_id_1",
                                                    "mem.numa.util.free",
                                                    "mem.numa.util.used",
                                                    "mem.numa.alloc.hit",
                                                    "mem.numa.alloc.miss",
                                                    "mem.numa.alloc.local_node",
                                                    "mem.numa.alloc.other_node",
                                                    "perfevent.hwcounters.RAPL_ENERGY_PKG.value",
                                                    "perfevent.hwcounters.RAPL_ENERGY_DRAM.value"]

ALWAYS_HAVE_MONITOR_SINGLE_SOCKET = ALWAYS_EXISTS_MONITOR + ["mem.util.used",
                                                             "mem.util.free",
                                                             "perfevent.hwcounters.RAPL_ENERGY_PKG.value",
                                                             "perfevent.hwcounters.RAPL_ENERGY_DRAM.value"]

SKL_DONT_HAVE = ["perfevent.hwcounters.RAPL_ENERGY_DRAM.value"]
ICL_DONT_HAVE = ["perfevent.hwcounters.RAPL_ENERGY_DRAM.value",
                 "perfevent.hwcounters.RAPL_ENERGY_PKG.value"] ##RAPL is not currenty available on Icelake
ALWAYS_HAVE_MONITOR_SKL = [x for x in ALWAYS_HAVE_MONITOR_SINGLE_SOCKET if x not in SKL_DONT_HAVE]
ALWAYS_HAVE_MONITOR_ICL = [x for x in ALWAYS_HAVE_MONITOR_SINGLE_SOCKET if x not in ICL_DONT_HAVE]


ALWAYS_HAVE_OBSERVATION = ["RAPL_ENERGY_PKG",
                           "RAPL_ENERGY_DRAM"]
ALWAYS_HAVE_OBSERVATION_SKL = ["RAPL_ENERGY_PKG"]
ALWAYS_HAVE_OBSERVATION_ICL = [] ##RAPL is not currently available on Icelake

##
met = {
        'monitor':{
            'general_single': ALWAYS_HAVE_MONITOR_SINGLE_SOCKET,
            'general_numa': ALWAYS_HAVE_MONITOR_NUMA,
            'skl': ALWAYS_HAVE_MONITOR_SKL,
            'icl': ALWAYS_HAVE_MONITOR_ICL
        },
        'observation': {
            'general': ALWAYS_HAVE_OBSERVATION,
            'skl': ALWAYS_HAVE_OBSERVATION_SKL,
            'icl': ALWAYS_HAVE_OBSERVATION_ICL
        }
    }
##


def get_twin_description(hostProbFile, alias, SSHuser, SSHpass, addr):

    with open(hostProbFile, "r") as j:
        _sys_dict = json.loads(j.read())

    _twin = generate_dt.main(_sys_dict, alias, SSHuser, SSHpass, addr)
    return _twin


def insert_twin_description(_twin, supertwin):

    date = datetime.datetime.now()
    date = date.strftime("%d-%m-%Y")

    hostname = supertwin.name
    CONNECTION_STRING = supertwin.mongodb_addr
    
    mongodb = utils.get_mongo_database(hostname, CONNECTION_STRING)
    collection = mongodb["twin"]
    
    metadata = {
        "uid": supertwin.uid,
        "address": supertwin.addr,
        "hostname": supertwin.name,
        "date": date,
        "twin_description": _twin,
        "influxdb_name": supertwin.influxdb_name,
        "influxdb_tag": supertwin.monitor_tag,
        "monitor_pid": "",
        "prob_file": supertwin.prob_file,
        "roofline_dashboard": "to be added",
        "monitoring_dashboard": "to be added"}

    result = collection.insert_one(metadata)
    twin_id = str(result.inserted_id)

    return twin_id


def register_twin_state(SuperTwin):

    db = utils.get_mongo_database(SuperTwin.name, SuperTwin.mongodb_addr)["twin"]
    meta = loads(dumps(db.find({"_id": ObjectId(SuperTwin.mongodb_id)})))[0]

    
    meta["twin_state"] = {}
    meta["twin_state"]["SSHuser"] = SuperTwin.SSHuser
    meta["twin_state"]["SSHpass"] = utils.obscure(str.encode(SuperTwin.SSHpass))
    meta["twin_state"]["monitor_tag"] = SuperTwin.monitor_tag
    meta["twin_state"]["benchmarks"] = SuperTwin.benchmarks
    meta["twin_state"]["benchmark_results"] = SuperTwin.benchmark_results
    meta["twin_state"]["monitor_metrics"] = SuperTwin.monitor_metrics
    meta["twin_state"]["observation_metrics"] = SuperTwin.observation_metrics
    meta["twin_state"]["grafana_datasource"] = SuperTwin.grafana_datasource
    meta["twin_state"]["pcp_pids"] = SuperTwin.pcp_pids
        
        
    db.replace_one({"_id": ObjectId(SuperTwin.mongodb_id)}, meta)
    
    print("Twin state is registered to db..")


def query_twin_state(name, mongodb_id, mongodb_addr):

    print("in query_twin_state: name: ", name)
    db = utils.get_mongo_database(name, mongodb_addr)["twin"]
    meta = loads(dumps(db.find({"_id": ObjectId(mongodb_id)})))[0]
    print("Found db..")
    
    return meta

            
class SuperTwin:

    def __init__(self, *args):

        exist = False
        name = None
        twin_id = None
        collection_id =None
        
        if(len(args) == 1): ##Check if existed and wanted to be reconstructed from non-existed
            try:
                exist, name, twin_id, collection_id = utils.check_state(args[0])
                print("exist:", exist, "name:", name, "twin_id:", twin_id, "collection_id:", collection_id, "args[0]:", args[0])
            except:
                print("A SuperTwin instance is tried to be reconstructed from address", args[0])
                print("However, there is no such twin with that address..")
                exit(1)
        
        if(len(args) == 1 and exist): ##Reconstruct from db

            self.addr = args[0]
            self.name = name
            self.mongodb_id = collection_id
            self.mongodb_addr, self.influxdb_addr, self.grafana_addr, self.grafana_token = utils.read_env()
            meta = query_twin_state(self.name, self.mongodb_id, self.mongodb_addr)
            self.monitor_metrics = meta["twin_state"]["monitor_metrics"]
            self.observation_metrics = meta["twin_state"]["observation_metrics"]
            self.SSHuser = meta["twin_state"]["SSHuser"]
            self.SSHpass = utils.unobscure(meta["twin_state"]["SSHpass"]).decode()
            self.monitor_tag = meta["twin_state"]["monitor_tag"]
            self.benchmarks = meta["twin_state"]["benchmarks"]
            self.benchmark_results = meta["twin_state"]["benchmark_results"]
            self.grafana_datasource = meta["twin_state"]["grafana_datasource"]
            self.prob_file = meta["prob_file"]
            self.uid = meta["uid"]
            self.influxdb_name = meta["influxdb_name"]
            self.monitor_tag = meta["influxdb_tag"]
            self.monitor_pid = meta["monitor_pid"]
            self.roofline_dashboard = meta["roofline_dashboard"]
            self.monitoring_dashboard = meta["monitoring_dashboard"]
            self.pcp_pids = meta["twin_state"]["pcp_pids"]
            
            print("SuperTwin is reconstructed from db..")

        else: ##Construct from scratch

            if(len(args) == 3):
                
                self.addr = args[0]
                self.SSHuser = args[1]
                self.SSHpass = args[2]
                self.name, self.prob_file  = remote_probe.main(self.addr, self.SSHuser, self.SSHpass)
                
            else:
                self.addr = input("Address of the remote system: ")
                alias = input("Alias for hostname: ")
                self.name, self.prob_file, self.SSHuser, self.SSHpass = remote_probe.main(self.addr)

            if(alias != ""):
                self.name = alias

            print("!!self.name:", self.name)
            self.uid = str(uuid.uuid4())
            print("Creating a new digital twin with id:", self.uid)
            
            self.influxdb_name = self.name #+ "_main"
            self.mongodb_addr, self.influxdb_addr, self.grafana_addr, self.grafana_token = utils.read_env()
            utils.get_influx_database(self.influxdb_addr, self.influxdb_name)
            self.grafana_datasource = utils.create_grafana_datasource(self.name, self.uid, self.grafana_token, self.grafana_addr, self.influxdb_addr)["datasource"]["uid"]
            #self.monitor_metrics = utils.read_monitor_metrics() ##These are the continuously sampled metrics

            self.monitor_tag = "_monitor"
            self.pcp_pids = utils.get_pcp_pids(self)
            
            self.mongodb_id = insert_twin_description(get_twin_description(self.prob_file, self.name, self.SSHuser, self.SSHpass, self.addr),self)
            print("Collection id:", self.mongodb_id)
            #self.monitor_pid = sampling.main(self.name, self.addr, self.influxdb_name, self.monitor_tag, self.monitor_metrics)
            
            
            #benchmark members
            self.benchmarks = 0
            self.benchmark_results = 0
            
            ##
            ##This is a breaking point where we know everything and can configure now
            ##
            
            #self.observation_metrics = utils.read_observation_metrics() #This may become problematic with multinode
            self.monitor_metrics = []
            self.observation_metrics = [] #Start empty
            self.reconfigure_observation_events_beginning() ##Only add available power
            
            self.monitor_pid = sampling.main(self)
            
            utils.update_state(self.name, self.addr, self.uid, self.mongodb_id)
            self.kill_zombie_monitors() ##If there is any zombie monitor sampler
            self.generate_monitoring_dashboard()
            
            ##benchmark functions
            #self.add_stream_benchmark()
            #self.add_hpcg_benchmark(HPCG_PARAM) ##One can change HPCG_PARAM and call this function repeatedly as wanted
            #self.add_adcarm_benchmark()
            #self.generate_roofline_dashboard()
            
            register_twin_state(self)
            
            
    def kill_zombie_monitors(self):
        
        out = detect_utils.output_lines("ps aux | grep pcp2influxdb")

        for line in out: ##Accesses are emprical
            if(line.find("/usr/bin/pcp2influxdb") != -1):
                fields = line.split(" ")
                fields = [x for x in fields if x != ""]
                pid = None
                state = None
                conf_file = None
                try:
                    pid = int(fields[1])
                    state = fields[7]
                    conf_file = fields[15]
                except:
                    continue
                                    
                #print("pid:", pid, "state:", state, "conf_file:", conf_file)
                if(pid != self.monitor_pid):
                    print("Killing zombie monitoring sampler with pid:", pid)
                    detect_utils.cmd("sudo kill " + str(pid))

                    
    def update_twin_document__assert_new_monitor_pid(self):
        
        db = utils.get_mongo_database(self.name, self.mongodb_addr)["twin"]
        print("Killing existed monitor sampler with pid:", self.monitor_pid)
        detect_utils.cmd("sudo kill " + str(self.monitor_pid))
        new_pid = sampling.main(self.name, self.addr, self.influxdb_name, self.monitor_tag, self.monitor_metrics)
        print("New sampler pid: ", new_pid)
        to_new = loads(dumps(db.find({"_id": ObjectId(self.mongodb_id)})))[0]
        #print(to_new)
        to_new["monitor_pid"] = new_pid        
        db.replace_one({"_id": ObjectId(self.mongodb_id)}, to_new)
        self.monitor_pid = new_pid

    def update_twin_document__update_monitor_pid(self):
        
        db = utils.get_mongo_database(self.name, self.mongodb_addr)["twin"]
        to_new = loads(dumps(db.find({"_id": ObjectId(self.mongodb_id)})))[0]
        to_new["monitor_pid"] = self.monitor_pid
        db.replace_one({"_id": ObjectId(self.mongodb_id)}, to_new)
        self.monitor_pid = new_pid

        
    def prepare_stream_content(self, stream_modifiers, stream_res):

        print("stream_modifiers:", stream_modifiers)
        
        benchmark_id = str(self.benchmarks)
        benchmark_result_id = self.benchmark_results ##Note that benchmark_id is str but this one is int, since we will keep incrementing this one

        id_base = "dtmi:dt:" + self.name + ":"
        
        content = {}
        content["@id"] = id_base + "benchmark:B" + benchmark_id + ";1"
        content["@type"] = "benchmark"
        content["@date"] = datetime.datetime.now().strftime("%d-%m-%Y")
        content["@name"] = "STREAM"
        content["@environment"] = stream_modifiers['environment']
        
        content["@mvres"] = stream_res["Max_Glob"]
        content["@mvres_name"] = "Global Max"
        content["@mvres_unit"] = "MB/s"
        
        content["@contents"] = []

        print("stream_res:", stream_res)
        
        for _field_key in stream_res:
            try: ##Field key is a thread
                for _thread_key in stream_res[_field_key]:
                    _dict = {}
                    _dict["@id"] = id_base + "benchmark_res:B" + str(benchmark_result_id) + ";1"
                    _dict["@type"] = "benchmark_result"
                    _dict["@field"] = _field_key
                    _dict["@threads"] = int(_thread_key)
                    _dict["@modifier"] = stream_modifiers[_thread_key]
                    _dict["@result"] = stream_res[_field_key][_thread_key]
                    _dict["@unit"] = "MB/s" #We know that beforehand
                    
                    content["@contents"].append(_dict)
                    benchmark_result_id += 1
            except: ##Field key is a global or local max
                continue

        self.benchmarks += 1
        self.benchmark_results = benchmark_result_id

        return content

    
    def prepare_hpcg_content(self, hpcg_modifiers, hpcg_res):

        print("hpcg_modifiers:", hpcg_modifiers)
        print("hpcg_res:", hpcg_res)
        
        benchmark_id = str(self.benchmarks)
        benchmark_result_id = self.benchmark_results ##Note that benchmark_id is str but this one is int, since we will keep incrementing this one

        id_base = "dtmi:dt:" + self.name + ":"
        
        content = {}
        content["@id"] = id_base + "benchmark:B" + benchmark_id + ";1"
        content["@type"] = "benchmark"
        content["@date"] = datetime.datetime.now().strftime("%d-%m-%Y")
        content["@name"] = "HPCG"
        print("hpcg_modifiers:", hpcg_modifiers)
        content["@environment"] = hpcg_modifiers['environment']
        content["@global_parameters"] = hpcg_res["parameters"] 
        
        content["@mvres"] = hpcg_res["Max_Glob"] 
        content["@mvres_name"] = "Global Max"
        content["@mvres_unit"] = "GFlop/s"
        
        content["@contents"] = []
        
        for _field_key in hpcg_res:
            if(_field_key == "spmv" or _field_key == "ddot" or _field_key == "waxpby"):
                for _thread_key in hpcg_res[_field_key]: 
                    _dict = {}
                    _dict["@id"] = id_base + "benchmark_res:B" + str(benchmark_result_id) + ";1"
                    _dict["@type"] = "benchmark_result"
                    _dict["@field"] = _field_key
                    _dict["@threads"] = int(_thread_key)
                    _dict["@modifier"] = hpcg_modifiers[_thread_key]
                    _dict["@result"] = hpcg_res[_field_key][_thread_key]
                    _dict["@unit"] = "GFlop/s" #We know that beforehand

                    content["@contents"].append(_dict)
                    benchmark_result_id += 1
            else: ##Field key is a global or local max or parameter
                continue

        self.benchmarks += 1
        self.benchmark_results = benchmark_result_id

        return content

    
    def prepare_adcarm_content(self, adcarm_modifiers, adcarm_res):
        ##We are not probably using adcarm_modifiers here
        ##It only contains global environment variable changes in the system
        ##Since it is also exist in adcarm_res, in contrary to other benchmarks

        print("adcarm_res:", adcarm_res)
        
        def max_threads():
            threads = adcarm_res["threads"].keys()
            threads = [int(x) for x in threads]
            max_thread = max(threads)
            return str(max_thread)

        def which():
            runs = adcarm_res["threads"][max_threads()]

            for i in range(len(runs)):
                if("binding" not in runs[i].keys()):
                    return i
        
        benchmark_id = str(self.benchmarks) ##These may get GLOBAL (including other systems) later
        benchmark_result_id = self.benchmark_results

        id_base = "dtmi:dt:" + self.name + ":"

        content = {}
        content["@id"] = id_base + "benchmark:B" + benchmark_id + ";1"
        content["@type"] = "benchmark"
        content["@date"] = datetime.datetime.now().strftime("%d-%m-%Y")
        content["@name"] = "CARM"
        
        if(adcarm_modifiers["environment"] != []):
            content["@environment"] = adcarm_modifiers["environment"]
            
        #content["@global_parameters"] = carm config values, L1size, L2size, Frequency?
        content["@mvres"] = adcarm_res["threads"][max_threads()][which()]["FP"]
        content["@mvres_name"] = "Max threads ridge point, without modifiers"
        content["@mvres_unit"] = "GFlop/s"

        content["@contents"] = []

        for _thread_key in adcarm_res["threads"]:
            for i in range(len(adcarm_res["threads"][_thread_key])):
                _run_dict = adcarm_res["threads"][_thread_key][i]
                _dict = {}
                _dict["@id"] = id_base + "benchmark_res:B" + str(benchmark_result_id) + ";1"
                _dict["@type"] = "benchmark_result"
                _dict["@threads"] = int(_thread_key)
                if("binding" in _run_dict.keys()):
                    _dict["@modifier"] = _run_dict["binding"]

                _dict["@local_parameters"] = []
                _dict["@local_parameters"].append({'inst': _run_dict["inst"]})
                _dict["@local_parameters"].append({'isa': _run_dict["isa"]})
                _dict["@local_parameters"].append({'precision': _run_dict["precision"]})
                _dict["@local_parameters"].append({'ld_st_ratio': int(_run_dict["ldstratio"])})
                _dict["@local_parameters"].append({'only_ld': bool(_run_dict["onlyld"])})
                _dict["@local_parameters"].append({'interleaved': bool(_run_dict["interleaved"])})
                _dict["@local_parameters"].append({'numops': int(_run_dict["numops"])})
                _dict["@local_parameters"].append({'dram_bytes': int(_run_dict["drambytes"])})
                
                _dict["@result"] = []
                _dict["@result"].append({"L1": _run_dict["L1"]})
                _dict["@result"].append({"L2": _run_dict["L2"]})
                _dict["@result"].append({"L3": _run_dict["L3"]})
                _dict["@result"].append({"DRAM": _run_dict["DRAM"]})
                _dict["@result"].append({"FP": _run_dict["FP"]})

                _dict["@unit"] = "GFLOPs/s"

                content["@contents"].append(_dict)
                benchmark_result_id += 1

            
        self.benchmarks += 1
        self.benchmark_results = benchmark_result_id

        return content
        
    def update_twin_document__add_stream_benchmark(self, stream_modifiers, stream_res):
        
        db = utils.get_mongo_database(self.name, self.mongodb_addr)["twin"]
        meta_with_twin = loads(dumps(db.find({"_id": ObjectId(self.mongodb_id)})))[0]
        new_twin = meta_with_twin["twin_description"]

        for key in new_twin:
            if(key.find("system") != -1): ##Get the system interface and add the benchmarks
                content = self.prepare_stream_content(stream_modifiers, stream_res)
                new_twin[key]["contents"].append(content)

        meta_with_twin["twin_description"] = new_twin
        db.replace_one({"_id": ObjectId(self.mongodb_id)}, meta_with_twin)
        print("STREAM benchmark result added to Digital Twin")
        
        
    def add_stream_benchmark(self):
        
        stream_modifiers, maker, runs = stream_benchmark.generate_stream_bench_sh(self)
        stream_benchmark.compile_stream_bench(self, maker)
        stream_benchmark.execute_stream_runs(self, runs)
        stream_res = stream_benchmark.parse_stream_bench(self)
        self.update_twin_document__add_stream_benchmark(stream_modifiers, stream_res)
        

    def update_twin_document__add_hpcg_benchmark(self, hpcg_modifiers, hpcg_res):

        db = utils.get_mongo_database(self.name, self.mongodb_addr)["twin"]
        meta_with_twin = loads(dumps(db.find({"_id": ObjectId(self.mongodb_id)})))[0]
        new_twin = meta_with_twin["twin_description"]

        for key in new_twin:
            if(key.find("system") != -1): ##Get the system interface and add the benchmarks
                content = self.prepare_hpcg_content(hpcg_modifiers, hpcg_res)
                new_twin[key]["contents"].append(content)

        meta_with_twin["twin_description"] = new_twin
        db.replace_one({"_id": ObjectId(self.mongodb_id)}, meta_with_twin)
        print("HPCG benchmark result added to Digital Twin")


    def add_hpcg_benchmark(self, HPCG_PARAM):

        hpcg_modifiers, runs = hpcg_benchmark.generate_hpcg_bench_sh(self, HPCG_PARAM)
        hpcg_benchmark.execute_hpcg_runs(self, runs)
        hpcg_res = hpcg_benchmark.parse_hpcg_bench(self)

        self.update_twin_document__add_hpcg_benchmark(hpcg_modifiers, hpcg_res)

    def update_twin_document__add_adcarm_benchmark(self, adcarm_modifiers, adcarm_res):
        ##Different from stream and hpcg benchmarks, adcarm have it's modifiers in result

        db = utils.get_mongo_database(self.name, self.mongodb_addr)["twin"]
        meta_with_twin = loads(dumps(db.find({"_id": ObjectId(self.mongodb_id)})))[0]
        new_twin = meta_with_twin["twin_description"]

                
        for key in new_twin:
            if(key.find("system") != -1): ##Get the system interface and add the benchmarks
                content = self.prepare_adcarm_content(adcarm_modifiers, adcarm_res)
                new_twin[key]["contents"].append(content)

        meta_with_twin["twin_description"] = new_twin
        db.replace_one({"_id": ObjectId(self.mongodb_id)}, meta_with_twin)
        print("CARM benchmark result added to Digital Twin")
        

    def add_adcarm_benchmark(self):
        adcarm_config = adcarm_benchmark.generate_adcarm_config(self)
        adcarm_modifiers = adcarm_benchmark.generate_adcarm_bench_sh(self, adcarm_config)
        adcarm_benchmark.execute_adcarm_bench(self)
        adcarm_res = adcarm_benchmark.parse_adcarm_bench(self)
                        
        self.update_twin_document__add_adcarm_benchmark(adcarm_modifiers, adcarm_res)
        

    def update_twin_document__add_roofline_dashboard(self, url):

        db = utils.get_mongo_database(self.name, self.mongodb_addr)["twin"]
                
        to_new = loads(dumps(db.find({"_id": ObjectId(self.mongodb_id)})))[0]
        to_new["roofline_dashboard"] = url
        db.replace_one({"_id": ObjectId(self.mongodb_id)}, to_new)
        print("Roofline dashboard added to Digital Twin")

        
    def update_twin_document__add_monitoring_dashboard(self, url):

        db = utils.get_mongo_database(self.name, self.mongodb_addr)["twin"]
                
        to_new = loads(dumps(db.find({"_id": ObjectId(self.mongodb_id)})))[0]
        to_new["monitoring_dashboard"] = url
        db.replace_one({"_id": ObjectId(self.mongodb_id)}, to_new)
        print("Monitoring dashboard added to Digital Twin")

    #def update_twin_document__update_monitoring_dashboard(self, url):
    #monitoring_dashboard.update_dashboard(self)

        
    def generate_roofline_dashboard(self):
        url = roofline_dashboard.generate_roofline_dashboard(self)
        self.update_twin_document__add_roofline_dashboard(url)

        
    def generate_monitoring_dashboard(self):
        url = monitoring_dashboard.generate_monitoring_dashboard(self)
        self.update_twin_document__add_monitoring_dashboard(url)

        
    def reconfigure_monitor_events(self):

        metrics = self.observation_metrics
        
        for item in ALWAYS_HAVE_MONITOR_WIDER:
            if item not in metrics:
                metrics.append(item)
        
        writer = open("monitor_metrics.txt", "w+")
        for item in metrics:
            writer.write(item + "\n")
        writer.close()

        self.monitor_metrics = metrics
        self.update_twin_document__assert_new_monitor_pid()
        register_twin_state(self)

        
    def reconfigure_observation_events(self, metrics):

        for item in ALWAYS_HAVE_OBSERVATION:
            if item not in metrics:
                metrics.append(item)
        
        writer = open("last_observation_metrics.txt", "w+")
        for item in metrics:
            writer.write(item + "\n")
        writer.close()

        self.observation_metrics = metrics
        self.reconfigure_perfevent()
        register_twin_state(self)

        
    def reconfigure_observation_events_parameterized(self, obs_metric_file):

        msr = utils.get_msr(self)
        #metrics = self.observation_metrics

        metrics = []
        
        reader = open(obs_metric_file)
        lines = reader.readlines()
        for item in lines:
            metrics.append(item.strip("\n"))
        print("METRICS:", metrics)
        
        if(msr == "icl"):
            for item in ALWAYS_HAVE_OBSERVATION_ICL:
                if item not in metrics:
                    metrics.append(item)

        elif(msr == "skl"):
            for item in ALWAYS_HAVE_OBSERVATION_SKL:
                if item not in metrics:
                    metrics.append(item)

        else:
            for item in ALWAYS_HAVE_OBSERVATION:
                if item not in metrics:
                    metrics.append(item)
        
                    
        writer = open("last_observation_metrics.txt", "w+")
        for item in metrics:
            writer.write(item + "\n")
        writer.close()

        self.observation_metrics = metrics
        self.reconfigure_perfevent()
        register_twin_state(self)


    def reconfigure_observation_events_beginning(self):

        msr = utils.get_msr(self)
        metrics = self.observation_metrics
        always_have_metrics = utils.always_have_metrics("observation", self)

        for item in always_have_metrics:
            if item not in metrics:
                metrics.append(item)

        '''
        writer = open("last_observation_metrics.txt", "w+")
        for item in metrics:
            writer.write(item + "\n")
        writer.close()
        '''

        self.observation_metrics = metrics
        self.reconfigure_perfevent()
        register_twin_state(self)
                    
    def reconfigure_perfevent(self):

        sampling.generate_perfevent_conf(self)
        sampling.reconfigure_perfevent(self)
        

    def execute_observation(self, command):
        observation_id = str(uuid.uuid4())
        obs_conf = sampling.generate_pcp2influxdb_config_observation(self, observation_id)
        duration = observation.observe_single(self, observation_id, command, obs_conf)
        print("Observation", observation_id, "is completed..")
        return duration

    
    def execute_observation_batch_element(self, command, observation_id, element_id):
        
        this_observation_id = observation_id + "_" + str(element_id)
        obs_conf = sampling.generate_pcp2influxdb_config_observation(self, this_observation_id)
        duration = observation.observe_single(self, this_observation_id, command, obs_conf)
        print("Observation", this_observation_id, "is completed..")
        return duration

    
    def execute_observation_batch_element_parameters(self, path, affinity, command, observation_id, element_id):
        print("Called")
        this_observation_id = observation_id + "_" + str(element_id)
        obs_conf = sampling.generate_pcp2influxdb_config_observation(self, this_observation_id)
        print("obs_conf:", obs_conf)
        duration = observation.observe_single_parameters(self, path, affinity, this_observation_id, command, obs_conf)
        print("Observation", this_observation_id, "is completed..")
        return duration

        
    def execute_observation_batch(self, commands):

        observation = {}
        
        observation_id = str(uuid.uuid4())
        for i in range(len(commands)):
            tag = observation_id + "_" + str(i)
            observation_id
            self.execute_observation_batch_element(commands[i], observation_id, i)
        
        influx_help.normalize_tag(self, observation_id, len(commands))
        #update_twin_document__add_observation(times, commands)

    def update_twin_document__add_observation(self, observation):

        db = utils.get_mongo_database(self.name, self.mongodb_addr)["observations"]
        db.insert_one(observation)
        print("Observation", observation["uid"], "is added to twin description..")

    def execute_observation_batch_parameters(self, path, affinity, commands):
                
        observation = {}
        observation_id = str(uuid.uuid4())
        observation["uid"] = observation_id
        observation["affinity"] = affinity
        observation["metrics"] = []
        for metric in self.observation_metrics:
            observation["metrics"].append(metric)
        for metric in self.monitor_metrics:
            observation["metrics"].append(metric)
        
        observation["elements"] = {}
        for i in range(len(commands)):
            tag = observation_id + "_" + str(i)
            observation["elements"][tag] = {}
            fields = commands[i].split("|")
            name = fields[0]
            command = fields[1]
            observation["elements"][tag]["name"] = name
            observation["elements"][tag]["command"] = command
            observation["elements"][tag]["duration"] = self.execute_observation_batch_element_parameters(path, affinity, command, observation_id, i)

        influx_help.normalize_tag(self, observation_id, len(commands))
        observation["report"] = observation_standard.main(self, observation)
        self.update_twin_document__add_observation(observation)

##################################################################################################################################################
    def execute_observation_element_parameters(self, path, affinity, command, observation_id):
        this_observation_id = observation_id
        obs_conf = sampling.generate_pcp2influxdb_config_observation(self, this_observation_id)
        print("obs_conf:", obs_conf)
        duration = observation.observe_single_parameters(self, path, affinity, this_observation_id, command, obs_conf)
        print("Observation", this_observation_id, "is completed..")
        return duration

    def execute_observation_parameters(self, path, threads, affinity, command):

        affinity = utils.prepare_bind(self, threads, affinity, -1)
        observation = {}
        observation_id = str(uuid.uuid4())
        observation["uid"] = observation_id
        observation["affinity"] = affinity
        observation["metrics"] = []
        for metric in self.observation_metrics:
            observation["metrics"].append(metric)
        for metric in self.monitor_metrics:
            observation["metrics"].append(metric)
        
        tag = observation_id
        observation[tag] = {}
        fields = command.split("|")
        name = fields[0]
        command = fields[1]
        observation[tag]["name"] = name
        observation[tag]["command"] = command
        observation[tag]["duration"] = self.execute_observation_element_parameters(path, affinity, command, observation_id)

        #influx_help.normalize_tag(self, observation_id, len(commands)) ##Here, observation_id will be a list
        #observation["report"] = observation_standard.main(self, observation)
        self.update_twin_document__add_observation(observation)
        #return time, observation_id
        return observation_id
######################################################################################################################################################


def resolve_test(my_superTwin, threads):

    print("#############################################################################")
    print("##Threads: ", threads)
    compact_16 = utils.prepare_bind(my_superTwin, threads, "compact", -1)
    balanced_16 = utils.prepare_bind(my_superTwin, threads, "balanced", -1)
    compact_numa_16 = utils.prepare_bind(my_superTwin, threads, "compact numa", -1)
    balanced_numa_16 = utils.prepare_bind(my_superTwin, threads, "balanced numa", -1)

    print("##")
    print("compact bind:", compact_16)
    print("compact resolve:", utils.resolve_bind(my_superTwin, compact_16))
    print("##")
    print("balanced bind:", balanced_16)
    print("balanced resolve:", utils.resolve_bind(my_superTwin, balanced_16))
    print("##")
    print("compact numa bind:", compact_numa_16)
    print("compact numa resolve: ", utils.resolve_bind(my_superTwin, compact_numa_16))
    print("##")
    print("balanced numa bind:", balanced_numa_16)
    print("balanced numa resolve: ", utils.resolve_bind(my_superTwin, balanced_numa_16))
    print("#############################################################################")
    
    
if __name__ == "__main__":

    #user_name = "ftasyaran"
    
    args = sys.argv
    if(len(args) == 1):
        my_superTwin = SuperTwin() ##From scratch
    else:
        addr = args[1]
        my_superTwin = SuperTwin(addr) ##Re-construct


    affinity = utils.prepare_bind(my_superTwin, 1, "compact", -1)
    commands = ["rcm|./rcm 1138_bus.mtx","degree|./degree 1138_bus.mtx","random|./random 1138_bus.mtx","none|./none 1138_bus.mtx"]
    my_superTwin.execute_observation_batch_parameters("/home/fatih/SparseBaseOrderExample", affinity, commands)
    #my_superTwin.add_stream_benchmark()
    #my_superTwin.add_hpcg_benchmark(HPCG_PARAM) 
    #my_superTwin.add_adcarm_benchmark()
    #my_superTwin.generate_roofline_dashboard()

    
    #resolve_test(my_superTwin, 1)
    #resolve_test(my_superTwin, 2)
    #resolve_test(my_superTwin, 4)
    #resolve_test(my_superTwin, 6)
    #resolve_test(my_superTwin, 8)
    #resolve_test(my_superTwin, 64)
    #resolve_test(my_superTwin, 80)

    #my_superTwin.update_twin_document__assert_new_monitor_pid()

    '''
    empty_dash = mdm.generate_empty_dash(my_superTwin)
    empty_dash = mdm.name_panel(my_superTwin, empty_dash)
    empty_dash = mdm.freq_clock_panel(my_superTwin, 5, 5, 5, 5, [2,6,7,22,23,65], empty_dash)
    empty_dash = mdm.stat_panel(my_superTwin, 5, 5, 5, 5, "continuous-GrYlRd", "kernel_pernode_cpu_idle", empty_dash)
    url = mdm.upload_dashboard(my_superTwin, empty_dash)
    print("url here:", url)
    '''

    #sampling.get_pcp_pids(my_superTwin)


    
