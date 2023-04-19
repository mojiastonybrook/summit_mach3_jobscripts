import os
import sys

def job_config():
    ''' 
    configuration of resource sets on summit and corresponding jobs
    '''
    try:
        submission_dir=input("where to generate the submission and run scripts: ")
    except:
        print("no valid inputs, using default directory")
        submission_dir="~/job_scripts/job_1"
    if len(submission_dir)==0:
        print("no inputs, using default directory")
        submission_dir="/ccs/home/mojia/job_scripts/job_1"

    try:
        storage_dir=input("where to store MaCh3 outputs: ")
    except:
        print("no valid inputs, using default directory")
        storage_dir="/gpfs/alpine/phy171/scratch/mojia/MaCh3_results/JointAtmFit"
    if len(storage_dir)==0:
        print("no inputs, using default directory")
        storage_dir="/gpfs/alpine/phy171/scratch/mojia/MaCh3_results/JointAtmFit"

    try:
        n_jobs=int(input("number of jobs(1,2,3 or 4): "))
    except:
        print("invalid inputs, using default 1")
        n_jobs=1
    if n_jobs < 1 or n_jobs > 4:
        raise Exception("number of jobs should be within 1-4. ")

    try:
        n_iter=int(input("number of iterations: "))
    except:
        print("invalid inputs")

    try:
        node_per_job=int(input("number of nodes in one job: "))
    except:
        print("invalid inputs, using default 1")
        node_per_job = 1

    try:
        chain_per_rs=int(input("number of chains within one resource set: "))
    except:
        print("invalid inputs, using default 2")
        chain_per_rs = 2
    try:
        n_step=int(input("number of steps in one chain: "))
    except:
        print("invalid inputs, using default: 10000")
        n_step=10000
    try: 
        w_time=input("wall time [hh:mm]: ")
    except:
        print("invalid inputs.")
    if len(w_time)==0:
        print("no inputs, using default: 24:00")
        w_time="24:00"

    try:
        use_nvme=int(input("use nvme or not? [1 for yes, 0 for no]: "))
    except:
        print("invalid inputs, not using nvme")
        use_nvme=0

    return {"sub_dir":submission_dir,
            "out_dir":storage_dir,
            "job_num":n_jobs,
            "iter_num":n_iter,
            "node_per_job":node_per_job,
            "chain_per_rs":chain_per_rs,
            "num_step":n_step,
            "wall_time":w_time,
            "use_bb":use_nvme
            }

def replaceText(File,oldText,newText):
    with open(File) as f:
        newText=f.read().replace(oldText,newText)
    with open(File,"w") as f:
        f.write(newText)

