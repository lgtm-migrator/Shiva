import time, os
import torch
import numpy as np
from mpi4py import MPI

from shiva.core.admin import Admin

from shiva.metalearners.CommMultiLearnerMetaLearnerServer import get_meta_stub
from shiva.helpers.launch_servers_helper import start_learner_server
from shiva.envs.CommMultiEnvironmentServer import get_menv_stub

from shiva.helpers.config_handler import load_class

class CommMultiAgentLearner():
    def __init__(self, id):
        self.id = id
        self.address = ':'.join(['localhost', '50000'])
        self.agents = []

    def launch(self, meta_address):
        self.meta_stub = get_meta_stub(meta_address)
        self.debug("gRPC Request Meta for Configs")
        self.configs = self.meta_stub.get_configs()
        self.debug("gRPC Received Config from Meta")

        # self.meta_comm = MPI.Comm.Get_parent()
        # self.id = self.meta_comm.Get_rank()
        # self.configs = {}
        # self.meta_comm.bcast(self.configs, root=0) # receive configs
        # self.debug("MPI Received Config from Meta")

        {setattr(self, k, v) for k, v in self.configs['Learner'].items()}
        Admin.init(self.configs['Admin'])
        Admin.add_learner_profile(self, function_only=True)

        # initiate server
        self.comm_learner_server, self.learner_tags = start_learner_server(self.address, maxprocs=1)
        time.sleep(1)
        # self.debug("MPI send Configs to LearnerServer")
        self.comm_learner_server.send(self.configs, 0, self.learner_tags.configs)

        self.debug("gRPC send LearnerSpecs to MetaServer")
        self.meta_stub.send_learner_specs(self._get_learner_specs())

        # receive multienv specs
        self.menv_specs = self.comm_learner_server.recv(None, 0, self.learner_tags.menv_specs)
        self.menv_stub = get_menv_stub(self.menv_specs['address'])

        self.num_agents = 1 # this is given by the environment or by the metalearner

        self.debug("Ready to instantiate algorithm, buffer and agents!")

        self.alg = self.create_algorithm(self.menv_specs['env_specs']['observation_space'], self.menv_specs['env_specs']['action_space'])
        self.buffer = self.create_buffer()

        self.agents = [self.alg.create_agent(ix) for ix in range(self.num_agents)]
        self.agents[0].step_count = 0

        Admin.checkpoint(self, checkpoint_num=0, function_only=True)

        self.debug("Algorithm, Buffer and Agent created")
        self.menv_stub.send_learner_specs(self._get_learner_specs())
        self.debug("Learner Specs sent to MultiEnv")

        self.run()

    def run(self):
        self.step_count = 0
        self.done_count = 0
        trajectory = None
        while True:
            # self.debug("Waiting trajectory...")

            # try receiving as tensor later
            # trajectory_length = self.comm_learner_server.recv(None, 0, self.learner_tags.trajectories_length)
            # self.debug(trajectory_length)
            # trajectory = np.empty(trajectory_length)
            # self.comm_learner_server.Recv([trajectory, MPI.FLOAT], 0, self.learner_tags.trajectories) # blocking receive
            # self.debug(trajectory.shape)

            trajectory = self.comm_learner_server.recv(None, 0, self.learner_tags.trajectories) # blocking communication

            self.done_count += 1
            for observation, action, reward, next_observation, done in trajectory:
                exp = list(map(torch.clone, (torch.tensor(observation), torch.tensor(action), torch.tensor(reward), torch.tensor(next_observation), torch.tensor([done], dtype=torch.bool))))
                self.buffer.push(exp)
                self.step_count += 1
            if True:
            # if self.step_count > self.configs['Agent']['exploration_steps'] and self.done_count % self.save_checkpoint_episodes == 0:
                self.alg.update(self.agents[0], self.buffer, self.step_count)
                self.agents[0].step_count = self.step_count
                self.debug("Sending Agent Step # {}".format(self.step_count))
                Admin.checkpoint(self, checkpoint_num=self.done_count, function_only=True)
                self._collect_metrics()
                self.menv_stub.send_new_agents(Admin.get_last_checkpoint(self))
            # self.debug("Sent new agents")

    def create_algorithm(self, observation_space, action_space):
        algorithm_class = load_class('shiva.algorithms', self.configs['Algorithm']['type'])
        return algorithm_class(self.menv_specs['env_specs']['observation_space'], self.menv_specs['env_specs']['action_space'], self.configs)

    def create_buffer(self):
        # SimpleBuffer
        # buffer_class = load_class('shiva.buffers', self.configs['Buffer']['type'])
        # return buffer_class(self.configs['Buffer']['batch_size'], self.configs['Buffer']['capacity'])
        # TensorBuffer
        buffer_class = load_class('shiva.buffers', self.configs['Buffer']['type'])
        return buffer_class(self.configs['Buffer']['capacity'], self.configs['Buffer']['batch_size'], self.num_agents, self.menv_specs['env_specs']['observation_space'], self.menv_specs['env_specs']['action_space']['acs_space'])

    def _collect_metrics(self):
        metrics = self.alg.get_metrics(True)# + self.env.get_metrics(episodic)
        for metric_name, y_val in metrics:
            Admin.add_summary_writer(self, self.agents[0], metric_name, y_val, self.step_count)

    def _get_learner_specs(self):
        return {
            'id': self.id,
            'algorithm': self.configs['Algorithm']['type'],
            'address': self.address,
            'load_path': Admin.get_last_checkpoint(self),
            'num_agents': self.num_agents if hasattr(self, 'num_agents') else 0
        }


    def __getstate__(self):
        d = dict(self.__dict__)
        attributes_to_ignore = ['meta_stub', 'comm_learner_server', 'menv_stub', 'learner_tags']
        for a in attributes_to_ignore:
            try:
                del d[a]
            except:
                pass
        return d

    def debug(self, msg):
        print("PID {} Learner\t\t{}".format(os.getpid(), msg))

def collect_forever(minibuffer, queue, ix, num_agents, acs_dim, obs_dim, metrics):
    '''
        Separate process who collects the data from the server queue and puts it into a temporary minibuffer
    '''
    while True: # maybe a lock here
        pass
        # trajectory = from_TrajectoryProto_2_trajectory( queue.pop() )
        # collect metrics
        # metrics['rewards'] =
        # push to minibuffer