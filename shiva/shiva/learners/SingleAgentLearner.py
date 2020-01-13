import torch
import copy
import random
import numpy as np

from shiva.core.admin import Admin
from shiva.learners.Learner import Learner
from shiva.helpers.config_handler import load_class

class SingleAgentLearner(Learner):
    def __init__(self, learner_id, config):
        super(SingleAgentLearner ,self).__init__(learner_id, config)

    def run(self, train=True):
        self.step_count_per_run = 0
        while not self.env.finished(self.episodes):
            self.env.reset()
            while not self.env.is_done():
                self.step()
                # self.alg.update(self.agent, self.buffer, self.env.step_count)
                self.collect_metrics()
                if self.is_multi_process_cutoff(): return None # PBT Cutoff
                else: continue
            self.alg.update(self.agent, self.buffer, self.env.step_count)
            self.collect_metrics()
            self.alg.update(self.agent, self.buffer, self.env.step_count, episodic=True)
            self.collect_metrics(episodic=True)
            self.checkpoint()
            print('Episode {} complete on {} steps!\tEpisodic reward: {} '.format(self.env.done_count, self.env.steps_per_episode, self.env.reward_per_episode))
        self.env.close()

    def step(self):
        observation = self.env.get_observation()

        """Temporary fix for Unity as it receives multiple observations"""
        if len(observation.shape) > 1 and self.env.env_name != 'RoboCup':
            action = [self.agent.get_action(obs, self.env.step_count) for obs in observation]
            next_observation, reward, done, more_data = self.env.step(action)
            z = copy.deepcopy([
                torch.tensor(observation), 
                torch.tensor(action), 
                torch.tensor(reward).reshape(self.env.num_instance,1), 
                torch.tensor(next_observation), 
                torch.tensor(done).reshape(self.env.num_instance,1)
            ])
            self.buffer.push(z)
        else:
            action = self.agent.get_action(observation, self.env.step_count)
            next_observation, reward, done, more_data = self.env.step(action)
            exp = copy.deepcopy([
                torch.tensor(observation), 
                torch.tensor(more_data['action']), 
                torch.tensor(reward), 
                torch.tensor(next_observation), 
                torch.tensor(int(done))
            ])
            self.buffer.push(copy.deepcopy(exp))


    def is_multi_process_cutoff(self):
        ''' FOR MULTIPROCESS PBT PURPOSES '''
        self.step_count = self.env.step_count
        self.ep_count = self.env.done_count
        try:
            if self.multi and self.step_count_per_run >= self.updates_per_iteration:
                return True
        except:
            pass
        self.step_count_per_run += 1
        return False

    def create_algorithm(self):
        algorithm_class = load_class('shiva.algorithms', self.configs['Algorithm']['type'])
        return algorithm_class(self.env.get_observation_space(), self.env.get_action_space(), [self.configs['Algorithm'], self.configs['Agent'], self.configs['Network']])

    def create_buffer(self, obs_dim, ac_dim):
        buffer = load_class('shiva.buffers', self.configs['Buffer']['type'])
        return buffer(self.configs['Buffer']['capacity'], self.configs['Buffer']['batch_size'], 1, obs_dim, ac_dim)

    def launch(self):
        self.env = self.create_environment()
        if hasattr(self, 'manual_play') and self.manual_play:
            '''
                Only for RoboCup!
                Maybe for Unity at some point?????
            '''
            from shiva.envs.RoboCupEnvironment import HumanPlayerInterface
            self.HPI = HumanPlayerInterface()
        self.alg = self.create_algorithm()
        if self.load_agents:
            self.agent = Admin._load_agent(self.load_agents)
            self.buffer = Admin._load_buffer(self.load_agents)
        else:
            self.agent = self.alg.create_agent(self.get_new_agent_id())
            if self.using_buffer:
                # self.buffer = self.create_buffer()
                self.buffer = self.create_buffer(self.env.get_observation_space(), self.env.get_action_space()['acs_space'])

        print('Launch Successful.')