if __name__=="__main__":

    config=job_config()
    print(config)
    
    work_dir=os.getcwd()

    if (os.path.exists(config["sub_dir"])==False):
        os.system("mkdir "+config["sub_dir"])
        os.chdir(config["sub_dir"])
    else:
        os.chdir(config["sub_dir"])

    #
    for itr in range(config["iter_num"]):

        #generate submission/job lsf scripts
        submission_scripts=[]
        run_scripts_tot=[]
        num_rs_job = 6*config["node_per_job"]
        for i in range(config["job_num"]):
            submission_scripts.append("submit_mach3_JointAtmFit_{0}_iter_{1}.lsf".format(i,itr))
            run_scripts_job=[]
            start_id = i * num_rs_job * config["chain_per_rs"]
            for j in range(num_rs_job):
                run_scripts_job.append("run_mach3_JointAtmFit_{0}_{1}_iter_{2}.sh".format(start_id,start_id+config["chain_per_rs"]-1,itr))
                start_id = start_id+config["chain_per_rs"]
            run_scripts_tot.append(run_scripts_job)

        print(submission_scripts)
        print(run_scripts_tot)

        for i,job_script in enumerate(submission_scripts):
            os.system("cp "+work_dir+"/submit_mach3_TEMPLATE.lsf "+job_script)
            replaceText(job_script,"WALLTIME",config["wall_time"])
            replaceText(job_script,"NNODE",str(config["node_per_job"]))
            replaceText(job_script,"ID",str(i))
            for run_script in run_scripts_tot[i]:
                sed_command="sed -i -e '/^#RUNSCRIPTS/a jsrun -n1 -a1 -g1 -c7 -bpacked:7 -dpacked "+config["sub_dir"]+"/"+run_script+" &' "+job_script
                os.system(sed_command)

        #generate run scripts
        for i,run_scripts_job in enumerate(run_scripts_tot):
            start_id = i * num_rs_job * config["chain_per_rs"]

            for j,run_script in enumerate(run_scripts_job):
                os.system("cp "+work_dir+"/run_mach3_TEMPLATE.sh "+run_script)
                replaceText(run_script,"OUTPUTDIR",config["out_dir"]+"/job_1")
                replaceText(run_script,"THREADSNUM",str(int(28/config["chain_per_rs"])))

                if(config["use_bb"]):
                    sed_command="sed -i -e '/^#NVME/a export MACH3_MC=/mnt/bb/mojia/P6MC' "+run_script 
                    os.system(sed_command)
                    sed_command="sed -i -e '/^#NVME/a export MACH3_DATA=/mnt/bb/mojia/P6Data' "+run_script 
                    os.system(sed_command)
                    sed_command="sed -i -e '/^#NVME/a unset MACH3_DATA' "+run_script 
                    os.system(sed_command)
                    sed_command="sed -i -e '/^#NVME/a unset MACH3_MC' "+run_script 
                    os.system(sed_command)

                chain_ids= [start_id + j * config["chain_per_rs"]+k for k in range(config["chain_per_rs"])]
                for chain_id in chain_ids:
                    sed_command="sed -i -e '/^#CHAINS/a background_pid_"+str(chain_id)+"=$!' "+run_script
                    os.system(sed_command)
                    sed_command="sed -i -e '/^#CHAINS/a ./AtmJointFit_Bin/JointAtmFit ${storage_dir}/chain_"+str(chain_id)+"/config/AtmConfig_Iter_"+str(itr)+".cfg &> ${storage_dir}/chain_"+str(chain_id)+"/output/jointAtmFit_Iter_"+str(itr)+".log &' "+run_script
                    os.system(sed_command)
                
                    sed_command="sed -i -e '/^#WAIT/a wait ${background_pid_"+str(chain_id)+"}' "+run_script
                    os.system(sed_command)

    #generate output directories and configuration files
    if (os.path.exists(config["out_dir"]+"/job_1")==False):
        os.system("mkdir "+config["out_dir"]+"/job_1")
        os.chdir(config["out_dir"]+"/job_1")
    else:
        os.chdir(config["out_dir"]+"/job_1")

    if (os.path.exists("./SampleConfigs")==False):
        os.system("cp -r "+work_dir+"/SampleConfigs .")

    chains=[i for i in range(config["job_num"]*num_rs_job*config["chain_per_rs"])]
    for cid in chains:
        os.system("mkdir "+"chain_"+str(cid))
        os.chdir("chain_"+str(cid))
        os.system("mkdir output")
        os.system("mkdir config")

        os.chdir("config")
        for itr in range(config["iter_num"]):
            if itr == 0:
                startFromFile=False
            else:
                startFromFile=True

            os.system("cp "+work_dir+"/AtmConfig.cfg AtmConfig_Iter_"+str(itr)+".cfg")
            #change configs
            sed_command="sed -i 's|NSTEPS.*|NSTEPS = "+str(config["num_step"])+"|' AtmConfig_Iter_"+str(itr)+".cfg"
            os.system(sed_command)    
            sed_command="sed -i 's|OUTPUTNAME.*|OUTPUTNAME = \""+config["out_dir"]+"/job_1/chain_"+str(cid)+"/output/MaCh3-Atmospherics-MCMC_Iter_"+str(itr)+".root\"|' AtmConfig_Iter_"+str(itr)+".cfg"
            os.system(sed_command)
            if config["use_bb"]:
                sed_command="sed -i 's|ATMCONFIGDIR.*|ATMCONFIGDIR = \""+config["out_dir"]+"/job_1/SampleConfigs/SampleConfigs_bb\"|' AtmConfig_Iter_"+str(itr)+".cfg"
                os.system(sed_command)
                sed_command="sed -i 's|BEAMCONFIGDIR.*|BEAMCONFIGDIR = \""+config["out_dir"]+"/job_1/SampleConfigs/SampleConfigs_bb\"|' AtmConfig_Iter_"+str(itr)+".cfg"
                os.system(sed_command)
            else: 
                sed_command="sed -i 's|ATMCONFIGDIR.*|ATMCONFIGDIR = \""+config["out_dir"]+"/job_1/SampleConfigs\"|' AtmConfig_Iter_"+str(itr)+".cfg"
                os.system(sed_command)
                sed_command="sed -i 's|BEAMCONFIGDIR.*|BEAMCONFIGDIR = \""+config["out_dir"]+"/job_1/SampleConfigs\"|' AtmConfig_Iter_"+str(itr)+".cfg"
                os.system(sed_command)

            if startFromFile:
                sed_command="sed -i 's|STARTFROMPOS.*|STARTFROMPOS = true|' AtmConfig_Iter_"+str(itr)+".cfg"
                os.system(sed_command)
                sed_command="sed -i 's|POSFILES.*|POSFILES = \""+config["out_dir"]+"/job_1/chain_"+str(cid)+"/output/MaCh3-Atmospherics-MCMC_Iter_"+str(itr-1)+".root\"|' AtmConfig_Iter_"+str(itr)+".cfg"
                os.system(sed_command)

        os.chdir(config["out_dir"]+"/job_1")

    print("DONE!")
